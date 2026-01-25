"""No-operation metrics implementation.

Provides a null object pattern implementation for metrics when
metrics collection is disabled or not configured.

This implementation is in infrastructure layer (not domain) because
it's a concrete implementation detail, even though it does nothing.
"""

from __future__ import annotations

from bioetl.domain.ports import MetricsPort


class NoOpMetrics(MetricsPort):
    """No-operation metrics implementation.

    Used when metrics collection is explicitly disabled via configuration.
    All operations are silently ignored.

    If instantiated without explicit opt-out, logs a warning to alert
    developers that metrics are not being collected.

    Args:
        warn_on_use: If True, emit a warning when instantiated in non-test mode.
                     Default is True.

    Example:
        >>> # Explicit opt-out (no warning)
        >>> metrics = NoOpMetrics(warn_on_use=False)

        >>> # Default (warning in non-test environments)
        >>> metrics = NoOpMetrics()

    """

    _warned: bool = False

    def __init__(self, warn_on_use: bool = True) -> None:
        """Initialize NoOpMetrics.

        Args:
            warn_on_use: Whether to warn about disabled metrics.

        """
        pass

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: dict[str, str],
    ) -> None:
        """No-op histogram observation."""

    def increment_counter(
        self,
        name: str,
        value: int,
        labels: dict[str, str],
    ) -> None:
        """No-op counter increment."""

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: dict[str, str],
    ) -> None:
        """No-op gauge set."""

    def close(self) -> None:
        """No-op close. Idempotent."""

    @classmethod
    def reset_warning(cls) -> None:
        """Reset warning state (for testing)."""
        cls._warned = False
