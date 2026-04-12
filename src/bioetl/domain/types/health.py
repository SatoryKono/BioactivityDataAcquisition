"""Health check and validation value objects for BioETL domain layer.

Frozen dataclasses for health reports and preflight validation.
No I/O operations allowed (REQ-ARCH-003).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from bioetl.domain.types.enums import HealthStatus
from bioetl.domain.types_config_validation import ConfigValidationError

__all__ = [
    "ComponentHealthResult",
    "HealthReport",
    "PreflightReport",
    "ValidationResult",
]


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Result of record validation.

    Attributes:
        valid: True if validation passed.
        errors: List of validation errors (empty if valid=True).
    """

    valid: bool
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ComponentHealthResult:
    """Result of a single component health check.

    Attributes:
        component: Name of the component (e.g., 'storage', 'data_source').
        status: Health status of the component.
        duration_seconds: Time taken to perform the health check.
        error_message: Optional error message if check failed.
        provider: Optional provider identity for enhanced health-check probes.
        latency_ms: Optional provider probe latency in milliseconds.
        probe_fallback_reason: Optional deterministic probe-mode fallback reason.
    """

    component: str
    status: HealthStatus
    duration_seconds: float
    error_message: str | None = None
    provider: str | None = None
    latency_ms: float | None = None
    probe_fallback_reason: str | None = None


@dataclass(frozen=True, slots=True)
class HealthReport:
    """Aggregated health check report.

    Attributes:
        results: List of individual component health results.
        checked_at: Timestamp when checks were performed.
    """

    results: list[ComponentHealthResult]
    checked_at: datetime | None = None

    @property
    def is_healthy(self) -> bool:
        """Return True if all critical components are healthy."""
        return all(r.status != HealthStatus.UNHEALTHY for r in self.results)

    @property
    def overall_status(self) -> HealthStatus:
        """Return worst status among all components."""
        if not self.results:
            return HealthStatus.HEALTHY

        statuses = [r.status for r in self.results]
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY

    def get_failures(self) -> list[ComponentHealthResult]:
        """Return list of components with UNHEALTHY status.

        Returns:
            Failures.
        """
        return [r for r in self.results if r.status == HealthStatus.UNHEALTHY]


@dataclass(frozen=True, slots=True)
class PreflightReport:
    """Preflight validation report.

    Aggregates results from infrastructure health checks and
    medallion policy validation.

    Attributes:
        health_report: Infrastructure health check results.
        medallion_policy_valid: True if config is compatible with policy.
        config_errors: List of configuration validation errors.
        checked_at: Timestamp when validation was performed.
    """

    health_report: HealthReport
    medallion_policy_valid: bool
    config_errors: list[ConfigValidationError] = field(default_factory=list)
    checked_at: datetime | None = None

    @property
    def is_valid(self) -> bool:
        """Return True if all validations passed."""
        return self.health_report.is_healthy and self.medallion_policy_valid

    @property
    def should_block_startup(self) -> bool:
        """Return True if validation failures should block pipeline startup."""
        return not self.medallion_policy_valid or not self.health_report.is_healthy
