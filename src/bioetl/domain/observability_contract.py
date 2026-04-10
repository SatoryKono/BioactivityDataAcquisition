"""Stable facade for shared observability contract utilities."""

from __future__ import annotations

from bioetl.domain._observability_contract_core import (
    ObservabilityContractPayload,
    build_observability_contract_payload,
    enforce_observability_contract_context,
    is_observability_contract_valid,
    missing_observability_fields,
    normalize_observability_context,
    normalize_observability_metric_labels,
    normalize_observability_pipeline_label,
)

__all__ = [
    "ObservabilityContractPayload",
    "build_observability_contract_payload",
    "enforce_observability_contract_context",
    "is_observability_contract_valid",
    "missing_observability_fields",
    "normalize_observability_context",
    "normalize_observability_metric_labels",
    "normalize_observability_pipeline_label",
]
