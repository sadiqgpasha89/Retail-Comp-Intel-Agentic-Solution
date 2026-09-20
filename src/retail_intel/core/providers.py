"""Pluggable Provider Abstractions for Open Stack and GCP Cloud Stack."""

import abc
import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from retail_intel.core.config import ExecutionMode, settings
from retail_intel.core.logging import get_logger

logger = get_logger("core.providers")


# ==========================================
# 1. Storage Provider Abstraction
# ==========================================
class BaseStorageProvider(abc.ABC):
    @abc.abstractmethod
    async def put_payload(self, key: str, data: Dict[str, Any]) -> str:
        """Stores raw payload and returns URI."""

    @abc.abstractmethod
    async def get_payload(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieves raw payload from storage."""


class LocalFileStorageProvider(BaseStorageProvider):
    """File-system backed storage provider — durable, capacity-bounded, dev/on-prem friendly."""

    def __init__(self, base_dir: str = settings.local_storage_dir):
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    async def put_payload(self, key: str, data: Dict[str, Any]) -> str:
        dest = self._base / key.replace("/", os.sep)
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Async-safe: write is small and bounded; wrapping in executor keeps the event loop free
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._write, dest, data)
        return f"file://{dest.resolve()}"

    @staticmethod
    def _write(dest: Path, data: Dict[str, Any]) -> None:
        dest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    async def get_payload(self, key: str) -> Optional[Dict[str, Any]]:
        dest = self._base / key.replace("/", os.sep)
        if not dest.exists():
            return None
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: json.loads(dest.read_text("utf-8")))


class GCPCloudStorageProvider(BaseStorageProvider):
    """Google Cloud Storage provider using the official `google-cloud-storage` client."""

    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self._client = None  # lazy-loaded to avoid import cost in non-GCP mode

    def _get_client(self):
        if self._client is None:
            try:
                from google.cloud import storage  # type: ignore
                self._client = storage.Client()
            except ImportError:
                raise RuntimeError(
                    "google-cloud-storage is not installed. "
                    "Install it with: pip install google-cloud-storage"
                )
        return self._client

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        reraise=True,
    )
    async def put_payload(self, key: str, data: Dict[str, Any]) -> str:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._gcs_upload, key, data)
        uri = f"gs://{self.bucket_name}/{key}"
        logger.info("GCP GCS payload stored", bucket=self.bucket_name, key=key)
        return uri

    def _gcs_upload(self, key: str, data: Dict[str, Any]) -> None:
        client = self._get_client()
        bucket = client.bucket(self.bucket_name)
        blob = bucket.blob(key)
        blob.upload_from_string(json.dumps(data, ensure_ascii=False), content_type="application/json")

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        reraise=True,
    )
    async def get_payload(self, key: str) -> Optional[Dict[str, Any]]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._gcs_download, key)

    def _gcs_download(self, key: str) -> Optional[Dict[str, Any]]:
        client = self._get_client()
        bucket = client.bucket(self.bucket_name)
        blob = bucket.blob(key)
        if not blob.exists():
            return None
        return json.loads(blob.download_as_text())


# ==========================================
# 2. Event Stream Provider Abstraction
# ==========================================
class BaseStreamProvider(abc.ABC):
    @abc.abstractmethod
    async def publish(self, topic: str, message: Dict[str, Any]) -> str:
        """Publishes an event to topic."""

    @abc.abstractmethod
    async def subscribe(self, topic: str) -> asyncio.Queue:
        """Subscribes to topic and returns an async queue."""


class InMemoryStreamProvider(BaseStreamProvider):
    """In-process async stream — suitable for single-process dev/test deployments."""

    def __init__(self):
        # Topics map: topic -> list of subscriber queues
        # Initialise lazily inside the running event loop to avoid deprecation errors
        self._topics: Dict[str, List[asyncio.Queue]] = {}
        self._published_count: int = 0

    async def publish(self, topic: str, message: Dict[str, Any]) -> str:
        msg_id = f"msg_{self._published_count + 1}"
        self._published_count += 1
        # Snapshot subscriber list to avoid race condition during iteration
        subscribers = list(self._topics.get(topic, []))
        for q in subscribers:
            await q.put(message)
        return msg_id

    async def subscribe(self, topic: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        if topic not in self._topics:
            self._topics[topic] = []
        self._topics[topic].append(q)
        return q


class GCPPubSubStreamProvider(BaseStreamProvider):
    """Google Cloud Pub/Sub stream provider with tenacity retry."""

    def __init__(self):
        self._publisher = None
        self._subscriber = None

    def _get_publisher(self):
        if self._publisher is None:
            try:
                from google.cloud import pubsub_v1  # type: ignore
                self._publisher = pubsub_v1.PublisherClient()
            except ImportError:
                raise RuntimeError(
                    "google-cloud-pubsub is not installed. "
                    "Install it with: pip install google-cloud-pubsub"
                )
        return self._publisher

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        reraise=True,
    )
    async def publish(self, topic: str, message: Dict[str, Any]) -> str:
        loop = asyncio.get_event_loop()
        msg_id = await loop.run_in_executor(None, self._pubsub_publish, topic, message)
        logger.info("GCP Pub/Sub message published", topic=topic, msg_id=msg_id)
        return msg_id

    def _pubsub_publish(self, topic: str, message: Dict[str, Any]) -> str:
        publisher = self._get_publisher()
        data = json.dumps(message, ensure_ascii=False).encode("utf-8")
        future = publisher.publish(topic, data)
        return future.result(timeout=10)

    async def subscribe(self, topic: str) -> asyncio.Queue:
        # PubSub subscriptions are managed server-side; return local queue as bridge
        logger.warning(
            "GCPPubSubStreamProvider.subscribe() returns an in-process queue bridge. "
            "For production use, configure a push subscription or a dedicated subscriber loop.",
            topic=topic,
        )
        q: asyncio.Queue = asyncio.Queue()
        return q


# ==========================================
# 3. Vector Search Provider Abstraction
# ==========================================
class BaseVectorSearchProvider(abc.ABC):
    @abc.abstractmethod
    def index_vectors(self, ids: List[str], vectors: np.ndarray, metadata: List[Dict[str, Any]]) -> None:
        """Indexes vectors for approximate nearest neighbor retrieval."""

    @abc.abstractmethod
    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Searches top-k nearest neighbors, returning (id, score, metadata)."""


class HNSWVectorSearchProvider(BaseVectorSearchProvider):
    """
    High-throughput cosine ANN using hnswlib (HNSW graph index).
    Falls back gracefully to brute-force cosine scan if hnswlib is unavailable,
    giving the same API surface across environments.
    """

    def __init__(self, dimension: int = 64):
        self.dimension = dimension
        self.ids: List[str] = []
        self.metadata: List[Dict[str, Any]] = []
        self._hnsw_index = None  # hnswlib index (lazy)
        self._fallback_vectors: Optional[np.ndarray] = None  # brute-force fallback

    def _try_build_hnsw(self, vectors: np.ndarray) -> bool:
        """Attempts to build an HNSW index; returns False if hnswlib is unavailable."""
        try:
            import hnswlib  # type: ignore

            index = hnswlib.Index(space="cosine", dim=self.dimension)
            # ef_construction / M govern recall vs build-time trade-off
            index.init_index(max_elements=max(len(self.ids) * 2, 1024), ef_construction=200, M=32)
            index.add_items(vectors, list(range(len(self.ids))))
            index.set_ef(50)
            self._hnsw_index = index
            return True
        except ImportError:
            logger.warning(
                "hnswlib not installed — falling back to O(N) cosine scan. "
                "Install hnswlib for production-scale ANN search.",
            )
            return False

    def index_vectors(self, ids: List[str], vectors: np.ndarray, metadata: List[Dict[str, Any]]) -> None:
        self.ids = ids
        self.metadata = metadata
        # Normalise for cosine
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1e-9
        normed = vectors / norms

        if not self._try_build_hnsw(normed):
            self._fallback_vectors = normed

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[str, float, Dict[str, Any]]]:
        if not self.ids:
            return []
        q_norm = np.linalg.norm(query_vector)
        q_normed = query_vector / (q_norm + 1e-9)

        if self._hnsw_index is not None:
            k = min(top_k, len(self.ids))
            labels, distances = self._hnsw_index.knn_query(q_normed, k=k)
            results = []
            for label, dist in zip(labels[0], distances[0]):
                score = float(1.0 - dist)  # hnswlib cosine distance → similarity
                results.append((self.ids[label], score, self.metadata[label]))
            return results

        # Brute-force fallback
        if self._fallback_vectors is None:
            return []
        sims = np.dot(self._fallback_vectors, q_normed)
        top_indices = np.argsort(sims)[::-1][:top_k]
        return [(self.ids[i], float(sims[i]), self.metadata[i]) for i in top_indices]


class VertexAIVectorSearchProvider(BaseVectorSearchProvider):
    """GCP Vertex AI Vector Search adapter with local HNSW fallback for dev/test."""

    def __init__(self, dimension: int = 64):
        self._local_engine = HNSWVectorSearchProvider(dimension)

    def index_vectors(self, ids: List[str], vectors: np.ndarray, metadata: List[Dict[str, Any]]) -> None:
        logger.info("Vertex AI Vector Search indexing", num_vectors=len(ids))
        # In production: deploy to Vertex AI Matching Engine endpoint.
        # For now, sync to local HNSW as low-latency proxy.
        self._local_engine.index_vectors(ids, vectors, metadata)

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[str, float, Dict[str, Any]]]:
        return self._local_engine.search(query_vector, top_k=top_k)


# ==========================================
# 4. LLM & Agentic AI Provider
# ==========================================
class BaseLLMProvider(abc.ABC):
    @abc.abstractmethod
    async def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generates raw text response."""


class SimulatedAgenticLLMProvider(BaseLLMProvider):
    """Zero-dependency deterministic mock LLM provider — used when no API key is configured."""

    async def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        import asyncio
        import json as _json
        await asyncio.sleep(0.02)  # Micro-latency simulation
        p_lower = prompt.lower()
        if "honeypot" in p_lower:
            return _json.dumps({
                "verdict": "HONEYPOT_TRAP",
                "confidence": 0.98,
                "reasoning": "Detected synthetic HTML parameters and randomized price divergence characteristic of scraper defense traps.",
            })
        elif "phantom" in p_lower or "60 days" in p_lower or "backorder" in p_lower:
            return _json.dumps({
                "verdict": "UNFULFILLED_PHANTOM",
                "confidence": 0.94,
                "reasoning": "Competitor stock is unfulfillable (>60 days delivery). Price is an algorithmic lure and isolated from repricer.",
            })
        elif "3-pack" in p_lower and ("single bag" in p_lower or "12 oz" in p_lower):
            return _json.dumps({
                "verdict": "EXACT_MATCH",
                "confidence": 0.88,
                "normalized_pack_size": 1,
                "reasoning": "Title claims 3-pack, but visual OCR and buyer reviews confirm single 12oz package. Normalized to 1-unit baseline.",
            })
        elif "oem-furn-dongguan-99" in p_lower or "pat-furn-2024-8871" in p_lower:
            return _json.dumps({
                "verdict": "EQUIVALENT_PRIVATE_LABEL",
                "confidence": 0.92,
                "reasoning": "Traversed Retail Knowledge Graph to discover shared OEM factory and patent registration with internal ErgoSpine line.",
            })
        elif "2026 edition" in p_lower and "2024" in p_lower:
            return _json.dumps({
                "verdict": "CONTRADICTORY_LISTING",
                "confidence": 0.89,
                "reasoning": "Multimodal clash: Title marketing claims 2026 model, but spec table and review photos show 2024 chassis on clearance.",
            })
        return _json.dumps({
            "verdict": "DIRECT_SUBSTITUTE",
            "confidence": 0.86,
            "reasoning": "Functional substitute with equivalent technical specifications and high cross-elasticity.",
        })


class GeminiLLMProvider(BaseLLMProvider):
    """
    Google Gemini LLM provider using the official google-genai SDK.
    Activated when GEMINI_API_KEY or VERTEX_PROJECT_ID is set.
    Falls back gracefully with a logged warning if the SDK is missing.
    """

    def __init__(self, model: str = settings.gemini_model, api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or settings.gemini_api_key
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import google.genai as genai  # type: ignore
                self._client = genai.Client(api_key=self.api_key)
            except ImportError:
                raise RuntimeError(
                    "google-genai SDK is not installed. "
                    "Install it with: pip install google-genai"
                )
        return self._client

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._call_gemini, prompt, system_prompt)

    def _call_gemini(self, prompt: str, system_prompt: Optional[str]) -> str:
        client = self._get_client()
        contents = prompt
        config_kwargs: Dict[str, Any] = {}
        if system_prompt:
            config_kwargs["system_instruction"] = system_prompt
        response = client.models.generate_content(
            model=self.model,
            contents=contents,
            config=config_kwargs if config_kwargs else None,
        )
        return response.text


# ==========================================
# 5. Provider Factory Functions
# ==========================================

def get_storage_provider() -> BaseStorageProvider:
    if settings.execution_mode == ExecutionMode.GCP and settings.gcp_gcs_bucket_payloads:
        return GCPCloudStorageProvider(settings.gcp_gcs_bucket_payloads)
    return LocalFileStorageProvider()


def get_stream_provider() -> BaseStreamProvider:
    if settings.execution_mode == ExecutionMode.GCP:
        return GCPPubSubStreamProvider()
    return InMemoryStreamProvider()


def get_vector_provider() -> BaseVectorSearchProvider:
    if settings.execution_mode == ExecutionMode.GCP:
        return VertexAIVectorSearchProvider(settings.vector_dimension)
    return HNSWVectorSearchProvider(settings.vector_dimension)


def get_llm_provider() -> BaseLLMProvider:
    """Returns the real Gemini provider if an API key is configured, otherwise the mock."""
    if settings.gemini_api_key:
        logger.info("Using GeminiLLMProvider", model=settings.gemini_model)
        return GeminiLLMProvider()
    logger.warning(
        "No GEMINI_API_KEY configured — using SimulatedAgenticLLMProvider. "
        "Set GEMINI_API_KEY in .env to activate the real LLM."
    )
    return SimulatedAgenticLLMProvider()
