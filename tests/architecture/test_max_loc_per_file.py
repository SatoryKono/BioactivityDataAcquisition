"""Repository-level guardrail for maximum source file size."""

from __future__ import annotations

from pathlib import Path

import pytest

MAX_FILE_LOC = 500

# Files that exceed MAX_FILE_LOC due to ruff format line expansion but are
# within their layer-specific limit (test_code_metrics.py).  Each entry maps
# a repo-relative POSIX path to its allowed LOC ceiling.
_FORMAT_EXPANSION_EXEMPTIONS: dict[str, int] = {
    "bioetl/infrastructure/storage/silver_writer_metadata_mixin.py": 520,
}


def test_no_source_file_exceeds_500_loc(src_dir: Path) -> None:
    """Keep source modules compact for readability and reviewability."""
    source_root = src_dir / "bioetl"
    if not source_root.exists():
        pytest.skip("Source directory not found: src/bioetl")

    violations: list[tuple[int, Path]] = []
    for py_file in sorted(source_root.rglob("*.py")):
        if py_file.name == "__init__.py":
            continue
        rel = py_file.relative_to(src_dir)
        loc = len(py_file.read_text(encoding="utf-8").splitlines())
        limit = _FORMAT_EXPANSION_EXEMPTIONS.get(str(rel), MAX_FILE_LOC)
        if loc > limit:
            violations.append((loc, rel))

    assert not violations, (
        f"Found {len(violations)} source files above LOC limit:\n"
        + "\n".join(
            f"  - {path}: {loc} LOC" for loc, path in sorted(violations, reverse=True)
        )
    )
