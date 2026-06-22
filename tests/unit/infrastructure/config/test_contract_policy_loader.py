"""Unit tests for unified contract policy loader."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bioetl.infrastructure.config.contract_policy_loader import (
    load_pipeline_contract_policy,
)


def _explicit_contracts(
    *,
    provider: str,
    entity: str,
    primary_key: list[str],
    merge_keys: list[str],
    hash_include: list[str] | None = None,
    hash_exclude: list[str] | None = None,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    contracts: dict[str, object] = {
        "primary_key": primary_key,
        "merge_keys": merge_keys,
        "contract_ref": f"{provider}.{entity}",
        "active_version": "1.0.0",
        "rollout": {
            "mode": "single",
            "read_order": ["1.0.0"],
            "write_versions": ["1.0.0"],
            "affects_hash": False,
        },
    }
    if hash_include is not None:
        contracts["hash_include"] = hash_include
    if hash_exclude is not None:
        contracts["hash_exclude"] = hash_exclude
    if extra:
        contracts.update(extra)
    return contracts


@pytest.mark.unit
def test_load_contracts_from_unified_entity_with_base_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Loader should read contracts section from configs/entities and merge base defaults."""
    load_pipeline_contract_policy.cache_clear()
    monkeypatch.chdir(tmp_path)

    base_dir = tmp_path / "configs" / "base"
    base_dir.mkdir(parents=True)
    (base_dir / "pipeline.yaml").write_text(
        yaml.safe_dump(
            {
                "contract_defaults": {
                    "rename_map": {"run_id": "_run_id"},
                    "hash_exclude": ["_ingestion_ts"],
                    "hash_include": [],
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    entity_dir = tmp_path / "configs" / "entities" / "test_provider"
    entity_dir.mkdir(parents=True)
    (entity_dir / "test_entity.yaml").write_text(
        yaml.safe_dump(
            {
                "contracts": _explicit_contracts(
                    provider="test_provider",
                    entity="test_entity",
                    primary_key=["id"],
                    merge_keys=["id"],
                )
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    policy = load_pipeline_contract_policy("test_provider", "test_entity")

    assert policy.primary_key == ["id"]
    assert policy.merge_keys == ["id"]
    assert policy.rename_map == {"run_id": "_run_id"}
    assert policy.hash_exclude == ["_ingestion_ts"]
    assert policy.contract_ref == "test_provider.test_entity"
    assert policy.active_version == "1.0.0"
    assert policy.rollout_mode == "single"
    assert policy.read_order == ["1.0.0"]
    assert policy.write_versions == ["1.0.0"]


@pytest.mark.unit
def test_missing_unified_contract_file_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Loader should fail when unified entity contract config is missing."""
    load_pipeline_contract_policy.cache_clear()
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="Contract policy file not found"):
        load_pipeline_contract_policy("test_provider", "test_entity")


@pytest.mark.unit
def test_missing_contracts_section_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Loader should fail when unified entity file has no contracts section."""
    load_pipeline_contract_policy.cache_clear()
    monkeypatch.chdir(tmp_path)

    entity_dir = tmp_path / "configs" / "entities" / "test_provider"
    entity_dir.mkdir(parents=True)
    (entity_dir / "test_entity.yaml").write_text(
        yaml.safe_dump({"pipeline": {"pipeline_name": "test_provider_test_entity"}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="section 'contracts' not found"):
        load_pipeline_contract_policy("test_provider", "test_entity")


@pytest.mark.unit
def test_no_base_defaults_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Loader should work when base pipeline config is absent (no defaults)."""
    load_pipeline_contract_policy.cache_clear()
    monkeypatch.chdir(tmp_path)

    entity_dir = tmp_path / "configs" / "entities" / "test_provider"
    entity_dir.mkdir(parents=True)
    (entity_dir / "test_entity.yaml").write_text(
        yaml.safe_dump(
            {
                "contracts": _explicit_contracts(
                    provider="test_provider",
                    entity="test_entity",
                    primary_key=["id"],
                    merge_keys=["id"],
                )
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    policy = load_pipeline_contract_policy("test_provider", "test_entity")
    assert policy.primary_key == ["id"]


@pytest.mark.unit
def test_base_defaults_no_contract_defaults_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Loader should work when base pipeline config has no contract_defaults key."""
    load_pipeline_contract_policy.cache_clear()
    monkeypatch.chdir(tmp_path)

    base_dir = tmp_path / "configs" / "base"
    base_dir.mkdir(parents=True)
    (base_dir / "pipeline.yaml").write_text(
        yaml.safe_dump({"other_key": "value"}),
        encoding="utf-8",
    )

    entity_dir = tmp_path / "configs" / "entities" / "test_provider"
    entity_dir.mkdir(parents=True)
    (entity_dir / "entity2.yaml").write_text(
        yaml.safe_dump(
            {
                "contracts": _explicit_contracts(
                    provider="test_provider",
                    entity="entity2",
                    primary_key=["pk"],
                    merge_keys=["pk"],
                )
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    policy = load_pipeline_contract_policy("test_provider", "entity2")
    assert policy.primary_key == ["pk"]


@pytest.mark.unit
def test_base_defaults_contract_defaults_not_dict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Loader should handle contract_defaults being null."""
    load_pipeline_contract_policy.cache_clear()
    monkeypatch.chdir(tmp_path)

    base_dir = tmp_path / "configs" / "base"
    base_dir.mkdir(parents=True)
    (base_dir / "pipeline.yaml").write_text(
        "contract_defaults: null\n",
        encoding="utf-8",
    )

    entity_dir = tmp_path / "configs" / "entities" / "test_provider"
    entity_dir.mkdir(parents=True)
    (entity_dir / "entity3.yaml").write_text(
        yaml.safe_dump(
            {
                "contracts": _explicit_contracts(
                    provider="test_provider",
                    entity="entity3",
                    primary_key=["pk"],
                    merge_keys=["pk"],
                )
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    policy = load_pipeline_contract_policy("test_provider", "entity3")
    assert policy.primary_key == ["pk"]


@pytest.mark.unit
def test_contracts_section_is_not_dict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Loader should fail when contracts is a non-dict value."""
    load_pipeline_contract_policy.cache_clear()
    monkeypatch.chdir(tmp_path)

    entity_dir = tmp_path / "configs" / "entities" / "test_provider"
    entity_dir.mkdir(parents=True)
    (entity_dir / "entity4.yaml").write_text(
        "contracts: not_a_dict\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="section 'contracts' not found"):
        load_pipeline_contract_policy("test_provider", "entity4")


@pytest.mark.unit
def test_entity_contract_values_override_base_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Entity contract values should override base defaults when explicitly set."""
    load_pipeline_contract_policy.cache_clear()
    monkeypatch.chdir(tmp_path)

    base_dir = tmp_path / "configs" / "base"
    base_dir.mkdir(parents=True)
    (base_dir / "pipeline.yaml").write_text(
        yaml.safe_dump(
            {
                "contract_defaults": {
                    "rename_map": {"run_id": "_run_id"},
                    "hash_exclude": ["_ingestion_ts"],
                    "hash_include": [],
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    entity_dir = tmp_path / "configs" / "entities" / "test_provider"
    entity_dir.mkdir(parents=True)
    (entity_dir / "entity5.yaml").write_text(
        yaml.safe_dump(
            {
                "contracts": _explicit_contracts(
                    provider="test_provider",
                    entity="entity5",
                    primary_key=["pk"],
                    merge_keys=["pk"],
                    hash_exclude=["_custom_meta"],
                    extra={"rename_map": {"custom": "_custom"}},
                )
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    policy = load_pipeline_contract_policy("test_provider", "entity5")

    assert policy.rename_map == {"custom": "_custom"}
    assert policy.hash_exclude == ["_custom_meta"]


@pytest.mark.unit
def test_loader_uses_root_hash_policy_for_effective_hash_selectors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Root hash_policy should supply the runtime-effective hash selectors."""
    load_pipeline_contract_policy.cache_clear()
    monkeypatch.chdir(tmp_path)

    base_dir = tmp_path / "configs" / "base"
    base_dir.mkdir(parents=True)
    (base_dir / "pipeline.yaml").write_text(
        yaml.safe_dump(
            {
                "contract_defaults": {
                    "hash_exclude": ["_ingestion_ts", "_run_id"],
                    "hash_include": [],
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    entity_dir = tmp_path / "configs" / "entities" / "chembl"
    entity_dir.mkdir(parents=True)
    (entity_dir / "activity.yaml").write_text(
        yaml.safe_dump(
            {
                "contracts": _explicit_contracts(
                    provider="chembl",
                    entity="activity",
                    primary_key=["activity_id"],
                    merge_keys=["activity_id"],
                    hash_include=[],
                    hash_exclude=[],
                ),
                "hash_policy": {
                    "provider": "chembl",
                    "entity": "activity",
                    "contract": {
                        "version": "1.0.0",
                        "migration_note": "Root hash_policy stays informational here.",
                    },
                    "hash_policy": {
                        "algorithm": "sha256",
                        "canonicalization": (
                            "provider + canonical_json_dumps(normalized_record)"
                        ),
                        "include_fields": ["activity_id"],
                        "exclude_fields": ["_ingestion_ts"],
                        "normalization": {
                            "trim_strings": True,
                            "round_floats": {"enabled": True, "precision": 10},
                            "dates": {"enabled": True, "format": "YYYY-MM-DD"},
                            "null_handling": {
                                "nan_to_null": True,
                                "inf_to_null": True,
                            },
                        },
                    },
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    policy = load_pipeline_contract_policy("chembl", "activity")

    assert policy.hash_include == ["activity_id"]
    assert policy.hash_exclude == ["_ingestion_ts", "_run_id"]


@pytest.mark.unit
def test_explicit_rollout_and_registry_alignment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Loader should validate explicitly configured rollout metadata."""
    load_pipeline_contract_policy.cache_clear()
    monkeypatch.chdir(tmp_path)

    base_dir = tmp_path / "configs" / "base"
    base_dir.mkdir(parents=True)
    (base_dir / "contract_registry.yaml").write_text(
        yaml.safe_dump(
            {
                "entries": {
                    "test_provider.entity6": {
                        "identity": {"contract_version": "1.0.0"},
                        "supported_versions": ["1.0.0", "2.0.0"],
                        "migration_guides": {"1.0.0->2.0.0": "docs/migrate.md"},
                    }
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    entity_dir = tmp_path / "configs" / "entities" / "test_provider"
    entity_dir.mkdir(parents=True)
    (entity_dir / "entity6.yaml").write_text(
        yaml.safe_dump(
            {
                "contracts": _explicit_contracts(
                    provider="test_provider",
                    entity="entity6",
                    primary_key=["pk"],
                    merge_keys=["pk"],
                    extra={
                        "contract_ref": "test_provider.entity6",
                        "active_version": "2.0.0",
                        "rollout": {
                            "mode": "dual_read_write",
                            "read_order": ["2.0.0", "1.0.0"],
                            "write_versions": ["1.0.0", "2.0.0"],
                            "affects_hash": True,
                        },
                    },
                )
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    policy = load_pipeline_contract_policy("test_provider", "entity6")

    assert policy.rollout_mode == "dual_read_write"
    assert policy.read_order == ["2.0.0", "1.0.0"]
    assert policy.write_versions == ["1.0.0", "2.0.0"]
    assert policy.affects_hash is True
