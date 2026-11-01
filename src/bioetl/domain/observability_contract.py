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
from bioetl.domain.events import ORDINARY_PIPELINE_STAGE_NAMES, PipelineEvent
from bioetl.domain.runtime_observability_publication_contract import (
    get_runtime_observability_publication_contract,
)

__all__ = [
    "ORDINARY_PIPELINE_STAGE_NAMES",
    "ObservabilityContractPayload",
    "PipelineEvent",
    "build_observability_contract_payload",
    "enforce_observability_contract_context",
    "get_runtime_observability_publication_contract",
    "is_observability_contract_valid",
    "missing_observability_fields",
    "normalize_observability_context",
    "normalize_observability_metric_labels",
    "normalize_observability_pipeline_label",
]
