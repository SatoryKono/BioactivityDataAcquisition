"""Business-rule and quality profile DQ result value objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Mapping

from bioetl.domain.types import GoldRejectReason
from bioetl.domain.value_objects.dq_report_enums import DQCheckStatus


@dataclass(frozen=True, slots=True)
class CompletenessResult:
    """Completeness check result for Gold layer."""

    required_fields: Mapping[str, float]
    overall_completeness_score: float
    minimum_threshold: float
    status: DQCheckStatus
    reject_reasons: tuple[GoldRejectReason, ...] = ()

    def __post_init__(self) -> None:
        """Convert lists to tuples and freeze mappings."""
        if isinstance(self.reject_reasons, list):
            object.__setattr__(self, "reject_reasons", tuple(self.reject_reasons))
        object.__setattr__(
            self,
            "required_fields",
            MappingProxyType(dict(self.required_fields)),
        )


@dataclass(frozen=True, slots=True)
class BusinessRuleResult:
    """Single business rule check result."""

    rule_id: str
    name: str
    description: str
    passed: bool
    violations: int | None  # None indicates unknown (e.g., exception during check)
    config_path: str | None = None
    layer: str | None = None
    field: str | None = None
    severity: str | None = None
    decision: str | None = None
    reject_reason: GoldRejectReason | None = None


@dataclass(frozen=True, slots=True)
class BusinessRulesResult:
    """Business rules check result."""

    rules_evaluated: int
    rules_passed: int
    rules_failed: int
    rules: tuple[BusinessRuleResult, ...] = ()
    status: DQCheckStatus = DQCheckStatus.PASS

    def __post_init__(self) -> None:
        """Convert lists to tuples for immutability."""
        if isinstance(self.rules, list):
            object.__setattr__(self, "rules", tuple(self.rules))


@dataclass(frozen=True, slots=True)
class ForeignKeyResult:
    """Foreign key check result."""

    reference: str
    total_references: int
    valid_references: int
    orphan_records: int
    status: DQCheckStatus
    note: str | None = None
    reject_reason: GoldRejectReason | None = None


@dataclass(frozen=True, slots=True)
class ReferentialIntegrityResult:
    """Referential integrity check result."""

    foreign_keys: Mapping[str, ForeignKeyResult] = field(default_factory=dict)
    status: DQCheckStatus = DQCheckStatus.PASS

    def __post_init__(self) -> None:
        """Freeze foreign_keys mapping."""
        object.__setattr__(
            self,
            "foreign_keys",
            MappingProxyType(dict(self.foreign_keys)),
        )


@dataclass(frozen=True, slots=True)
class StatisticalMetric:
    """Single statistical metric for profiling."""

    current: float
    baseline: float
    ratio: float
    threshold_warning: float
    threshold_critical: float
    status: DQCheckStatus


@dataclass(frozen=True, slots=True)
class StatisticalProfileResult:
    """Statistical profile check result."""

    baseline_period_days: int
    metrics: Mapping[str, StatisticalMetric] = field(default_factory=dict)
    status: DQCheckStatus = DQCheckStatus.PASS

    def __post_init__(self) -> None:
        """Freeze metrics mapping."""
        object.__setattr__(
            self,
            "metrics",
            MappingProxyType(dict(self.metrics)),
        )


@dataclass(frozen=True, slots=True)
class AnomalyMetric:
    """Single anomaly detection metric."""

    metric: str
    current_value: float
    baseline_value: float | None = None
    zscore: float | None = None
    threshold_warning: float | None = None
    threshold_critical: float | None = None
    status: str = "normal"


@dataclass(frozen=True, slots=True)
class AnomalyDetectionResult:
    """AnomalyRecord detection check result."""

    cold_start_days: int
    current_day: int
    cold_start_mode: bool
    anomalies_detected: tuple[str, ...] = ()
    metrics_monitored: tuple[AnomalyMetric, ...] = ()
    status: DQCheckStatus = DQCheckStatus.PASS

    def __post_init__(self) -> None:
        """Convert lists to tuples for immutability."""
        if isinstance(self.anomalies_detected, list):
            object.__setattr__(
                self, "anomalies_detected", tuple(self.anomalies_detected)
            )
        if isinstance(self.metrics_monitored, list):
            object.__setattr__(self, "metrics_monitored", tuple(self.metrics_monitored))


@dataclass(frozen=True, slots=True)
class SCDIntegrityResult:
    """SCD (Slowly Changing Dimension) integrity check result."""

    scd_type: int
    total_entities: int
    entities_with_history: int
    avg_versions_per_entity: float
    version_gaps: int
    temporal_conflicts: int
    overlapping_validity_periods: int
    status: DQCheckStatus = DQCheckStatus.PASS


@dataclass(frozen=True, slots=True)
class DataFreshnessResult:
    """Data freshness check result."""

    max_updated_at: datetime | None
    freshness_lag_seconds: float
    freshness_lag_hours: float
    status: DQCheckStatus


__all__ = [
    "AnomalyDetectionResult",
    "AnomalyMetric",
    "BusinessRuleResult",
    "BusinessRulesResult",
    "CompletenessResult",
    "DataFreshnessResult",
    "ForeignKeyResult",
    "ReferentialIntegrityResult",
    "SCDIntegrityResult",
    "StatisticalMetric",
    "StatisticalProfileResult",
]
