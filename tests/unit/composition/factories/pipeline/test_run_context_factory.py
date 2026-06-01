"""Tests for run-context assembly control-plane hash surfaces."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from bioetl.domain.config import RuntimeConfig
from bioetl.composition.factories.pipeline.run_context_factory import RunContextFactory
from bioetl.composition.runtime_builders.run_manifest_support import (
    RunManifestContractIdentity,
)
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.domain.types import RunID, RunType


pytestmark = pytest.mark.unit

def _runtime() -> RuntimeConfig:
    return RuntimeConfig(run_type=RunType.INCREMENTAL)


def _yaml_config() -> PipelineYamlConfig:
    return PipelineYamlConfig(
        pipeline_name="chembl_activity",
        provider="chembl",
        entity_type="activity",
        business_primary_keys=["activity_id"],
    )


def _factory() -> RunContextFactory:
    return RunContextFactory(
        pipeline_name="chembl_activity",
        provider="chembl",
        entity_type_extractor=lambda _pipeline_name: "activity",
        pipeline_version_getter=lambda _yaml_config: "1.0.0",
        git_commit_getter=lambda: "abc123",
        dependency_lock_hash_getter=lambda: "sha256:deps",
        config_hash_getter=lambda _yaml_config: "resolved-hash",
        transform_version_getter=lambda _yaml_config: None,
        transform_steps_getter=lambda _yaml_config: (),
        contract_identity_resolver=lambda _provider, _entity: (
            "chembl.activity",
            "1.0.0",
            "schema-hash",
            "dq.policy",
            "rules-v1",
            "chembl.activity.norm",
            "1.0.0",
            "f" * 64,
        ),
    )


def test_run_context_factory_preserves_distinct_config_hash_surfaces() -> None:
    """Legacy, resolved, and effective config hashes are independent anchors."""
    factory = _factory()
    runtime = _runtime()
    yaml_config = _yaml_config()
    run_id = RunID(uuid4())
    context = factory.create(
        run_id=run_id,
        runtime=runtime,
        started_at=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
        yaml_config=yaml_config,
        config_hash="legacy-config-hash",
        resolved_config_hash="resolved-config-hash",
        effective_config_hash="effective-config-hash",
    )

    assert context.config_hash == "legacy-config-hash"
    assert context.resolved_config_hash == "resolved-config-hash"
    assert context.effective_config_hash == "effective-config-hash"
    assert context.dependency_lock_hash == "sha256:deps"


def test_run_context_factory_does_not_alias_missing_effective_hash() -> None:
    """Missing effective hash remains explicit instead of falling back to config_hash."""
    factory = _factory()
    runtime = _runtime()
    yaml_config = _yaml_config()
    run_id = RunID(uuid4())
    context = factory.create(
        run_id=run_id,
        runtime=runtime,
        started_at=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
        yaml_config=yaml_config,
        config_hash="legacy-config-hash",
        resolved_config_hash="resolved-config-hash",
        effective_config_hash=None,
    )

    assert context.config_hash == "legacy-config-hash"
    assert context.resolved_config_hash == "resolved-config-hash"
    assert context.effective_config_hash is None


def test_run_context_factory_uses_explicit_started_at_anchor() -> None:
    """RunContext timestamps must come from the caller-provided runtime anchor."""
    started_at = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    runtime = _runtime()
    yaml_config = _yaml_config()
    run_id = RunID(uuid4())
    factory = RunContextFactory(
        pipeline_name="chembl_activity",
        provider="chembl",
        entity_type_extractor=lambda _pipeline_name: "activity",
        config_hash_getter=lambda _yaml_config: "resolved-hash",
    )

    context = factory.create(
        run_id=run_id,
        runtime=runtime,
        started_at=started_at,
        yaml_config=yaml_config,
    )

    assert context.started_at == started_at


def test_run_context_factory_propagates_replay_parentage_and_snapshot_anchor() -> None:
    """Replay parentage and input snapshot fingerprint must survive into RunContext."""
    factory = _factory()
    context = factory.create(
        run_id=RunID(uuid4()),
        runtime=RuntimeConfig(run_type=RunType.INCREMENTAL, exact_replay=True),
        started_at=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
        yaml_config=_yaml_config(),
        replay_of_run_id="run-parent-1",
        replay_of_manifest_id="manifest-parent-1",
        input_snapshot_fingerprint="snapshot-fingerprint-1",
    )

    assert context.exact_replay is True
    assert context.replay_of_run_id == "run-parent-1"
    assert context.replay_of_manifest_id == "manifest-parent-1"
    assert context.input_snapshot_fingerprint == "snapshot-fingerprint-1"


def test_run_context_factory_fails_closed_for_strict_contract_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Exact replay metadata must not silently carry partial contract identity."""
    registry_dir = tmp_path / "configs" / "base"
    registry_dir.mkdir(parents=True)
    (registry_dir / "contract_registry.yaml").write_text(
        """
entries:
  chembl.activity:
    identity:
      contract_version: "1.2.3"
      schema_hash: deadbeef
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    factory = RunContextFactory(
        pipeline_name="chembl_activity",
        provider="chembl",
        entity_type_extractor=lambda _pipeline_name: "activity",
        config_hash_getter=lambda _yaml_config: "resolved-hash",
    )

    with pytest.raises(RuntimeError, match="complete contract identity"):
        factory.create(
            run_id=RunID(uuid4()),
            runtime=RuntimeConfig(
                run_type=RunType.INCREMENTAL,
                exact_replay=True,
            ),
            started_at=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
            yaml_config=_yaml_config(),
        )


def test_run_context_factory_allows_degraded_partial_contract_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Degraded runs may retain compatibility fallback without exact-replay claim."""
    registry_dir = tmp_path / "configs" / "base"
    registry_dir.mkdir(parents=True)
    (registry_dir / "contract_registry.yaml").write_text(
        "entries: [invalid",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    factory = RunContextFactory(
        pipeline_name="chembl_activity",
        provider="chembl",
        entity_type_extractor=lambda _pipeline_name: "activity",
        config_hash_getter=lambda _yaml_config: "resolved-hash",
    )

    context = factory.create(
        run_id=RunID(uuid4()),
        runtime=_runtime(),
        started_at=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
        yaml_config=_yaml_config(),
    )

    assert context.contract_ref == "chembl.activity"
    assert context.contract_version is None


def test_run_context_factory_maps_extended_contract_identity_fields() -> None:
    """Canonical 8-field identity should populate normalization profile metadata."""
    factory = RunContextFactory(
        pipeline_name="chembl_activity",
        provider="chembl",
        entity_type_extractor=lambda _pipeline_name: "activity",
        config_hash_getter=lambda _yaml_config: "resolved-hash",
        contract_identity_resolver=lambda _provider, _entity: (
            "chembl.activity",
            "1.0.0",
            "schema-hash",
            "dq.policy",
            "rules-v1",
            "chembl.activity",
            "1.2.3",
            "profile-hash",
        ),
    )

    context = factory.create(
        run_id=RunID(uuid4()),
        runtime=_runtime(),
        started_at=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
        yaml_config=_yaml_config(),
    )

    assert context.contract_ref == "chembl.activity"
    assert context.rule_bundle_version == "rules-v1"
    assert context.normalization_profile_ref == "chembl.activity"
    assert context.normalization_profile_version == "1.2.3"
    assert context.normalization_profile_hash == "profile-hash"


def test_run_context_factory_accepts_dataclass_contract_identity() -> None:
    """Dataclass-based manifest identity should normalize into RunContext fields."""
    factory = RunContextFactory(
        pipeline_name="chembl_activity",
        provider="chembl",
        entity_type_extractor=lambda _pipeline_name: "activity",
        config_hash_getter=lambda _yaml_config: "resolved-hash",
        contract_identity_resolver=lambda _provider, _entity: (
            RunManifestContractIdentity(
                contract_ref="chembl.activity",
                contract_version="1.0.0",
                contract_schema_hash="schema-hash",
                dq_policy_ref="dq.policy",
                rule_bundle_version="rules-v1",
                normalization_profile_ref="chembl.activity",
                normalization_profile_version="1.2.3",
                normalization_profile_hash="profile-hash",
            )
        ),
    )

    context = factory.create(
        run_id=RunID(uuid4()),
        runtime=_runtime(),
        started_at=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
        yaml_config=_yaml_config(),
    )

    assert context.contract_ref == "chembl.activity"
    assert context.contract_version == "1.0.0"
    assert context.contract_schema_hash == "schema-hash"
    assert context.dq_policy_ref == "dq.policy"
    assert context.rule_bundle_version == "rules-v1"
    assert context.normalization_profile_ref == "chembl.activity"
    assert context.normalization_profile_version == "1.2.3"
    assert context.normalization_profile_hash == "profile-hash"
