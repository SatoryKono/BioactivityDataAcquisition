"""Guard against reintroducing the removed pipeline base fallback claim."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BASE_PIPELINE_CONFIG = ROOT / "configs" / "base" / "pipeline.yaml"


@pytest.mark.architecture
def test_pipeline_base_config_does_not_claim_removed_base_yaml_fallback() -> None:
    """The canonical base pipeline config must not advertise removed fallback paths."""
    text = BASE_PIPELINE_CONFIG.read_text(encoding="utf-8")
    assert "configs/pipelines/_base.yaml" not in text


@pytest.mark.architecture
def test_removed_pipeline_base_yaml_directory_is_absent() -> None:
    """The historical configs/pipelines surface must not silently return."""
    assert not (ROOT / "configs" / "pipelines").exists()
