"""Data quality monitor protocol port."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class DQMonitorPort(Protocol):
    """Port for data quality monitoring and anomaly detection."""

    def add_metric(
        self,
        metric_name: str,
        baseline: Sequence[float],
        min_threshold: float | None = None,
        max_threshold: float | None = None,
    ) -> None: ...

    def check_quality(
        self,
        metrics: dict[str, float],
    ) -> list[Any]:  # Any: list[Anomaly] (infrastructure type)
        ...

    def update_baseline_from_metrics(
        self,
        metrics: dict[str, float],
    ) -> None: ...

    def get_baseline_stats(
        self,
        metric_name: str,
    ) -> tuple[float, float, int] | None: ...
