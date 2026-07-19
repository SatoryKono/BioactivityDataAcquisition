"""Private profile normalizers for ChEMBL target-specific derived fields."""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.domain.mapping.organism_classification import classify_organism
from bioetl.domain.normalization.profiles._profile_value_normalizers import (
    normalize_profile_governed_vocabulary,
)
from bioetl.domain.schemas.constants import TARGET_ORGANISM_CLASSES

__all__ = ["normalize_profile_target_organism_class"]


def normalize_profile_target_organism_class(
    value: object,
    *,
    record: Mapping[str, object] | None = None,
) -> object:
    """Derive the governed target cellularity class from sibling organism fields."""
    if record is not None:
        taxonomy_raw = record.get("taxonomy_id", record.get("tax_id"))
        taxonomy_id = taxonomy_raw if isinstance(taxonomy_raw, (int, str)) else None
        classification = classify_organism(
            _record_string(record, "organism"),
            taxonomy_id,
        )
        if classification.organism_class is not None:
            return classification.organism_class.value

    return normalize_profile_governed_vocabulary(
        value,
        allowed_values=TARGET_ORGANISM_CLASSES,
        preserve_unknown=False,
    )


def _record_string(record: Mapping[str, object], key: str) -> str | None:
    value = record.get(key)
    return value if isinstance(value, str) else None
