"""Unit tests for domain command facade packages."""

from __future__ import annotations

import builtins
import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


@pytest.mark.parametrize(
    ("relative_path", "export_name", "command_module_name"),
    [
        (
            "src/bioetl/interfaces/cli/commands/domains/composite/__init__.py",
            "run_composite",
            "bioetl.interfaces.cli.commands.domains.composite.command",
        ),
        (
            "src/bioetl/interfaces/cli/commands/domains/health/__init__.py",
            "health",
            "bioetl.interfaces.cli.commands.domains.health.command",
        ),
        (
            "src/bioetl/interfaces/cli/commands/domains/quarantine/__init__.py",
            "quarantine",
            "bioetl.interfaces.cli.commands.domains.quarantine.command",
        ),
        (
            "src/bioetl/interfaces/cli/commands/domains/run_all/__init__.py",
            "run_all",
            "bioetl.interfaces.cli.commands.domains.run_all.command",
        ),
    ],
)
def test_domain_command_packages_export_lazy_command_symbol(
    monkeypatch: pytest.MonkeyPatch,
    relative_path: str,
    export_name: str,
    command_module_name: str,
) -> None:
    sentinel = object()
    fake_command_module = ModuleType(command_module_name)
    setattr(fake_command_module, export_name, sentinel)
    original_import = builtins.__import__

    def _fake_import(
        name: str,
        globals: dict[str, object] | None = None,
        locals: dict[str, object] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> ModuleType:
        if name == command_module_name:
            return fake_command_module
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    module_path = Path(relative_path)
    spec = importlib.util.spec_from_file_location(
        f"_test_{module_path.parent.name}_domain_package",
        module_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.__all__ == [export_name]
    assert getattr(module, export_name) is sentinel
    with pytest.raises(AttributeError, match="missing"):
        module.__getattr__("missing")


def test_maintenance_domain_package_has_lazy_export() -> None:
    """Maintenance domain has different architecture - verify __getattr__ works."""
    module_path = Path("src/bioetl/interfaces/cli/commands/domains/maintenance/__init__.py")
    spec = importlib.util.spec_from_file_location(
        "_test_maintenance_domain_package",
        module_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.__all__ == ["maintenance"]
    # Verify that __getattr__ is defined and works for missing attributes
    with pytest.raises(AttributeError, match="missing"):
        module.__getattr__("missing")
