"""Closeout ratchets for Wave 4 complexity/shared-seam slices."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

FACADE_RATCHETS: dict[str, tuple[int, set[str]]] = {
    "src/bioetl/infrastructure/adapters/decorators/retry.py": (
        285,
        {"bioetl.infrastructure.adapters.decorators._retry_support"},
    ),
}


def _path(relative_path: str) -> Path:
    return ROOT / relative_path


def _imported_modules(relative_path: str) -> set[str]:
    tree = ast.parse(_path(relative_path).read_text(encoding="utf-8"))
    return {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }


@pytest.mark.architecture
@pytest.mark.parametrize(
    ("relative_path", "max_lines", "required_modules"),
    [
        (relative_path, max_lines, required_modules)
        for relative_path, (max_lines, required_modules) in FACADE_RATCHETS.items()
    ],
)
def test_wave4_complexity_facades_stay_bounded_and_helper_backed(
    relative_path: str,
    max_lines: int,
    required_modules: set[str],
) -> None:
    """Wave 4 seams should stay thin and routed through extracted helpers."""
    path = _path(relative_path)
    source = path.read_text(encoding="utf-8")
    line_count = len(source.splitlines())
    assert line_count <= max_lines, (
        f"{relative_path} regrew to {line_count} lines "
        f"(max {max_lines}). Keep Wave 4 complexity seams narrow and move "
        "policy/helper logic into extracted modules."
    )

    imported_modules = _imported_modules(relative_path)
    missing_modules = required_modules - imported_modules
    assert not missing_modules, (
        f"{relative_path} no longer imports required extracted helpers:\n"
        + "\n".join(sorted(missing_modules))
    )
