"""Base protocol for anomaly detection strategies.

Defines interface that all detection algorithms must implement.
"""

from __future__ import annotations

__all__ = ["DetectorStrategy"]


from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bioetl.infrastructure.observability.anomaly.types import (
        AnomalyRecord,
        AnomalySeverity,
    )


class DetectorStrategy(ABC):
    """Abstract base for anomaly detection algorithms.

    All detection strategies must implement:
    - detect(): Analyze value against baseline
    - get_severity(): Map score to severity level

    Strategies should be stateless; baseline data is passed to detect().
    """

    @abstractmethod
    def detect(
        self,
        metric_name: str,
        current_value: float,
        baseline: Sequence[float],
        threshold: float,
        timestamp: datetime,
    ) -> AnomalyRecord | None:
        """Detect anomaly in current value.

        Args:
            metric_name: Name of metric being analyzed
            current_value: Current observed value
            baseline: Historical values for comparison
            threshold: Detection threshold (interpretation varies by strategy)
            timestamp: Timestamp for the anomaly (created in application layer)

        Returns:
            AnomalyRecord if detected, None otherwise

        """

    @abstractmethod
    def get_severity(self, score: float) -> AnomalySeverity:
        """Map detection score to severity level.

        Args:
            score: Detection score (e.g., z-score, IQR multiplier)

        Returns:
            Severity level based on score

        """
