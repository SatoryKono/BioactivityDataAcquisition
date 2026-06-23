"""Integration tests for strict/probe preflight health behavior."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Literal
from unittest.mock import MagicMock
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

import pytest

from bioetl.application.core.preflight.health_aggregator import HealthAggregator
from bioetl.application.core.preflight.medallion_validator import (
    MedallionConfigValidator,
)
from bioetl.application.core.preflight.service import PreflightService
from bioetl.domain.config import PipelineConfig, TableConfig
from bioetl.domain.context import PipelineContext
from bioetl.domain.exceptions import InfrastructureError
from bioetl.domain.medallion import WriteModePolicy
from bioetl.domain.ports.health_check import HealthCheckResult
from bioetl.domain.types import HealthStatus, RunType


class _HealthyStorage:
    async def health_check(self) -> HealthStatus:
        await asyncio.sleep(0)
        return HealthStatus.HEALTHY


class _FailingLegacyDataSource:
    async def health_check(self) -> HealthStatus:
        await asyncio.sleep(0)
        raise OSError("upstream timeout")


class _UnhealthyEnhancedDataSource:
    async def check_health(self) -> HealthCheckResult:
        await asyncio.sleep(0)
        return HealthCheckResult(
            status=HealthStatus.UNHEALTHY,
            latency_ms=42.0,
            provider="stub_provider",
            endpoint="/health",
            last_error="stub provider unhealthy",
            consecutive_failures=3,
        )


def _build_preflight_service(
    *,
    health_check_mode: Literal["strict", "probe"],
    metrics: MagicMock,
    logger: MagicMock,
    pipeline_name: str,
) -> PreflightService:
    config = PipelineConfig(
        pipeline_name=pipeline_name,
        provider="stub_provider",
        entity_type="publication",
        table=TableConfig(
            primary_keys=["entity_id"],
            silver_table="stub_silver",
            gold_write_mode="scd2",
        ),
    )
    context = PipelineContext(
        run_id=deterministic_uuid_from_callsite("test_preflight_health_modes"),
        run_type=RunType.INCREMENTAL,
        logger=logger,
    )
    health_aggregator = HealthAggregator(
        logger=logger,
        health_check_mode=health_check_mode,
    )
    medallion_validator = MedallionConfigValidator(
        config=config,
        logger=logger,
        write_mode_policy=WriteModePolicy(),
    )
    return PreflightService(
        config=config,
        context=context,
        logger=logger,
        metrics=metrics,
        health_aggregator=health_aggregator,
        medallion_validator=medallion_validator,
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_strict_mode_blocks_on_data_source_health_exception() -> None:
    logger = MagicMock()
    metrics = MagicMock()
    service = _build_preflight_service(
        health_check_mode="strict",
        metrics=metrics,
        logger=logger,
        pipeline_name="strict_health_pipeline",
    )
    services = SimpleNamespace(
        storage=_HealthyStorage(),
        data_source=_FailingLegacyDataSource(),
    )

    with pytest.raises(InfrastructureError, match="data_source"):
        await service.validate_infrastructure(services)
    metrics.increment_counter.assert_not_called()
    metrics.set_gauge.assert_not_called()
    metrics.observe_histogram.assert_not_called()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_probe_mode_downgrades_exception_and_counts_fallback() -> None:
    logger = MagicMock()
    metrics = MagicMock()
    service = _build_preflight_service(
        health_check_mode="probe",
        metrics=metrics,
        logger=logger,
        pipeline_name="probe_health_pipeline",
    )
    services = SimpleNamespace(
        storage=_HealthyStorage(),
        data_source=_FailingLegacyDataSource(),
    )

    report = await service.validate_infrastructure(services)
    data_source_result = next(
        result for result in report.results if result.component == "data_source"
    )
    assert report.is_healthy
    assert data_source_result.status == HealthStatus.DEGRADED
    assert data_source_result.error_message == "probe_mode_fallback: upstream timeout"
    assert data_source_result.probe_fallback_reason == "exception"
    metrics.increment_counter.assert_not_called()
    metrics.set_gauge.assert_not_called()
    metrics.observe_histogram.assert_not_called()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_probe_mode_downgrades_unhealthy_status_with_deterministic_reason() -> (
    None
):
    logger = MagicMock()
    metrics = MagicMock()
    service = _build_preflight_service(
        health_check_mode="probe",
        metrics=metrics,
        logger=logger,
        pipeline_name="probe_status_pipeline",
    )
    services = SimpleNamespace(
        storage=_HealthyStorage(),
        data_source=_UnhealthyEnhancedDataSource(),
    )

    report = await service.validate_infrastructure(services)
    data_source_result = next(
        result for result in report.results if result.component == "data_source"
    )
    assert report.is_healthy
    assert data_source_result.status == HealthStatus.DEGRADED
    assert data_source_result.error_message == (
        "probe_mode_fallback: stub provider unhealthy"
    )
    assert data_source_result.provider == "stub_provider"
    assert data_source_result.latency_ms == pytest.approx(42.0)
    assert data_source_result.probe_fallback_reason == "status_downgrade"
    metrics.increment_counter.assert_not_called()
    metrics.set_gauge.assert_not_called()
    metrics.observe_histogram.assert_not_called()
