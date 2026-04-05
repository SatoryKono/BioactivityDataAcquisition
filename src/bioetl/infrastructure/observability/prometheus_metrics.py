"""Prometheus Metrics adapter implementing MetricsPort.

Provides concrete implementation of the MetricsPort interface using
Prometheus client library.
"""

from __future__ import annotations

from bioetl.domain.ports import MetricLabels, MetricsPort, resolve_metric_labels
from bioetl.infrastructure.observability.prometheus_metric_label_policies import (
    normalize_dq_severity,
    normalize_dq_stage,
    normalize_metric_dispatch_labels,
    normalize_quarantine_reason,
    normalize_silver_filter_field,
    normalize_silver_filter_reason_code,
    normalize_silver_filter_rule_type,
)
from bioetl.infrastructure.observability.prometheus_metric_registries import (
    COUNTERS,
    GAUGES,
    HISTOGRAMS,
)

__all__ = ["COUNTERS", "GAUGES", "HISTOGRAMS", "PrometheusMetrics"]


class PrometheusMetrics(MetricsPort):
    """Prometheus implementation of MetricsPort.

    Uses the generic MetricsPort API with standardized metric names that map
    into ``HISTOGRAMS``, ``COUNTERS``, and ``GAUGES`` registries.

    Extension rule: add new metric definitions in
    ``infrastructure/observability/metrics.py`` and register them in this
    module, rather than creating duplicate domain-level metrics interfaces.
    """

    def __init__(self) -> None:
        self._closed = False

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: MetricLabels | None = None,
        *,
        _labels: MetricLabels | None = None,
        tags: MetricLabels | None = None,
    ) -> None:
        """Record a histogram observation for the named metric.

        Args:
            name: Identifier name.
            value: Input value.
            labels: Labels dict (primary parameter).
            _labels: Alias for labels (backward compatibility).
            tags: Alias for labels (alternative naming convention).
        """
        resolved_labels = resolve_metric_labels(
            labels,
            _labels=_labels,
            tags=tags,
        )
        if name in HISTOGRAMS:
            HISTOGRAMS[name].labels(**resolved_labels).observe(value)

    def increment_counter(
        self,
        name: str,
        value: int,
        labels: MetricLabels | None = None,
        *,
        _labels: MetricLabels | None = None,
        tags: MetricLabels | None = None,
    ) -> None:
        """Increment a counter metric by the given value.

        Args:
            name: Identifier name.
            value: Input value.
            labels: Labels dict (primary parameter).
            _labels: Alias for labels (backward compatibility).
            tags: Alias for labels (alternative naming convention).
        """
        resolved_labels = resolve_metric_labels(
            labels,
            _labels=_labels,
            tags=tags,
        )
        if name in COUNTERS:
            COUNTERS[name].labels(
                **normalize_metric_dispatch_labels(name, resolved_labels)
            ).inc(value)

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: MetricLabels | None = None,
        *,
        _labels: MetricLabels | None = None,
        tags: MetricLabels | None = None,
    ) -> None:
        """Set a gauge metric to the given value.

        Args:
            name: Identifier name.
            value: Input value.
            labels: Labels dict (primary parameter).
            _labels: Alias for labels (backward compatibility).
            tags: Alias for labels (alternative naming convention).
        """
        resolved_labels = resolve_metric_labels(
            labels,
            _labels=_labels,
            tags=tags,
        )
        if name in GAUGES:
            GAUGES[name].labels(**resolved_labels).set(value)

    def inc_quarantine_records(
        self, pipeline: str, reason: str, count: int = 1
    ) -> None:
        """Increment quarantine record counter with normalized reason label.

        Args:
            pipeline: Pipeline.
            reason: Reason description.
            count: Count.
        """
        bounded_reason = normalize_quarantine_reason(reason)
        self.increment_counter(
            "quarantine_records_total",
            count,
            {"pipeline": pipeline, "reason": bounded_reason},
        )

    def inc_dq_validation_failures(
        self,
        pipeline: str,
        stage: str,
        severity: str,
        count: int = 1,
    ) -> None:
        """Increment DQ validation failure counter with normalized labels.

        Args:
            pipeline: Pipeline.
            stage: Stage.
            severity: Severity.
            count: Count.
        """
        bounded_stage = normalize_dq_stage(stage)
        bounded_severity = normalize_dq_severity(severity)
        self.increment_counter(
            "dq_validation_failures_total",
            count,
            {
                "pipeline": pipeline,
                "stage": bounded_stage,
                "severity": bounded_severity,
            },
        )

    def inc_silver_filter_rejections(
        self,
        pipeline: str,
        run_type: str,
        reason_code: str | None = None,
        rule_type: str | None = None,
        field: str | None = None,
        count: int = 1,
    ) -> None:
        """Increment bounded Silver filter rejection breakdown counters."""
        self.increment_counter(
            "silver_filter_rejections_total",
            count,
            {
                "pipeline": pipeline,
                "run_type": run_type,
                "reason_code": normalize_silver_filter_reason_code(reason_code),
                "rule_type": normalize_silver_filter_rule_type(rule_type),
                "field": normalize_silver_filter_field(field),
            },
        )

    def close(self) -> None:
        """Mark the metrics adapter as closed (idempotent)."""
        if self._closed:
            return
        self._closed = True
