"""DQ monitor bootstrap helpers for runtime observability wiring."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.ports import DQMonitorPort, LoggerPort
from bioetl.infrastructure.observability.anomaly import DataQualityMonitor
from bioetl.infrastructure.observability.noop_logger import NoOpLogger

if TYPE_CHECKING:
    from bioetl.infrastructure.config import Settings


__all__ = [
    "bootstrap_dq_monitor",
    "bootstrap_dq_monitor_port",
]


def bootstrap_dq_monitor_port(
    settings: Settings,
    logger: LoggerPort | None = None,
    monitor_cls: type[DataQualityMonitor] = DataQualityMonitor,
    noop_logger_cls: type[NoOpLogger] = NoOpLogger,
) -> DQMonitorPort | None:
    """Create a data quality monitor port implementation.

    Returns:
        DQMonitorPort if DQ monitoring is enabled, None otherwise.
    """
    obs_settings = settings.observability

    if not obs_settings.dq_monitor_enabled:
        return None

    effective_logger = logger if logger is not None else noop_logger_cls()
    monitor = monitor_cls(
        logger=effective_logger,
        baseline_window=obs_settings.dq_baseline_window,
        z_score_threshold=obs_settings.dq_z_score_threshold,
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


def bootstrap_dq_monitor(
    settings: Settings,
    logger: LoggerPort | None = None,
    monitor_cls: type[DataQualityMonitor] = DataQualityMonitor,
    noop_logger_cls: type[NoOpLogger] = NoOpLogger,
) -> DQMonitorPort | None:
    """Deprecated alias for :func:`bootstrap_dq_monitor_port`.

    Returns:
        DQMonitorPort if DQ monitoring is enabled, None otherwise.
    """
    return bootstrap_dq_monitor_port(
        settings=settings,
        logger=logger,
        monitor_cls=monitor_cls,
        noop_logger_cls=noop_logger_cls,
    )
