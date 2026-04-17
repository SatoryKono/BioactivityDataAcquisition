"""Tests for health check and validation value objects.

Tests for ValidationResult, ComponentHealthResult, HealthReport, PreflightReport.
"""

from __future__ import annotations

import pytest

from bioetl.domain.types.enums import HealthStatus
from bioetl.domain.types.health import (
    ComponentHealthResult,
    HealthReport,
    PreflightReport,
    ValidationResult,
)
from bioetl.domain.types_config_validation import ConfigValidationError


@pytest.mark.unit
class TestValidationResult:
    """Tests for ValidationResult frozen dataclass."""

    def test_valid_result(self) -> None:
        result = ValidationResult(valid=True)
        assert result.valid is True
        assert result.errors == []

    def test_invalid_result_with_errors(self) -> None:
        errors = ["field is required", "value out of range"]
        result = ValidationResult(valid=False, errors=errors)
        assert result.valid is False
        assert result.errors == errors

    def test_frozen(self) -> None:
        result = ValidationResult(valid=True)
        with pytest.raises(AttributeError):
            result.valid = False  # type: ignore[misc]


@pytest.mark.unit
class TestComponentHealthResult:
    """Tests for ComponentHealthResult frozen dataclass."""

    def test_healthy_component(self) -> None:
        result = ComponentHealthResult(
            component="storage",
            status=HealthStatus.HEALTHY,
            duration_seconds=0.5,
        )
        assert result.component == "storage"
        assert result.status == HealthStatus.HEALTHY
        assert result.duration_seconds == pytest.approx(0.5)
        assert result.error_message is None

    def test_unhealthy_component_with_error(self) -> None:
        result = ComponentHealthResult(
            component="data_source",
            status=HealthStatus.UNHEALTHY,
            duration_seconds=5.0,
            error_message="Connection refused",
        )
        assert result.status == HealthStatus.UNHEALTHY
        assert result.error_message == "Connection refused"


@pytest.mark.unit
class TestHealthReport:
    """Tests for HealthReport frozen dataclass."""

    def _make_result(
        self,
        component: str = "test",
        status: HealthStatus = HealthStatus.HEALTHY,
    ) -> ComponentHealthResult:
        return ComponentHealthResult(
            component=component, status=status, duration_seconds=0.1
        )

    def test_all_healthy(self) -> None:
        report = HealthReport(
            results=[
                self._make_result("storage"),
                self._make_result("data_source"),
            ]
        )
        assert report.is_healthy is True
        assert report.overall_status == HealthStatus.HEALTHY
        assert report.get_failures() == []

    def test_one_unhealthy_component(self) -> None:
        report = HealthReport(
            results=[
                self._make_result("storage", HealthStatus.HEALTHY),
                self._make_result("data_source", HealthStatus.UNHEALTHY),
            ]
        )
        assert report.is_healthy is False
        assert report.overall_status == HealthStatus.UNHEALTHY
        failures = report.get_failures()
        assert len(failures) == 1
        assert failures[0].component == "data_source"

    def test_degraded_status(self) -> None:
        report = HealthReport(
            results=[
                self._make_result("storage", HealthStatus.HEALTHY),
                self._make_result("data_source", HealthStatus.DEGRADED),
            ]
        )
        assert report.is_healthy is True  # DEGRADED is not UNHEALTHY
        assert report.overall_status == HealthStatus.DEGRADED

    def test_empty_results(self) -> None:
        report = HealthReport(results=[])
        assert report.is_healthy is True
        assert report.overall_status == HealthStatus.HEALTHY

    def test_unhealthy_takes_precedence_over_degraded(self) -> None:
        report = HealthReport(
            results=[
                self._make_result("a", HealthStatus.DEGRADED),
                self._make_result("b", HealthStatus.UNHEALTHY),
            ]
        )
        assert report.overall_status == HealthStatus.UNHEALTHY

    def test_checked_at_has_default(self) -> None:
        report = HealthReport(results=[])
        assert report.checked_at is None


@pytest.mark.unit
class TestPreflightReport:
    """Tests for PreflightReport frozen dataclass."""

    def _make_healthy_report(self) -> HealthReport:
        return HealthReport(
            results=[
                ComponentHealthResult(
                    component="storage",
                    status=HealthStatus.HEALTHY,
                    duration_seconds=0.1,
                )
            ]
        )

    def _make_unhealthy_report(self) -> HealthReport:
        return HealthReport(
            results=[
                ComponentHealthResult(
                    component="storage",
                    status=HealthStatus.UNHEALTHY,
                    duration_seconds=5.0,
                    error_message="Down",
                )
            ]
        )

    def test_valid_preflight(self) -> None:
        report = PreflightReport(
            health_report=self._make_healthy_report(),
            medallion_policy_valid=True,
        )
        assert report.is_valid is True
        assert report.should_block_startup is False

    def test_invalid_medallion_policy(self) -> None:
        report = PreflightReport(
            health_report=self._make_healthy_report(),
            medallion_policy_valid=False,
        )
        assert report.is_valid is False
        assert report.should_block_startup is True

    def test_unhealthy_infrastructure(self) -> None:
        report = PreflightReport(
            health_report=self._make_unhealthy_report(),
            medallion_policy_valid=True,
        )
        assert report.is_valid is False
        assert report.should_block_startup is True

    def test_config_errors(self) -> None:
        report = PreflightReport(
            health_report=self._make_healthy_report(),
            medallion_policy_valid=True,
            config_errors=[
                ConfigValidationError(
                    field="test", expected="value", actual="other", rule="rule1"
                )
            ],
        )
        assert len(report.config_errors) == 1
