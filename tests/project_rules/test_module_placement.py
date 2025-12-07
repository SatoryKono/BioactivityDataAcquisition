from __future__ import annotations

from pathlib import Path

import pytest
from tests.project_rules.conftest import iter_python_files

ALLOWED_LAYERS = {"domain", "application", "infrastructure", "interfaces"}
ALLOWED_ROOT_FILES = {"__init__.py", "__main__.py"}


def test_new_modules_are_in_layers(bioetl_root: Path) -> None:
    violations: list[str] = []
    for path in iter_python_files(bioetl_root):
        try:
            relative = path.relative_to(bioetl_root)
        except ValueError:
            continue

        parts = relative.parts
        if not parts:
            continue

        first = parts[0]
        if first not in ALLOWED_LAYERS:
            if path.name in ALLOWED_ROOT_FILES and len(parts) == 1:
                continue
            violations.append(
                f"{path.as_posix()}: модуль должен находиться в одном из слоёв "
                f"{sorted(ALLOWED_LAYERS)}"
            )

    if violations:
        pytest.fail("\n".join(sorted(set(violations))))
