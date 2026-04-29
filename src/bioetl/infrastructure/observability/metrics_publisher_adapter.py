"""Adapter for metrics publication to Pushgateway-like sinks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.infrastructure.observability.server import (
    delete_metrics_from_gateway,
    push_metrics_to_gateway,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricLabels

__all__ = ["MetricsPublisherAdapter"]


class MetricsPublisherAdapter:
    """Infrastructure adapter implementing composition-owned metrics publication."""

    def __init__(self, logger: LoggerPort | None = None) -> None:
        self._logger = logger

    def push_to_gateway(
        self,
        *,
        gateway: str,
        run_label: str,
        grouping_key: MetricLabels | None = None,
    ) -> bool:
        """Publish current metrics to the configured gateway."""
        return push_metrics_to_gateway(
            gateway=gateway,
            run_label=run_label,
            grouping_key=grouping_key,
            logger=self._logger,
        )

    def delete_from_gateway(
        self,
        *,
        gateway: str,
        run_label: str,
        grouping_key: MetricLabels | None = None,
    ) -> bool:
        """Delete current metrics from the configured gateway."""
        return delete_metrics_from_gateway(
            gateway=gateway,
            run_label=run_label,
            grouping_key=grouping_key,
            logger=self._logger,
        )
