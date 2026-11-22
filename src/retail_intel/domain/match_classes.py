"""Explicit match classes, hard-conflict guards and auditable match decisions (plan section 2.3)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from retail_intel.domain.units import same_quantity


class MatchClass(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"
    EQUIVALENT_VARIANT = "EQUIVALENT_VARIANT"          # same product, material variant difference recorded
    DIRECT_SUBSTITUTE = "DIRECT_SUBSTITUTE"
    PRIVATE_LABEL_EQUIVALENT = "PRIVATE_LABEL_EQUIVALENT"  # evidence-backed only
    COMPLEMENTARY_PRODUCT = "COMPLEMENTARY_PRODUCT"
    RELATED_PRODUCT = "RELATED_PRODUCT"
    NO_MATCH = "NO_MATCH"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class MatchTier(str, Enum):
    DETERMINISTIC = "DETERMINISTIC"
    CLASSICAL_ML = "CLASSICAL_ML"
    AGENTIC = "AGENTIC"
    HUMAN = "HUMAN"


# Maps the verdict strings emitted by the pre-existing pipeline to the plan's match classes.
# None = not a match class (an availability or safety finding handled elsewhere).
LEGACY_VERDICT_TO_CLASS: Dict[str, Optional[MatchClass]] = {
    "EXACT_MATCH": MatchClass.EXACT_MATCH,
    "EQUIVALENT_PRIVATE_LABEL": MatchClass.PRIVATE_LABEL_EQUIVALENT,
    "DIRECT_SUBSTITUTE": MatchClass.DIRECT_SUBSTITUTE,
    "CONTRADICTORY_LISTING": MatchClass.NEEDS_REVIEW,
    "NO_INTERNAL_EQUIVALENT": MatchClass.NO_MATCH,
    "HONEYPOT_TRAP": MatchClass.NO_MATCH,
    "UNFULFILLED_PHANTOM": None,
}

# Classes that may drive price comparison automatically. Anything else needs a human or is not comparable.
PRICE_COMPARABLE = {MatchClass.EXACT_MATCH, MatchClass.EQUIVALENT_VARIANT,
                    MatchClass.PRIVATE_LABEL_EQUIVALENT, MatchClass.DIRECT_SUBSTITUTE}


class ProductFacts(BaseModel):
    """The comparable facts of one listing. Missing facts are None, never defaulted."""
    brand: Optional[str] = None
    model: Optional[str] = None
    gtin: Optional[str] = None
    gtin_valid: bool = False
    pack_size: Optional[int] = None
    size_value: Optional[Decimal] = None
    size_unit: Optional[str] = None
    capacity: Optional[str] = None
    generation: Optional[str] = None          # model year / generation label
    is_bundle: Optional[bool] = None


class HardConflict(BaseModel):
    field: str
    ours: str
    theirs: str
    reason: str


def _norm(s: Optional[str]) -> Optional[str]:
    return re.sub(r"[^a-z0-9]", "", s.lower()) if s else None


def detect_hard_conflicts(ours: ProductFacts, theirs: ProductFacts) -> List[HardConflict]:
    """Facts that must block a silent auto-match (plan: pack size, model, capacity, generation, bundle)."""
    out: List[HardConflict] = []

    def add(field: str, a: object, b: object, why: str) -> None:
        out.append(HardConflict(field=field, ours=str(a), theirs=str(b), reason=why))

    if _norm(ours.brand) and _norm(theirs.brand) and _norm(ours.brand) != _norm(theirs.brand):
        add("brand", ours.brand, theirs.brand, "Different brands (private-label equivalence needs separate evidence)")
    if _norm(ours.model) and _norm(theirs.model) and _norm(ours.model) != _norm(theirs.model):
        add("model", ours.model, theirs.model, "Different model identifiers")
    if ours.pack_size is not None and theirs.pack_size is not None and ours.pack_size != theirs.pack_size:
        add("pack_size", ours.pack_size, theirs.pack_size, "Different pack quantities")
    if ours.size_value is not None and theirs.size_value is not None and ours.size_unit and theirs.size_unit:
        same = same_quantity((ours.size_value, ours.size_unit), (theirs.size_value, theirs.size_unit))
        if same is False:
            add("size", f"{ours.size_value} {ours.size_unit}", f"{theirs.size_value} {theirs.size_unit}",
                "Different size / weight / volume")
    if _norm(ours.capacity) and _norm(theirs.capacity) and _norm(ours.capacity) != _norm(theirs.capacity):
        add("capacity", ours.capacity, theirs.capacity, "Different capacity")
    if _norm(ours.generation) and _norm(theirs.generation) and _norm(ours.generation) != _norm(theirs.generation):
        add("generation", ours.generation, theirs.generation, "Different generation / model year")
    if ours.is_bundle is not None and theirs.is_bundle is not None and ours.is_bundle != theirs.is_bundle:
        add("bundle", ours.is_bundle, theirs.is_bundle, "One listing is a bundle, the other is not")
    return out


_PACK_PATTERNS = [
    re.compile(r"\b(\d{1,3})\s*-?\s*(?:pack|pk|ct|count)\b", re.I),
    re.compile(r"\bpack\s+of\s+(\d{1,3})\b", re.I),
    re.compile(r"\b(\d{1,3})\s*x\s*\d", re.I),
]
_YEAR = re.compile(r"\b(20[0-4]\d)\b")
_SIZE = re.compile(r"(\d+(?:\.\d+)?)\s*(fl\s*oz|oz|lbs?|kg|g|ml|l|litre|liter)\b", re.I)


def extract_title_facts(title: str) -> ProductFacts:
    """Best-effort extraction of pack size, size and generation from a title. Titles are untrusted marketing text,
    so these facts are *claims*; callers must prefer structured specs and physical evidence."""
    facts = ProductFacts()
    for pat in _PACK_PATTERNS:
        m = pat.search(title)
        if m:
            facts.pack_size = int(m.group(1))
            break
    m = _SIZE.search(title)
    if m:
        facts.size_value, facts.size_unit = Decimal(m.group(1)), m.group(2).lower()
    m = _YEAR.search(title)
    if m:
        facts.generation = m.group(1)
    if re.search(r"\bbundle\b|\bwith free\b|\b\+\s*\w+ (?:case|kit)\b", title, re.I):
        facts.is_bundle = True
    return facts


class Resolution(BaseModel):
    match_class: Optional[MatchClass]          # None = deterministic tier cannot decide, pass to next tier
    reason: str
    conflicts: List[HardConflict] = Field(default_factory=list)


def resolve_by_identifier(ours: ProductFacts, theirs: ProductFacts) -> Resolution:
    """Deterministic tier. Exact identifiers match only when no hard conflict contradicts them (false-GTIN guard)."""
    conflicts = detect_hard_conflicts(ours, theirs)
    if ours.gtin and theirs.gtin and ours.gtin_valid and theirs.gtin_valid and ours.gtin == theirs.gtin:
        if conflicts:
            return Resolution(match_class=MatchClass.NEEDS_REVIEW, conflicts=conflicts,
                              reason="Identifiers match but listing facts conflict (possible false GTIN or variant)")
        return Resolution(match_class=MatchClass.EXACT_MATCH, reason="Valid GTIN equality with no conflicting facts")
    if (ours.gtin and not ours.gtin_valid) or (theirs.gtin and not theirs.gtin_valid):
        return Resolution(match_class=None, conflicts=conflicts,
                          reason="GTIN present but failed checksum; ignored as an identifier")
    if _norm(ours.model) and _norm(ours.model) == _norm(theirs.model) and _norm(ours.brand) == _norm(theirs.brand):
        if conflicts:
            return Resolution(match_class=MatchClass.NEEDS_REVIEW, conflicts=conflicts,
                              reason="Brand and model match but variant facts conflict")
        return Resolution(match_class=MatchClass.EXACT_MATCH, reason="Trusted brand + model key equality")
    return Resolution(match_class=None, conflicts=conflicts, reason="No deterministic identifier decision")


def guard_auto_match(proposed: MatchClass, conflicts: List[HardConflict]) -> MatchClass:
    """Never silently auto-match a materially different pack, model, capacity, generation or bundle."""
    if conflicts and proposed in {MatchClass.EXACT_MATCH, MatchClass.EQUIVALENT_VARIANT, MatchClass.DIRECT_SUBSTITUTE}:
        return MatchClass.NEEDS_REVIEW
    if proposed == MatchClass.PRIVATE_LABEL_EQUIVALENT:
        # A different brand is expected for private label; any *other* material difference still needs a human.
        if any(c.field != "brand" for c in conflicts):
            return MatchClass.NEEDS_REVIEW
    return proposed


class MatchEvidence(BaseModel):
    kind: str                       # e.g. "gtin", "spec", "image", "knowledge_graph", "model_score"
    detail: str
    reference: Optional[str] = None  # evidence URI / observation id


class ReviewOverride(BaseModel):
    reviewer: str
    previous_class: MatchClass
    new_class: MatchClass
    reason: str
    at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MatchDecision(BaseModel):
    decision_id: str
    competitor_listing_id: str
    internal_sku: Optional[str] = None
    match_class: MatchClass
    tier: MatchTier
    confidence: float = Field(ge=0.0, le=1.0)
    feature_scores: Dict[str, float] = Field(default_factory=dict)
    evidence: List[MatchEvidence] = Field(default_factory=list)
    conflicts: List[HardConflict] = Field(default_factory=list)
    model_version: str = "unversioned"
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    overrides: List[ReviewOverride] = Field(default_factory=list)

    @property
    def effective_class(self) -> MatchClass:
        return self.overrides[-1].new_class if self.overrides else self.match_class

    @property
    def price_comparable(self) -> bool:
        return self.effective_class in PRICE_COMPARABLE

    def apply_override(self, reviewer: str, new_class: MatchClass, reason: str) -> None:
        if not reviewer or not reason:
            raise ValueError("Overrides require a reviewer and a reason")
        self.overrides.append(ReviewOverride(reviewer=reviewer, previous_class=self.effective_class,
                                             new_class=new_class, reason=reason))
