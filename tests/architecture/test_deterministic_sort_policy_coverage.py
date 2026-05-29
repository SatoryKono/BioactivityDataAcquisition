"""Architecture guard: deterministic sort policy coverage in configs."""

from __future__ import annotations

import pytest

from pathlib import Path
from typing import Any

import yaml

from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config
from bioetl.infrastructure.schemas.composite_config import (
    validate_composite_config_payload,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENTITIES_DIR = PROJECT_ROOT / "configs" / "entities"
COMPOSITES_DIR = PROJECT_ROOT / "configs" / "composites"


def _pipeline_names() -> list[str]:
    names: list[str] = []
    for provider_dir in sorted(ENTITIES_DIR.iterdir()):
        if not provider_dir.is_dir() or provider_dir.name.startswith(("_", ".")):
            continue
        for yaml_file in sorted(provider_dir.glob("*.yaml")):
            if yaml_file.name.startswith("_"):
                continue
            raw = _load_yaml(yaml_file)
            # Some entity files are status stubs (e.g. composite/*) and do not
            # expose pipeline settings, so they must be excluded from coverage.
            if not isinstance(raw.get("pipeline"), dict):
                continue
            pipeline_name = f"{provider_dir.name}_{yaml_file.stem}"
            try:
                # Keep the coverage set aligned with configs that the runtime
                # loader can actually resolve.
                load_pipeline_config(pipeline_name)
            except ValueError:
                continue
            names.append(pipeline_name)
    return names


def test_entity_pipeline_sink_sort_policy_coverage_is_full() -> None:
    total = 0
    missing: list[str] = []

    for pipeline_name in _pipeline_names():
        config = load_pipeline_config(pipeline_name)
        for layer_name in ("silver", "gold"):
            layer = config.sink.get(layer_name)
            if layer is None or not layer.enabled:
                continue
            total += 1
            if not layer.sort_by:
                missing.append(f"{pipeline_name}: sink.{layer_name}.sort_by missing")

    covered = total - len(missing)
    coverage = covered / total if total else 1.0
    assert coverage == pytest.approx(1.0), (
        "Deterministic sink sort policy coverage is incomplete: "
        f"{coverage:.2%} ({covered}/{total}).\n"
        + "\n".join(f"  - {item}" for item in missing)
    )


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def test_composite_merge_sort_policy_coverage_is_full() -> None:
    total = 0
    missing: list[str] = []

    for config_path in sorted(COMPOSITES_DIR.glob("*.yaml")):
        if config_path.name.startswith("_"):
            continue
        raw = _load_yaml(config_path)
        validated = validate_composite_config_payload(raw)
        sort_policy = validated.composite.merge.sort_by
        for layer_name in ("silver", "gold"):
            total += 1
            if not getattr(sort_policy, layer_name):
                missing.append(
                    f"{config_path.name}: composite.merge.sort_by.{layer_name}"
                )

    covered = total - len(missing)
    coverage = covered / total if total else 1.0
    assert coverage == pytest.approx(1.0), (
        "Composite deterministic sort policy coverage is incomplete: "
        f"{coverage:.2%} ({covered}/{total}).\n"
        + "\n".join(f"  - {item}" for item in missing)
    )
