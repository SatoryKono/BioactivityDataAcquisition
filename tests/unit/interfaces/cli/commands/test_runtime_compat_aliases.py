"""Runtime coverage for thin CLI compatibility alias modules."""

from __future__ import annotations

import importlib
import sys

import pytest


CLI_ALIAS_MODULE_CASES = (
    (
        "bioetl.interfaces.cli.commands.archive",
        "bioetl.interfaces.cli.commands.domains.maintenance.archive",
        ("archive_command", "get_lifecycle_service"),
    ),
    (
        "bioetl.interfaces.cli.commands.cleanup",
        "bioetl.interfaces.cli.commands.domains.maintenance.cleanup",
        ("bronze_cleanup_command", "preview_pipeline_cleanup"),
    ),
    (
        "bioetl.interfaces.cli.commands.health_rendering",
        "bioetl.interfaces.cli.commands.domains.health.rendering",
        ("all_health_results_healthy", "render_health_results_json"),
    ),
    (
        "bioetl.interfaces.cli.commands.quarantine_execution",
        "bioetl.interfaces.cli.commands.domains.quarantine.execution",
        ("QuarantineExecutionPolicy", "run_quarantine_sync"),
    ),
    (
        "bioetl.interfaces.cli.commands.quarantine_rendering",
        "bioetl.interfaces.cli.commands.domains.quarantine.rendering",
        ("build_quarantine_stats_lines", "build_purge_preview_lines"),
    ),
    (
        "bioetl.interfaces.cli.commands.run_all_execution",
        "bioetl.interfaces.cli.commands.domains.run_all.execution",
        ("RunAllBatchExecutionRequest", "run_all_pipelines_async"),
    ),
    (
        "bioetl.interfaces.cli.commands.run_composite_execution",
        "bioetl.interfaces.cli.commands.domains.composite.execution",
        ("load_composite_config", "run_composite_async"),
    ),
    (
        "bioetl.interfaces.cli.commands.run_composite_helpers",
        "bioetl.interfaces.cli.commands.domains.composite.support",
        ("emit_composite_startup", "run_composite_with_cli_policy"),
    ),
    (
        "bioetl.interfaces.cli.commands.run_result_flow_helpers",
        "bioetl.interfaces.cli.commands.domains.run.result_flow",
        ("finalize_run_result", "present_run_health_info"),
    ),
    (
        "bioetl.interfaces.cli.commands.run_runtime_helpers",
        "bioetl.interfaces.cli.commands.domains.run.runtime_helpers",
        ("build_run_command_input", "run_prepared_request_async"),
    ),
    (
        "bioetl.interfaces.cli.commands.run_service_access",
        "bioetl.interfaces.cli.commands.domains.run.service_access",
        ("get_cli_run_orchestration_service",),
    ),
    (
        "bioetl.interfaces.cli.commands.vacuum",
        "bioetl.interfaces.cli.commands.domains.maintenance.vacuum",
        ("vacuum_command", "get_vacuum_service"),
    ),
)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("compat_module_name", "target_module_name", "export_names"),
    CLI_ALIAS_MODULE_CASES,
)
def test_cli_alias_module_runtime_exports_match_canonical_target(
    compat_module_name: str,
    target_module_name: str,
    export_names: tuple[str, ...],
) -> None:
    """Compat module imports should alias to the canonical runtime module."""
    sys.modules.pop(compat_module_name, None)

    compat_module = importlib.import_module(compat_module_name)
    target_module = importlib.import_module(target_module_name)

    assert compat_module is target_module

    for export_name in export_names:
        assert getattr(compat_module, export_name) is getattr(
            target_module, export_name
        )
