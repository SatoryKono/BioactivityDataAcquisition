"""No-operation metrics implementation with optional startup warning.

Extends the domain NoOpMetrics with a warn_on_use mechanism to alert
developers when metrics collection is disabled in non-test environments.

The base no-op behavior is defined in bioetl.domain.ports.noop.NoOpMetrics.
This subclass adds only the warning infrastructure for composition layer use.
"""

from __future__ import annotations

import warnings

from bioetl.domain.ports.noop import NoOpMetrics as _DomainNoOpMetrics


class NoOpMetrics(_DomainNoOpMetrics):
    """No-operation metrics with optional startup warning.

    Inherits all no-op metric methods from domain.ports.noop.NoOpMetrics.
    Adds warn_on_use flag for composition/CLI layers that intentionally
    opt out of metrics collection.

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
        if warn_on_use and not NoOpMetrics._warned:
            warnings.warn(
                "NoOpMetrics is being used - metrics are NOT being collected. "
                "Set BIOETL_METRICS_ENABLED=true or inject PrometheusMetrics "
                "to enable metrics collection.",
                UserWarning,
                stacklevel=2,
            )
            NoOpMetrics._warned = True

    @classmethod
    def reset_warning(cls) -> None:
        """Reset warning state (for testing)."""
        cls._warned = False
