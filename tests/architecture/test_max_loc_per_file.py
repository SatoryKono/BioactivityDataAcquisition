"""Repository-level guardrail for maximum source file size."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.infrastructure.quality import (
    build_module_path_key,
    get_registry_values,
    resolve_registry_value,
)

# Layer-specific limits (in lines of code)
LAYER_LIMITS = {
    "domain": 305,
    "application": 500,
    "composition": 350,
    "infrastructure": 650,
    "interfaces": 420,
}


def test_no_source_file_exceeds_500_loc(src_dir: Path) -> None:
    """Keep source modules compact for readability and reviewability."""
    source_root = src_dir / "bioetl"
    if not source_root.exists():
        pytest.skip("Source directory not found: src/bioetl")

    # Load file size limit exemptions
    EXEMPTIONS = get_registry_values("file_size_limits")

    violations: list[tuple[int, Path, int]] = []
    for py_file in sorted(source_root.rglob("*.py")):
        if py_file.name == "__init__.py":
            continue
        
        loc = len(py_file.read_text(encoding="utf-8").splitlines())
        
        # Determine the layer for this file
        parts = py_file.relative_to(source_root).parts
        if len(parts) < 1:
            continue
        layer = parts[0]
        
        # Get layer-specific limit
        default_limit = LAYER_LIMITS.get(layer, 500)
        
        # Check for exemptions
        file_limit = resolve_registry_value(
            EXEMPTIONS,
            module_path=build_module_path_key(py_file, src_root=src_dir),
            legacy_name=py_file.name,
        )
        if file_limit is None:
            file_limit = default_limit

        if loc > file_limit:
            violations.append((loc, py_file.relative_to(src_dir), file_limit))

    assert not violations, (
        f"Found {len(violations)} source files above their LOC limits:\n"
        + "\n".join(
            f"  - {path}: {loc} LOC (limit: {file_limit})"
            for loc, path, file_limit in sorted(violations, reverse=True)
        )
    )
