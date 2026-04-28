"""Architecture guardrails for legacy Silver metadata identity paths."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TARGET = (
    ROOT / "src/bioetl/infrastructure/storage/silver/operations/metadata_builders.py"
)


@pytest.mark.architecture
def test_silver_metadata_builder_does_not_emit_placeholder_content_identity() -> None:
    """Silver sidecars must not publish placeholder content or run-derived IDs."""
    source = TARGET.read_text(encoding="utf-8")

    assert "placeholder-hash" not in source
    assert "{request.table_name}-{request.run_id" not in source
    assert "build_dataset_content_hash" in source
    assert "DatasetRef" in source
