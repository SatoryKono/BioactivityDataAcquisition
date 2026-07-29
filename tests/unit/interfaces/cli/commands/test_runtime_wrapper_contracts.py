# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Runtime coverage for retained public CLI wrapper contracts."""

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
        "bioetl.interfaces.cli.commands.domains.quarantine.command",
        "bioetl.interfaces.cli.commands.quarantine",
        ("quarantine", "get_quarantine_runtime_service", "get_quarantine_service"),
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


@pytest.mark.unit
def test_removed_plan_command_facade_stays_absent() -> None:
    """The former top-level maintenance plan facade must not return."""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("bioetl.interfaces.cli.commands.plan")


@pytest.mark.unit
def test_removed_run_command_wrapper_stays_absent() -> None:
    """Retired run-command wrapper must not return under the domains package."""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("bioetl.interfaces.cli.commands.domains.run.command")


@pytest.mark.unit
def test_removed_maintenance_command_wrapper_stays_absent() -> None:
    """Retired maintenance wrapper must not return under the domains package."""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(
            "bioetl.interfaces.cli.commands.domains.maintenance.command"
        )


@pytest.mark.unit
def test_removed_composite_command_wrapper_stays_absent() -> None:
    """Retired composite wrapper must not return under the domains package."""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(
            "bioetl.interfaces.cli.commands.domains.composite.command"
        )


@pytest.mark.unit
def test_commands_package_does_not_advertise_removed_plan_facade() -> None:
    """Package-root CLI exports must stay aligned with the removed plan seam."""
    commands_package = importlib.import_module("bioetl.interfaces.cli.commands")

    assert "plan" not in commands_package.__all__
    assert "plan" not in dir(commands_package)


@pytest.mark.unit
def test_diagnostics_domain_package_lazy_exports_command() -> None:
    """Diagnostics domain package should lazily expose its command group."""
    package = importlib.import_module(
        "bioetl.interfaces.cli.commands.domains.diagnostics"
    )
    command_module = importlib.import_module(
        "bioetl.interfaces.cli.commands.domains.diagnostics.command"
    )

    assert package.__getattr__("diagnostics") is command_module.diagnostics

    with pytest.raises(AttributeError, match="unknown"):
        package.__getattr__("unknown")


@pytest.mark.unit
def test_maintenance_domain_package_lazy_exports_public_group() -> None:
    """Maintenance domain package owns the group; public seam re-exports it."""
    package = importlib.import_module(
        "bioetl.interfaces.cli.commands.domains.maintenance"
    )
    owner_module = importlib.import_module(
        "bioetl.interfaces.cli.commands.domains.maintenance.command_group"
    )
    public_module = importlib.import_module(
        "bioetl.interfaces.cli.commands.maintenance"
    )

    assert package.__getattr__("maintenance") is owner_module.maintenance
    assert public_module.maintenance is owner_module.maintenance

    with pytest.raises(AttributeError, match="unknown"):
        package.__getattr__("unknown")
