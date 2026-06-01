"""Architecture guardrail for pipeline-level source pagination overrides."""

from __future__ import annotations

import pytest

from pathlib import Path
from typing import Any

import yaml

pytestmark = pytest.mark.architecture

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENTITIES_DIR = PROJECT_ROOT / "configs" / "entities"

_FORBIDDEN_PROVIDER_KEYS: tuple[str, ...] = (
    "batch_size",
    "page_size",
    "max_url_length",
    "cursor_pagination",
)


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else {}


def _collect_forbidden_paths(path: Path) -> list[str]:
    payload = _load_yaml(path)
    pipeline = payload.get("pipeline")
    if not isinstance(pipeline, dict):
        return []

    source = pipeline.get("source")
    if not isinstance(source, dict):
        return []

    forbidden: list[str] = []
    if "batch_size" in source:
        forbidden.append("pipeline.source.batch_size")
    provider_config = source.get("provider_config")
    if isinstance(provider_config, dict):
        pagination = provider_config.get("pagination")
        if isinstance(pagination, dict) and pagination:
            forbidden.append("pipeline.source.provider_config.pagination")
        for key in _FORBIDDEN_PROVIDER_KEYS:
            if key in provider_config:
                forbidden.append(f"pipeline.source.provider_config.{key}")

    batch = source.get("batch")
    if isinstance(batch, dict) and batch:
        forbidden.append("pipeline.source.batch")

    return forbidden


def test_pipeline_configs_do_not_override_source_pagination_directly() -> None:
    """Unified entity configs must use page_size_override instead of source pagination."""
    violations: list[str] = []
    for path in sorted(ENTITIES_DIR.rglob("*.yaml")):
        forbidden = _collect_forbidden_paths(path)
        if forbidden:
            rel = path.relative_to(PROJECT_ROOT)
            violations.append(f"{rel}: {', '.join(forbidden)}")

    assert not violations, (
        "Pipeline configs must not override provider source pagination directly. "
        "Use pipeline.page_size_override instead.\n" + "\n".join(violations)
    )
