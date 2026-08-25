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
"""Unit tests for service access through narrow composition owner APIs."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest


ROOT = Path(__file__).resolve().parents[3]

pytestmark = pytest.mark.unit


def test_retired_services_api_module_stays_absent() -> None:
    """The legacy services_api umbrella must not return as a first-party seam."""
    assert not (ROOT / "src" / "bioetl" / "composition" / "services_api.py").exists()


def test_registered_zero_argument_getters_resolve_typed_ports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Migrated zero-argument getters resolve their typed registry keys."""
    from bioetl.application.ports import (
        AuditInspectionServiceProtocol,
        CheckpointServiceProtocol,
        ConfigServiceProtocol,
        ContractMigrationServiceProtocol,
        ExportServiceProtocol,
        ForensicRunDiffServiceProtocol,
        HistoricalReplayClosureServiceProtocol,
        HistoricalReplayCorpusServiceProtocol,
        HistoricalReplayUniverseServiceProtocol,
        LineageInspectionServiceProtocol,
        LockServiceProtocol,
        MetricsService,
        ObservabilityWorkflowServiceProtocol,
        RunManifestInspectionServiceProtocol,
        VacuumServiceProtocol,
        WorkflowInspectionServiceProtocol,
    )
    from bioetl.composition import _services
    from bioetl.composition.contracts import BronzeCleanupServiceProtocol
    from bioetl.domain.ports import AdrServicePort, QuarantinePort

    expected = object()
    monkeypatch.setattr(_services, "_ensure_provider_registrations", lambda: None)
    resolve = Mock(return_value=expected)
    monkeypatch.setattr(_services, "_resolve", resolve)
    getter_ports = {
        "get_checkpoint_service": CheckpointServiceProtocol,
        "get_audit_service": AuditInspectionServiceProtocol,
        "get_bronze_cleanup_service": BronzeCleanupServiceProtocol,
        "get_vacuum_service": VacuumServiceProtocol,
        "get_contract_migration_service": ContractMigrationServiceProtocol,
        "get_observability_workflow_service": ObservabilityWorkflowServiceProtocol,
        "get_metrics_service": MetricsService,
        "get_quarantine_port": QuarantinePort,
        "get_adr_service": AdrServicePort,
        "get_config_service": ConfigServiceProtocol,
        "get_export_service": ExportServiceProtocol,
        "get_lock_service": LockServiceProtocol,
        "get_forensic_run_diff_service": ForensicRunDiffServiceProtocol,
        "get_historical_replay_closure_service": (
            HistoricalReplayClosureServiceProtocol
        ),
        "get_historical_replay_corpus_service": HistoricalReplayCorpusServiceProtocol,
        "get_historical_replay_universe_service": (
            HistoricalReplayUniverseServiceProtocol
        ),
        "get_lineage_service": LineageInspectionServiceProtocol,
        "get_run_manifest_service": RunManifestInspectionServiceProtocol,
        "get_workflow_inspection_service": WorkflowInspectionServiceProtocol,
    }

    for getter_name, port in getter_ports.items():
        resolve.reset_mock()
        assert getattr(_services, getter_name)() is expected
        resolve.assert_called_once_with(port)


def test_get_health_service_resolves_typed_application_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Health pilot resolves its application port instead of a locator name."""
    from bioetl.application.ports import HealthServiceProtocol
    from bioetl.composition import _services

    expected = object()
    monkeypatch.setattr(_services, "_ensure_provider_registrations", lambda: None)
    resolve = Mock(return_value=expected)
    monkeypatch.setattr(_services, "_resolve", resolve)

    assert _services.get_health_service() is expected
    resolve.assert_called_once_with(HealthServiceProtocol)


@pytest.mark.parametrize(
    ("module_name", "expected_exports"),
    [
        (
            "bioetl.composition.execution_api",
            {
                "get_pipeline_runner_service",
                "run_pipeline",
                "create_pipeline_runner",
            },
        ),
        (
            "bioetl.composition.execution_api",
            {
                "ensure_metrics_server_started",
                "get_pipeline_runner_service",
            },
        ),
        (
            "bioetl.composition.control_plane_runtime",
            {
                "get_adr_service",
                "get_config_service",
                "get_forensic_run_diff_service",
                "get_lineage_service",
                "get_lock_service",
                "get_run_manifest_service",
                "get_workflow_execution_service",
                "get_workflow_inspection_service",
                "get_workflow_runner_service",
                "load_workflow_config",
            },
        ),
        (
            "bioetl.composition.control_plane_service_access",
            {
                "bootstrap_control_plane_lifecycle_store",
                "get_adr_service",
                "get_checkpoint_runtime_service",
                "get_config_service",
                "get_export_service",
                "get_forensic_run_diff_service",
                "get_historical_replay_closure_service",
                "get_historical_replay_corpus_service",
                "get_historical_replay_universe_service",
                "get_lineage_service",
                "get_lock_service",
                "get_run_manifest_service",
                "get_workflow_execution_service",
                "get_workflow_inspection_service",
                "get_workflow_runner_service",
                "list_configured_pipeline_names",
                "load_workflow_config",
                "persist_historical_replay_closure_report",
                "persist_historical_replay_universe_report",
            },
        ),
        (
            "bioetl.composition.health_api",
            {
                "get_health_server_dependencies",
                "get_health_service",
                "get_quarantine_port",
                "get_quarantine_runtime_service",
                "get_quarantine_service",
            },
        ),
        (
            "bioetl.composition.maintenance_api",
            {
                "cleanup_bronze",
                "get_bronze_cleanup_service",
                "get_contract_migration_service",
                "get_vacuum_service",
            },
        ),
        (
            "bioetl.composition.observability_runtime",
            {
                "get_audit_service",
                "get_checkpoint_service",
                "get_metrics_service",
                "get_observability_workflow_service",
            },
        ),
    ],
)
def test_service_access_is_partitioned_by_narrow_owner_api(
    module_name: str,
    expected_exports: set[str],
) -> None:
    module = __import__(module_name, fromlist=["__all__"])
    exported = set(module.__all__)

    assert expected_exports <= exported
