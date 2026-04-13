"""Public seam for ID-mapping fetch helpers."""

from __future__ import annotations

from bioetl.application.core._idmapping_fetch_support import (
    apply_limit,
    build_mapping_record,
    fetch_records,
    format_repr,
    read_chembl_ids,
    resolve_chembl_ids,
    warn_unexpected_entity_type,
)

__all__ = [
    "apply_limit",
    "build_mapping_record",
    "fetch_records",
    "format_repr",
    "read_chembl_ids",
    "resolve_chembl_ids",
    "warn_unexpected_entity_type",
]
