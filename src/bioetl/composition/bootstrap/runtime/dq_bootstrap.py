"""DQ monitor bootstrap helpers for runtime observability wiring."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, cast

from bioetl.domain.ports import DQMonitorPort, LoggerPort
from bioetl.infrastructure.observability.anomaly import DataQualityMonitor
from bioetl.infrastructure.observability.noop_logger import NoOpLogger

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.infrastructure.config._base import Settings


class _ConfigurableDQMonitor(DQMonitorPort, Protocol):
    """DQ monitor contract with detector configuration support."""

    detector: _DQDetectorConfig


class _DQDetectorConfig(Protocol):
    """Configuration surface used by bootstrap when wiring DQ thresholds."""

    min_baseline_samples: int

    def set_threshold(
        self,
        metric_name: str,
        *,
        min_value: float,
        max_value: float,
    ) -> None: ...


__all__ = [
    "bootstrap_dq_monitor",
]


def bootstrap_dq_monitor(
    settings: Settings,
    logger: LoggerPort | None = None,
    monitor_factory: Callable[..., DQMonitorPort] = DataQualityMonitor,
    noop_logger_factory: Callable[[], LoggerPort] = NoOpLogger,
) -> DQMonitorPort | None:
    """Create a data quality monitor port implementation.

    Args:
        settings: Application settings providing DQ monitoring flags, baseline window,
            Z-score threshold, error rate max, and quality score min.
        logger: Optional LoggerPort for structured DQ monitor logging; uses NoOpLogger
            when None.
        monitor_factory: Factory creating the DQ monitor implementation.
        noop_logger_factory: Factory used when no logger is provided.

    Returns:
        DQMonitorPort if DQ monitoring is enabled, None otherwise.
    """
    obs_settings = settings.observability

    if not obs_settings.dq_monitor_enabled:
        return None

    effective_logger = logger if logger is not None else noop_logger_factory()
    monitor = cast(
        _ConfigurableDQMonitor,
        monitor_factory(
            logger=effective_logger,
            baseline_window=obs_settings.dq_baseline_window,
            z_score_threshold=obs_settings.dq_z_score_threshold,
        ),
    )

    monitor.detector.min_baseline_samples = obs_settings.dq_min_baseline_samples
    monitor.detector.set_threshold(
        "error_rate",
        min_value=0.0,
        max_value=obs_settings.dq_error_rate_max,
    )
    monitor.detector.set_threshold(
        "quality_score",
        min_value=obs_settings.dq_quality_score_min,
        max_value=1.0,
    )

    return monitor
