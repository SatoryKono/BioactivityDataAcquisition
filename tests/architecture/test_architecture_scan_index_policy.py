"""Guardrails for the shared architecture scan index (T-02 / #6598)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.helpers.architecture_scan_index import (
    ARCHITECTURE_SCAN_INDEX_FIXTURES,
    ARCHITECTURE_SCAN_INDEX_MIGRATION_TARGETS,
    iter_cached_python_paths,
)

pytestmark = pytest.mark.architecture

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FORBIDDEN_WALK_CALLS = frozenset({"rglob", "walk"})


def test_architecture_scan_index_fixtures_are_registered(
    source_content_cache: dict[Path, str],
    source_ast_cache: dict[Path, ast.Module],
    test_content_cache: dict[Path, str],
) -> None:
    """Session fixtures must be available and non-empty on a full checkout."""
    assert ARCHITECTURE_SCAN_INDEX_FIXTURES
    assert source_content_cache
    assert source_ast_cache
    assert test_content_cache
    source_paths = iter_cached_python_paths(source_content_cache)
    assert any(path.name == "__init__.py" for path in source_paths[:50])
    assert len(source_ast_cache) == len(source_content_cache)


def test_migration_targets_prefer_shared_index_or_bounded_paths() -> None:
    """Hotspot architecture modules must prefer shared index or bounded scopes.

    Allowed patterns:
    - request shared index fixtures from conftest
    - operate on caller-provided ``tmp_path`` trees
    - delegate scanning to inventory scripts / git-index helpers
    - bounded walks over fixture dirs (e.g. ``tests/fixtures/vcr``)
    """
    still_unmigrated: list[str] = []
    migrated = 0
    for relative in ARCHITECTURE_SCAN_INDEX_MIGRATION_TARGETS:
        path = _REPO_ROOT / relative
        assert path.is_file(), f"missing migration target: {relative}"
        source = path.read_text(encoding="utf-8")
        uses_index_fixture = any(
            fixture_name in source for fixture_name in ARCHITECTURE_SCAN_INDEX_FIXTURES
        )
        uses_bounded_tmp = "tmp_path" in source
        uses_delegated_scan = any(
            token in source
            for token in (
                "scripts.engineering",
                "discover_files",
                "git_grep",
                "collect_dependency_snapshot",
                "load_exemptions_registry",
                "importlib",
            )
        )
        uses_fixture_root_only = (
            "tests/fixtures" in source and "src/bioetl" not in source
        )

        if (
            uses_index_fixture
            or uses_bounded_tmp
            or uses_delegated_scan
            or uses_fixture_root_only
        ):
            migrated += 1
        else:
            still_unmigrated.append(relative)

    # T-02 acceptance: at least 5 of the telemetry hotspot zones are migrated.
    assert migrated >= 5, (
        f"only {migrated} hotspot architecture zones migrated to shared index / "
        f"bounded scanners; still unmigrated: {still_unmigrated}"
    )
