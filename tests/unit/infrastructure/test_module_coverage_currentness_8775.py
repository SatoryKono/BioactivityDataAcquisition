"""Infrastructure coverage regression vectors for #8775."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.infrastructure.config.source_normalizers.source import (
    _deep_merge,
    _normalize_rate_limit,
)
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.infrastructure.storage.support.checkpoint_writer import (
    CheckpointPathError,
    CheckpointSizeError,
    FileCompositeCheckpointWriter,
)


pytestmark = pytest.mark.unit


def test_source_normalizer_merges_and_rejects_conflicting_rate_aliases() -> None:
    assert _deep_merge({"nested": {"a": 1}}, {"nested": {"b": 2}}) == {
        "nested": {"a": 1, "b": 2}
    }
    payload = {
        "rate_limit": {
            "authenticated": {"requests_per_second": 1},
            "with_api_key": {"requests_per_second": 2},
        }
    }
    with pytest.raises(ValueError, match="Conflicting rate_limit"):
        _normalize_rate_limit(payload)


def test_pipeline_config_rejects_oversized_batches() -> None:
    with pytest.raises(ValueError, match="batch_size cannot exceed"):
        PipelineYamlConfig.validate_batch_size(5001)


def test_checkpoint_writer_residual_safety_branches(tmp_path: Path) -> None:
    writer = FileCompositeCheckpointWriter(tmp_path, max_checkpoint_bytes=2)

    with pytest.raises(CheckpointPathError):
        writer.read("/absolute.json")

    (tmp_path / "large.json").write_text("oversized", encoding="utf-8")
    with pytest.raises(CheckpointSizeError):
        writer.read("large.json")

    with pytest.raises(CheckpointPathError):
        writer.list_glob("../*.json")
