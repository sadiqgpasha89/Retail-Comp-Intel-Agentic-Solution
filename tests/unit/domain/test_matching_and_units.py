"""Acceptance scenarios 3 and 4: deterministic exact match with explanation; look-alikes routed to review."""
from decimal import Decimal

import pytest

from retail_intel.domain.match_classes import (LEGACY_VERDICT_TO_CLASS, MatchClass, MatchDecision, MatchTier, ProductFacts,
                                               detect_hard_conflicts, extract_title_facts, guard_auto_match,
                                               resolve_by_identifier)
from retail_intel.domain.units import UnitError, per_unit_price, same_quantity, to_base

pytestmark = pytest.mark.unit
GTIN = "0084008050120"


def facts(**kw):
    return ProductFacts(**{"brand": "AuraWave", "gtin": GTIN, "gtin_valid": True, "pack_size": 1, **kw})


def test_exact_gtin_match_is_deterministic_and_explained():
    r = resolve_by_identifier(facts(), facts())
    assert r.match_class == MatchClass.EXACT_MATCH
    assert "GTIN" in r.reason and not r.conflicts


@pytest.mark.parametrize("field,theirs", [
    ("pack_size", 3), ("model", "X2"), ("capacity", "256GB"), ("generation", "2026"), ("is_bundle", True)])
def test_same_gtin_but_conflicting_variant_goes_to_review(field, theirs):
    base = {"model": "X1", "capacity": "128GB", "generation": "2024", "is_bundle": False}
    ours = facts(**base)
    other = facts(**{**base, field: theirs})
    r = resolve_by_identifier(ours, other)
    assert r.match_class == MatchClass.NEEDS_REVIEW
    assert any(c.field.startswith(field.replace("is_", "").split("_")[0]) for c in r.conflicts)


def test_invalid_gtin_is_not_used_as_identifier():
    r = resolve_by_identifier(facts(), facts(gtin_valid=False))
    assert r.match_class is None and "checksum" in r.reason


def test_size_conflict_uses_unit_conversion():
    assert detect_hard_conflicts(facts(size_value=Decimal("12"), size_unit="oz"), facts(size_value=Decimal("340"), size_unit="g")) == []
    conflicts = detect_hard_conflicts(facts(size_value=Decimal("12"), size_unit="oz"), facts(size_value=Decimal("24"), size_unit="oz"))
    assert [c.field for c in conflicts] == ["size"]


def test_guard_never_lets_conflicts_auto_match():
    c = detect_hard_conflicts(facts(pack_size=1), facts(pack_size=6))
    assert guard_auto_match(MatchClass.EXACT_MATCH, c) == MatchClass.NEEDS_REVIEW
    assert guard_auto_match(MatchClass.RELATED_PRODUCT, c) == MatchClass.RELATED_PRODUCT
    assert guard_auto_match(MatchClass.EXACT_MATCH, []) == MatchClass.EXACT_MATCH


def test_title_facts_are_claims_extracted_not_trusted():
    f = extract_title_facts("Mountain Coffee 3-Pack 12 oz 2026 Edition")
    assert (f.pack_size, f.size_value, f.size_unit, f.generation) == (3, Decimal("12"), "oz", "2026")


def test_override_history_and_effective_class():
    d = MatchDecision(decision_id="d1", competitor_listing_id="C1", internal_sku="S1", match_class=MatchClass.NEEDS_REVIEW,
                      tier=MatchTier.AGENTIC, confidence=0.7)
    assert not d.price_comparable
    d.apply_override("rita", MatchClass.EQUIVALENT_VARIANT, "same product, new colour")
    assert d.effective_class == MatchClass.EQUIVALENT_VARIANT and d.price_comparable
    assert d.overrides[0].previous_class == MatchClass.NEEDS_REVIEW
    with pytest.raises(ValueError):
        d.apply_override("", MatchClass.NO_MATCH, "")


def test_legacy_verdicts_map_to_plan_classes():
    assert LEGACY_VERDICT_TO_CLASS["EQUIVALENT_PRIVATE_LABEL"] == MatchClass.PRIVATE_LABEL_EQUIVALENT
    assert LEGACY_VERDICT_TO_CLASS["CONTRADICTORY_LISTING"] == MatchClass.NEEDS_REVIEW
    assert LEGACY_VERDICT_TO_CLASS["UNFULFILLED_PHANTOM"] is None


def test_units():
    assert same_quantity((12, "oz"), (340, "g")) is True
    assert same_quantity((1, "kg"), (1, "l")) is None
    assert per_unit_price("6.80", 340, "g", "kg") == Decimal("20")
    with pytest.raises(UnitError):
        per_unit_price(5, 1, "l", "kg")
    with pytest.raises(UnitError):
        to_base(1, "parsec")


def test_private_label_with_different_pack_still_needs_review():
    from retail_intel.domain.match_classes import HardConflict, MatchClass, guard_auto_match
    brand = HardConflict(field="brand", ours="A", theirs="Store", reason="x")
    pack = HardConflict(field="pack_size", ours="1", theirs="3", reason="x")
    assert guard_auto_match(MatchClass.PRIVATE_LABEL_EQUIVALENT, [brand]) == MatchClass.PRIVATE_LABEL_EQUIVALENT
    assert guard_auto_match(MatchClass.PRIVATE_LABEL_EQUIVALENT, [brand, pack]) == MatchClass.NEEDS_REVIEW
