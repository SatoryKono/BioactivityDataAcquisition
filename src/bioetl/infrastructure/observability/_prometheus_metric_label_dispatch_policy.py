"""Specialized Prometheus label dispatch for DQ, quarantine, and policy metrics."""

from __future__ import annotations

from bioetl.domain.ports import MetricLabels
from bioetl.infrastructure.observability._prometheus_metric_label_dispatch_core import (
    _normalize_simple_string_label,
    _normalize_single_metric_label,
    _optional_string_label,
)
from bioetl.infrastructure.observability._prometheus_metric_label_normalizers import (
    normalize_dq_check_type,
    normalize_dq_disposition,
    normalize_dq_severity,
    normalize_dq_stage,
    normalize_quarantine_reason,
    normalize_record_flow_invariant,
    normalize_record_flow_invariant_status,
    normalize_silver_filter_field,
    normalize_silver_filter_reason_code,
    normalize_silver_filter_rule_type,
    normalize_structural_action,
    normalize_structural_comparison,
    normalize_terminal_status,
)

__all__ = ["normalize_policy_metric_labels"]


def normalize_policy_metric_labels(
    name: str,
    labels: MetricLabels,
) -> MetricLabels | None:
    """Normalize bounded labels for DQ, quarantine, silver-filter, and policy metrics."""
    for normalizer in (
        _normalize_quarantine_metric_labels,
        _normalize_dq_metric_labels,
        _normalize_silver_filter_metric_labels,
        _normalize_structural_metric_labels,
    ):
        normalized = normalizer(name, labels)
        if normalized is not None:
            return normalized
    return None


def _normalize_quarantine_metric_labels(
    name: str,
    labels: MetricLabels,
) -> MetricLabels | None:
    if name == "bioetl_quarantine_records_total":
        return _normalize_single_metric_label(
            labels,
            key="reason",
            default="other",
            normalize=normalize_quarantine_reason,
        )
    if name == "bioetl_dq_records_quarantined_total":
        return _normalize_simple_string_label(
            labels,
            key="run_type",
            default="unknown",
        )
    return None


def _normalize_dq_metric_labels(
    name: str,
    labels: MetricLabels,
) -> MetricLabels | None:
    if name == "bioetl_dq_dispositions_total":
        return {
            **labels,
            "stage": normalize_dq_stage(str(labels.get("stage", "other"))),
            "disposition": normalize_dq_disposition(
                str(labels.get("disposition", "other"))
            ),
            "terminal_status": normalize_terminal_status(
                str(labels.get("terminal_status", "other"))
            ),
        }
    if name == "bioetl_dq_validation_failures_total":
        return {
            **labels,
            "stage": normalize_dq_stage(str(labels.get("stage", "other"))),
            "severity": normalize_dq_severity(str(labels.get("severity", "other"))),
        }
    if name == "bioetl_record_flow_invariants_total":
        return {
            **labels,
            "invariant": normalize_record_flow_invariant(
                str(labels.get("invariant", "other"))
            ),
            "status": normalize_record_flow_invariant_status(
                str(labels.get("status", "other"))
            ),
        }
    if name == "bioetl_dq_check_failures_total":
        return {
            **labels,
            "stage": normalize_dq_stage(str(labels.get("stage", "other"))),
            "check_type": normalize_dq_check_type(
                str(labels.get("check_type", "other"))
            ),
            "severity": normalize_dq_severity(str(labels.get("severity", "other"))),
        }
    return None


def _normalize_silver_filter_metric_labels(
    name: str,
    labels: MetricLabels,
) -> MetricLabels | None:
    if name != "bioetl_silver_filter_rejections_total":
        return None
    return {
        **labels,
        "reason_code": normalize_silver_filter_reason_code(
            _optional_string_label(labels, "reason_code")
        ),
        "rule_type": normalize_silver_filter_rule_type(
            _optional_string_label(labels, "rule_type")
        ),
        "field": normalize_silver_filter_field(_optional_string_label(labels, "field")),
    }


def _normalize_structural_metric_labels(
    name: str,
    labels: MetricLabels,
) -> MetricLabels | None:
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
    return None
