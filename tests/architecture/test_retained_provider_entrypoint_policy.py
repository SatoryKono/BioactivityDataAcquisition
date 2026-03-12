"""Guardrails for retained provider adapter entrypoints."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src"
TEST_ROOT = ROOT / "tests"
CURRENT_TEST_FILE = Path(__file__).resolve()

LEGACY_PROVIDER_PATHS = frozenset(
    {
        "bioetl.infrastructure.adapters.pubmed.pubmed_client",
        "bioetl.infrastructure.adapters.semanticscholar.adapter",
    }
)

ALLOWED_SRC_FILES = frozenset(
    {
        ROOT
        / "src"
        / "bioetl"
        / "infrastructure"
        / "adapters"
        / "pubmed"
        / "client.py",
        ROOT
        / "src"
        / "bioetl"
        / "infrastructure"
        / "adapters"
        / "semanticscholar"
        / "client.py",
    }
)

ALLOWED_TEST_FILES = frozenset(
    {
        CURRENT_TEST_FILE,
        ROOT
        / "tests"
        / "unit"
        / "infrastructure"
        / "adapters"
        / "test_provider_entrypoints.py",
        ROOT / "tests" / "architecture" / "test_adapter_contracts.py",
    }
)


def _find_legacy_path_references(search_root: Path, allowed_files: frozenset[Path]) -> list[str]:
    violations: list[str] = []
    for py_file in search_root.rglob("*.py"):
        if py_file in allowed_files or "__pycache__" in py_file.parts:
            continue
        text = py_file.read_text(encoding="utf-8")
        for legacy_path in LEGACY_PROVIDER_PATHS:
            if legacy_path in text:
                rel_path = py_file.relative_to(ROOT).as_posix()
                violations.append(f"{rel_path} references {legacy_path}")
    return violations


@pytest.mark.architecture
def test_legacy_provider_implementation_paths_are_not_used_in_src() -> None:
    """First-party source must import retained provider entrypoints, not old impl paths."""
    violations = _find_legacy_path_references(SRC_ROOT, ALLOWED_SRC_FILES)
    assert not violations, (
        "Legacy provider implementation paths are still referenced from src/:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_legacy_provider_implementation_paths_are_limited_to_compat_tests() -> None:
    """Legacy provider implementation paths in tests must stay confined to compat coverage."""
    violations = _find_legacy_path_references(TEST_ROOT, ALLOWED_TEST_FILES)
    assert not violations, (
        "Legacy provider implementation paths leaked outside dedicated compatibility tests:\n"
        + "\n".join(violations)
    )
