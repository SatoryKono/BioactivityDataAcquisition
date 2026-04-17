"""Label policy helpers for PrometheusMetrics."""

from __future__ import annotations

import re

from bioetl.domain.observability_contract import normalize_observability_metric_labels
from bioetl.domain.ports import MetricLabels

OBSERVABILITY_EVENTS_COUNTER_NAME = "bioetl_observability_events_total"

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
        "silver",
        "gold",
        "postrun",
        "other",
    }
)
_ALLOWED_SEVERITY_LABELS = frozenset(
    {"soft_fail", "hard_fail", "warning", "error", "other"}
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

_DYNAMIC_ENDPOINT_SEGMENT_PATTERNS = (
    re.compile(r"^[0-9]+$"),
    re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        re.IGNORECASE,
    ),
    re.compile(r"^[0-9a-f]{16,}$", re.IGNORECASE),
)


def normalize_metric_dispatch_labels(
    name: str,
    labels: MetricLabels,
) -> MetricLabels:
    """Normalize metric labels for metrics with stricter label contracts."""
    if name == OBSERVABILITY_EVENTS_COUNTER_NAME:
        return normalize_observability_metric_labels(labels)
    if name == "bioetl_quarantine_records_total":
        return {
            **labels,
            "reason": normalize_quarantine_reason(str(labels.get("reason", "other"))),
        }
    if name == "bioetl_dq_validation_failures_total":
        return {
            **labels,
            "stage": normalize_dq_stage(str(labels.get("stage", "other"))),
            "severity": normalize_dq_severity(str(labels.get("severity", "other"))),
        }
    if name == "bioetl_silver_filter_rejections_total":
        return {
            **labels,
            "reason_code": normalize_silver_filter_reason_code(
                labels.get("reason_code")
                if isinstance(labels.get("reason_code"), str)
                else None
            ),
            "rule_type": normalize_silver_filter_rule_type(
                labels.get("rule_type")
                if isinstance(labels.get("rule_type"), str)
                else None
            ),
            "field": normalize_silver_filter_field(
                labels.get("field") if isinstance(labels.get("field"), str) else None
            ),
        }
    if name == "bioetl_structural_policy_events_total":
        return {
            **labels,
            "action": normalize_structural_action(labels.get("action", "other")),
        }
    if name == "bioetl_structural_policy_shadow_comparisons_total":
        return {
            **labels,
            "comparison": normalize_structural_comparison(
                labels.get("comparison", "other")
            ),
        }
    return labels


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


def normalize_dq_severity(severity: str) -> str:
    """Normalize DQ severity label to a bounded label set."""
    return _normalize_bounded_label(severity, _ALLOWED_SEVERITY_LABELS)


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
