"""Unit and quantity normalisation. Source values are preserved by callers; this only derives base units."""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, Optional, Tuple

# unit -> (dimension, factor to base unit). Base units: g, ml, mm, count.
_UNITS: Dict[str, Tuple[str, Decimal]] = {
    "g": ("mass", Decimal("1")),
    "gram": ("mass", Decimal("1")),
    "kg": ("mass", Decimal("1000")),
    "oz": ("mass", Decimal("28.349523125")),
    "lb": ("mass", Decimal("453.59237")),
    "lbs": ("mass", Decimal("453.59237")),
    "ml": ("volume", Decimal("1")),
    "l": ("volume", Decimal("1000")),
    "litre": ("volume", Decimal("1000")),
    "liter": ("volume", Decimal("1000")),
    "fl oz": ("volume", Decimal("29.5735295625")),
    "floz": ("volume", Decimal("29.5735295625")),
    "gal": ("volume", Decimal("3785.411784")),
    "mm": ("length", Decimal("1")),
    "cm": ("length", Decimal("10")),
    "m": ("length", Decimal("1000")),
    "in": ("length", Decimal("25.4")),
    "ft": ("length", Decimal("304.8")),
    "count": ("count", Decimal("1")),
    "ct": ("count", Decimal("1")),
    "each": ("count", Decimal("1")),
    "item": ("count", Decimal("1")),
    "pair": ("count", Decimal("2")),
}
_BASE_UNIT = {"mass": "g", "volume": "ml", "length": "mm", "count": "count"}

# Display units for per-unit pricing.
_PER_UNIT_TARGET = {"kg": ("mass", Decimal("1000")), "100g": ("mass", Decimal("100")),
                    "l": ("volume", Decimal("1000")), "100ml": ("volume", Decimal("100")),
                    "m": ("length", Decimal("1000")), "item": ("count", Decimal("1"))}


class UnitError(ValueError):
    """Raised for unknown units or incompatible dimensions. Never guessed."""


def normalize_unit_name(unit: str) -> str:
    return " ".join(unit.strip().lower().replace(".", "").split())


def to_base(value: Decimal | float | int | str, unit: str) -> Tuple[Decimal, str, str]:
    """Return (value in base unit, base unit, dimension). Raises UnitError for unknown units."""
    key = normalize_unit_name(unit)
    if key not in _UNITS:
        raise UnitError(f"Unknown unit '{unit}'")
    dim, factor = _UNITS[key]
    return Decimal(str(value)) * factor, _BASE_UNIT[dim], dim


def same_quantity(a: Tuple[Decimal | float | str, str], b: Tuple[Decimal | float | str, str],
                  rel_tol: Decimal = Decimal("0.005")) -> Optional[bool]:
    """True/False if both quantities are comparable; None when the dimensions differ (not comparable)."""
    try:
        av, _, ad = to_base(*a)
        bv, _, bd = to_base(*b)
    except UnitError:
        return None
    if ad != bd:
        return None
    if av == 0 and bv == 0:
        return True
    return abs(av - bv) / max(av, bv) <= rel_tol


def per_unit_price(total_price: Decimal | float | str, quantity_value: Decimal | float | str,
                   quantity_unit: str, per: str) -> Decimal:
    """Price per kg / 100g / l / 100ml / m / item for a package of `quantity_value` `quantity_unit`."""
    per = per.lower()
    if per not in _PER_UNIT_TARGET:
        raise UnitError(f"Unsupported per-unit target '{per}'")
    target_dim, target_size = _PER_UNIT_TARGET[per]
    base_qty, _, dim = to_base(quantity_value, quantity_unit)
    if dim != target_dim:
        raise UnitError(f"Cannot express a {dim} quantity per '{per}'")
    if base_qty <= 0:
        raise UnitError("Quantity must be positive")
    return (Decimal(str(total_price)) / base_qty) * target_size
