"""Unit tests for unified contract policy loader."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bioetl.infrastructure.config.contract_policy_loader import (
    load_pipeline_contract_policy,
)


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
                "contracts": {
                    "primary_key": ["id"],
                    "merge_keys": ["id"],
                }
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
