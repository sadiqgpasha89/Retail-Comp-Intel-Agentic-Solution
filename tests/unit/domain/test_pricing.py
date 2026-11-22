"""Acceptance scenario 5: conditional coupon/cart offers, effective price with visible eligibility conditions."""
from datetime import datetime, timezone
from decimal import Decimal as D

import pytest

from retail_intel.domain.pricing import (Condition, DiscountKind, FxError, FxRates, Offer, OfferType, PriceBasis,
                                         TaxTreatment, compute_effective_price, convert)

pytestmark = pytest.mark.unit


def coupon(amount="10", **kw):
    return Offer(offer_id="c1", offer_type=OfferType.COUPON_CODE, kind=DiscountKind.AMOUNT_OFF, value=D(amount), code="SAVE", **kw)


def member(pct="5"):
    return Offer(offer_id="m1", offer_type=OfferType.LOYALTY, kind=DiscountKind.PERCENT_OFF, value=D(pct), conditions={Condition.MEMBERSHIP})


def test_general_basis_excludes_member_price_and_shows_why():
    e = compute_effective_price(list_price="100", currency="USD", offers=[coupon(), member()])
    assert e.comparable_price == D("90.00")
    assert e.unapplied_offer_ids == ["m1"]
    assert "REQUIRES_CODE_OR_CLIP" in e.flags and "CONDITIONAL_PRICE" not in e.flags
    reasons = [l.reason for l in e.lines if l.offer_id == "m1"]
    assert reasons and "MEMBERSHIP" in reasons[0]


def test_asserted_membership_applies_and_flags_conditional_price():
    e = compute_effective_price(list_price="100", currency="USD", offers=[coupon(), member()],
                                basis=PriceBasis.ASSUMING_ELIGIBLE, assume_conditions=frozenset({Condition.MEMBERSHIP}))
    assert e.comparable_price == D("85.50")           # 100 - 10 = 90, then 5% = 85.50
    assert "CONDITIONAL_PRICE" in e.flags and "MEMBERSHIP" in e.visible_conditions


def test_threshold_offer_only_when_basket_qualifies():
    o = Offer(offer_id="t1", offer_type=OfferType.THRESHOLD, kind=DiscountKind.AMOUNT_OFF, value=D("20"), min_spend=D("150"))
    assert compute_effective_price(list_price="100", currency="USD", offers=[o]).comparable_price == D("100.00")
    e = compute_effective_price(list_price="100", currency="USD", offers=[o], quantity=2)
    assert e.comparable_price == D("180.00") and e.per_item_price == D("90.00")


def test_buy_two_get_one_free():
    o = Offer(offer_id="b1", offer_type=OfferType.MULTI_BUY, kind=DiscountKind.BUY_N_GET_M_FREE, value=D(1), buy_quantity=2)
    assert compute_effective_price(list_price="30", currency="USD", offers=[o], quantity=3).comparable_price == D("60.00")
    assert "b1" in compute_effective_price(list_price="30", currency="USD", offers=[o], quantity=2).unapplied_offer_ids


def test_non_stackable_applies_only_the_best():
    a = Offer(offer_id="a", offer_type=OfferType.CART_DISCOUNT, kind=DiscountKind.PERCENT_OFF, value=D(10), stackable=False)
    b = Offer(offer_id="b", offer_type=OfferType.CART_DISCOUNT, kind=DiscountKind.PERCENT_OFF, value=D(20), stackable=False)
    e = compute_effective_price(list_price="100", currency="USD", offers=[a, b])
    assert e.comparable_price == D("80.00") and e.unapplied_offer_ids == ["a"]


def test_time_window_requires_evaluation_time():
    o = Offer(offer_id="w", offer_type=OfferType.LIMITED_TIME, kind=DiscountKind.PERCENT_OFF, value=D(20),
              valid_to=datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert "OFFER_WINDOW_UNCHECKED" in compute_effective_price(list_price="100", currency="USD", offers=[o]).flags
    live = compute_effective_price(list_price="100", currency="USD", offers=[o], at=datetime(2025, 12, 1, tzinfo=timezone.utc))
    expired = compute_effective_price(list_price="100", currency="USD", offers=[o], at=datetime(2026, 2, 1, tzinfo=timezone.utc))
    assert live.comparable_price == D("80.00") and expired.comparable_price == D("100.00")


def test_tax_and_shipping_are_explicit():
    e = compute_effective_price(list_price="120", currency="EUR", tax_treatment=TaxTreatment.INCLUSIVE, tax_rate="0.20")
    assert e.comparable_price == D("100.00")
    unknown = compute_effective_price(list_price="120", currency="EUR")
    assert "TAX_TREATMENT_UNKNOWN" in unknown.flags and unknown.comparable_price == D("120.00")
    s = compute_effective_price(list_price="40", currency="USD", shipping_fee="6", include_shipping=True, free_shipping_threshold="50")
    assert s.comparable_price == D("46.00") and s.shipping_included
    free = compute_effective_price(list_price="60", currency="USD", shipping_fee="6", include_shipping=True, free_shipping_threshold="50")
    assert free.comparable_price == D("60.00") and not free.shipping_included


def test_pack_size_drives_per_item_price():
    assert compute_effective_price(list_price="30", currency="USD", pack_size=3).per_item_price == D("10.00")


def test_discount_cannot_go_negative_and_bad_input_rejected():
    big = Offer(offer_id="x", offer_type=OfferType.CART_DISCOUNT, kind=DiscountKind.AMOUNT_OFF, value=D(500))
    assert compute_effective_price(list_price="100", currency="USD", offers=[big]).comparable_price == D("0.00")
    with pytest.raises(ValueError):
        compute_effective_price(list_price="0", currency="USD")
    with pytest.raises(ValueError):
        Offer(offer_id="p", offer_type=OfferType.COUPON_CODE, kind=DiscountKind.PERCENT_OFF, value=D(150))


def test_fx_conversion_never_guesses():
    fx = FxRates(base="USD", rates={"EUR": D("0.9")}, as_of=datetime(2026, 1, 1, tzinfo=timezone.utc), source="test-table")
    assert convert("90", "EUR", "USD", fx) == D("100")
    assert convert("10", "USD", "USD", fx) == D("10")
    with pytest.raises(FxError):
        convert("10", "USD", "JPY", fx)
