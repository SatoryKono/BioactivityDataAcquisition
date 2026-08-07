"""Data Quality result value objects.

Immutable value objects representing Data Quality evaluation results.
Part of the domain layer - no I/O dependencies.

Note:
    DQEvaluationStatus is for DQ threshold checks (PASSED/WARNING/FAILED).
    This is distinct from QuarantineStatus in aggregates/quarantine_entry.py
    which tracks quarantine record lifecycle (NEW/UNDER_REVIEW/IGNORED/etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from bioetl.domain.types.dq_contracts import (
    DQDisposition,
    DQPolicyRef,
    DQRuleOutcome,
    DQViolationKind,
)
from bioetl.domain.value_objects.dq_anomaly import DQAnomaly


class DQEvaluationStatus(StrEnum):
    """Status of Data Quality evaluation.

    Represents the outcome of DQ threshold checks during pipeline execution.
    This enum is used for runtime DQ assessment, NOT for quarantine record status.

    For quarantine record lifecycle status, use QuarantineStatus from
    bioetl.domain.aggregates.quarantine_entry.

    Attributes:
        PASSED: Error rate is below soft_fail_threshold (< 5% by default).
        WARNING: Error rate is between soft and hard thresholds (5-20%).
        FAILED: Error rate exceeds hard_fail_threshold (> 50% default).

    Example:
        >>> from bioetl.domain.value_objects import DQEvaluationStatus
        >>> status = DQEvaluationStatus.PASSED
        >>> status.value
        'passed'
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
        rule_outcomes: List of individual rule evaluation outcomes (contract-based DQ).
        policy_ref: Reference to the governing DQ policy contract.
    """

    error_rate: float
    status: DQEvaluationStatus
    anomalies: tuple[DQAnomaly, ...] = field(default_factory=tuple)
    has_critical: bool = False
    check_duration_ms: float = 0.0
    rule_outcomes: tuple[DQRuleOutcome, ...] = field(default_factory=tuple)
    policy_ref: DQPolicyRef | None = None

    def __post_init__(self) -> None:
        """Validate and ensure immutability of anomalies and rule outcomes."""
        if isinstance(self.anomalies, list):
            object.__setattr__(self, "anomalies", tuple(self.anomalies))
        if isinstance(self.rule_outcomes, list):
            object.__setattr__(self, "rule_outcomes", tuple(self.rule_outcomes))

    @property
    def is_passed(self) -> bool:
        """Check if DQ evaluation passed (no threshold violations)."""
        return self.status == DQEvaluationStatus.PASSED

    @property
    def is_warning(self) -> bool:
        """Check if DQ evaluation resulted in warning."""
        return self.status == DQEvaluationStatus.WARNING

    @property
    def is_failed(self) -> bool:
        """Check if DQ evaluation failed."""
        return self.status == DQEvaluationStatus.FAILED

    @property
    def anomalies_count(self) -> int:
        """Count of detected anomalies."""
        return len(self.anomalies)

    @property
    def rule_outcomes_count(self) -> int:
        """Count of rule evaluation outcomes."""
        return len(self.rule_outcomes)

    @property
    def has_rule_violations(self) -> bool:
        """Check if any rules resulted in violations (non-PASS dispositions)."""
        return any(
            outcome.disposition != DQDisposition.PASS for outcome in self.rule_outcomes
        )

    @property
    def has_quarantine_decisions(self) -> bool:
        """Check if any rules resulted in quarantine decisions."""
        return any(
            outcome.disposition == DQDisposition.QUARANTINE
            for outcome in self.rule_outcomes
        )

    @property
    def has_fail_decisions(self) -> bool:
        """Check if any rules resulted in fail decisions."""
        return any(
            outcome.disposition == DQDisposition.FAIL for outcome in self.rule_outcomes
        )

    def get_outcomes_by_violation_kind(
        self, kind: DQViolationKind
    ) -> list[DQRuleOutcome]:
        """Get rule outcomes filtered by violation kind."""
        return [
            outcome for outcome in self.rule_outcomes if outcome.violation_kind == kind
        ]

    def get_outcomes_by_severity(self, severity: str) -> list[DQRuleOutcome]:
        """Get rule outcomes filtered by severity."""
        return [
            outcome for outcome in self.rule_outcomes if outcome.severity == severity
        ]


__all__ = ["DQEvaluationStatus", "DQResult"]
