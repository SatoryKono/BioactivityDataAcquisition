"""Architecture guardrails for legacy Bronze metadata builder imports."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TARGET_MODULE = "bioetl.infrastructure.storage.bronze.metadata_builders"
ALLOWED_IMPORTERS = {
    "src/bioetl/infrastructure/storage/bronze/metadata_mixin.py",
}

# Narrow scan: only the bronze storage package (and its package root).
# Full-tree scans hang on cloud-synced checkouts with large __pycache__ trees.
_SCAN_DIRS = (ROOT / "src" / "bioetl" / "infrastructure" / "storage" / "bronze",)


def _iter_python_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(
        path
        for path in directory.glob("*.py")
        if path.is_file() and path.name != "__pycache__"
    )


def _candidate_import_paths(pattern: str) -> list[Path]:
    """Return bronze package paths that contain *pattern* as text."""
    needle = pattern.encode("utf-8")
    matches: list[Path] = []
    for scan_dir in _SCAN_DIRS:
        for path in _iter_python_files(scan_dir):
            try:
                if needle in path.read_bytes():
                    matches.append(path)
            except OSError:
                continue
    return matches


@pytest.mark.architecture
@pytest.mark.timeout(30)
def test_runtime_code_does_not_import_legacy_bronze_metadata_builders_directly() -> (
    None
):
    violations: list[str] = []
    for path in _candidate_import_paths(TARGET_MODULE):
        relative_path = path.relative_to(ROOT).as_posix()
        if relative_path in ALLOWED_IMPORTERS:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if any(
            isinstance(node, ast.ImportFrom) and node.module == TARGET_MODULE
            for node in ast.walk(tree)
        ):
            violations.append(relative_path)

    assert not violations, (
        "Legacy Bronze metadata builders must stay behind the canonical "
        "metadata_mixin adapter / MetadataCoordinator path. Violations:\n"
        + "\n".join(sorted(violations))
    )
