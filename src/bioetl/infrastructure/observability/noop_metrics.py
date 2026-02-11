"""No-operation metrics implementation with optional usage warning.

Extends the canonical domain NoOpMetrics with a developer-facing warning
when metrics collection is silently disabled.

The base no-op behaviour (all methods are silent no-ops) is inherited from
``bioetl.domain.ports.noop.NoOpMetrics``.  This module adds only the
``warn_on_use`` / ``reset_warning`` helpers used by the composition layer.
"""

from __future__ import annotations

import warnings

from bioetl.domain.ports import MetricsPort, NoOpMetrics as _DomainNoOpMetrics


class NoOpMetrics(_DomainNoOpMetrics, MetricsPort):
    """No-operation metrics with optional usage warning.

    Extends the canonical domain NoOpMetrics with a ``warn_on_use`` flag.
    When *warn_on_use* is True (the default), a one-time ``UserWarning``
    is emitted to alert developers that metrics are not being collected.

    If instantiated with ``warn_on_use=False``, behaves identically to
    the domain NoOpMetrics (pure silent no-op).

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
