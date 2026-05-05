"""Architecture/config guard for append-mode idempotency contracts."""

from __future__ import annotations

from pathlib import Path

import yaml

CONFIG_ROOT = Path("configs/entities")


def _iter_pipeline_configs() -> list[Path]:
    return sorted(CONFIG_ROOT.rglob("*.yaml"))


def test_append_mode_requires_explicit_idempotency_contract() -> None:
    for config_path in _iter_pipeline_configs():
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        pipeline = payload.get("pipeline")
        if not isinstance(pipeline, dict):
            continue
        sink = pipeline.get("sink")
        if not isinstance(sink, dict):
            continue
        for layer_name in ("silver", "gold"):
            layer = sink.get(layer_name)
            if not isinstance(layer, dict):
                continue
            if str(layer.get("mode", "")).strip().lower() != "append":
                continue
            assert layer.get("idempotency_contract"), (
                f"{config_path}: sink.{layer_name}.mode=append requires "
                "sink.{layer_name}.idempotency_contract"
            )


def test_base_pipeline_declares_semantic_output_idempotency_defaults() -> None:
    payload = yaml.safe_load(
        Path("configs/base/pipeline.yaml").read_text(encoding="utf-8")
    ) or {}
    pipeline = payload.get("pipeline")
    assert isinstance(pipeline, dict)
    sink = pipeline.get("sink")
    assert isinstance(sink, dict)

    silver = sink.get("silver")
    gold = sink.get("gold")
    assert isinstance(silver, dict)
    assert isinstance(gold, dict)

    assert silver.get("mode") == "merge"
    assert silver.get("idempotency_contract") == "merge_upsert"
    assert gold.get("mode") == "scd2"
    assert gold.get("idempotency_contract") == "scd2"
