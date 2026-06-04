"""Prometheus label dispatch for publication and workflow-stage metrics."""

from __future__ import annotations

from bioetl.domain.ports import MetricLabels
from bioetl.infrastructure.observability._prometheus_metric_label_normalizers import (
    normalize_batch_lifecycle_event,
    normalize_observability_component,
    normalize_observability_mode,
    normalize_publication_status,
    normalize_publication_target,
    normalize_publication_vocab_field,
    normalize_publication_vocab_handling,
    normalize_publication_vocab_provider,
    normalize_runtime_phase,
    normalize_runtime_stage,
    normalize_stage_model_outcome,
    normalize_stage_model_stage,
)
from bioetl.infrastructure.observability.prometheus_metric_label_policy_sets import (
    _BATCH_LIFECYCLE_LABEL_METRICS,
    _METRICS_PUBLICATION_LABEL_METRICS,
    _OBSERVABILITY_RUNTIME_STATUS_METRICS,
    _OUTPUT_ARTIFACT_PUBLICATION_LABEL_METRICS,
    _PHASE_LABEL_KEY_BY_METRIC_GROUP,
    _PUBLICATION_VOCAB_DRIFT_LABEL_METRICS,
    _STAGE_BACKLOG_LABEL_METRICS,
    _STAGE_LAG_LABEL_METRICS,
    _STAGE_MODEL_LABEL_METRICS,
)

__all__ = ["normalize_publication_metric_labels"]


def normalize_publication_metric_labels(
    name: str,
    labels: MetricLabels,
) -> MetricLabels | None:
    """Normalize publication lifecycle, registry, stage, and composite labels."""
    for normalizer in (
        _normalize_publication_lifecycle_labels,
        _normalize_publication_registry_labels,
        _normalize_publication_stage_labels,
        _normalize_composite_phase_labels,
    ):
        normalized = normalizer(name, labels)
        if normalized is not None:
            return normalized
    return None


def _normalize_publication_lifecycle_labels(
    name: str,
    labels: MetricLabels,
) -> MetricLabels | None:
    if name in _BATCH_LIFECYCLE_LABEL_METRICS:
        return {
            **labels,
            "event": normalize_batch_lifecycle_event(str(labels.get("event", "other"))),
            "stage": normalize_runtime_stage(str(labels.get("stage", "other"))),
            "status": normalize_publication_status(str(labels.get("status", "other"))),
        }
    if name in _OUTPUT_ARTIFACT_PUBLICATION_LABEL_METRICS:
        return {
            **labels,
            "stage": normalize_runtime_stage(str(labels.get("stage", "other"))),
            "status": normalize_publication_status(str(labels.get("status", "other"))),
        }
    return None


def _normalize_publication_registry_labels(
    name: str,
    labels: MetricLabels,
) -> MetricLabels | None:
    if name in _METRICS_PUBLICATION_LABEL_METRICS:
        return {
            **labels,
            "target": normalize_publication_target(str(labels.get("target", "other"))),
            "status": normalize_publication_status(str(labels.get("status", "other"))),
        }
    if name in _PUBLICATION_VOCAB_DRIFT_LABEL_METRICS:
        return {
            **labels,
            "provider": normalize_publication_vocab_provider(
                str(labels.get("provider", "other"))
            ),
            "field": normalize_publication_vocab_field(
                str(labels.get("field", "other"))
            ),
            "handling": normalize_publication_vocab_handling(
                str(labels.get("handling", "other"))
            ),
        }
    if name in _OBSERVABILITY_RUNTIME_STATUS_METRICS:
        return {
            **labels,
            "component": normalize_observability_component(
                str(labels.get("component", "other"))
            ),
            "mode": normalize_observability_mode(str(labels.get("mode", "other"))),
        }
    return None


def _normalize_publication_stage_labels(
    name: str,
    labels: MetricLabels,
) -> MetricLabels | None:
    if name in _STAGE_BACKLOG_LABEL_METRICS:
        return {
            **labels,
            "stage": normalize_stage_model_stage(str(labels.get("stage", "other"))),
        }
    if name in _STAGE_LAG_LABEL_METRICS:
        return {
            **labels,
            "stage": normalize_runtime_stage(str(labels.get("stage", "other"))),
        }
    if name in _STAGE_MODEL_LABEL_METRICS:
        return {
            **labels,
            "stage": normalize_stage_model_stage(str(labels.get("stage", "other"))),
            "outcome": normalize_stage_model_outcome(
                str(labels.get("outcome", "other"))
            ),
        }
    return None


def _normalize_composite_phase_labels(
    name: str,
    labels: MetricLabels,
) -> MetricLabels | None:
    for metric_group, label_key, label_normalizer in _PHASE_LABEL_KEY_BY_METRIC_GROUP:
        if name in metric_group:
            return {
                **labels,
                "phase": normalize_runtime_phase(str(labels.get("phase", "other"))),
                label_key: label_normalizer(str(labels.get(label_key, "other"))),
            }
    return None
