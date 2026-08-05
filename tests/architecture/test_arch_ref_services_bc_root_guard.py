"""ARCH-REF-03 / #7704: block accidental new root-level application services modules."""

from __future__ import annotations

from pathlib import Path

import pytest

SERVICES_ROOT = Path("src/bioetl/application/services")

# Existing root compatibility shims + package inits allowed after BC split.
# New root-level *.py modules (non-underscore) must go into a BC package.
ALLOWED_ROOT_MODULES = frozenset(
    {
        "__init__.py",
        # BC packages exist as directories; root .py below are shims or residual.
        "quarantine_service.py",
        "data_quality_service.py",
        "data_quality_anomalies.py",
        "data_quality_thresholds.py",
        "config_dq_service.py",
        "dq_report_service.py",
        "dq_report_models.py",
        "dq_report_generation_mixin.py",
        "health_service.py",
        "lock_service.py",
        "shutdown_service.py",
        "vacuum_service.py",
        "metrics_service.py",
        "admin_runtime_api.py",
        "bronze_cleanup_service.py",
        "error_handler.py",
        "config_service.py",
        "export_service.py",
        "export_execution.py",
        "export_manifests.py",
        "export_models.py",
        "export_manifest_attribution.py",
        "export_manifest_identity.py",
        "debug_export_service.py",
        "debug_export_collector.py",
        "debug_export_helpers.py",
        "debug_export_pack_assembly.py",
        "debug_export_service_recording_mixin.py",
        "debug_export_collector_gold_mixin.py",
        "debug_export_collector_helpers.py",
        "debug_export_collector_transform_mixin.py",
        "debug_reason_dictionary.py",
        "audit_inspection_service.py",
        "pipeline_debug_service.py",
        "workflow_runner_service.py",
        "workflow_runner_models.py",
        "workflow_runner_reports.py",
        "workflow_runner_support.py",
        "workflow_transform_artifacts.py",
        "workflow_transform_service.py",
        "workflow_transition_policy.py",
        "observability_workflow_service.py",
        "checkpoint_service.py",
        "checkpoint_models.py",
        "checkpoint_compatibility_service.py",
        "checkpoint_compatibility_policy.py",
        "checkpoint_compatibility_results.py",
        "checkpoint_compatibility_telemetry.py",
        "contract_migration_service.py",
        "contract_migration_models.py",
        "contract_migration_ports.py",
        # Underscore helper shims created by BC migration
        "_quarantine_models.py",
        "_quarantine_service_async_mixin.py",
        "_quarantine_service_filtered_helpers.py",
        "_quarantine_service_filtered_mixin.py",
        "_quarantine_service_replay_purge_sync.py",
        "_quarantine_service_status_sync.py",
        "_quarantine_service_support.py",
        "_quarantine_service_sync_mixin.py",
        "_quarantine_service_sync_operations.py",
        "_quarantine_service_sync_support.py",
        "_dq_report_layer_flows.py",
        "_metrics_service_gateway_support.py",
        "_observability_workflow_checkpoint_support.py",
        "_observability_workflow_evidence_support.py",
        "_observability_workflow_execution.py",
        "_observability_workflow_lookup_support.py",
        "_observability_workflow_models.py",
        "_observability_workflow_next_steps_support.py",
        "_observability_workflow_quarantine_support.py",
        "_observability_workflow_status_support.py",
        "_observability_workflow_support.py",
        "_observability_workflow_traceability_support.py",
        "_observability_trace_support.py",
        "_checkpoint_compatibility_execution_validation.py",
        "_checkpoint_compatibility_message_helpers.py",
        "_checkpoint_compatibility_runtime_identity.py",
        "_checkpoint_compatibility_runtime_identity_details.py",
        "_checkpoint_execution_identity_payload.py",
        "_checkpoint_service_runtime.py",
        "_checkpoint_service_support.py",
    }
)

REQUIRED_BC_PACKAGES = frozenset(
    {
        "control_plane",
        "execution",
        "dq",
        "lineage",
        "quality",
        "ops",
        "export_lineage",
        "workflow",
        "checkpoint",
        "contract",
    }
)


@pytest.mark.architecture
def test_services_bc_packages_exist() -> None:
    for name in REQUIRED_BC_PACKAGES:
        path = SERVICES_ROOT / name
        assert path.is_dir(), f"missing BC package: {path}"
        assert (path / "__init__.py").is_file(), f"missing package init: {path}"


@pytest.mark.architecture
def test_no_unexpected_root_service_modules() -> None:
    root_py = sorted(p.name for p in SERVICES_ROOT.glob("*.py"))
    unexpected = [name for name in root_py if name not in ALLOWED_ROOT_MODULES]
    assert unexpected == [], (
        "New root-level modules under application/services must live in a BC package. "
        f"Unexpected: {unexpected}"
    )


@pytest.mark.architecture
def test_root_service_shims_are_reexports() -> None:
    """Public root service modules must re-export BC implementations."""
    samples = (
        "quarantine_service.py",
        "metrics_service.py",
        "export_service.py",
        "workflow_transition_policy.py",
    )
    for name in samples:
        text = (SERVICES_ROOT / name).read_text(encoding="utf-8")
        assert "Compatibility re-export" in text or "domain.workflow.step_transition" in text or "from bioetl.application.services." in text
        assert "class " not in text or name == "workflow_transition_policy.py"
