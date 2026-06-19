"""Shared boundary-test families for thin CLI command wrappers.

New command seams should default to these parametrized families instead of
adding one-off boundary suites.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner


def _no_args(_module: ModuleType) -> tuple[tuple[object, ...], dict[str, object]]:
    """Build an empty invocation for zero-argument wrappers."""
    return (), {}


def _registry_kwarg(
    _module: ModuleType,
) -> tuple[tuple[object, ...], dict[str, object]]:
    """Build a representative registry kwarg for runner-service wrappers."""
    return (), {"registry": MagicMock()}


def _composite_config_args(
    _module: ModuleType,
) -> tuple[tuple[object, ...], dict[str, object]]:
    """Build representative args for composite config loading."""
    return ("publication",), {}


def _composite_runner_args(
    module: ModuleType,
) -> tuple[tuple[object, ...], dict[str, object]]:
    """Build representative args for composite runner bootstrap."""
    return (MagicMock(), module.CompositeRuntimeConfig()), {}


def _push_metrics_kwargs(
    _module: ModuleType,
) -> tuple[tuple[object, ...], dict[str, object]]:
    """Build representative kwargs for the composite metrics helper."""
    return (), {"run_label": "composite", "pipeline_name": "publication"}


def _cli_metrics_publish_kwargs(
    _module: ModuleType,
) -> tuple[tuple[object, ...], dict[str, object]]:
    """Build representative kwargs for CLI metrics publication wrappers."""
    return (), {
        "run_label": "bioetl",
        "pipeline_name": "workflow_chembl_activity",
        "run_type": None,
        "grouping_key_extra": None,
    }


COMMAND_DELEGATION_CASES: tuple[
    tuple[
        str,
        str,
        str,
        Callable[[ModuleType], tuple[tuple[object, ...], dict[str, object]]],
        object,
        object,
    ],
    ...,
] = (
    (
        "bioetl.interfaces.cli.commands.adr",
        "get_adr_service",
        "bioetl.composition.control_plane_api.get_adr_service",
        _no_args,
        object(),
        "identity",
    ),
    (
        "bioetl.interfaces.cli.commands.archive",
        "get_lifecycle_service",
        "bioetl.interfaces.cli.commands.domains.maintenance.service_access.get_lifecycle_service",
        _no_args,
        object(),
        "identity",
    ),
    (
        "bioetl.interfaces.cli.commands.config",
        "get_config_service",
        "bioetl.composition.control_plane_api.get_config_service",
        _no_args,
        object(),
        "identity",
    ),
    (
        "bioetl.interfaces.cli.commands.debug",
        "get_pipeline_runner_service",
        "bioetl.composition.execution_api.get_pipeline_runner_service",
        _registry_kwarg,
        object(),
        "identity",
    ),
    (
        "bioetl.interfaces.cli.commands.diagnostics",
        "get_observability_diagnostics_bundle",
        "bioetl.composition.observability_api.get_observability_diagnostics_bundle",
        _no_args,
        object(),
        "identity",
    ),
    (
        "bioetl.interfaces.cli.commands.export",
        "get_export_service",
        "bioetl.composition.control_plane_api.get_export_service",
        _no_args,
        object(),
        "identity",
    ),
    (
        "bioetl.interfaces.cli.commands.health",
        "get_health_service",
        "bioetl.composition._services.get_health_service",
        _no_args,
        object(),
        "identity",
    ),
    (
        "bioetl.interfaces.cli.commands.health",
        "get_health_server_dependencies",
        "bioetl.interfaces.cli.commands.domains.health.server_integration.get_health_server_dependencies",
        _no_args,
        object(),
        "identity",
    ),
    (
        "bioetl.interfaces.cli.commands.lock",
        "get_lock_service",
        "bioetl.composition.control_plane_api.get_lock_service",
        _no_args,
        object(),
        "identity",
    ),
    (
        "bioetl.interfaces.cli.commands.domains.health.metrics_server_integration",
        "ensure_metrics_server_started",
        "bioetl.composition.execution_api.ensure_metrics_server_started",
        _no_args,
        True,
        True,
    ),
    (
        "bioetl.interfaces.cli.commands.run",
        "get_pipeline_runner_service",
        "bioetl.composition.execution_api.get_pipeline_runner_service",
        _registry_kwarg,
        object(),
        "identity",
    ),
    (
        "bioetl.interfaces.cli.commands.run_all",
        "get_pipeline_runner_service",
        "bioetl.composition.execution_api.get_pipeline_runner_service",
        _registry_kwarg,
        object(),
        "identity",
    ),
    (
        "bioetl.interfaces.cli.commands.run_composite",
        "load_composite_config",
        "bioetl.composition.composite_api.load_composite_config",
        _composite_config_args,
        object(),
        "identity",
    ),
    (
        "bioetl.interfaces.cli.commands.run_composite",
        "bootstrap_composite_runner",
        "bioetl.composition.composite_api.bootstrap_composite_runner",
        _composite_runner_args,
        object(),
        "identity",
    ),
    (
        "bioetl.interfaces.cli.commands.domains.composite.support",
        "push_metrics_to_gateway",
        "bioetl.composition.execution_api.push_metrics_to_gateway",
        _push_metrics_kwargs,
        True,
        True,
    ),
    (
        "bioetl.interfaces.cli.commands.domains.health.metrics_publication_integration",
        "publish_metrics_safely",
        "bioetl.composition.execution_api.push_metrics_to_gateway",
        _cli_metrics_publish_kwargs,
        True,
        True,
    ),
    (
        "bioetl.interfaces.cli.commands.vacuum",
        "get_lifecycle_service",
        "bioetl.interfaces.cli.commands.domains.maintenance.service_access.get_lifecycle_service",
        _no_args,
        object(),
        "identity",
    ),
    (
        "bioetl.interfaces.cli.commands.vacuum",
        "get_vacuum_service",
        "bioetl.interfaces.cli.commands.domains.maintenance.service_access.get_vacuum_service",
        _no_args,
        object(),
        "identity",
    ),
)

CLI_MAIN_LAZY_COMMAND_CASES = (
    ("diagnostics", "bioetl.interfaces.cli.commands.diagnostics", "diagnostics"),
    ("health", "bioetl.interfaces.cli.commands.health", "health"),
    ("maintenance", "bioetl.interfaces.cli.commands.maintenance", "maintenance"),
    ("quarantine", "bioetl.interfaces.cli.commands.quarantine", "quarantine"),
    ("run", "bioetl.interfaces.cli.commands.run", "run"),
    ("run-all", "bioetl.interfaces.cli.commands.run_all", "run_all"),
    (
        "run-composite",
        "bioetl.interfaces.cli.commands.run_composite",
        "run_composite",
    ),
)


@pytest.mark.unit
@pytest.mark.parametrize(
    (
        "module_name",
        "wrapper_name",
        "patch_target",
        "call_factory",
        "patched_return_value",
        "expected_result",
    ),
    COMMAND_DELEGATION_CASES,
    ids=(
        "adr-service",
        "archive-lifecycle",
        "config-service",
        "debug-runner-service",
        "diagnostics-bundle",
        "export-service",
        "health-service",
        "health-server-deps",
        "lock-service",
        "metrics-server-start",
        "run-runner-service",
        "run-all-runner-service",
        "run-composite-config",
        "run-composite-bootstrap",
        "composite-support-push-metrics",
        "cli-health-publish-metrics",
        "vacuum-lifecycle",
        "vacuum-service",
    ),
)
def test_cli_command_wrappers_delegate_to_public_facades(
    module_name: str,
    wrapper_name: str,
    patch_target: str,
    call_factory: Callable[[ModuleType], tuple[tuple[object, ...], dict[str, object]]],
    patched_return_value: object,
    expected_result: object,
) -> None:
    """Thin command wrappers should stay as lazy delegates to sanctioned seams."""
    module = importlib.import_module(module_name)
    args, kwargs = call_factory(module)

    with patch(patch_target, return_value=patched_return_value) as mock_impl:
        result = getattr(module, wrapper_name)(*args, **kwargs)

    if expected_result == "identity":
        assert result is patched_return_value
    else:
        assert result is expected_result
    mock_impl.assert_called_once_with(*args, **kwargs)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("command_name", "module_name", "attribute_name"),
    CLI_MAIN_LAZY_COMMAND_CASES,
    ids=(
        "diagnostics",
        "health",
        "maintenance",
        "quarantine",
        "run",
        "run-all",
        "run-composite",
    ),
)
def test_cli_main_registers_public_command_seams(
    command_name: str,
    module_name: str,
    attribute_name: str,
) -> None:
    """cli.main should resolve lazy commands via the public seam modules."""
    cli_main = importlib.import_module("bioetl.interfaces.cli.main")

    registered_module_name, registered_attribute_name, _help_text = (
        cli_main._LAZY_COMMAND_SPECS[command_name]
    )

    assert registered_module_name == module_name
    assert registered_attribute_name == attribute_name


@pytest.mark.unit
def test_run_help_exposes_replay_parentage_flags() -> None:
    """Published run CLI must expose explicit replay ancestry flags."""
    from bioetl.interfaces.cli.commands.run import run

    runner = CliRunner()
    result = runner.invoke(run, ["--help"])

    assert result.exit_code == 0
    assert "--replay-of-run-id" in result.output
    assert "--replay-of-manifest-id" in result.output
