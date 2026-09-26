"""Shared architecture scan index for governance tests.

Architecture tests must consume session-scoped, content-addressed caches from
``tests/architecture/conftest.py`` instead of independently walking
``src/`` / ``tests/`` trees. This module documents the canonical fixture names
and provides small pure helpers that tests can import without reimplementing
file discovery.

Canonical fixtures (defined in ``tests/architecture/conftest.py``):

- ``source_content_cache`` / ``source_ast_cache``
- ``test_content_cache`` / ``test_ast_cache``
- ``source_import_records`` / ``test_import_records``
- ``docs_text_cache`` / ``config_yaml_cache``
- ``subprocess_scanner_cache`` / ``test_governance_report_cache``

Migration rule (issue #6598 / T-02): any new whole-repo architecture scan MUST
request one of the fixtures above or call helpers here. Independent
``Path.rglob`` / ``os.walk`` over ``src/bioetl`` inside test bodies is forbidden
for new tests.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path

# Fixture names that constitute the shared architecture scan index.
ARCHITECTURE_SCAN_INDEX_FIXTURES: frozenset[str] = frozenset(
    {
        "source_content_cache",
        "source_ast_cache",
        "test_content_cache",
        "test_ast_cache",
        "source_import_records",
        "test_import_records",
        "docs_text_cache",
        "config_yaml_cache",
        "subprocess_scanner_cache",
        "test_governance_report_cache",
    }
)

# First-wave migration targets from slowest-tests telemetry (T-02).
ARCHITECTURE_SCAN_INDEX_MIGRATION_TARGETS: tuple[str, ...] = (
    "tests/architecture/test_naming_ambiguity_classifier.py",
    "tests/architecture/test_provider_registry_decomposition.py",
    "tests/architecture/test_debt_governance_telemetry_reporting.py",
    "tests/architecture/test_quality_exemptions_registry.py",
    "tests/architecture/test_import_graph_invariants.py",
    "tests/architecture/test_private_module_imports.py",
    "tests/architecture/test_vcr_metadata_catalog_drift.py",
)


def iter_cached_python_paths(content_cache: Mapping[Path, str]) -> tuple[Path, ...]:
    """Return sorted Python paths from a session content cache."""
    return tuple(sorted(content_cache, key=lambda path: path.as_posix()))


def filter_cache_by_suffix(
    content_cache: Mapping[Path, str],
    *,
    suffixes: Iterable[str],
) -> dict[Path, str]:
    """Return a subset of the content cache limited to filename suffixes."""
    suffix_tuple = tuple(suffixes)
    return {
        path: text
        for path, text in content_cache.items()
        if path.name.endswith(suffix_tuple)
    }


def relative_posix(path: Path, root: Path) -> str:
    """Return a stable POSIX path relative to ``root`` when possible."""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()
