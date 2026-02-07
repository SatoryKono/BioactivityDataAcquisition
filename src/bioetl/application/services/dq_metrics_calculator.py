"""Re-export DQMetricsCalculator from domain layer.

.. deprecated::
    This module re-exports DQMetricsCalculator and DQMetricsInput from the domain
    layer for backward compatibility. The actual implementation has been moved to
    ``bioetl.domain.services.dq_metrics_calculator``.

    New code should import directly from ``bioetl.domain.services``.
"""

import warnings

warnings.warn(
    "bioetl.application.services.dq_metrics_calculator is deprecated. "
    "Import from bioetl.domain.services instead.",
    DeprecationWarning,
    stacklevel=2,
)

from bioetl.domain.services.dq_metrics_calculator import (  # noqa: E402
    DQMetricsCalculator,
    DQMetricsInput,
)

__all__ = ["DQMetricsCalculator", "DQMetricsInput"]
