"""Normalization and Cleansing Pipeline: GTIN checksum validation, metric conversion, and GPC taxonomy harmonization."""

import re
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, Field

from retail_intel.core.logging import get_logger
from retail_intel.data_engineering.ingestion.ingestion_pipeline import IngestionPayload

logger = get_logger("data_engineering.normalization")


class NormalizedProductRecord(BaseModel):
    """Cleaned, validated, and normalized product record aligned to enterprise ontology."""
    source_type: str = "competitor"  # "internal" or "competitor"
    source_id: str
    sku: str
    gtin_normalized: Optional[str] = None
    gtin_valid: bool = False
    title_clean: str
    brand_clean: str
    gpc_category_code: str
    gpc_category_name: str
    base_price: float
    effective_price: float
    unit_price: float
    unit_measure_standard: str  # "count", "oz", "fl_oz", "pair"
    pack_size: int
    normalized_attributes: Dict[str, Any] = Field(default_factory=dict)
    stock_status: str
    fulfillment_latency_days: int
    image_url: str
    pdp_url: str
    raw_payload_ref: Dict[str, Any] = Field(default_factory=dict)


class NormalizationPipeline:
    """Enterprise Normalization Engine."""

    GPC_TAXONOMY_MAP = {
        "headphone": ("50192700", "Audio - Headphones & Earphones"),
        "audio": ("50192700", "Audio - Headphones & Earphones"),
        "tv": ("50192800", "Televisions - OLED & 4K Displays"),
        "television": ("50192800", "Televisions - OLED & 4K Displays"),
        "display": ("50192800", "Televisions - OLED & 4K Displays"),
        "coffee": ("50201706", "Grocery - Whole Bean & Ground Coffee"),
        "beverage": ("50201706", "Grocery - Whole Bean & Ground Coffee"),
        "laundry": ("47131811", "Household - Liquid & Pod Detergents"),
        "detergent": ("47131811", "Household - Liquid & Pod Detergents"),
        "chair": ("56112102", "Furniture - Ergonomic Task & Office Seating"),
        "office furniture": ("56112102", "Furniture - Ergonomic Task & Office Seating"),
        "drill": ("27112700", "Tools - Cordless Power Drills"),
        "power tool": ("27112700", "Tools - Cordless Power Drills"),
        "shoe": ("53111600", "Apparel - Athletic & Running Footwear"),
        "running": ("53111600", "Apparel - Athletic & Running Footwear"),
        "jacket": ("53101802", "Apparel - Outerwear & Technical Jackets"),
        "outerwear": ("53101802", "Apparel - Outerwear & Technical Jackets"),
    }

    @staticmethod
    def validate_and_normalize_gtin(gtin: Optional[str]) -> tuple[Optional[str], bool]:
        """Validates GTIN/UPC/EAN check digit using standard GS1 modulo-10 algorithm."""
        if not gtin:
            return None, False
        digits = re.sub(r"\D", "", str(gtin))
        if len(digits) not in [8, 12, 13, 14]:
            return digits if digits else None, False

        try:
            data = digits[:-1]
            rev = [int(c) for c in reversed(data)]
            total = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(rev))
            expected_check = (10 - (total % 10)) % 10
            is_valid = expected_check == int(digits[-1])
            normalized = digits.zfill(14)
            return normalized, is_valid
        except Exception:
            return digits, False

    @classmethod
    def align_gpc_category(cls, raw_category: str, title: str) -> tuple[str, str]:
        """Resolves disparate catalog category trees into standard Global Product Classification (GPC)."""
        combined = f"{raw_category} {title}".lower()
        for keyword, (code, name) in cls.GPC_TAXONOMY_MAP.items():
            if keyword in combined:
                return code, name
        return "99999999", "General Unclassified Retail"

    @classmethod
    def normalize_attributes(cls, specs: Dict[str, Any], title: str) -> Dict[str, Any]:
        """Normalizes units (imperial/metric) and cleans specification keys."""
        normalized: Dict[str, Any] = {}
        for k, v in specs.items():
            clean_k = re.sub(r"[^a-zA-Z0-9_]", "_", k.lower()).strip("_")
            normalized[clean_k] = v

        # Extract size/weight cues from title if missing in specs
        vol_match = re.search(
            r"(\d+(?:\.\d+)?)\s*(oz|fl\s*oz|lbs|kg|g|count|pack|mm|in)",
            title,
            re.IGNORECASE,
        )
        if vol_match:
            normalized["extracted_spec_unit"] = {
                "value": float(vol_match.group(1)),
                "unit": vol_match.group(2).lower(),
            }
        return normalized

    def normalize_competitor_payload(
        self, payload: Union[IngestionPayload, Dict[str, Any]]
    ) -> NormalizedProductRecord:
        """Transforms a raw IngestionPayload or dictionary into a NormalizedProductRecord."""
        if isinstance(payload, dict):
            payload = IngestionPayload(**payload)
        norm_gtin, gtin_valid = self.validate_and_normalize_gtin(payload.gtin)
        gpc_code, gpc_name = self.align_gpc_category(payload.raw_category, payload.title)
        clean_title = re.sub(r"\s+", " ", payload.title).strip()
        clean_brand = payload.brand.strip()

        pack_size = max(1, payload.pack_size)
        effective_price = payload.final_effective_price or payload.scraped_base_price
        unit_price = round(effective_price / pack_size, 4)

        norm_specs = self.normalize_attributes(payload.specifications, payload.title)

        return NormalizedProductRecord(
            source_type="competitor",
            source_id=payload.competitor_id,
            sku=payload.competitor_sku,
            gtin_normalized=norm_gtin,
            gtin_valid=gtin_valid,
            title_clean=clean_title,
            brand_clean=clean_brand,
            gpc_category_code=gpc_code,
            gpc_category_name=gpc_name,
            base_price=payload.scraped_base_price,
            effective_price=effective_price,
            unit_price=unit_price,
            unit_measure_standard=payload.unit_measure,
            pack_size=pack_size,
            normalized_attributes=norm_specs,
            stock_status=payload.stock_status,
            fulfillment_latency_days=payload.fulfillment_latency_days,
            image_url=payload.image_url,
            pdp_url=payload.pdp_url,
            raw_payload_ref=payload.model_dump(),
        )

    def normalize_internal_product(self, raw_item: Dict[str, Any]) -> NormalizedProductRecord:
        """Transforms an internal catalog item into a NormalizedProductRecord."""
        norm_gtin, gtin_valid = self.validate_and_normalize_gtin(raw_item.get("gtin"))
        gpc_code = raw_item.get("gpc_category", "99999999")
        gpc_name = raw_item.get("category", "General Internal Category")

        pack_size = max(1, raw_item.get("pack_size", 1))
        effective_price = raw_item.get("current_price", raw_item.get("msrp", 0.0))
        unit_price = round(effective_price / pack_size, 4)

        norm_specs = self.normalize_attributes(raw_item.get("attributes", {}), raw_item.get("title", ""))

        return NormalizedProductRecord(
            source_type="internal",
            source_id="ENTERPRISE_INTERNAL",
            sku=raw_item.get("sku", ""),
            gtin_normalized=norm_gtin,
            gtin_valid=gtin_valid,
            title_clean=raw_item.get("title", "").strip(),
            brand_clean=raw_item.get("brand", "").strip(),
            gpc_category_code=gpc_code,
            gpc_category_name=gpc_name,
            base_price=raw_item.get("msrp", 0.0),
            effective_price=effective_price,
            unit_price=unit_price,
            unit_measure_standard=raw_item.get("unit_measure", "count"),
            pack_size=pack_size,
            normalized_attributes=norm_specs,
            stock_status=raw_item.get("stock_status", "IN_STOCK"),
            fulfillment_latency_days=1,
            image_url=raw_item.get("image_url", ""),
            pdp_url=f"/internal/catalog/{raw_item.get('sku')}",
            raw_payload_ref=raw_item,
        )
