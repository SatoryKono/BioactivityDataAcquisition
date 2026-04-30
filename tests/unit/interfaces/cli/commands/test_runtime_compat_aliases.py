"""Runtime coverage for retained public CLI compatibility alias modules."""

from __future__ import annotations

import importlib
import sys

import pytest


CLI_ALIAS_MODULE_CASES = (
    (
        "bioetl.interfaces.cli.commands.archive",
        "bioetl.interfaces.cli.commands.domains.maintenance.archive",
        ("archive_command", "get_lifecycle_service"),
        True,
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
        True,
    ),
    (
        "bioetl.interfaces.cli.commands.diagnostics",
        "bioetl.interfaces.cli.commands.domains.diagnostics.command",
        (
            "diagnostics",
            "get_observability_diagnostics_bundle",
            "get_metrics_operator_profile",
            "get_quarantine_runtime_service",
        ),
        True,
    ),
    (
        "bioetl.interfaces.cli.commands.health",
        "bioetl.interfaces.cli.commands.domains.health.command",
        ("health", "get_health_service", "get_health_server_dependencies"),
        True,
    ),
    (
        "bioetl.interfaces.cli.commands.maintenance",
        "bioetl.interfaces.cli.commands.domains.maintenance.command",
        ("maintenance",),
        True,
    ),
    (
        "bioetl.interfaces.cli.commands.plan",
        "bioetl.interfaces.cli.commands.domains.maintenance.plan",
        ("get_contract_migration_service", "plan_command"),
        True,
    ),
    (
        "bioetl.interfaces.cli.commands.quarantine",
        "bioetl.interfaces.cli.commands.domains.quarantine.command",
        ("quarantine", "get_quarantine_runtime_service", "get_quarantine_service"),
        True,
    ),
    (
        "bioetl.interfaces.cli.commands.run",
        "bioetl.interfaces.cli.commands.domains.run.command",
        ("run", "execute_run", "get_cli_run_orchestration_service"),
        True,
    ),
    (
        "bioetl.interfaces.cli.commands.run_all",
        "bioetl.interfaces.cli.commands.domains.run_all.command",
        ("run_all", "get_pipeline_runner_service"),
        True,
    ),
    (
        "bioetl.interfaces.cli.commands.run_composite",
        "bioetl.interfaces.cli.commands.domains.composite.command",
        ("run_composite", "load_composite_config", "bootstrap_composite_runner"),
        True,
    ),
    (
        "bioetl.interfaces.cli.commands.vacuum",
        "bioetl.interfaces.cli.commands.domains.maintenance.vacuum",
        ("vacuum_command", "get_vacuum_service"),
        True,
    ),
)


@pytest.mark.unit
@pytest.mark.parametrize(
    (
        "compat_module_name",
        "target_module_name",
        "export_names",
        "aliases_runtime_module",
    ),
    CLI_ALIAS_MODULE_CASES,
)
def test_cli_alias_module_runtime_exports_match_canonical_target(
    compat_module_name: str,
    target_module_name: str,
    export_names: tuple[str, ...],
    aliases_runtime_module: bool,
) -> None:
    """Retained public command modules should alias canonical runtime modules."""
    sys.modules.pop(compat_module_name, None)

    compat_module = importlib.import_module(compat_module_name)
    target_module = importlib.import_module(target_module_name)

    assert aliases_runtime_module is True
    assert compat_module is target_module

    for export_name in export_names:
        assert getattr(compat_module, export_name) is getattr(
            target_module, export_name
        )
