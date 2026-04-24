"""Runtime coverage for thin CLI compatibility alias modules.

This is the default family for top-level compat shims implemented through
``alias_module(...)``.
"""

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
        (
            "bronze_cleanup_command",
            "cleanup_preview_command",
            "get_bronze_cleanup_service",
            "preview_pipeline_cleanup",
        ),
    ),
    (
        "bioetl.interfaces.cli.commands.diagnostics",
        "bioetl.interfaces.cli.commands.domains.diagnostics.command",
        (
            "diagnostics",
            "get_observability_diagnostics_bundle",
            "get_metrics_operator_profile",
            "get_quarantine_manager",
        ),
    ),
    (
        "bioetl.interfaces.cli.commands.health",
        "bioetl.interfaces.cli.commands.domains.health.command",
        ("health", "get_health_service", "get_health_server_dependencies"),
    ),
    (
        "bioetl.interfaces.cli.commands.health_rendering",
        "bioetl.interfaces.cli.commands.domains.health.rendering",
        ("all_health_results_healthy", "render_health_results_json"),
    ),
    (
        "bioetl.interfaces.cli.commands.health_server_integration",
        "bioetl.interfaces.cli.commands.domains.health.server_integration",
        ("DEFAULT_HEALTH_SERVER_PORT", "add_health_server_options"),
    ),
    (
        "bioetl.interfaces.cli.commands.maintenance",
        "bioetl.interfaces.cli.commands.domains.maintenance.command",
        ("maintenance",),
    ),
    (
        "bioetl.interfaces.cli.commands.metrics_server_integration",
        "bioetl.interfaces.cli.commands.domains.health.metrics_server_integration",
        ("ensure_metrics_server_started", "metrics_server_context"),
    ),
    (
        "bioetl.interfaces.cli.commands.plan",
        "bioetl.interfaces.cli.commands.domains.maintenance.plan",
        ("get_contract_migration_service", "plan_command"),
    ),
    (
        "bioetl.interfaces.cli.commands.quarantine",
        "bioetl.interfaces.cli.commands.domains.quarantine.command",
        ("quarantine", "get_quarantine_manager", "get_quarantine_service"),
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
        "bioetl.interfaces.cli.commands.quarantine_support",
        "bioetl.interfaces.cli.commands.domains.quarantine.support",
        ("_inspect_quarantine", "_purge_quarantine", "_replay_quarantine"),
    ),
    (
        "bioetl.interfaces.cli.commands.run",
        "bioetl.interfaces.cli.commands.domains.run.command",
        ("run", "execute_run", "get_cli_run_orchestration_service"),
    ),
    (
        "bioetl.interfaces.cli.commands.run_all",
        "bioetl.interfaces.cli.commands.domains.run_all.command",
        ("run_all", "get_pipeline_runner_service"),
    ),
    (
        "bioetl.interfaces.cli.commands.run_composite",
        "bioetl.interfaces.cli.commands.domains.composite.command",
        ("run_composite", "load_composite_config", "bootstrap_composite_runner"),
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
