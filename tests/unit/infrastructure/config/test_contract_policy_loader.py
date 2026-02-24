"""Unit tests for contract policy loader unified/legacy resolution."""

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
def test_load_contracts_from_legacy_path_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Loader should fallback to configs/contracts/pipelines path when needed."""
    load_pipeline_contract_policy.cache_clear()
    monkeypatch.chdir(tmp_path)

    contracts_dir = (
        tmp_path / "configs" / "contracts" / "pipelines" / "test_provider"
    )
    contracts_dir.mkdir(parents=True)
    (contracts_dir / "test_entity.yaml").write_text(
        yaml.safe_dump(
            {
                "primary_key": ["id"],
                "merge_keys": ["id"],
                "rename_map": {"source": "_source"},
                "hash_include": [],
                "hash_exclude": ["_run_id"],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    policy = load_pipeline_contract_policy("test_provider", "test_entity")
    assert policy.primary_key == ["id"]
    assert policy.merge_keys == ["id"]
    assert policy.rename_map == {"source": "_source"}
