"""Promotion-adjusted comparable pricing with a transparent breakdown (plan section 2.4).

All money is `Decimal`. Nothing here guesses: unknown tax treatment, missing FX rates and unmet offer conditions
are surfaced as flags or errors, and conditional offers are only applied when the caller states the assumption.
"""

from __future__ import annotations

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Set

from pydantic import BaseModel, Field, model_validator

CENT = Decimal("0.01")


def money(x: Decimal) -> Decimal:
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


class OfferType(str, Enum):
    COUPON_CODE = "COUPON_CODE"
    CLIPPED_COUPON = "CLIPPED_COUPON"
    CART_DISCOUNT = "CART_DISCOUNT"
    MULTI_BUY = "MULTI_BUY"
    BUNDLE = "BUNDLE"
    THRESHOLD = "THRESHOLD"
    LOYALTY = "LOYALTY"
    PAYMENT_OFFER = "PAYMENT_OFFER"
    LIMITED_TIME = "LIMITED_TIME"


class Condition(str, Enum):
    MEMBERSHIP = "MEMBERSHIP"
    NEW_CUSTOMER = "NEW_CUSTOMER"
    APP_ONLY = "APP_ONLY"
    PAYMENT_INSTRUMENT = "PAYMENT_INSTRUMENT"
    GEOGRAPHY = "GEOGRAPHY"
    PERSONALIZED = "PERSONALIZED"
    QUANTITY_THRESHOLD = "QUANTITY_THRESHOLD"
    SPEND_THRESHOLD = "SPEND_THRESHOLD"
    CODE_REQUIRED = "CODE_REQUIRED"
    CLIP_REQUIRED = "CLIP_REQUIRED"
    TIME_WINDOW = "TIME_WINDOW"


# Conditions about *who the shopper is*: never assumed, only applied when the caller states them.
SHOPPER_CONDITIONS: FrozenSet[Condition] = frozenset({
    Condition.MEMBERSHIP, Condition.NEW_CUSTOMER, Condition.APP_ONLY,
    Condition.PAYMENT_INSTRUMENT, Condition.GEOGRAPHY, Condition.PERSONALIZED})
# Conditions evaluated numerically from the basket being priced.
BASKET_CONDITIONS: FrozenSet[Condition] = frozenset({Condition.QUANTITY_THRESHOLD, Condition.SPEND_THRESHOLD})
# Publicly obtainable steps: applied, but always shown to the user.
ACCESS_STEPS: FrozenSet[Condition] = frozenset({Condition.CODE_REQUIRED, Condition.CLIP_REQUIRED})


class DiscountKind(str, Enum):
    PERCENT_OFF = "PERCENT_OFF"
    AMOUNT_OFF = "AMOUNT_OFF"
    BUY_N_GET_M_FREE = "BUY_N_GET_M_FREE"


class Offer(BaseModel):
    offer_id: str
    offer_type: OfferType
    kind: DiscountKind
    value: Decimal = Field(description="Percent (10 = 10%), amount in listing currency, or M free units")
    buy_quantity: Optional[int] = Field(default=None, ge=1, description="N in buy-N-get-M-free")
    min_quantity: Optional[int] = Field(default=None, ge=1)
    min_spend: Optional[Decimal] = Field(default=None, ge=0)
    conditions: Set[Condition] = Field(default_factory=set)
    stackable: bool = True
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    code: Optional[str] = None
    evidence_ref: Optional[str] = None
    description: str = ""

    @model_validator(mode="after")
    def _derive_conditions(self) -> "Offer":
        if self.min_quantity:
            self.conditions.add(Condition.QUANTITY_THRESHOLD)
        if self.min_spend:
            self.conditions.add(Condition.SPEND_THRESHOLD)
        if self.code:
            self.conditions.add(Condition.CODE_REQUIRED)
        if self.valid_from or self.valid_to:
            self.conditions.add(Condition.TIME_WINDOW)
        if self.kind == DiscountKind.BUY_N_GET_M_FREE and not self.buy_quantity:
            raise ValueError("BUY_N_GET_M_FREE needs buy_quantity")
        if self.kind == DiscountKind.PERCENT_OFF and not (Decimal(0) <= self.value <= Decimal(100)):
            raise ValueError("Percent discount must be within 0-100")
        return self

    @property
    def is_generally_available(self) -> bool:
        return not (self.conditions & SHOPPER_CONDITIONS)


class PriceBasis(str, Enum):
    GENERAL = "GENERAL"                 # only offers any shopper can obtain
    ASSUMING_ELIGIBLE = "ASSUMING_ELIGIBLE"  # also applies offers whose shopper conditions the caller asserts


class TaxTreatment(str, Enum):
    INCLUSIVE = "INCLUSIVE"
    EXCLUSIVE = "EXCLUSIVE"
    UNKNOWN = "UNKNOWN"


class BreakdownLine(BaseModel):
    label: str
    amount: Decimal                      # signed; negative = reduction
    applied: bool = True
    offer_id: Optional[str] = None
    reason: Optional[str] = None
    conditions: List[str] = Field(default_factory=list)


class EffectivePrice(BaseModel):
    currency: str
    basis: PriceBasis
    quantity: int
    pack_size: int
    list_price: Decimal
    comparable_price: Decimal            # total for `quantity` listings, after offers (+ shipping if requested)
    per_item_price: Decimal
    shipping_included: bool
    tax_treatment: TaxTreatment
    lines: List[BreakdownLine]
    flags: List[str] = Field(default_factory=list)
    visible_conditions: List[str] = Field(default_factory=list)   # conditions attached to applied offers
    unapplied_offer_ids: List[str] = Field(default_factory=list)


def _saving(offer: Offer, running_total: Decimal, unit_price: Decimal, quantity: int) -> Decimal:
    if offer.kind == DiscountKind.PERCENT_OFF:
        return running_total * offer.value / Decimal(100)
    if offer.kind == DiscountKind.AMOUNT_OFF:
        return min(offer.value, running_total)
    group = (offer.buy_quantity or 1) + int(offer.value)
    free_units = (quantity // group) * int(offer.value)
    return min(running_total, unit_price * free_units)


def compute_effective_price(
    *,
    list_price: Decimal | float | str,
    currency: str,
    offers: List[Offer] | None = None,
    quantity: int = 1,
    pack_size: int = 1,
    shipping_fee: Decimal | float | str | None = None,
    free_shipping_threshold: Decimal | float | str | None = None,
    include_shipping: bool = False,
    tax_treatment: TaxTreatment = TaxTreatment.UNKNOWN,
    tax_rate: Decimal | float | str | None = None,
    basis: PriceBasis = PriceBasis.GENERAL,
    assume_conditions: FrozenSet[Condition] = frozenset(),
    at: Optional[datetime] = None,
) -> EffectivePrice:
    """Comparable price with every adjustment listed. Prices are compared pre-tax when the rate is known."""
    if quantity < 1 or pack_size < 1:
        raise ValueError("quantity and pack_size must be >= 1")
    price = Decimal(str(list_price))
    if price <= 0:
        raise ValueError("list_price must be positive")
    flags: List[str] = []
    lines: List[BreakdownLine] = [BreakdownLine(label="List price per listing", amount=price)]

    unit = price
    if tax_treatment == TaxTreatment.INCLUSIVE:
        if tax_rate is None:
            flags.append("TAX_INCLUSIVE_RATE_UNKNOWN")
        else:
            unit = price / (Decimal(1) + Decimal(str(tax_rate)))
            lines.append(BreakdownLine(label="Tax removed (price shown is tax-inclusive)", amount=money(unit - price)))
    elif tax_treatment == TaxTreatment.UNKNOWN:
        flags.append("TAX_TREATMENT_UNKNOWN")

    subtotal = unit * quantity
    if quantity > 1:
        lines.append(BreakdownLine(label=f"x{quantity} listings", amount=money(subtotal - unit)))

    eligible: List[Offer] = []
    unapplied: List[str] = []
    for off in sorted(offers or [], key=lambda o: o.offer_id):
        why = _ineligible_reason(off, subtotal, quantity, basis, assume_conditions, at)
        if why:
            unapplied.append(off.offer_id)
            lines.append(BreakdownLine(label=off.description or off.offer_type.value, amount=Decimal(0),
                                       applied=False, offer_id=off.offer_id, reason=why,
                                       conditions=sorted(c.value for c in off.conditions)))
            if why.startswith("time window") and at is None:
                flags.append("OFFER_WINDOW_UNCHECKED")
        else:
            eligible.append(off)

    running = subtotal
    visible: Set[str] = set()

    def apply(off: Offer) -> None:
        nonlocal running
        s = _saving(off, running, unit, quantity)
        running -= s
        lines.append(BreakdownLine(label=off.description or off.offer_type.value, amount=-money(s),
                                   offer_id=off.offer_id, conditions=sorted(c.value for c in off.conditions)))
        visible.update(c.value for c in off.conditions)

    non_stack = [o for o in eligible if not o.stackable]
    if non_stack:
        best = max(non_stack, key=lambda o: (_saving(o, running, unit, quantity), o.offer_id))
        apply(best)
        unapplied += [o.offer_id for o in non_stack if o is not best]
        for o in non_stack:
            if o is not best:
                lines.append(BreakdownLine(label=o.description or o.offer_type.value, amount=Decimal(0),
                                           applied=False, offer_id=o.offer_id,
                                           reason="not stackable; a larger non-stackable offer was applied"))
    for off in eligible:
        if off.stackable:
            apply(off)
    running = max(Decimal(0), running)

    ship_included = False
    if include_shipping:
        if shipping_fee is None:
            flags.append("SHIPPING_FEE_UNKNOWN")
        else:
            fee = Decimal(str(shipping_fee))
            if free_shipping_threshold is not None and running >= Decimal(str(free_shipping_threshold)):
                lines.append(BreakdownLine(label="Shipping (waived at threshold)", amount=Decimal(0), applied=False,
                                           reason="free shipping threshold met"))
            else:
                running += fee
                ship_included = True
                lines.append(BreakdownLine(label="Shipping", amount=money(fee)))

    if visible & {c.value for c in SHOPPER_CONDITIONS}:
        flags.append("CONDITIONAL_PRICE")
    if visible & {c.value for c in ACCESS_STEPS}:
        flags.append("REQUIRES_CODE_OR_CLIP")

    total = money(running)
    return EffectivePrice(
        currency=currency, basis=basis, quantity=quantity, pack_size=pack_size, list_price=money(price),
        comparable_price=total, per_item_price=money(total / (quantity * pack_size)), shipping_included=ship_included,
        tax_treatment=tax_treatment, lines=lines, flags=sorted(set(flags)), visible_conditions=sorted(visible),
        unapplied_offer_ids=sorted(set(unapplied)),
    )


def _ineligible_reason(off: Offer, subtotal: Decimal, quantity: int, basis: PriceBasis,
                       assume: FrozenSet[Condition], at: Optional[datetime]) -> Optional[str]:
    if at is not None:
        if off.valid_from and at < off.valid_from:
            return "time window: not started"
        if off.valid_to and at > off.valid_to:
            return "time window: expired"
    elif off.valid_from or off.valid_to:
        return "time window: evaluation time not supplied"
    shopper = off.conditions & SHOPPER_CONDITIONS
    if shopper:
        if basis == PriceBasis.GENERAL:
            return "requires " + ", ".join(sorted(c.value for c in shopper)) + " (not generally available)"
        missing = shopper - assume
        if missing:
            return "requires unasserted " + ", ".join(sorted(c.value for c in missing))
    if off.min_quantity and quantity < off.min_quantity:
        return f"quantity {quantity} below minimum {off.min_quantity}"
    if off.min_spend and subtotal < off.min_spend:
        return f"spend {money(subtotal)} below minimum {off.min_spend}"
    if off.kind == DiscountKind.BUY_N_GET_M_FREE and quantity < (off.buy_quantity or 1) + int(off.value):
        return f"quantity {quantity} too low for buy {off.buy_quantity} get {int(off.value)} free"
    return None


class FxError(ValueError):
    pass


class FxRates(BaseModel):
    """Explicit, dated rate table. `rates[c]` = units of currency c per 1 unit of `base`."""
    base: str
    rates: Dict[str, Decimal]
    as_of: datetime
    source: str


def convert(amount: Decimal | float | str, from_currency: str, to_currency: str, fx: FxRates) -> Decimal:
    """Convert using a supplied rate table. A missing rate raises; no rate is ever assumed."""
    if from_currency == to_currency:
        return Decimal(str(amount))

    def rate(c: str) -> Decimal:
        if c == fx.base:
            return Decimal(1)
        if c not in fx.rates:
            raise FxError(f"No FX rate for {c} in table from {fx.source} as of {fx.as_of.isoformat()}")
        return fx.rates[c]

    return Decimal(str(amount)) / rate(from_currency) * rate(to_currency)
