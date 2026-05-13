"""Runtime coverage for retained public CLI compatibility wrappers."""

from __future__ import annotations

import importlib
import sys

import pytest


CLI_INTERNAL_WRAPPER_CASES = (
    (
        "bioetl.interfaces.cli.commands.domains.diagnostics.command",
        "bioetl.interfaces.cli.commands.diagnostics",
        (
            "diagnostics",
            "get_observability_diagnostics_bundle",
            "get_metrics_operator_profile",
            "get_quarantine_runtime_service",
        ),
    ),
    (
        "bioetl.interfaces.cli.commands.domains.health.command",
        "bioetl.interfaces.cli.commands.health",
        ("health", "get_health_service", "get_health_server_dependencies"),
    ),
    (
        "bioetl.interfaces.cli.commands.domains.maintenance.command",
        "bioetl.interfaces.cli.commands.maintenance",
        ("maintenance",),
    ),
    (
        "bioetl.interfaces.cli.commands.domains.maintenance.plan",
        "bioetl.interfaces.cli.commands.plan",
        ("get_contract_migration_service", "plan_command"),
    ),
    (
        "bioetl.interfaces.cli.commands.domains.quarantine.command",
        "bioetl.interfaces.cli.commands.quarantine",
        ("quarantine", "get_quarantine_runtime_service", "get_quarantine_service"),
    ),
    (
        "bioetl.interfaces.cli.commands.domains.run.command",
        "bioetl.interfaces.cli.commands.run",
        ("run", "execute_run", "get_cli_run_orchestration_service"),
    ),
    (
        "bioetl.interfaces.cli.commands.domains.run_all.command",
        "bioetl.interfaces.cli.commands.run_all",
        ("run_all", "get_pipeline_runner_service"),
    ),
    (
        "bioetl.interfaces.cli.commands.domains.composite.command",
        "bioetl.interfaces.cli.commands.run_composite",
        ("run_composite", "load_composite_config", "bootstrap_composite_runner"),
    ),
)


@pytest.mark.unit
@pytest.mark.parametrize(
    (
        "wrapper_module_name",
        "public_module_name",
        "export_names",
    ),
    CLI_INTERNAL_WRAPPER_CASES,
)
def test_cli_internal_wrappers_reexport_public_command_symbols(
    wrapper_module_name: str,
    public_module_name: str,
    export_names: tuple[str, ...],
) -> None:
    """Internal domain bridges should re-export the sanctioned public CLI seams."""
    sys.modules.pop(wrapper_module_name, None)

    wrapper_module = importlib.import_module(wrapper_module_name)
    public_module = importlib.import_module(public_module_name)

    assert wrapper_module is not public_module
    assert wrapper_module.__name__ == wrapper_module_name

    for export_name in export_names:
        assert getattr(wrapper_module, export_name) is getattr(
            public_module, export_name
        )
