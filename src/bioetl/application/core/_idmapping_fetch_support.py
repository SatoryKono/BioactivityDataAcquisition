"""Backward-compatible re-export for `bioetl.application.core.idmapping_fetch_support`."""

from __future__ import annotations

from bioetl.application.core import idmapping_fetch_support as _public

apply_limit = _public.apply_limit
build_mapping_record = _public.build_mapping_record
fetch_records = _public.fetch_records
format_repr = _public.format_repr
read_chembl_ids = _public.read_chembl_ids
resolve_chembl_ids = _public.resolve_chembl_ids
warn_unexpected_entity_type = _public.warn_unexpected_entity_type

__all__ = [
    "apply_limit",
    "build_mapping_record",
    "fetch_records",
    "format_repr",
    "read_chembl_ids",
    "resolve_chembl_ids",
    "warn_unexpected_entity_type",
]
