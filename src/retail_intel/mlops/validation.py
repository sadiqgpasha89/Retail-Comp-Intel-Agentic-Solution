"""Data Contract and Catalog Validation Suite."""

from typing import Any, Dict, List, Tuple

from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    validated_record_count: int = 0


class DataContractValidator:
    """Validates catalog records against strict retail enterprise contracts."""

    @staticmethod
    def validate_catalog_record(record: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errors = []
        for f in ["sku", "title", "brand"]:
            if not record.get(f):
                errors.append(f"Missing required field: '{f}'")

        price = record.get("current_price") or record.get("scraped_base_price") or record.get("msrp")
        if price is None or float(price) <= 0:
            errors.append(f"Invalid non-positive price: {price}")

        pack = record.get("pack_size", 1)
        if int(pack) < 1:
            errors.append(f"Invalid pack size: {pack}")

        return len(errors) == 0, errors

    def validate_batch(self, records: List[Dict[str, Any]]) -> ValidationResult:
        all_errors = []
        all_warnings = []
        valid_count = 0

        for idx, rec in enumerate(records):
            is_valid, errors = self.validate_catalog_record(rec)
            if not is_valid:
                all_errors.extend([f"Row {idx} ({rec.get('sku', 'unknown')}): {e}" for e in errors])
            else:
                valid_count += 1
                if float(rec.get("current_price", rec.get("scraped_base_price", 100))) > 5000:
                    all_warnings.append(f"Row {idx}: Unusually high price detected (> $5,000)")

        return ValidationResult(
            is_valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings,
            validated_record_count=valid_count,
        )
