# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for sanctioned CLI service-graph builders."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from bioetl.application.services.checkpoint.checkpoint_service import CheckpointService
from bioetl.composition.registry_api import PipelineRegistry
from bioetl.composition.bootstrap.cli.service_builders import (
    build_cli_checkpoint_runtime_service,
    build_cli_checkpoint_service,
    build_cli_config_service,
    build_cli_observability_workflow_service,
)
from bioetl.domain.ports.noop import NoOpMetrics, NoOpTracing
from bioetl.domain.types import RunID
from bioetl.infrastructure.observability.noop_logger import NoOpLogger


@pytest.mark.unit
def test_service_builders_public_surface_prefers_runtime_service_vocabulary() -> None:
    from bioetl.composition.bootstrap.cli import service_builders

    assert "build_cli_checkpoint_runtime_service" in service_builders.__all__
    assert "build_cli_quarantine_runtime_service" in service_builders.__all__
    assert "build_cli_checkpoint_manager" not in service_builders.__all__
    assert "build_cli_quarantine_manager" not in service_builders.__all__
    assert not hasattr(service_builders, "build_cli_checkpoint_manager")
    assert not hasattr(service_builders, "build_cli_quarantine_manager")


@pytest.mark.unit
def test_build_cli_config_service_requires_explicit_registry_and_wires_dq() -> None:
    registry = PipelineRegistry()
    effective_config_service = MagicMock()
    dq_config_loader = MagicMock()

    service = build_cli_config_service(
        registry=registry,
        logger_factory=NoOpLogger,
        settings_loader=MagicMock(),
        pipeline_config_loader=MagicMock(),
        domain_config_mapper=MagicMock(),
        pipeline_yaml_getter=MagicMock(),
        dq_config_loader=dq_config_loader,
        effective_config_service_factory=lambda: effective_config_service,
    )

    assert service._registry_accessor() is registry
    assert service._dq_service._dq_config_loader is dq_config_loader
    assert service._dq_service._effective_config_service is effective_config_service


@pytest.mark.unit
def test_build_cli_config_service_rejects_missing_registry() -> None:
    with pytest.raises(ValueError, match="explicit pipeline registry"):
        build_cli_config_service(
            registry=None,
            logger_factory=NoOpLogger,
            settings_loader=MagicMock(),
            pipeline_config_loader=MagicMock(),
            domain_config_mapper=MagicMock(),
            pipeline_yaml_getter=MagicMock(),
            dq_config_loader=MagicMock(),
            effective_config_service_factory=MagicMock(),
        )


@pytest.mark.unit
def test_build_cli_checkpoint_runtime_service_uses_injected_sentinel_and_compatibility() -> (
    None
):
    checkpoint_port = MagicMock()
    logger = NoOpLogger()
    compatibility_service = MagicMock()
    run_id = RunID(UUID("00000000-0000-0000-0000-000000003351"))

    runtime_service = build_cli_checkpoint_runtime_service(
        pipeline_name="chembl_activity",
        run_id=run_id,
        checkpoint_port_factory=MagicMock(return_value=checkpoint_port),
        logger_factory=MagicMock(return_value=logger),
        compatibility_service_factory=MagicMock(return_value=compatibility_service),
    )

    assert runtime_service._checkpoint is checkpoint_port
    assert runtime_service._logger is logger
    assert runtime_service._run_id == run_id
    assert runtime_service._resume is False
    assert runtime_service._compatibility_service is compatibility_service


@pytest.mark.unit
def test_build_cli_checkpoint_service_resolves_observability_from_settings() -> None:
    settings = MagicMock(checkpoint_path=Path("/tmp/bioetl/checkpoints"))
    metrics = NoOpMetrics(warn_on_use=False)
    tracer = NoOpTracing()
    metrics_resolver = MagicMock(return_value=metrics)
    tracing_resolver = MagicMock(return_value=tracer)

    service = build_cli_checkpoint_service(
        settings=settings,
        logger_factory=NoOpLogger,
        metrics_resolver=metrics_resolver,
        tracing_resolver=tracing_resolver,
    )

    assert isinstance(service, CheckpointService)
    assert service.checkpoint_port.pipeline_name == ""
    assert service.checkpoint_port.base_path == settings.checkpoint_path
    assert service.metrics is metrics
    assert service.tracer is tracer
    metrics_resolver.assert_called_once_with(metrics=None, settings=settings)
    tracing_resolver.assert_called_once_with(
        tracer=None,
        settings=settings,
        service_name="bioetl.checkpoint_admin",
    )


@pytest.mark.unit
def test_build_cli_observability_workflow_service_uses_sanctioned_factories() -> None:
    settings = MagicMock()
    checkpoint_service = MagicMock(spec=CheckpointService)
    audit_service = MagicMock()
    run_manifest_service = MagicMock()
    lineage_service = MagicMock()
    quarantine_service = MagicMock()
    tracer = NoOpTracing()
    tracing_resolver = MagicMock(return_value=tracer)

    service = build_cli_observability_workflow_service(
        settings=settings,
        checkpoint_service_factory=MagicMock(return_value=checkpoint_service),
        audit_service_factory=MagicMock(return_value=audit_service),
        run_manifest_service_factory=MagicMock(return_value=run_manifest_service),
        lineage_service_factory=MagicMock(return_value=lineage_service),
        quarantine_service_factory=MagicMock(return_value=quarantine_service),
        tracing_resolver=tracing_resolver,
    )

    assert service.checkpoint_service is checkpoint_service
    assert service.audit_service is audit_service
    assert service.run_manifest_service is run_manifest_service
    assert service.lineage_service is lineage_service
    assert service.quarantine_service is quarantine_service
    assert service.tracer is tracer
    tracing_resolver.assert_called_once_with(
        tracer=None,
        settings=settings,
        service_name="bioetl.diagnostics",
    )
