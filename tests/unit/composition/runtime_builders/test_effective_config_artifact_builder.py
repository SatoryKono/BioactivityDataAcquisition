"""Unit tests for effective-config artifact builder provenance helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path

from bioetl.composition.runtime_builders.effective_config_artifact_builder import (
    _build_effective_config_source_refs,
)


def test_build_effective_config_source_refs_persists_stable_source_hashes(
    tmp_path: Path,
) -> None:
    base_config = tmp_path / "configs" / "base" / "pipeline.yaml"
    contract_registry = tmp_path / "configs" / "base" / "contract_registry.yaml"
    entity_config = tmp_path / "configs" / "entities" / "chembl" / "activity.yaml"
    base_config.parent.mkdir(parents=True, exist_ok=True)
    entity_config.parent.mkdir(parents=True, exist_ok=True)
    base_config.write_text("pipeline:\n  version: 1\n", encoding="utf-8")
    contract_registry.write_text(
        "contracts:\n  chembl.activity: 1.0.0\n", encoding="utf-8"
    )
    entity_config.write_text("entity:\n  provider: chembl\n", encoding="utf-8")

    refs = _build_effective_config_source_refs(
        provider="chembl",
        entity="activity",
        repo_root=tmp_path,
    )

    assert [ref.source_path for ref in refs] == [
        "configs/base/pipeline.yaml",
        "configs/entities/chembl/activity.yaml",
        "configs/base/contract_registry.yaml",
    ]
    assert [ref.source_hash for ref in refs] == [
        hashlib.sha256(base_config.read_bytes()).hexdigest(),
        hashlib.sha256(entity_config.read_bytes()).hexdigest(),
        hashlib.sha256(contract_registry.read_bytes()).hexdigest(),
    ]


def test_build_effective_config_source_refs_is_stable_across_equivalent_calls(
    tmp_path: Path,
) -> None:
    base_config = tmp_path / "configs" / "base" / "pipeline.yaml"
    contract_registry = tmp_path / "configs" / "base" / "contract_registry.yaml"
    entity_config = tmp_path / "configs" / "entities" / "chembl" / "activity.yaml"
    base_config.parent.mkdir(parents=True, exist_ok=True)
    entity_config.parent.mkdir(parents=True, exist_ok=True)
    base_config.write_text("pipeline:\n  version: 1\n", encoding="utf-8")
    contract_registry.write_text(
        "contracts:\n  chembl.activity: 1.0.0\n", encoding="utf-8"
    )
    entity_config.write_text("entity:\n  provider: chembl\n", encoding="utf-8")

    refs_first = _build_effective_config_source_refs(
        provider="chembl",
        entity="activity",
        repo_root=tmp_path,
    )
    refs_second = _build_effective_config_source_refs(
        provider="chembl",
        entity="activity",
        repo_root=tmp_path,
    )

    assert refs_first == refs_second
