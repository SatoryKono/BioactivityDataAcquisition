"""Closeout ratchets for Wave 4 complexity/shared-seam slices."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

FACADE_RATCHETS: dict[str, tuple[int, set[str]]] = {
    "src/bioetl/infrastructure/adapters/cached_bronze_data_source.py": (
        230,
        {"bioetl.infrastructure.adapters._cached_bronze_support"},
    ),
    "src/bioetl/infrastructure/adapters/common/base_title_fallback.py": (
        260,
        {"bioetl.infrastructure.adapters.common._title_fallback_flow"},
    ),
    "src/bioetl/infrastructure/adapters/decorators/circuit_breaker.py": (
        250,
        {"bioetl.infrastructure.adapters.decorators._circuit_breaker_support"},
    ),
    "src/bioetl/infrastructure/adapters/http/circuit_breaker.py": (
        220,
        {"bioetl.infrastructure.adapters.http._circuit_breaker_support"},
    ),
    "src/bioetl/infrastructure/adapters/decorators/retry.py": (
        285,
        {"bioetl.infrastructure.adapters.decorators._retry_support"},
    ),
}

CONTRACT_RATCHETS: dict[str, tuple[int, set[str]]] = {
    "src/bioetl/infrastructure/adapters/decorators/_circuit_breaker_support.py": (
        120,
        {"bioetl.infrastructure.adapters.circuit_breaker_contract"},
    ),
    "src/bioetl/infrastructure/adapters/http/_circuit_breaker_support.py": (
        210,
        {"bioetl.infrastructure.adapters.circuit_breaker_contract"},
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


@pytest.mark.architecture
@pytest.mark.parametrize(
    ("relative_path", "max_lines", "required_modules"),
    [
        (relative_path, max_lines, required_modules)
        for relative_path, (max_lines, required_modules) in CONTRACT_RATCHETS.items()
    ],
)
def test_wave4_circuit_breaker_support_modules_stay_contract_backed(
    relative_path: str,
    max_lines: int,
    required_modules: set[str],
) -> None:
    """Circuit-breaker support modules should keep one shared typed contract."""
    path = _path(relative_path)
    source = path.read_text(encoding="utf-8")
    line_count = len(source.splitlines())
    assert line_count <= max_lines, (
        f"{relative_path} regrew to {line_count} lines "
        f"(max {max_lines}). Keep transition/state logic in the shared "
        "circuit-breaker contract instead of reintroducing duplicate helpers."
    )

    imported_modules = _imported_modules(relative_path)
    missing_modules = required_modules - imported_modules
    assert not missing_modules, (
        f"{relative_path} no longer imports the shared circuit-breaker "
        "contract:\n" + "\n".join(sorted(missing_modules))
    )
