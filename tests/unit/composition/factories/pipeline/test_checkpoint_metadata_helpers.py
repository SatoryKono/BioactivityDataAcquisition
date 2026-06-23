"""Unit tests for checkpoint metadata composition helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

import pytest

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline

from bioetl.application.services.control_plane.manifest.service import (
    RunManifestCreateSpec as RunManifestCreateRequest,
    RunManifestService,
)
from bioetl.composition.runtime_builders.cached_bronze_snapshot_support import (
    build_cached_bronze_input_snapshot_refs,
)
from bioetl.composition.factories.pipeline.checkpoint_metadata_helpers import (
    build_current_checkpoint_metadata,
)
from bioetl.domain.context import CachedBronzeContext
from bioetl.domain.control_plane import (
    ReplayCapability,
    RunArtifactRef,
    RunInputSnapshotRef,
    RunSourceRef,
)
from bioetl.domain.types import RunType
from bioetl.domain.value_objects.run_context import RunContext
from tests.helpers.control_plane import InMemoryRunManifestStore

pytestmark = pytest.mark.unit


def _make_pipeline(**overrides: object) -> object:
    defaults = {
        "config": SimpleNamespace(
            pipeline_name="chembl_activity",
            provider="chembl",
            entity_type="activity",
        ),
        "runtime": SimpleNamespace(
            run_type=RunType.INCREMENTAL,
            exact_replay=True,
            cached_bronze=CachedBronzeContext.disabled(),
        ),
        "services": SimpleNamespace(metadata_coordinator=None),
    }
    defaults.update(overrides)
    return cast("BasePipeline", SimpleNamespace(**defaults))


_InMemoryRunManifestStore = InMemoryRunManifestStore


def test_build_current_checkpoint_metadata_includes_resume_anchors(tmp_path) -> None:
    """Current checkpoint metadata should include manifest, contract, and snapshots."""
    bronze_root = tmp_path / "bronze-cache"
    bronze_root.mkdir()
    (bronze_root / "batch_0001.jsonl.zst").write_bytes(b'{"id":1}\n')
    (bronze_root / "batch_0002.jsonl.zst").write_bytes(b'{"id":2}\n')

    run_context = RunContext.create(
        run_id=deterministic_uuid_from_callsite("test_checkpoint_metadata_helpers"),
        run_type=RunType.INCREMENTAL,
        started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        provider="chembl",
        entity="activity",
        pipeline_version="1.2.3",
        git_commit="a" * 40,
        dependency_lock_hash="sha256:deps-001",
        config_hash="a" * 64,
        effective_config_hash="a" * 64,
        manifest_id="manifest-1",
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        normalization_profile_ref="chembl.activity",
        normalization_profile_version="2.0.0",
        normalization_profile_hash="p" * 64,
        dq_contract_compatibility_hash="dq-hash",
        effective_config_artifact_id="artifact-1",
    )
    pipeline = _make_pipeline(
        runtime=SimpleNamespace(
            run_type=RunType.INCREMENTAL,
            exact_replay=True,
            cached_bronze=CachedBronzeContext.from_options(path=str(bronze_root)),
        ),
        services=SimpleNamespace(
            metadata_coordinator=SimpleNamespace(run_context=run_context)
        ),
    )

    metadata = build_current_checkpoint_metadata(pipeline)

    assert metadata.manifest_id == "manifest-1"
    assert metadata.pipeline_name == "chembl_activity"
    assert metadata.run_type == "incremental"
    assert metadata.git_commit == "a" * 40
    assert metadata.dependency_lock_hash == "sha256:deps-001"
    assert metadata.run_context is not None
    assert metadata.run_context["dependency_lock_hash"] == "sha256:deps-001"
    assert metadata.contract_ref == "chembl.activity"
    assert metadata.contract_version == "1.0.0"
    assert metadata.normalization_profile_ref == "chembl.activity"
    assert metadata.normalization_profile_version == "2.0.0"
    assert metadata.normalization_profile_hash == "p" * 64
    assert metadata.exact_replay is True
    assert len(metadata.input_snapshot_refs) == 2
    assert metadata.input_snapshot_refs[0]["snapshot_id"].startswith("sha256:")
    assert len(metadata.input_snapshot_ids) == 2
    assert metadata.input_snapshot_ids == tuple(sorted(metadata.input_snapshot_ids))
    assert metadata.input_snapshot_fingerprint is not None
    assert metadata.execution_fingerprint is not None


def test_checkpoint_metadata_execution_fingerprint_matches_manifest_contract(
    tmp_path,
) -> None:
    """Checkpoint metadata should share the same canonical execution identity."""
    bronze_root = tmp_path / "bronze-cache"
    bronze_root.mkdir()
    (bronze_root / "batch_0001.jsonl.zst").write_bytes(b'{"id":1}\n')
    (bronze_root / "batch_0002.jsonl.zst").write_bytes(b'{"id":2}\n')

    run_context = RunContext.create(
        run_id=deterministic_uuid_from_callsite("test_checkpoint_metadata_helpers"),
        run_type=RunType.INCREMENTAL,
        started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        provider="chembl",
        entity="activity",
        pipeline_version="1.2.3",
        git_commit="test-commit-hash",
        dependency_lock_hash="sha256:deps-001",
        config_hash="a" * 64,
        resolved_config_hash="a" * 64,
        effective_config_hash="a" * 64,
        manifest_id="manifest-1",
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        contract_schema_hash="schema-deadbeef",
        dq_policy_ref="chembl.activity.policy",
        rule_bundle_version="2026.04",
        normalization_profile_ref="chembl.activity",
        normalization_profile_version="2.0.0",
        normalization_profile_hash="p" * 64,
        dq_contract_compatibility_hash="dq-hash",
        effective_config_artifact_id="artifact-1",
    )
    pipeline = _make_pipeline(
        runtime=SimpleNamespace(
            run_type=RunType.INCREMENTAL,
            exact_replay=True,
            cached_bronze=CachedBronzeContext.from_options(path=str(bronze_root)),
        ),
        services=SimpleNamespace(
            metadata_coordinator=SimpleNamespace(run_context=run_context)
        ),
    )

    checkpoint_metadata = build_current_checkpoint_metadata(pipeline)
    manifest_service = RunManifestService(
        manifest_port=_InMemoryRunManifestStore(),
        _manifest_id_factory=lambda: "manifest-1",
    )
    snapshot_refs = build_cached_bronze_input_snapshot_refs(
        bronze_root=bronze_root,
        bronze_date=None,
    )
    manifest = manifest_service.create_manifest(
        RunManifestCreateRequest(
            run_id=run_context.run_id,
            run_type=RunType.INCREMENTAL,
            pipeline_name="chembl_activity",
            provider="chembl",
            entity="activity",
            launch_context={"exact_replay": True},
            runtime_config={"run_type": "incremental", "exact_replay": True},
            resolved_config={"provider": "chembl", "entity_type": "activity"},
            source_refs=(
                RunSourceRef(
                    provider="chembl",
                    entity="activity",
                    pipeline_name="chembl_activity",
                    input_snapshots=snapshot_refs,
                ),
            ),
            planned_artifacts=(
                RunArtifactRef(
                    layer="bronze",
                    path="data/output/bronze/chembl/activity",
                ),
            ),
            pipeline_version="1.2.3",
            effective_config_hash=run_context.effective_config_hash,
            contract_ref="chembl.activity",
            contract_version="1.0.0",
            contract_schema_hash="schema-deadbeef",
            dq_policy_ref="chembl.activity.policy",
            rule_bundle_version="2026.04",
            dq_contract_compatibility_hash="dq-hash",
            effective_config_artifact_id="artifact-1",
            replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED,
            git_commit="test-commit-hash",
            source_revision_state="clean",
            dependency_lock_hash="sha256:deps-001",
            config_hash=run_context.config_hash,
            resolved_config_hash=run_context.resolved_config_hash,
            normalization_profile_ref="chembl.activity",
            normalization_profile_version="2.0.0",
            normalization_profile_hash="p" * 64,
        )
    )

    assert checkpoint_metadata.execution_fingerprint == manifest.execution_fingerprint


def test_build_current_checkpoint_metadata_prefers_manifest_snapshot_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Checkpoint metadata should reuse persisted manifest snapshot refs first."""
    run_context = RunContext.create(
        run_id=deterministic_uuid_from_callsite("test_checkpoint_metadata_helpers"),
        run_type=RunType.INCREMENTAL,
        started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        provider="chembl",
        entity="activity",
        pipeline_version="1.2.3",
        git_commit="test-commit-hash",
        dependency_lock_hash="sha256:deps-001",
        config_hash="a" * 64,
        effective_config_hash="a" * 64,
        manifest_id="manifest-1",
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        normalization_profile_ref="chembl.activity",
        normalization_profile_version="2.0.0",
        normalization_profile_hash="p" * 64,
        dq_contract_compatibility_hash="dq-hash",
        effective_config_artifact_id="artifact-1",
    )
    pipeline = _make_pipeline(
        runtime=SimpleNamespace(
            run_type=RunType.INCREMENTAL,
            exact_replay=True,
            cached_bronze=CachedBronzeContext.disabled(),
        ),
        services=SimpleNamespace(
            metadata_coordinator=SimpleNamespace(run_context=run_context)
        ),
    )
    manifest_snapshot = RunInputSnapshotRef(
        snapshot_id="sha256:manifest-snapshot",
        content_hash="manifest-snapshot",
        immutable_uri="bronze://chembl/activity/manifest.jsonl.zst",
    )
    monkeypatch.setattr(
        "bioetl.composition.factories.pipeline.checkpoint_metadata_helpers.resolve_manifest_input_snapshot_refs",
        lambda **_: (manifest_snapshot,),
    )

    metadata = build_current_checkpoint_metadata(pipeline)

    assert metadata.input_snapshot_ids == ("sha256:manifest-snapshot",)
    assert metadata.input_snapshot_refs[0]["immutable_uri"] == (
        "bronze://chembl/activity/manifest.jsonl.zst"
    )
