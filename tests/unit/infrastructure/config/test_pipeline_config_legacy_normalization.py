from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml

from bioetl.infrastructure.config.pipeline_config_api import (
    PipelineConfigReadPayload,
    load_pipeline_config,
)
from bioetl.infrastructure.config.pipeline_normalizers import (
    apply_pipeline_schema_normalization,
)


def _schema_signature(config: Any) -> dict[str, Any]:
    dumped = config.model_dump(mode="json", exclude_none=True)
    data_schema = dumped.get("data_schema")
    normalized_data_schema = None
    if isinstance(data_schema, dict):
        normalized_data_schema = {
            "column_groups": _normalize_column_groups(data_schema.get("column_groups")),
            "silver": data_schema.get("silver"),
            "gold": data_schema.get("gold"),
        }
    return {
        "column_groups": _normalize_column_groups(dumped.get("column_groups")),
        "data_schema": normalized_data_schema,
        "content_hash": dumped.get("content_hash"),
        "content_hash_policy": dumped.get("content_hash_policy"),
    }


def _normalize_column_groups(
    groups: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Strip non-semantic defaults to compare canonical schema intent."""
    if groups is None:
        return []
    return [
        {"name": g.get("name"), "fields": g.get("fields"), "pattern": g.get("pattern")}
        for g in groups
    ]


def _write_unified_pipeline(
    *,
    entities_dir: Path,
    provider: str,
    entity: str,
    pipeline: dict[str, Any],
    schema: dict[str, Any] | None = None,
    contracts: dict[str, Any] | None = None,
    hash_policy: dict[str, Any] | None = None,
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
    if contracts is not None:
        payload["contracts"] = contracts
    if hash_policy is not None:
        payload["hash_policy"] = hash_policy
    (entity_dir / f"{entity}.yaml").write_text(yaml.dump(payload), encoding="utf-8")


def test_pipeline_loader_uses_unified_schema_section(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Full loader should load unified schema from the `schema` section."""
    load_pipeline_config.cache_clear()
    schema_payload = {
        "column_groups": [
            {"name": "system", "fields": ["_etl_ts"]},
            {"name": "business", "fields": ["id"]},
        ],
        "content_hash": {"include": [], "exclude": ["_etl_ts"]},
        "silver": {"include_groups": ["system", "business"]},
        "gold": {"include_groups": ["business"]},
    }

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

    canonical_pipeline = copy.deepcopy(common_pipeline)
    canonical_pipeline.update(
        {
            "pipeline_name": "demo_canonical_schema",
            "entity_type": "canonical_schema",
        }
    )
    _write_unified_pipeline(
        entities_dir=entities_dir,
        provider="demo",
        entity="canonical_schema",
        pipeline=canonical_pipeline,
        schema=schema_payload,
    )

    monkeypatch.chdir(tmp_path)
    loaded = load_pipeline_config("demo_canonical_schema")
    assert _schema_signature(loaded) == {
        "column_groups": _normalize_column_groups(schema_payload["column_groups"]),
        "data_schema": {
            "column_groups": _normalize_column_groups(schema_payload["column_groups"]),
            "silver": {
                "include_groups": ["system", "business"],
                "rename_fields": {},
            },
            "gold": {
                "include_groups": ["business"],
                "rename_fields": {},
            },
        },
        "content_hash": schema_payload["content_hash"],
        "content_hash_policy": None,
    }


def test_pipeline_loader_projects_root_hash_policy_as_authoritative_runtime_object(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Root hash_policy should become the single typed runtime hash-policy object."""
    load_pipeline_config.cache_clear()
    entities_dir = tmp_path / "configs" / "entities"
    _write_unified_pipeline(
        entities_dir=entities_dir,
        provider="chembl",
        entity="activity",
        pipeline={
            "pipeline_name": "chembl_activity",
            "entity_type": "activity",
            "provider": "chembl",
            "business_primary_keys": ["activity_id"],
        },
        schema={
            "column_groups": [
                {"name": "system", "fields": ["_etl_ts"]},
                {"name": "business", "fields": ["activity_id"]},
            ],
            "content_hash": {"include": [], "exclude": []},
            "silver": {"include_groups": ["system", "business"]},
            "gold": {"include_groups": ["business"]},
        },
        contracts={
            "primary_key": ["activity_id"],
            "merge_keys": ["activity_id"],
            "hash_include": [],
        },
        hash_policy={
            "provider": "chembl",
            "entity": "activity",
            "contract": {
                "version": "1.0.0",
                "migration_note": "Introduce single authoritative hash policy.",
            },
            "hash_policy": {
                "algorithm": "sha256",
                "canonicalization": "provider + canonical_json_dumps(normalized_record)",
                "include_fields": ["activity_id", "value"],
                "exclude_fields": ["_run_id"],
                "exclude_patterns": ["^_dq_"],
                "normalization": {
                    "trim_strings": True,
                    "round_floats": {"enabled": True, "precision": 10},
                    "dates": {"enabled": True, "format": "YYYY-MM-DD"},
                    "null_handling": {"nan_to_null": True, "inf_to_null": True},
                },
            },
        },
    )

    monkeypatch.chdir(tmp_path)
    loaded = load_pipeline_config("chembl_activity")

    assert loaded.content_hash.include == []
    assert loaded.content_hash.exclude == []
    assert loaded.content_hash_policy is not None
    assert loaded.content_hash_policy.provider == "chembl"
    assert loaded.content_hash_policy.entity == "activity"
    assert loaded.content_hash_policy.contract.version == "1.0.0"
    assert loaded.content_hash_policy.include_fields == ["activity_id", "value"]
    assert loaded.content_hash_policy.exclude_fields == ["_run_id"]
    assert loaded.content_hash_policy.field_ordering == {}


def test_pipeline_loader_rejects_non_empty_legacy_hash_shims_when_root_policy_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Legacy schema/contract hash surfaces must stay empty compatibility shims."""
    load_pipeline_config.cache_clear()
    entities_dir = tmp_path / "configs" / "entities"
    _write_unified_pipeline(
        entities_dir=entities_dir,
        provider="chembl",
        entity="activity",
        pipeline={
            "pipeline_name": "chembl_activity",
            "entity_type": "activity",
            "provider": "chembl",
            "business_primary_keys": ["activity_id"],
        },
        schema={
            "column_groups": [
                {"name": "system", "fields": ["_etl_ts"]},
                {"name": "business", "fields": ["activity_id"]},
            ],
            "content_hash": {"include": ["activity_id"], "exclude": []},
            "silver": {"include_groups": ["system", "business"]},
            "gold": {"include_groups": ["business"]},
        },
        contracts={
            "primary_key": ["activity_id"],
            "merge_keys": ["activity_id"],
            "hash_include": [],
        },
        hash_policy={
            "provider": "chembl",
            "entity": "activity",
            "contract": {
                "version": "1.0.0",
                "migration_note": "Introduce single authoritative hash policy.",
            },
            "hash_policy": {
                "algorithm": "sha256",
                "canonicalization": "provider + canonical_json_dumps(normalized_record)",
                "include_fields": ["activity_id"],
                "exclude_fields": [],
                "normalization": {
                    "trim_strings": True,
                    "round_floats": {"enabled": True, "precision": 10},
                    "dates": {"enabled": True, "format": "YYYY-MM-DD"},
                    "null_handling": {"nan_to_null": True, "inf_to_null": True},
                },
            },
        },
    )

    monkeypatch.chdir(tmp_path)
    with pytest.raises(
        ValueError,
        match=r"schema\.content_hash\.include must be empty",
    ):
        load_pipeline_config("chembl_activity")


def test_pipeline_loader_rejects_chembl_field_ordering_hash_policy_mirrors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ChEMBL JSON ordering must stay authoritative only in domain policy/profile code."""
    load_pipeline_config.cache_clear()
    entities_dir = tmp_path / "configs" / "entities"
    _write_unified_pipeline(
        entities_dir=entities_dir,
        provider="chembl",
        entity="activity",
        pipeline={
            "pipeline_name": "chembl_activity",
            "entity_type": "activity",
            "provider": "chembl",
            "business_primary_keys": ["activity_id"],
        },
        schema={
            "column_groups": [
                {"name": "system", "fields": ["_etl_ts"]},
                {"name": "business", "fields": ["activity_id"]},
            ],
            "content_hash": {"include": [], "exclude": []},
            "silver": {"include_groups": ["system", "business"]},
            "gold": {"include_groups": ["business"]},
        },
        contracts={
            "primary_key": ["activity_id"],
            "merge_keys": ["activity_id"],
            "hash_include": [],
        },
        hash_policy={
            "provider": "chembl",
            "entity": "activity",
            "contract": {
                "version": "1.0.0",
                "migration_note": "Introduce single authoritative hash policy.",
            },
            "hash_policy": {
                "algorithm": "sha256",
                "canonicalization": "provider + canonical_json_dumps(normalized_record)",
                "include_fields": ["activity_id"],
                "exclude_fields": [],
                "field_ordering": {"activity_properties": "order_sensitive_json"},
                "normalization": {
                    "trim_strings": True,
                    "round_floats": {"enabled": True, "precision": 10},
                    "dates": {"enabled": True, "format": "YYYY-MM-DD"},
                    "null_handling": {"nan_to_null": True, "inf_to_null": True},
                },
            },
        },
    )

    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="field_ordering must be empty for ChEMBL"):
        load_pipeline_config("chembl_activity")


def test_pipeline_schema_normalizer_golden_vector(
    tmp_path: Path,
) -> None:
    """Unified schema should be normalized to the expected pipeline shape."""
    config_path = tmp_path / "configs" / "entities" / "demo" / "item.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("version: 1.0.0\n", encoding="utf-8")

    schema_payload = {
        "column_groups": [
            {"name": "system", "fields": ["_etl_ts"]},
            {"name": "business", "fields": ["id"]},
        ],
        "content_hash": {"exclude": ["_etl_ts"]},
        "silver": {"include_groups": ["system", "business"]},
        "gold": {"include_groups": ["business"]},
    }

    expected = {
        "column_groups": schema_payload["column_groups"],
        "content_hash": schema_payload["content_hash"],
        "data_schema": {
            "column_groups": schema_payload["column_groups"],
            "silver": {"include_groups": ["system", "business"]},
            "gold": {"include_groups": ["business"]},
        },
    }

    unified_cfg: dict[str, Any] = {}
    apply_pipeline_schema_normalization(
        unified_cfg,
        entity_config={},
        config_path=config_path,
        unified_schema=None,
    )
    assert {k: unified_cfg.get(k) for k in expected} != expected

    unified_cfg = {}
    apply_pipeline_schema_normalization(
        unified_cfg,
        entity_config={},
        config_path=config_path,
        unified_schema=schema_payload,
    )
    assert {k: unified_cfg.get(k) for k in expected} == expected


def test_load_pipeline_config_cache_isolated_by_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cache key must include cwd context for the same logical pipeline name."""
    load_pipeline_config.cache_clear()

    def write_pipeline(root: Path, *, extra_hash: str) -> None:
        schema_payload = {
            "column_groups": [
                {"name": "system", "fields": ["_etl_ts"]},
                {"name": "business", "fields": ["id"]},
            ],
            "content_hash": {"exclude": [extra_hash]},
            "silver": {"include_groups": ["system", "business"]},
            "gold": {"include_groups": ["business"]},
        }
        _write_unified_pipeline(
            entities_dir=root / "configs" / "entities",
            provider="demo",
            entity="item",
            pipeline={
                "pipeline_name": "demo_item",
                "entity_type": "item",
                "provider": "demo",
                "business_primary_keys": ["id"],
                "silver_table": "demo_item",
                "gold_table": "demo_item",
            },
            schema=schema_payload,
        )

    dir_one = tmp_path / "context_one"
    dir_two = tmp_path / "context_two"
    write_pipeline(dir_one, extra_hash="_one")
    write_pipeline(dir_two, extra_hash="_two")

    monkeypatch.chdir(dir_one)
    config_one = load_pipeline_config("demo_item")
    monkeypatch.chdir(dir_two)
    config_two = load_pipeline_config("demo_item")

    assert config_one.content_hash.exclude == ["_one"]
    assert config_two.content_hash.exclude == ["_two"]
    assert config_one.content_hash != config_two.content_hash


def test_load_pipeline_config_runs_read_normalize_validate_map_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Canonical pipeline API orchestration should remain explicit and stage-ordered."""
    import bioetl.infrastructure.config.pipeline_config_api as module

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

    def fake_normalize(
        payload: PipelineConfigReadPayload,
        *,
        filter_loader: object,
    ) -> dict[str, Any]:
        assert payload is raw_payload
        assert filter_loader is not None
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


def test_chembl_publication_term_business_primary_keys_follow_canonical_identity() -> (
    None
):
    """Publication-term config should expose logical business identity, not digest id."""
    load_pipeline_config.cache_clear()
    loaded = load_pipeline_config("chembl_publication_term")

    assert loaded.business_primary_keys == [
        "publication_id",
        "term_type",
        "term",
    ]


def test_chembl_subcellular_fraction_business_primary_keys_follow_canonical_field() -> (
    None
):
    """Subcellular-fraction config should use canonical fraction as business identity."""
    load_pipeline_config.cache_clear()
    loaded = load_pipeline_config("chembl_subcellular_fraction")

    assert loaded.business_primary_keys == ["subcellular_fraction"]
