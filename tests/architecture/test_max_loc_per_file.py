"""Repository-level guardrail for maximum source file size."""

from __future__ import annotations

from pathlib import Path

import pytest

MAX_FILE_LOC = 500


def test_no_source_file_exceeds_500_loc(src_dir: Path) -> None:
    """Keep source modules compact for readability and reviewability."""
    source_root = src_dir / "bioetl"
    if not source_root.exists():
        pytest.skip("Source directory not found: src/bioetl")

    # Files allowed to exceed 500 LOC per configs/quality/architecture_metric_exemptions.yaml
    exemptions = {
        "bioetl/infrastructure/storage/silver_writer_metadata_mixin.py"
    }

    violations: list[tuple[int, Path]] = []
    for py_file in sorted(source_root.rglob("*.py")):
        if py_file.name == "__init__.py":
            continue
        rel_path = str(py_file.relative_to(src_dir))
        if rel_path in exemptions:
            continue

        loc = len(py_file.read_text(encoding="utf-8").splitlines())
        if loc > MAX_FILE_LOC:
            violations.append((loc, py_file.relative_to(src_dir)))

    assert not violations, (
        f"Found {len(violations)} source files above {MAX_FILE_LOC} LOC:\n"
        + "\n".join(
            f"  - {path}: {loc} LOC" for loc, path in sorted(violations, reverse=True)
        )
    )
