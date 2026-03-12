"""Guardrails for retained adapter entrypoint policy."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src"
TESTS_ROOT = ROOT / "tests"
CURRENT_TEST_FILE = Path(__file__).resolve()
LEGACY_IMPLEMENTATION_PATHS = frozenset(
    {
        "bioetl.infrastructure.adapters.pubmed.pubmed_client",
        "bioetl.infrastructure.adapters.semanticscholar.adapter",
    }
)
ALLOWED_SRC_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "infrastructure" / "adapters" / "pubmed" / "client.py",
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


def _iter_legacy_path_mentions(
    search_root: Path,
    *,
    allowed_files: frozenset[Path],
) -> list[str]:
    violations: list[str] = []
    for py_file in search_root.rglob("*.py"):
        if py_file in allowed_files or "__pycache__" in py_file.parts:
            continue
        rel_path = py_file.relative_to(ROOT).as_posix()
        lines = py_file.read_text(encoding="utf-8").splitlines()
        for lineno, line in enumerate(lines, start=1):
            for legacy_path in LEGACY_IMPLEMENTATION_PATHS:
                if legacy_path in line:
                    violations.append(f"{rel_path}:{lineno} mentions {legacy_path}")
    return violations


@pytest.mark.architecture
def test_retained_adapter_entrypoints_keep_legacy_paths_out_of_src() -> None:
    """First-party source must use retained canonical entrypoints, not legacy paths."""
    violations = _iter_legacy_path_mentions(
        SRC_ROOT,
        allowed_files=ALLOWED_SRC_FILES,
    )
    assert not violations, (
        "Legacy adapter implementation paths leaked into first-party src/ imports:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_legacy_adapter_paths_are_confined_to_dedicated_compat_tests() -> None:
    """Ordinary tests must not accumulate new references to legacy adapter paths."""
    violations = _iter_legacy_path_mentions(
        TESTS_ROOT,
        allowed_files=ALLOWED_TEST_FILES,
    )
    assert not violations, (
        "Legacy adapter implementation paths gained new non-compat test usages:\n"
        + "\n".join(violations)
    )
