"""Unit tests for effective-config artifact builder provenance helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path

from bioetl.application.services.effective_config_service import (
    create_effective_config_service,
)
from bioetl.composition.runtime_builders.effective_config_artifact_builder import (
    _build_effective_config_source_refs,
)
from bioetl.domain.control_plane.config_source_hashing import (
    compute_canonical_yaml_sha256,
)


def test_build_effective_config_source_refs_persists_semantic_and_raw_source_hashes(
    tmp_path: Path,
) -> None:
    base_config = tmp_path / "configs" / "base" / "pipeline.yaml"
    base_quality = tmp_path / "configs" / "base" / "quality.yaml"
    provider_config = tmp_path / "configs" / "providers" / "chembl.yaml"
    contract_registry = tmp_path / "configs" / "base" / "contract_registry.yaml"
    entity_config = tmp_path / "configs" / "entities" / "chembl" / "activity.yaml"
    entity_quality = (
        tmp_path / "configs" / "quality" / "entities" / "chembl" / "activity.yaml"
    )
    base_config.parent.mkdir(parents=True, exist_ok=True)
    provider_config.parent.mkdir(parents=True, exist_ok=True)
    entity_config.parent.mkdir(parents=True, exist_ok=True)
    entity_quality.parent.mkdir(parents=True, exist_ok=True)
    base_config.write_text("pipeline:\n  version: 1\n", encoding="utf-8")
    base_quality.write_text("quality:\n  mode: strict\n", encoding="utf-8")
    provider_config.write_text("provider:\n  retries: 3\n", encoding="utf-8")
    contract_registry.write_text(
        "contracts:\n  chembl.activity: 1.0.0\n", encoding="utf-8"
    )
    entity_config.write_text("entity:\n  provider: chembl\n", encoding="utf-8")
    entity_quality.write_text("dq:\n  contract: chembl.activity\n", encoding="utf-8")

    refs = _build_effective_config_source_refs(
        provider="chembl",
        entity="activity",
        repo_root=tmp_path,
    )

    assert [ref.source_path for ref in refs] == [
        "configs/base/pipeline.yaml",
        "configs/base/quality.yaml",
        "configs/providers/chembl.yaml",
        "configs/entities/chembl/activity.yaml",
        "configs/quality/entities/chembl/activity.yaml",
        "configs/base/contract_registry.yaml",
    ]
    assert [ref.source_hash for ref in refs] == [
        compute_canonical_yaml_sha256(base_config.read_bytes()),
        compute_canonical_yaml_sha256(base_quality.read_bytes()),
        compute_canonical_yaml_sha256(provider_config.read_bytes()),
        compute_canonical_yaml_sha256(entity_config.read_bytes()),
        compute_canonical_yaml_sha256(entity_quality.read_bytes()),
        compute_canonical_yaml_sha256(contract_registry.read_bytes()),
    ]
    assert [ref.raw_source_hash for ref in refs] == [
        hashlib.sha256(base_config.read_bytes()).hexdigest(),
        hashlib.sha256(base_quality.read_bytes()).hexdigest(),
        hashlib.sha256(provider_config.read_bytes()).hexdigest(),
        hashlib.sha256(entity_config.read_bytes()).hexdigest(),
        hashlib.sha256(entity_quality.read_bytes()).hexdigest(),
        hashlib.sha256(contract_registry.read_bytes()).hexdigest(),
    ]
    assert [ref.source_hash_strategy for ref in refs] == [
        "canonical_yaml",
        "canonical_yaml",
        "canonical_yaml",
        "canonical_yaml",
        "canonical_yaml",
        "canonical_yaml",
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


def test_effective_config_source_refs_ignore_yaml_formatting_for_semantic_identity(
    tmp_path: Path,
) -> None:
    left_root = tmp_path / "left"
    right_root = tmp_path / "right"
    for root in (left_root, right_root):
        (root / "configs" / "base").mkdir(parents=True, exist_ok=True)
        (root / "configs" / "entities" / "chembl").mkdir(parents=True, exist_ok=True)

    (left_root / "configs" / "base" / "pipeline.yaml").write_text(
        "pipeline:\n  version: 1\n  name: chembl_activity\n",
        encoding="utf-8",
    )
    (right_root / "configs" / "base" / "pipeline.yaml").write_text(
        "# same semantics, different bytes\n"
        "pipeline: {name: chembl_activity, version: 1}\n",
        encoding="utf-8",
    )
    for root in (left_root, right_root):
        (root / "configs" / "entities" / "chembl" / "activity.yaml").write_text(
            "entity:\n  provider: chembl\n",
            encoding="utf-8",
        )
        (root / "configs" / "base" / "contract_registry.yaml").write_text(
            "contracts:\n  chembl.activity: 1.0.0\n",
            encoding="utf-8",
        )

    refs_left = _build_effective_config_source_refs(
        provider="chembl",
        entity="activity",
        repo_root=left_root,
    )
    refs_right = _build_effective_config_source_refs(
        provider="chembl",
        entity="activity",
        repo_root=right_root,
    )

    assert [ref.source_hash for ref in refs_left] == [
        ref.source_hash for ref in refs_right
    ]
    assert refs_left[0].raw_source_hash != refs_right[0].raw_source_hash

    service = create_effective_config_service()
    artifact_left = service.create_effective_config_artifact(
        pipeline_name="chembl_activity",
        pipeline_kind="standard",
        resolved_config={"pipeline": {"name": "chembl_activity"}},
        runtime_overrides={},
        source_refs=refs_left,
    )
    artifact_right = service.create_effective_config_artifact(
        pipeline_name="chembl_activity",
        pipeline_kind="standard",
        resolved_config={"pipeline": {"name": "chembl_activity"}},
        runtime_overrides={},
        source_refs=refs_right,
    )

    assert artifact_left.source_fingerprint == artifact_right.source_fingerprint
    assert artifact_left.artifact_id == artifact_right.artifact_id


def test_effective_config_source_fingerprint_changes_when_provider_config_changes(
    tmp_path: Path,
) -> None:
    left_root = tmp_path / "left"
    right_root = tmp_path / "right"
    for root in (left_root, right_root):
        (root / "configs" / "base").mkdir(parents=True, exist_ok=True)
        (root / "configs" / "providers").mkdir(parents=True, exist_ok=True)
        (root / "configs" / "entities" / "chembl").mkdir(parents=True, exist_ok=True)
        (root / "configs" / "base" / "pipeline.yaml").write_text(
            "pipeline:\n  version: 1\n",
            encoding="utf-8",
        )
        (root / "configs" / "entities" / "chembl" / "activity.yaml").write_text(
            "entity:\n  provider: chembl\n",
            encoding="utf-8",
        )
        (root / "configs" / "base" / "contract_registry.yaml").write_text(
            "contracts:\n  chembl.activity: 1.0.0\n",
            encoding="utf-8",
        )

    (left_root / "configs" / "providers" / "chembl.yaml").write_text(
        "provider:\n  retries: 2\n",
        encoding="utf-8",
    )
    (right_root / "configs" / "providers" / "chembl.yaml").write_text(
        "provider:\n  retries: 5\n",
        encoding="utf-8",
    )

    refs_left = _build_effective_config_source_refs(
        provider="chembl",
        entity="activity",
        repo_root=left_root,
    )
    refs_right = _build_effective_config_source_refs(
        provider="chembl",
        entity="activity",
        repo_root=right_root,
    )

    service = create_effective_config_service()
    artifact_left = service.create_effective_config_artifact(
        pipeline_name="chembl_activity",
        pipeline_kind="standard",
        resolved_config={"pipeline": {"name": "chembl_activity"}},
        runtime_overrides={},
        source_refs=refs_left,
    )
    artifact_right = service.create_effective_config_artifact(
        pipeline_name="chembl_activity",
        pipeline_kind="standard",
        resolved_config={"pipeline": {"name": "chembl_activity"}},
        runtime_overrides={},
        source_refs=refs_right,
    )

    assert artifact_left.source_fingerprint != artifact_right.source_fingerprint
