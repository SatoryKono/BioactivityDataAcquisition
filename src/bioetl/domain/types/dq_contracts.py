"""Domain types for Data Quality contracts and canonical models.

This module defines the core value objects and enums for the contract-based DQ system,
following the canonical kernel approach from the architecture plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DQDisposition(StrEnum):
    """Canonical dispositions for DQ rule outcomes.

    Represents the final decision about how to handle a data quality violation.
    """

    PASS = "pass"  # No violation detected  # nosec B105
    WARN = "warn"  # Violation detected but not severe enough for action
    QUARANTINE = "quarantine"  # Isolate records for review
    SKIP = "skip"  # Skip processing this data
    FAIL = "fail"  # Hard failure - stop processing


class DQViolationKind(StrEnum):
    """Categories of DQ violations.

    Distinguishes between different types of quality issues for proper handling.
    """

    SCHEMA_VIOLATION = "schema_violation"  # Data doesn't match expected schema
    THRESHOLD_BREACH = "threshold_breach"  # Metric exceeds configured threshold
    BUSINESS_RULE_VIOLATION = "business_rule_violation"  # Violates business logic
    CROSS_VALIDATION_MISMATCH = (
        "cross_validation_mismatch"  # Composite validation failure
    )
    ANOMALY_SIGNAL = "anomaly_signal"  # Statistical anomaly detected


@dataclass(frozen=True)
class DQPolicyRef:
    """Reference to a specific DQ policy contract.

    Provides immutable reference to the contract version and rule bundle
    that governs data quality decisions.
    """

    contract_ref: str
    contract_version: str
    rule_bundle_version: str
    policy_hash: str | None = None

    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.contract_ref:
            raise ValueError("contract_ref cannot be empty")
        if not self.contract_version:
            raise ValueError("contract_version cannot be empty")
        if not self.rule_bundle_version:
            raise ValueError("rule_bundle_version cannot be empty")


@dataclass(frozen=True)
class DQRuleOutcome:
    """Immutable outcome of a single DQ rule evaluation.

    Represents the result of applying a specific data quality rule,
    including the disposition decision and provenance information.
    """

    rule_id: str
    violation_kind: DQViolationKind
    severity: str
    disposition: DQDisposition
    disposition_reason: str | None = None
    affected_fields: list[str] | None = None
    config_path: str | None = None
    policy_ref: DQPolicyRef | None = None

    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.rule_id:
            raise ValueError("rule_id cannot be empty")
        if not self.severity:
            raise ValueError("severity cannot be empty")

        # Ensure affected_fields is initialized
        if self.affected_fields is None:
            object.__setattr__(self, "affected_fields", [])


@dataclass(frozen=True)
class DQRuleProvenance:
    """Compact provenance information for metadata sidecars.

    Contains stable reference to rule outcomes for metadata tracking,
    designed to be lightweight compared to full DQRuleOutcome.
    """

    rule_id: str
    contract_version: str
    severity: str
    disposition: DQDisposition
    config_path: str | None = None
    report_artifact_path: str | None = None
    policy_hash: str | None = None

    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.rule_id:
            raise ValueError("rule_id cannot be empty")
        if not self.contract_version:
            raise ValueError("contract_version cannot be empty")
        if not self.severity:
            raise ValueError("severity cannot be empty")


# Convenience function for creating provenance from outcome


def create_provenance_from_outcome(
    outcome: DQRuleOutcome,
    policy_ref: DQPolicyRef,
    report_path: str | None = None,
) -> DQRuleProvenance:
    """Create compact provenance from a rule outcome."""
    return DQRuleProvenance(
        rule_id=outcome.rule_id,
        contract_version=policy_ref.contract_version,
        severity=outcome.severity,
        disposition=outcome.disposition,
        config_path=outcome.config_path,
        report_artifact_path=report_path,
        policy_hash=policy_ref.policy_hash,
    )
