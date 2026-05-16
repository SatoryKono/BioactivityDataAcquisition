"""Architecture/config guard for append-mode idempotency contracts."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_ROOTS = (
    ROOT / "configs" / "base",
    ROOT / "configs" / "entities",
    ROOT / "configs" / "composites",
)
APPEND_SAFE_CONTRACTS = {
    "append_log",
    "partition_append_with_stable_partition_key",
    "occurrence_only",
}
EXPECTED_NON_APPEND_CONTRACTS = {
    ("silver", "merge"): "merge_upsert",
    ("gold", "scd2"): "scd2",
    ("gold", "overwrite"): "overwrite_rebuild",
}


def _iter_pipeline_configs() -> list[Path]:
    return sorted(
        config_path for root in CONFIG_ROOTS for config_path in root.rglob("*.yaml")
    )


def _load_yaml(config_path: Path) -> dict[str, object]:
    return cast(
        dict[str, object],
        yaml.safe_load(config_path.read_text(encoding="utf-8")) or {},
    )


def _pipeline_sink(payload: dict[str, object]) -> dict[str, object]:
    pipeline = payload.get("pipeline")
    if isinstance(pipeline, dict) and isinstance(pipeline.get("sink"), dict):
        return cast(dict[str, object], pipeline["sink"])
    sink = payload.get("sink")
    if isinstance(sink, dict):
        return cast(dict[str, object], sink)
    return {}


def test_append_mode_requires_explicit_idempotency_contract() -> None:
    for config_path in _iter_pipeline_configs():
        sink = _pipeline_sink(_load_yaml(config_path))
        for layer_name in ("silver", "gold"):
            layer = sink.get(layer_name)
            if not isinstance(layer, dict):
                continue
            if str(layer.get("mode", "")).strip().lower() != "append":
                continue
            contract = str(layer.get("idempotency_contract") or "").strip().lower()
            assert layer.get("idempotency_contract"), (
                f"{config_path.relative_to(ROOT)}: sink.{layer_name}.mode=append requires "
                f"sink.{layer_name}.idempotency_contract"
            )
            assert contract in APPEND_SAFE_CONTRACTS, (
                f"{config_path.relative_to(ROOT)}: sink.{layer_name}.mode=append "
                f"requires append-safe idempotency_contract; got {contract!r}"
            )


def test_explicit_sink_mode_requires_matching_explicit_idempotency_contract() -> None:
    for config_path in _iter_pipeline_configs():
        sink = _pipeline_sink(_load_yaml(config_path))
        for layer_name in ("silver", "gold"):
            layer = sink.get(layer_name)
            if not isinstance(layer, dict) or "mode" not in layer:
                continue
            mode = str(layer.get("mode", "")).strip().lower()
            if mode == "append":
                continue
            expected_contract = EXPECTED_NON_APPEND_CONTRACTS.get((layer_name, mode))
            if expected_contract is None:
                continue
            assert layer.get("idempotency_contract"), (
                f"{config_path.relative_to(ROOT)}: explicit sink.{layer_name}.mode={mode} "
                f"requires explicit sink.{layer_name}.idempotency_contract"
            )
            contract = str(layer.get("idempotency_contract") or "").strip().lower()
            assert contract == expected_contract, (
                f"{config_path.relative_to(ROOT)}: explicit sink.{layer_name}.mode={mode} "
                f"requires sink.{layer_name}.idempotency_contract={expected_contract!r}; "
                f"got {contract!r}"
            )


def test_base_pipeline_declares_semantic_output_idempotency_defaults() -> None:
    sink = _pipeline_sink(_load_yaml(ROOT / "configs" / "base" / "pipeline.yaml"))

    silver = sink.get("silver")
    gold = sink.get("gold")
    assert isinstance(silver, dict)
    assert isinstance(gold, dict)

    assert silver.get("mode") == "merge"
    assert silver.get("idempotency_contract") == "merge_upsert"
    assert gold.get("mode") == "scd2"
    assert gold.get("idempotency_contract") == "scd2"
