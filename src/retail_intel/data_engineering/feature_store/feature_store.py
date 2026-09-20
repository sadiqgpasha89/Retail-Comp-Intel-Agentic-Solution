"""Multimodal Feature Store & Vector Embeddings: computes E_product = alpha*E_text + beta*E_vis + gamma*E_attr."""

import hashlib
import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel

from retail_intel.core.config import settings
from retail_intel.core.logging import get_logger
from retail_intel.core.providers import BaseVectorSearchProvider, get_vector_provider
from retail_intel.data_engineering.normalization.normalization_pipeline import NormalizedProductRecord

logger = get_logger("data_engineering.feature_store")


class MultimodalVector(BaseModel):
    """Encapsulates component representation vectors and combined multimodal embedding."""
    sku: str
    dimension: int
    alpha: float
    beta: float
    gamma: float
    embedding: List[float]


class FeatureStore:
    """Enterprise Multimodal Feature Store and ANN Vector Indexer."""

    def __init__(self, vector_search: Optional[BaseVectorSearchProvider] = None):
        self.vector_search = vector_search or get_vector_provider()
        self.dimension = settings.vector_dimension
        self.cached_features: Dict[str, NormalizedProductRecord] = {}

    def get_category_weights(self, gpc_name: str) -> Tuple[float, float, float]:
        """Resolves category-calibrated weights: alpha, beta, gamma."""
        name_lower = gpc_name.lower()
        if "apparel" in name_lower or "footwear" in name_lower:
            w = settings.category_weights["apparel"]
        elif "audio" in name_lower or "television" in name_lower or "electronic" in name_lower:
            w = settings.category_weights["electronics"]
        elif "grocery" in name_lower or "coffee" in name_lower:
            w = settings.category_weights["grocery"]
        elif "tool" in name_lower or "drill" in name_lower:
            w = settings.category_weights["hardware"]
        elif "furniture" in name_lower or "seating" in name_lower:
            w = settings.category_weights["furniture"]
        else:
            return (
                settings.default_weight_textual,
                settings.default_weight_visual,
                settings.default_weight_attributes,
            )
        return (w["alpha"], w["beta"], w["gamma"])

    def _encode_text(self, text: str) -> np.ndarray:
        """Deterministic dense projection for text representation."""
        vec = np.zeros(self.dimension, dtype=np.float32)
        words = re.findall(r"\w+", text.lower())
        for i, word in enumerate(words):
            h = int(hashlib.sha256(word.encode("utf-8")).hexdigest()[:8], 16)
            idx = h % self.dimension
            weight = 1.0 / (1.0 + np.log1p(i))
            vec[idx] += weight
        norm = np.linalg.norm(vec)
        return vec / (norm + 1e-9)

    def _encode_visual(self, image_url: str, title: str) -> np.ndarray:
        """Color, aesthetic, and visual feature embedding representation."""
        vec = np.zeros(self.dimension, dtype=np.float32)
        seed_str = f"{image_url}_{title}"
        h_bytes = hashlib.md5(seed_str.encode("utf-8")).digest()
        for idx in range(self.dimension):
            byte_val = h_bytes[idx % len(h_bytes)]
            vec[idx] = (byte_val / 128.0) - 1.0
        norm = np.linalg.norm(vec)
        return vec / (norm + 1e-9)

    def _encode_attributes(self, attrs: Dict[str, Any], pack_size: int, price: float) -> np.ndarray:
        """Encodes structured numerical and categorical attributes."""
        vec = np.zeros(self.dimension, dtype=np.float32)
        vec[0] = np.tanh(price / 500.0)
        vec[1] = np.tanh(pack_size / 10.0)
        for i, (k, v) in enumerate(attrs.items()):
            pos = (i + 2) % self.dimension
            h = int(hashlib.md5(f"{k}:{v}".encode("utf-8")).hexdigest()[:6], 16)
            vec[pos] += (h % 100) / 100.0 - 0.5
        norm = np.linalg.norm(vec)
        return vec / (norm + 1e-9)

    def compute_multimodal_vector(self, record: NormalizedProductRecord) -> MultimodalVector:
        """Computes: E_product = alpha*E_text + beta*E_vis + gamma*E_attr."""
        alpha, beta, gamma = self.get_category_weights(record.gpc_category_name)

        combined_text = f"{record.brand_clean} {record.title_clean} {record.gpc_category_name}"
        e_text = self._encode_text(combined_text)
        e_vis = self._encode_visual(record.image_url, record.title_clean)
        e_attr = self._encode_attributes(record.normalized_attributes, record.pack_size, record.effective_price)

        e_product = (alpha * e_text) + (beta * e_vis) + (gamma * e_attr)
        norm = np.linalg.norm(e_product)
        if norm > 0:
            e_product = e_product / norm

        return MultimodalVector(
            sku=record.sku,
            dimension=self.dimension,
            alpha=alpha,
            beta=beta,
            gamma=gamma,
            embedding=e_product.tolist(),
        )

    def index_internal_catalog(self, internal_records: List[NormalizedProductRecord]) -> int:
        """Indexes internal products into the vector search provider (HNSW/ANN)."""
        self.cached_features.clear()
        
        ids: List[str] = []
        vectors: List[List[float]] = []
        metadata: List[Dict[str, Any]] = []

        for rec in internal_records:
            self.cached_features[rec.sku] = rec
            mv = self.compute_multimodal_vector(rec)
            ids.append(rec.sku)
            vectors.append(mv.embedding)
            metadata.append(rec.model_dump())

        vec_array = np.array(vectors, dtype=np.float32)
        self.vector_search.index_vectors(ids, vec_array, metadata)
        logger.info("Internal catalog vector index populated", count=len(ids))
        return len(ids)

    def find_nearest_candidates(
        self, competitor_record: NormalizedProductRecord, top_k: int = 5
    ) -> List[Tuple[str, float, NormalizedProductRecord]]:
        """Surfaces top-k candidate internal products using ANN vector search."""
        mv = self.compute_multimodal_vector(competitor_record)
        q_vec = np.array(mv.embedding, dtype=np.float32)
        raw_matches = self.vector_search.search(q_vec, top_k=top_k)

        results = []
        for sku, score, meta in raw_matches:
            internal_rec = self.cached_features.get(sku)
            if not internal_rec:
                internal_rec = NormalizedProductRecord(**meta)
            results.append((sku, score, internal_rec))
        return results
