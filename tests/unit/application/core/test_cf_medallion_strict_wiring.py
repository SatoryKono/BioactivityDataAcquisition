"""Regression coverage for reachable DELETE and settings-bound strict preflight."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from bioetl.application.core.preflight.medallion_validator import (
    MedallionConfigValidator,
)
from bioetl.application.core.preflight.service import PreflightService
from bioetl.composition.bootstrap.runtime.assembly import assemble_runtime_config
from bioetl.composition.runtime_builders import (
    inputs_runtime_assembly,
    inputs_runtime_helpers,
)
from bioetl.domain.config import PipelineConfig, TableConfig
from bioetl.domain.medallion import (
    GoldWriteMode,
    Layer,
    SilverWriteMode,
    WriteMode,
    WriteModePolicy,
)
from bioetl.domain.types import RunType
from bioetl.infrastructure.config._pipeline_settings import PipelineSettings


def _config() -> PipelineConfig:
    return PipelineConfig(
        pipeline_name="test_activity",
        provider="test",
        entity_type="activity",
        table=TableConfig(
            primary_keys=("id",),
            silver_write_mode=SilverWriteMode.DELETE,
            gold_write_mode=GoldWriteMode.OVERWRITE,
            silver_idempotency_contract="overwrite_rebuild",
            gold_idempotency_contract="overwrite_rebuild",
        ),
    )


def test_delete_passes_both_gates_but_overwrite_remains_forbidden():
    WriteModePolicy().validate(Layer.SILVER, WriteMode.DELETE)
    from bioetl.domain.exceptions import PolicyViolationError

    with pytest.raises(PolicyViolationError):
        WriteModePolicy().validate(Layer.SILVER, WriteMode.OVERWRITE)
    validator = MedallionConfigValidator(_config(), Mock(), WriteModePolicy())
    assert validator.validate_write_modes() == []


@pytest.mark.asyncio
@pytest.mark.parametrize("strict", [True, False])
async def test_effective_setting_reaches_runtime_and_preflight(strict):
    projection = inputs_runtime_helpers.resolve_runtime_projection(
        ctx=SimpleNamespace(skip_gold=False),
        settings=SimpleNamespace(
            test_mode=False, pipeline=PipelineSettings(strict_validation=strict)
        ),
        yaml_config=SimpleNamespace(sink={}),
        observability=SimpleNamespace(logger=Mock()),
        default_health_check_mode="strict",
    )
    runtime = inputs_runtime_helpers.build_runtime_config(
        assemble_runtime_config_fn=inputs_runtime_assembly.assemble_runtime_config,
        ctx=SimpleNamespace(
            run_type=RunType.INCREMENTAL,
            resume=False,
            start_offset=None,
            limit=None,
            query=None,
            dry_run=False,
        ),
        vacuum=SimpleNamespace(enabled=False, retention_days=7),
        runtime_projection=projection,
    )
    assert runtime.strict_validation is strict
    validator = MedallionConfigValidator(_config(), Mock(), WriteModePolicy())
    health = Mock()
    health.assert_healthy = Mock()
    health.check_all = AsyncMock(return_value=Mock())
    service = PreflightService(_config(), Mock(), Mock(), Mock(), health, validator)
    arguments = {
        "runtime": runtime,
        "bronze_path": "bronze",
        "silver_path": "silver",
        "gold_path": "gold",
        "silver_format": "parquet",
        "gold_format": "delta",
    }
    if strict:
        with pytest.raises(ValueError, match="strict mode"):
            await service.validate_preflight(services=Mock(), **arguments)
    else:
        assert (
            await service.validate_preflight(services=Mock(), **arguments)
        ).config_errors


def test_shipped_settings_and_bootstrap_are_strict_by_default():
    assert PipelineSettings().strict_validation is True
    runtime = assemble_runtime_config(
        run_type=RunType.INCREMENTAL,
        resume=False,
        limit=None,
        query=None,
        dry_run=False,
        heartbeat_interval=30,
        vacuum=SimpleNamespace(enabled=False, retention_days=7),
    )
    assert runtime.strict_validation is True


@pytest.mark.asyncio
@pytest.mark.parametrize("strict", [True, False])
async def test_runner_startup_reaches_gate_before_preparation_and_extraction(strict):
    from bioetl.application.core.runner_execution_flow import _managed_pipeline_stages
    from bioetl.application.core.preflight.service import PreflightLayerConfig
    from bioetl.domain.types import HealthReport

    runtime = assemble_runtime_config(
        run_type=RunType.INCREMENTAL,
        resume=False,
        limit=None,
        query=None,
        dry_run=False,
        heartbeat_interval=30,
        vacuum=SimpleNamespace(enabled=False, retention_days=7),
        strict_validation=strict,
    )
    health = Mock()
    health.assert_healthy = Mock()
    health.check_all = AsyncMock(return_value=HealthReport(results=[]))
    validator = MedallionConfigValidator(_config(), Mock(), WriteModePolicy())
    service = PreflightService(
        _config(),
        Mock(),
        Mock(),
        Mock(),
        health,
        validator,
        layer_config=PreflightLayerConfig(
            "bronze", "silver", "gold", "parquet", "delta"
        ),
    )
    extraction = AsyncMock()
    host = SimpleNamespace(
        _runtime=runtime,
        _services=Mock(),
        _preflight_service=service,
        _observer=Mock(),
        _batch_executor=SimpleNamespace(execute=extraction),
    )
    stages = _managed_pipeline_stages(host)
    if strict:
        with pytest.raises(ValueError, match="sink.silver.format"):
            await stages[0].operation()
    else:
        await stages[0].operation()
    extraction.assert_not_awaited()


@pytest.mark.parametrize("strict", [True, False])
def test_env_setting_and_effective_snapshot_record_gate_policy(monkeypatch, strict):
    from bioetl.infrastructure.config.settings_api import Settings
    from bioetl.composition.runtime_builders._effective_config_runtime_snapshot_support import (
        build_execution_settings_snapshot,
    )

    monkeypatch.setenv("BIOETL_PIPELINE__STRICT_VALIDATION", str(strict).lower())
    settings = Settings(_env_file=None)
    assert settings.pipeline.strict_validation is strict
    snapshot = build_execution_settings_snapshot(settings)
    assert snapshot["pipeline"]["strict_validation"] is strict
