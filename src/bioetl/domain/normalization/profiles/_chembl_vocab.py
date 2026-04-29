"""Shared ChEMBL vocabulary access for normalization profiles."""

from __future__ import annotations

from bioetl.domain.schemas._chembl_enum_catalog import (
    CHEMBL_ENUM_CATALOG,
)

__all__ = ["chembl_enum"]

def chembl_enum(entity: str, field: str) -> frozenset[str]:
    """Return an immutable ChEMBL vocabulary for a profile entity field."""
    key = (entity, field)
    try:
        return CHEMBL_ENUM_CATALOG[key]
    except KeyError as exc:
        available = ", ".join(
            f"{known_entity}.{known_field}"
            for known_entity, known_field in sorted(CHEMBL_ENUM_CATALOG)
        )
        raise KeyError(
            f"Unknown ChEMBL vocabulary {entity}.{field}; available: {available}"
        ) from exc
