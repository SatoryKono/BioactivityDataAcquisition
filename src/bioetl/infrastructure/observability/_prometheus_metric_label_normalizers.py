"""Shared bounded-label normalizers for Prometheus metric policies."""

from __future__ import annotations

import re
from pathlib import PurePath

_ALLOWED_REASON_LABELS = frozenset(
    {
        "cross_validation",
        "filtered_out_silver",
        "data_quality",
        "schema_validation",
        "transform_error",
        "validation_error",
        "other",
    }
)
_ALLOWED_SILVER_FILTER_REASON_CODE_LABELS = frozenset(
    {
        "required_field_missing",
        "exclude_if_present",
        "column_filter_mismatch",
        "range_filter_mismatch",
        "list_length_filter_mismatch",
        "list_contains_filter_mismatch",
        "required_field_type_mismatch",
        "optional_nonnullable_field_type_mismatch",
        "nullable_field_type_coerced_to_null",
        "other",
    }
)
_ALLOWED_SILVER_FILTER_RULE_TYPE_LABELS = frozenset(
    {
        "required_fields",
        "exclude_if_present",
        "column_filters",
        "range_filters",
        "list_length_filters",
        "list_contains_filters",
        "structural_policy",
        "other",
    }
)
_ALLOWED_SILVER_FILTER_FIELD_LABELS = frozenset(
    {
        "_state",
        "accession",
        "activity_id",
        "assay_description",
        "assay_id",
        "assay_param_id",
        "assay_type",
        "assay_type_description",
        "bao_endpoint",
        "bao_format",
        "bao_label",
        "canonical_smiles",
        "cell_id",
        "cell_name",
        "class_level",
        "component_id",
        "confidence_score",
        "data_validity_comment",
        "description",
        "doc_1",
        "doc_2",
        "doi",
        "inorganic_flag",
        "journal",
        "mapping_status",
        "molecule_id",
        "molecule_type",
        "openalex_id",
        "organism",
        "organism_scientific",
        "other",
        "paper_id",
        "pchembl_value",
        "pmid",
        "potential_duplicate",
        "pref_name",
        "protein_class_id",
        "publication_id",
        "publication_type",
        "publication_year",
        "record_id",
        "relation",
        "relationship_type",
        "sim_id",
        "src_id",
        "standard_flag",
        "standard_relation",
        "standard_type",
        "standard_units",
        "standard_value",
        "structure_type",
        "subcellular_fraction",
        "target_id",
        "target_organism",
        "target_taxonomy_id",
        "target_type",
        "term",
        "term_type",
        "tissue_id",
        "title",
        "type",
        "units",
        "uo_units",
        "value",
    }
)
_ALLOWED_STAGE_LABELS = frozenset(
    {
        "validation",
        "threshold",
        "transform",
        "bronze",
        "silver",
        "gold",
        "postrun",
        "other",
    }
)
_ALLOWED_RUNTIME_STAGE_LABELS = frozenset(
    {
        "pipeline",
        "startup",
        "preflight",
        "lifecycle_clear",
        "execution",
        "postrun",
        "cleanup",
        "bronze",
        "silver",
        "gold",
        "filtered_out",
        "quarantined",
        "transform",
        "validation",
        "write",
        "checkpoint",
        "extract",
        "load",
        "other",
    }
)
_ALLOWED_FLOW_STAGE_LABELS = frozenset(
    {
        "fetched",
        "bronze",
        "silver",
        "gold",
        "filtered_out",
        "quarantined",
        "other",
    }
)
_ALLOWED_STAGE_MODEL_STAGE_LABELS = frozenset(
    {"input", "ingestion", "transform", "validation", "storage", "output", "other"}
)
_ALLOWED_STAGE_MODEL_OUTCOME_LABELS = frozenset(
    {
        "fetched",
        "bronze_written",
        "silver_ready",
        "gold_ready",
        "filtered_out",
        "evaluated",
        "quarantined",
        "silver_written",
        "gold_written",
        "ready",
        "other",
    }
)
_ALLOWED_PHASE_LABELS = frozenset(
    {
        "startup",
        "preflight",
        "lifecycle_clear",
        "execution",
        "postrun",
        "cleanup",
        "preflight_validation",
        "seed",
        "dependencies",
        "enrichment",
        "merge",
        "cross_validation",
        "gold_write",
        "other",
    }
)
_ALLOWED_POSTRUN_PHASE_LABELS = frozenset(
    {
        "dq_evaluation",
        "dq_reports",
        "compaction",
        "vacuum",
        "final_metadata",
        "other",
    }
)
_ALLOWED_SEVERITY_LABELS = frozenset(
    {"soft_fail", "hard_fail", "warning", "error", "other"}
)
_ALLOWED_DQ_DISPOSITION_LABELS = frozenset(
    {"pass", "warn", "quarantine", "skip", "fail", "other"}
)
_ALLOWED_TERMINAL_STATUS_LABELS = frozenset({"success", "failed", "shutdown", "other"})
_ALLOWED_PUBLICATION_TARGET_LABELS = frozenset(
    {"pushgateway", "metrics_server", "other"}
)
_ALLOWED_PUBLICATION_STATUS_LABELS = frozenset(
    {"success", "failed", "skipped", "disabled", "other"}
)
_ALLOWED_OBSERVABILITY_COMPONENT_LABELS = frozenset(
    {"metrics", "tracing", "audit", "dq_monitor", "other"}
)
_ALLOWED_OBSERVABILITY_MODE_LABELS = frozenset({"active", "noop", "disabled", "other"})
_ALLOWED_DQ_CHECK_TYPE_LABELS = frozenset(
    {
        "anomaly_detection",
        "business_rules",
        "completeness",
        "content_hash_integrity",
        "data_freshness",
        "deduplication_stats",
        "encoding_validation",
        "file_integrity",
        "key_nullability",
        "null_rate",
        "raw_field_presence",
        "record_count",
        "referential_integrity",
        "schema_drift",
        "schema_snapshot",
        "scd_integrity",
        "statistical_profile",
        "type_conformance",
        "uniqueness",
        "value_distribution",
        "other",
    }
)
_ALLOWED_STRUCTURAL_ACTION_LABELS = frozenset(
    {
        "presence_quarantine",
        "required_type_quarantine",
        "nullable_type_to_null",
        "optional_nonnullable_quarantine",
        "other",
    }
)
_ALLOWED_STRUCTURAL_COMPARISON_LABELS = frozenset(
    {
        "structural_pass_semantic_pass",
        "structural_pass_semantic_reject",
        "structural_reject_semantic_pass",
        "structural_reject_semantic_reject",
        "other",
    }
)
_ALLOWED_ADAPTER_OPERATION_LABELS = frozenset(
    {
        "doi_resolution",
        "fallback_flow",
        "fetch",
        "fetch_batch",
        "fetch_filtered_with_fallback",
        "health_check",
        "search",
        "title_fallback",
        "other",
    }
)

_DYNAMIC_ENDPOINT_SEGMENT_PATTERNS = (
    re.compile(r"^\d+$"),
    re.compile(
        r"^[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}$",
        re.IGNORECASE,
    ),
    re.compile(r"^[\da-f]{16,}$", re.IGNORECASE),
)


def normalize_adapter_endpoint_label(endpoint: str) -> str:
    """Normalize adapter endpoint labels to bounded route-template form."""
    stripped = endpoint.strip()
    if not stripped:
        return "/unknown"
    path = stripped.split("?", 1)[0]
    normalized_segments: list[str] = []
    for segment in path.split("/"):
        if not segment:
            continue
        normalized_segments.append(_normalize_endpoint_segment(segment))
    if not normalized_segments:
        return "/"
    return "/" + "/".join(normalized_segments)


def normalize_source_file_label(source_file: str) -> str:
    """Normalize filter source file labels to basename-only bounded values."""
    stripped = source_file.strip()
    if not stripped:
        return "unknown"
    path_like = stripped.replace("\\", "/")
    basename = PurePath(path_like).name
    candidate = basename or path_like
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "_", candidate.lower())
    collapsed = re.sub(r"_+", "_", normalized).strip("._-")
    if not collapsed:
        return "unknown"
    return collapsed[:64]


def normalize_adapter_operation_label(operation: str) -> str:
    """Normalize adapter operation labels to the reviewed bounded vocabulary."""
    return _normalize_bounded_label(operation, _ALLOWED_ADAPTER_OPERATION_LABELS)


def normalize_quarantine_reason(reason: str) -> str:
    """Normalize quarantine reason to a bounded label set."""
    return _normalize_bounded_label(reason, _ALLOWED_REASON_LABELS)


def normalize_silver_filter_reason_code(reason_code: str | None) -> str:
    """Normalize Silver filter reason_code to a bounded label set."""
    return _normalize_bounded_label(
        reason_code or "other", _ALLOWED_SILVER_FILTER_REASON_CODE_LABELS
    )


def normalize_silver_filter_rule_type(rule_type: str | None) -> str:
    """Normalize Silver filter rule_type to a bounded label set."""
    return _normalize_bounded_label(
        rule_type or "other", _ALLOWED_SILVER_FILTER_RULE_TYPE_LABELS
    )


def normalize_silver_filter_field(field: str | None) -> str:
    """Normalize Silver filter field name to a bounded label set."""
    return _normalize_bounded_label(
        field or "other", _ALLOWED_SILVER_FILTER_FIELD_LABELS
    )


def normalize_dq_stage(stage: str) -> str:
    """Normalize DQ stage label to a bounded label set."""
    return _normalize_bounded_label(stage, _ALLOWED_STAGE_LABELS)


def normalize_runtime_stage(stage: str) -> str:
    """Normalize generic runtime stage labels to a bounded label set."""
    return _normalize_bounded_label(stage, _ALLOWED_RUNTIME_STAGE_LABELS)


def normalize_flow_stage(flow_stage: str) -> str:
    """Normalize record-flow stage labels to the canonical bounded set."""
    return _normalize_bounded_label(flow_stage, _ALLOWED_FLOW_STAGE_LABELS)


def normalize_stage_model_stage(stage: str) -> str:
    """Normalize canonical stage-model stage labels."""
    return _normalize_bounded_label(stage, _ALLOWED_STAGE_MODEL_STAGE_LABELS)


def normalize_stage_model_outcome(outcome: str) -> str:
    """Normalize canonical stage-model outcome labels."""
    return _normalize_bounded_label(outcome, _ALLOWED_STAGE_MODEL_OUTCOME_LABELS)


def normalize_runtime_phase(phase: str) -> str:
    """Normalize lifecycle and composite phase labels to a bounded label set."""
    return _normalize_bounded_label(phase, _ALLOWED_PHASE_LABELS)


def normalize_postrun_phase(phase: str) -> str:
    """Normalize postrun subphase labels to the canonical bounded set."""
    return _normalize_bounded_label(phase, _ALLOWED_POSTRUN_PHASE_LABELS)


def normalize_dq_severity(severity: str) -> str:
    """Normalize DQ severity label to a bounded label set."""
    return _normalize_bounded_label(severity, _ALLOWED_SEVERITY_LABELS)


def normalize_dq_disposition(disposition: str) -> str:
    """Normalize DQ disposition labels to the canonical bounded set."""
    return _normalize_bounded_label(disposition, _ALLOWED_DQ_DISPOSITION_LABELS)


def normalize_terminal_status(terminal_status: str) -> str:
    """Normalize terminal run status labels to the bounded set."""
    return _normalize_bounded_label(terminal_status, _ALLOWED_TERMINAL_STATUS_LABELS)


def normalize_publication_target(target: str) -> str:
    """Normalize metrics publication target labels."""
    return _normalize_bounded_label(target, _ALLOWED_PUBLICATION_TARGET_LABELS)


def normalize_publication_status(status: str) -> str:
    """Normalize metrics publication status labels."""
    return _normalize_bounded_label(status, _ALLOWED_PUBLICATION_STATUS_LABELS)


def normalize_observability_component(component: str) -> str:
    """Normalize observability component labels."""
    return _normalize_bounded_label(component, _ALLOWED_OBSERVABILITY_COMPONENT_LABELS)


def normalize_observability_mode(mode: str) -> str:
    """Normalize observability runtime mode labels."""
    return _normalize_bounded_label(mode, _ALLOWED_OBSERVABILITY_MODE_LABELS)


def normalize_dq_check_type(check_type: str) -> str:
    """Normalize DQ check type label to the configured bounded set."""
    return _normalize_bounded_label(check_type, _ALLOWED_DQ_CHECK_TYPE_LABELS)


def normalize_structural_action(action: str) -> str:
    """Normalize structural action label to a bounded label set."""
    return _normalize_bounded_label(action, _ALLOWED_STRUCTURAL_ACTION_LABELS)


def normalize_structural_comparison(comparison: str) -> str:
    """Normalize structural comparison label to a bounded label set."""
    return _normalize_bounded_label(
        comparison,
        _ALLOWED_STRUCTURAL_COMPARISON_LABELS,
    )


def _normalize_endpoint_segment(segment: str) -> str:
    """Collapse likely dynamic path segments into a stable placeholder."""
    if "{" in segment and "}" in segment:
        return segment
    lowered = segment.lower()
    if lowered.startswith("10."):
        return "{id}"
    if any(pattern.match(lowered) for pattern in _DYNAMIC_ENDPOINT_SEGMENT_PATTERNS):
        return "{id}"
    return segment


def _normalize_bounded_label(value: str, allowed_values: frozenset[str]) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    return normalized if normalized in allowed_values else "other"
