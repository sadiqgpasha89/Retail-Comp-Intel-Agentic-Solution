"""Bi-Encoder Candidate Retrieval Service: surfaces top-k nearest internal products from vector space."""

from typing import List, Tuple

from retail_intel.core.logging import get_logger
from retail_intel.data_engineering.feature_store.feature_store import FeatureStore
from retail_intel.data_engineering.normalization.normalization_pipeline import NormalizedProductRecord

logger = get_logger("datascience.tier2_ml.bi_encoder")


class BiEncoderCandidateRetriever:
    """Surfaces top-k candidate matches from high-dimensional vector space."""

    def __init__(self, feature_store: FeatureStore):
        self.feature_store = feature_store

    def retrieve_candidates(
        self, competitor_record: NormalizedProductRecord, top_k: int = 5
    ) -> List[Tuple[str, float, NormalizedProductRecord]]:
        """Retrieves top-k candidates, enforcing high-level category taxonomy compatibility."""
        candidates = self.feature_store.find_nearest_candidates(competitor_record, top_k=top_k * 2)

        filtered: List[Tuple[str, float, NormalizedProductRecord]] = []
        for sku, sim, internal_rec in candidates:
            # Enforce hard category compatibility (e.g. Footwear cannot match Television)
            if competitor_record.gpc_category_code != "99999999" and internal_rec.gpc_category_code != "99999999":
                if competitor_record.gpc_category_code[:4] != internal_rec.gpc_category_code[:4]:
                    continue  # Incompatible high-level taxonomy branch
            filtered.append((sku, sim, internal_rec))
            if len(filtered) >= top_k:
                break

        return filtered
