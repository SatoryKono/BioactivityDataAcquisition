"""Architecture guardrails for legacy Silver metadata identity paths."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TARGET = (
    ROOT / "src/bioetl/infrastructure/storage/silver/operations/metadata_builders.py"
)
TARGET_MODULE = "bioetl.infrastructure.storage.silver.operations.metadata_builders"
ALLOWED_ADAPTER_IMPORTERS = {
    "src/bioetl/infrastructure/storage/silver/operations/metadata_write_support.py",
    "src/bioetl/infrastructure/storage/silver/operations/metadata_operations.py",
    "src/bioetl/infrastructure/storage/silver/operations/metadata_finalization_support.py",
}


@pytest.mark.architecture
def test_silver_metadata_builder_does_not_emit_placeholder_content_identity() -> None:
    """Silver sidecars must not publish placeholder content or run-derived IDs."""
    source = TARGET.read_text(encoding="utf-8")

    assert "placeholder-hash" not in source
    assert "{request.table_name}-{request.run_id" not in source
    assert "build_dataset_content_hash" in source
    assert "DatasetRef" in source


@pytest.mark.architecture
def test_source_tree_does_not_reintroduce_silver_placeholder_identity() -> None:
    """Placeholder hashes and run-derived artifact IDs are forbidden in src."""
    violations: list[str] = []
    for path in sorted((ROOT / "src").rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        if (
            "placeholder-hash" in source
            or "{request.table_name}-{request.run_id" in source
        ):
            violations.append(path.relative_to(ROOT).as_posix())

    assert not violations


@pytest.mark.architecture
def test_runtime_code_imports_silver_metadata_builder_only_through_adapters() -> None:
    """Keep the legacy builder isolated inside operations-level adapters."""
    importers: set[str] = set()
    for path in sorted((ROOT / "src").rglob("*.py")):
        if path == TARGET:
            continue
        source = path.read_text(encoding="utf-8")
        if TARGET_MODULE in source:
            importers.add(path.relative_to(ROOT).as_posix())

    assert importers <= ALLOWED_ADAPTER_IMPORTERS
