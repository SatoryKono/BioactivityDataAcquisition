"""Architecture guardrails for config-root normalization."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
EFFECTIVE_CONFIG_SOURCE_REF_BUILDER = (
    ROOT
    / "src"
    / "bioetl"
    / "composition"
    / "runtime_builders"
    / "_effective_config_artifact_builder_support.py"
)


def test_effective_config_source_refs_use_canonical_config_root_anchor() -> None:
    """Effective-config source refs must not infer repo root from source layout."""
    text = EFFECTIVE_CONFIG_SOURCE_REF_BUILDER.read_text(encoding="utf-8")

    assert "resolve_configs_root().parent" in text
    assert "Path(__file__).resolve().parents" not in text
