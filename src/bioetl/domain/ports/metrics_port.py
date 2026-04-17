"""Metrics port interface for BioETL.

This module defines the MetricsPort protocol that provides a metrics
collection interface for the application. All metrics implementations
should conform to this interface.

REQ-OBS-003: Metrics should be collected consistently
REQ-OBS-004: Metrics should include tags for filtering
"""

from __future__ import annotations

from typing import Any, Protocol


class MetricsPort(Protocol):
    """Metrics port protocol for collecting application metrics.

    This protocol defines the metrics interface that should be implemented
    by all metrics adapters in the infrastructure layer.
    """

    def increment(
        self,
        metric_name: str,
        value: float = 1.0,
        tags: dict[str, Any] | None = None,  # Any: Generic tag values for metric filtering
    ) -> None:
        """Increment a counter metric.

        Args:
            metric_name: Name of the metric
            value: Value to increment by (default: 1.0)
            tags: Optional tags for metric filtering
        """
        ...

    def gauge(
        self,
        metric_name: str,
        value: float,
        tags: dict[str, Any] | None = None,  # Any: Generic tag values for metric filtering
    ) -> None:
        """Set a gauge metric to a specific value.

        Args:
            metric_name: Name of the metric
            value: Value to set
            tags: Optional tags for metric filtering
        """
        ...

    def timing(
        self,
        metric_name: str,
        value: float,
        tags: dict[str, Any] | None = None,  # Any: Generic tag values for metric filtering
    ) -> None:
        """Record a timing metric.

        Args:
            metric_name: Name of the metric
            value: Time value in milliseconds
            tags: Optional tags for metric filtering
        """
        ...

    def histogram(
        self,
        metric_name: str,
        value: float,
        tags: dict[str, Any] | None = None,  # Any: Generic tag values for metric filtering
    ) -> None:
        """Record a histogram metric.

        Args:
            metric_name: Name of the metric
            value: Value to record
            tags: Optional tags for metric filtering
        """
        ...
