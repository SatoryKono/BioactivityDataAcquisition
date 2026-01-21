"""Re-export DQMetricsCalculator from domain layer.

This module re-exports DQMetricsCalculator and DQMetricsInput from the domain
layer for backward compatibility. The actual implementation has been moved to
bioetl.domain.services.dq_metrics_calculator to fix architecture violations
(infrastructure layer cannot import from application layer).

New code should import directly from bioetl.domain.services.
"""

from bioetl.domain.services.dq_metrics_calculator import (
    DQMetricsCalculator,
    DQMetricsInput,
)

__all__ = ["DQMetricsCalculator", "DQMetricsInput"]
