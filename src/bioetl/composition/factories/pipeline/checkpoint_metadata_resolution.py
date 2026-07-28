"""Compatibility re-export; implementation lives in pipeline_support."""

from __future__ import annotations

from bioetl.composition.factories.pipeline_support.checkpoint_metadata_resolution import (
    _coerce_optional_str,
    _normalize_execution_identity_payload,
    _resolve_checkpoint_snapshot_identity,
    _resolve_input_snapshot_refs,
    _resolve_run_context_metadata,
    _resolve_run_context_payload,
    _serialize_input_snapshot_ref,
)

__all__ = [
    "_coerce_optional_str",
    "_normalize_execution_identity_payload",
    "_resolve_checkpoint_snapshot_identity",
    "_resolve_input_snapshot_refs",
    "_resolve_run_context_metadata",
    "_resolve_run_context_payload",
    "_serialize_input_snapshot_ref",
]
