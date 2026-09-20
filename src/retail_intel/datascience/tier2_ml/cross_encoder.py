"""Cross-Encoder Re-Ranking Engine and Tri-Tier Decision Split."""

import re
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel

from retail_intel.core.config import settings
from retail_intel.core.logging import get_logger
from retail_intel.data_engineering.normalization.normalization_pipeline import NormalizedProductRecord

logger = get_logger("datascience.tier2_ml.cross_encoder")


class DecisionSplit(str, Enum):
    AUTO_COMMIT = "AUTO_COMMIT"                 # tau >= 0.92
    AGENTIC_ESCALATION = "AGENTIC_ESCALATION"   # 0.65 <= tau < 0.92
    REJECT = "REJECT"                           # tau < 0.65


class ScoredCandidatePair(BaseModel):
    competitor_sku: str
    internal_sku: str
    score: float
    decision: DecisionSplit
    brand_match: bool
    category_match: bool
    price_ratio: float
    feature_compatibility: Dict[str, float]


class CrossEncoderScorer:
    """Pairwise neural cross-encoder re-ranking simulator calculating semantic score tau."""

    def __init__(
        self,
        auto_commit_threshold: float = settings.auto_commit_threshold,
        escalation_threshold: float = settings.agentic_escalation_threshold,
    ):
        self.auto_commit_threshold = auto_commit_threshold
        self.escalation_threshold = escalation_threshold

    def score_pair(
        self,
        competitor_rec: NormalizedProductRecord,
        internal_rec: NormalizedProductRecord,
        bi_encoder_similarity: float,
    ) -> ScoredCandidatePair:
        """Calculates granular cross-encoder score tau using joint textual, brand, and specification alignment."""
        brand_match = competitor_rec.brand_clean.lower() == internal_rec.brand_clean.lower()
        category_match = competitor_rec.gpc_category_code == internal_rec.gpc_category_code

        # Title token overlap (Jaccard on alphanumeric tokens)
        comp_tokens = set(re.findall(r"\w+", competitor_rec.title_clean.lower()))
        int_tokens = set(re.findall(r"\w+", internal_rec.title_clean.lower()))
        intersection = len(comp_tokens.intersection(int_tokens))
        union = len(comp_tokens.union(int_tokens))
        token_jaccard = intersection / max(1, union)

        # Price ratio alignment
        c_price = max(0.01, competitor_rec.effective_price)
        i_price = max(0.01, internal_rec.effective_price)
        price_ratio = min(c_price, i_price) / max(c_price, i_price)

        # Composite score tau
        tau = (
            0.55 * bi_encoder_similarity
            + 0.15 * token_jaccard
            + (0.10 if brand_match else 0.0)
            + (0.15 if category_match else 0.0)
            + 0.05 * price_ratio
        )
        tau = float(min(1.0, max(0.0, tau)))

        if tau >= self.auto_commit_threshold:
            decision = DecisionSplit.AUTO_COMMIT
        elif tau >= self.escalation_threshold:
            decision = DecisionSplit.AGENTIC_ESCALATION
        else:
            decision = DecisionSplit.REJECT

        return ScoredCandidatePair(
            competitor_sku=competitor_rec.sku,
            internal_sku=internal_rec.sku,
            score=round(tau, 4),
            decision=decision,
            brand_match=brand_match,
            category_match=category_match,
            price_ratio=round(price_ratio, 4),
            feature_compatibility={
                "bi_encoder_sim": round(bi_encoder_similarity, 4),
                "token_jaccard": round(token_jaccard, 4),
                "price_ratio": round(price_ratio, 4),
            },
        )
