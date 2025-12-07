from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pytest
from tests.architecture.test_layer_dependencies import (
    _collect_imports,
    _module_from_path,
)
from tests.project_rules.conftest import iter_python_files

ALLOWED_LAYERS = {"domain", "application", "infrastructure", "interfaces"}


def _first_layer(path: Path, *, bioetl_root: Path) -> str | None:
    try:
        relative = path.relative_to(bioetl_root)
    except ValueError:
        return None
    parts = relative.parts
    return parts[0] if parts else None


def _assert_no_violations(violations: Iterable[str]) -> None:
    items = sorted(set(violations))
    if items:
        pytest.fail("\n".join(items))


def test_sources_reside_in_known_layers(bioetl_root: Path) -> None:
    violations: list[str] = []
    for path in iter_python_files(bioetl_root):
        layer = _first_layer(path, bioetl_root=bioetl_root)
        if layer not in ALLOWED_LAYERS and path.name not in {
            "__init__.py",
            "__main__.py",
        }:
            violations.append(f"{path.as_posix()}: unexpected layer '{layer}'")

    _assert_no_violations(violations)


def test_layer_dependencies(bioetl_root: Path) -> None:
    violations: list[str] = []

    for file_path in iter_python_files(bioetl_root):
        module, is_package = _module_from_path(file_path)

        for reference in _collect_imports(file_path):
            ref = reference.module

            if module.startswith("bioetl.domain"):
                if ref.startswith(
                    ("bioetl.infrastructure", "bioetl.application", "bioetl.interfaces")
                ):
                    violations.append(
                        f"{file_path.as_posix()}:{reference.lineno}: "
                        f"domain must not depend on outer layers ({ref})"
                    )

            if module.startswith("bioetl.application"):
                if ref.startswith(("bioetl.infrastructure", "bioetl.interfaces")):
                    violations.append(
                        f"{file_path.as_posix()}:{reference.lineno}: "
                        "application must not depend on "
                        f"infrastructure/interfaces ({ref})"
                    )

            if module.startswith("bioetl.infrastructure"):
                if ref.startswith("bioetl.application"):
                    violations.append(
                        f"{file_path.as_posix()}:{reference.lineno}: "
                        f"infrastructure must not depend on application ({ref})"
                    )

            if module.startswith("bioetl.interfaces"):
                # Interfaces can depend on others; no restriction.
                continue

            # Relative imports that resolve outside the current package are
            # handled in _collect_imports, but guard against accidental empty
            # module names.
            if not ref:
                violations.append(
                    f"{file_path.as_posix()}:{reference.lineno}: unresolved import target"
                )

    _assert_no_violations(violations)
