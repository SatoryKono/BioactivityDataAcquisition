from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml

from bioetl.infrastructure.config_loader import (
    PipelineConfigReadPayload,
    load_pipeline_config,
)
from bioetl.infrastructure.legacy_normalizers.pipeline import (
    apply_pipeline_schema_normalization,
)


def _schema_signature(config: Any) -> dict[str, Any]:
    dumped = config.model_dump(mode="json", exclude_none=True)
    return {
        "column_groups": dumped.get("column_groups"),
        "data_schema": dumped.get("data_schema"),
        "content_hash": dumped.get("content_hash"),
    }


def _write_unified_pipeline(
    *,
    entities_dir: Path,
    provider: str,
    entity: str,
    pipeline: dict[str, Any],
    schema: dict[str, Any] | None = None,
) -> None:
    entity_dir = entities_dir / provider
    entity_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": "1.0.0",
        "provider": provider,
        "entity": entity,
        "pipeline": pipeline,
    }
    if schema is not None:
        payload["schema"] = schema
    (entity_dir / f"{entity}.yaml").write_text(yaml.dump(payload), encoding="utf-8")


def test_pipeline_legacy_and_new_schema_file_aliases_are_equivalent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Full loader must produce equivalent schema payload for old/new aliases."""
    load_pipeline_config.cache_clear()

    schema_path = tmp_path / "configs" / "schemas" / "demo" / "common.yaml"
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    schema_payload = {
        "column_groups": [
            {"name": "system", "fields": ["_etl_ts"]},
            {"name": "business", "fields": ["id"]},
        ],
        "content_hash": {"exclude_fields": ["_etl_ts"]},
        "silver": {"include_groups": ["system", "business"]},
        "gold": {"include_groups": ["business"]},
    }
    schema_path.write_text(yaml.dump(schema_payload), encoding="utf-8")

    entities_dir = tmp_path / "configs" / "entities"
    common_pipeline = {
        "provider": "demo",
        "business_primary_keys": ["id"],
        "silver_table": "demo_common",
        "gold_table": "demo_common",
        "sink": {
            "bronze": {"path": "data/output/bronze/demo/common"},
            "silver": {"path": "data/output/silver/demo/common"},
            "gold": {"path": "data/output/gold/demo/common"},
        },
    }

    legacy_pipeline = copy.deepcopy(common_pipeline)
    legacy_pipeline.update(
        {
            "pipeline_name": "demo_legacy_alias",
            "entity_type": "legacy_alias",
            "data_schema_file": "../../schemas/demo/common.yaml",
        }
    )
    _write_unified_pipeline(
        entities_dir=entities_dir,
        provider="demo",
        entity="legacy_alias",
        pipeline=legacy_pipeline,
        schema={},
    )

    new_pipeline = copy.deepcopy(common_pipeline)
    new_pipeline.update(
        {
            "pipeline_name": "demo_new_alias",
            "entity_type": "new_alias",
            "schema_file": "../../schemas/demo/common.yaml",
        }
    )
    _write_unified_pipeline(
        entities_dir=entities_dir,
        provider="demo",
        entity="new_alias",
        pipeline=new_pipeline,
        schema={},
    )

    monkeypatch.chdir(tmp_path)
    legacy = load_pipeline_config("demo_legacy_alias")
    load_pipeline_config.cache_clear()
    new = load_pipeline_config("demo_new_alias")

    assert _schema_signature(legacy) == _schema_signature(new)


def test_pipeline_schema_normalizer_golden_vector(
    tmp_path: Path,
) -> None:
    """Legacy data_schema_file and new schema_file must normalize identically."""
    config_path = tmp_path / "configs" / "entities" / "demo" / "item.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("version: 1.0.0\n", encoding="utf-8")

    schema_rel = "../../schemas/demo/item.yaml"
    schema_path = (config_path.parent / schema_rel).resolve()
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    schema_payload = {
        "column_groups": [
            {"name": "system", "fields": ["_etl_ts"]},
            {"name": "business", "fields": ["id"]},
        ],
        "content_hash": {"exclude_fields": ["_etl_ts"]},
        "silver": {"include_groups": ["system", "business"]},
        "gold": {"include_groups": ["business"]},
    }
    schema_path.write_text(yaml.dump(schema_payload), encoding="utf-8")

    legacy_cfg = {"data_schema_file": schema_rel}
    new_cfg = {"schema_file": schema_rel}

    apply_pipeline_schema_normalization(
        legacy_cfg,
        entity_config={},
        config_path=config_path,
        unified_schema=None,
    )
    apply_pipeline_schema_normalization(
        new_cfg,
        entity_config={},
        config_path=config_path,
        unified_schema=None,
    )

    expected = {
        "column_groups": schema_payload["column_groups"],
        "content_hash": schema_payload["content_hash"],
        "data_schema": {
            "silver": schema_payload["silver"],
            "gold": schema_payload["gold"],
        },
    }
    assert {k: legacy_cfg.get(k) for k in expected} == expected
    assert {k: new_cfg.get(k) for k in expected} == expected


def test_load_pipeline_config_runs_read_normalize_validate_map_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Loader orchestration should remain explicit and stage-ordered."""
    import bioetl.infrastructure.config_loader as module

    module.load_pipeline_config.cache_clear()
    events: list[str] = []

    raw_payload = PipelineConfigReadPayload(
        config={"raw": True},
        entity_config={},
        config_path=Path("configs/entities/demo/item.yaml"),
        unified_schema=None,
    )
    normalized_payload = {"normalized": True}
    validated_payload = object()
    mapped_payload = object()

    def fake_read(name: str) -> PipelineConfigReadPayload:
        assert name == "demo_item"
        events.append("read")
        return raw_payload

    def fake_normalize(payload: PipelineConfigReadPayload) -> dict[str, Any]:
        assert payload is raw_payload
        events.append("normalize")
        return normalized_payload

    def fake_validate(payload: dict[str, Any]) -> object:
        assert payload == normalized_payload
        events.append("validate")
        return validated_payload

    def fake_map(payload: object) -> object:
        assert payload is validated_payload
        events.append("map")
        return mapped_payload

    monkeypatch.setattr(module, "read_pipeline_config_payload", fake_read)
    monkeypatch.setattr(module, "normalize_pipeline_config_payload", fake_normalize)
    monkeypatch.setattr(module, "validate_pipeline_config_payload", fake_validate)
    monkeypatch.setattr(module, "map_pipeline_config", fake_map)

    loaded = module.load_pipeline_config("demo_item")
    assert loaded is mapped_payload
    assert events == ["read", "normalize", "validate", "map"]
