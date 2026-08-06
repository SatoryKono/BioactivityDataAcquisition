"""Data quality monitor protocol port."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable

from bioetl.domain.value_objects.dq_anomaly import DQAnomaly


@runtime_checkable
class DQMonitorPort(Protocol):
    """Port for data quality monitoring and anomaly detection."""

    def add_metric(
        self,
        metric_name: str,
        baseline: Sequence[float],
        min_threshold: float | None = None,
        max_threshold: float | None = None,
    ) -> None:
        """Register a metric with its baseline distribution and optional thresholds.

        Args:
            metric_name: Unique name identifying the DQ metric.
            baseline: Historical baseline values for anomaly detection.
            min_threshold: Optional minimum acceptable value for the metric.
            max_threshold: Optional maximum acceptable value for the metric.
        """
        ...

    def check_quality(
        self,
        metrics: dict[str, float],
        timestamp: datetime,
    ) -> list[DQAnomaly]:
        """Evaluate metrics against baselines and return detected anomalies.

        Args:
            metrics: Mapping of metric name to current observed value.
            timestamp: Mandatory caller-owned timestamp for anomaly
                evaluation and emitted anomaly records. Adapters must not
                synthesize wall-clock time when the caller omits it.

        Returns:
            List of domain anomaly DTOs for metrics that deviate from baseline.
        """
        ...

    def update_baseline_from_metrics(
        self,
        metrics: dict[str, float],
        timestamp: datetime,
    ) -> None:
        """Update stored baselines by incorporating new observed metric values.

        Args:
            metrics: Mapping of metric name to newly observed value.
            timestamp: Mandatory caller-owned timestamp associated with
                this baseline update decision. Adapters must not invent time.
        """
        ...

    def get_baseline_stats(
        self,
        metric_name: str,
    ) -> tuple[float, float, int] | None:
        """Return summary statistics for the stored baseline of a metric.

        Args:
            metric_name: Name of the metric to query.

        Returns:
            Tuple of (mean, std_dev, sample_count), or None if metric is unknown.
        """
        ...
