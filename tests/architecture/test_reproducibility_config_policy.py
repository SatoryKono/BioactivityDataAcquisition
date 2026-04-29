"""Architecture checks for reproducibility-critical production configs."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
PUBLISHED_ENTITY_CONFIGS = ROOT / "configs" / "entities"
PUBLISHED_COMPOSITE_CONFIGS = ROOT / "configs" / "composites"


def _load_yaml(path: Path) -> dict[str, object]:
    return cast(
        dict[str, object], yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    )


def _pipeline_sink(payload: dict[str, object]) -> dict[str, object]:
    pipeline = payload.get("pipeline")
    if isinstance(pipeline, dict) and isinstance(pipeline.get("sink"), dict):
        return cast(dict[str, object], pipeline["sink"])
    sink = payload.get("sink")
    if isinstance(sink, dict):
        return cast(dict[str, object], sink)
    return {}


def _enabled_layer_mode(layer_config: object) -> str:
    if not isinstance(layer_config, dict):
        return ""
    if layer_config.get("enabled", True) is False:
        return ""
    return str(layer_config.get("mode") or "").strip().lower()


def _production_config_paths() -> tuple[Path, ...]:
    entity_paths = tuple(sorted(PUBLISHED_ENTITY_CONFIGS.glob("*/*.yaml")))
    composite_paths = tuple(sorted(PUBLISHED_COMPOSITE_CONFIGS.glob("*.yaml")))
    return entity_paths + composite_paths


@pytest.mark.architecture
def test_published_production_configs_do_not_enable_append_semantic_sinks() -> None:
    """Silver/Gold append mode is not replay-safe for production semantics."""
    violations: list[str] = []

    for path in _production_config_paths():
        sink = _pipeline_sink(_load_yaml(path))
        for layer_name in ("silver", "gold"):
            mode = _enabled_layer_mode(sink.get(layer_name))
            if mode == "append":
                violations.append(
                    f"{path.relative_to(ROOT)}: sink.{layer_name}.mode=append"
                )

    assert not violations, (
        "Published production configs must not enable append-mode Silver/Gold "
        f"semantic sinks: {violations}"
    )
