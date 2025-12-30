"""Data Quality result value objects.

Immutable value objects representing Data Quality evaluation results.
Part of the domain layer - no I/O dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


class DQStatus(str, Enum):
    """Status of Data Quality evaluation.

    Represents the outcome of DQ threshold checks.

    Attributes:
        PASSED: Error rate is below soft_fail_threshold.
        WARNING: Error rate is between soft and hard thresholds.
        FAILED: Error rate exceeds hard_fail_threshold.
    """

    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class DQResult:
    """Result of Data Quality evaluation.

    Immutable value object containing the results of DQ checks
    including threshold evaluation and anomaly detection.

    Attributes:
        error_rate: Calculated error rate (0.0-1.0).
        status: Overall DQ status based on thresholds.
        anomalies: List of detected anomalies (empty if dq_monitor not available).
        has_critical: Whether any critical anomalies were found.
        check_duration_ms: Duration of anomaly detection in milliseconds.
    """

    error_rate: float
    status: DQStatus
    anomalies: tuple[Any, ...] = field(default_factory=tuple)
    has_critical: bool = False
    check_duration_ms: float = 0.0

    def __post_init__(self) -> None:
        """Validate and ensure immutability of anomalies."""
        if isinstance(self.anomalies, list):
            object.__setattr__(self, "anomalies", tuple(self.anomalies))

    @property
    def is_passed(self) -> bool:
        """Check if DQ evaluation passed (no threshold violations)."""
        return self.status == DQStatus.PASSED

    @property
    def is_warning(self) -> bool:
        """Check if DQ evaluation resulted in warning."""
        return self.status == DQStatus.WARNING

    @property
    def is_failed(self) -> bool:
        """Check if DQ evaluation failed."""
        return self.status == DQStatus.FAILED

    @property
    def anomalies_count(self) -> int:
        """Count of detected anomalies."""
        return len(self.anomalies)


__all__ = ["DQResult", "DQStatus"]
