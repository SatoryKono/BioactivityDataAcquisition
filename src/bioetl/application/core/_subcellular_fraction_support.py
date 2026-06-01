"""Backward-compatible re-export for `bioetl.application.core.subcellular_fraction_support`."""

from __future__ import annotations

from bioetl.application.core import subcellular_fraction_support as _public

compute_entity_id = _public.compute_entity_id
create_fraction_record = _public.create_fraction_record
extract_unique_fraction_records = _public.extract_unique_fraction_records
normalize_fraction = _public.normalize_fraction
update_fraction_record = _public.update_fraction_record

__all__ = [
    "compute_entity_id",
    "create_fraction_record",
    "extract_unique_fraction_records",
    "normalize_fraction",
    "update_fraction_record",
]
