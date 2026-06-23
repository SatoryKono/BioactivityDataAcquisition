"""Unit tests for service access through narrow composition owner APIs."""

from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]

pytestmark = pytest.mark.unit


def test_retired_services_api_module_stays_absent() -> None:
    """The legacy services_api umbrella must not return as a first-party seam."""
    assert not (ROOT / "src" / "bioetl" / "composition" / "services_api.py").exists()


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
            "bioetl.composition.control_plane_api",
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
            "bioetl.composition.observability_api",
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
