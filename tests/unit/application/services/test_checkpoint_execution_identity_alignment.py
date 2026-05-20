"""Regression tests that keep legacy and V2 execution identity semantics aligned."""

from __future__ import annotations

from unittest.mock import MagicMock

from bioetl.application.core.lifecycle.checkpoint_runtime import (
    enrich_metadata_with_execution_identity,
)
from bioetl.application.services.checkpoint_compatibility_service import (
    CheckpointCompatibilityService,
)
from bioetl.application.services.checkpoint_compatibility_service_v2 import (
    CheckpointCompatibilityServiceV2,
    CheckpointIdentity,
    CompatibilityVerdict,
    ExecutionPhase,
)
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata


def _legacy_service() -> CheckpointCompatibilityService:
    return CheckpointCompatibilityService(logger=MagicMock())


def _v2_service() -> CheckpointCompatibilityServiceV2:
    return CheckpointCompatibilityServiceV2()


def _metadata(
    *,
    effective_config_hash: str | None = "a" * 64,
    composite_run_identity: str | None = None,
    execution_fingerprint: str | None = None,
    dq_contract_compatibility_hash: str | None = None,
    pipeline_version: str | None = None,
    manifest_id: str | None = None,
    contract_ref: str | None = None,
    contract_version: str | None = None,
    git_commit: str | None = None,
    dependency_lock_hash: str | None = None,
    normalization_profile_ref: str | None = None,
    normalization_profile_version: str | None = None,
    normalization_profile_hash: str | None = None,
    effective_config_artifact_id: str | None = None,
    input_snapshot_refs: tuple[dict[str, object], ...] = (),
    input_snapshot_ids: tuple[str, ...] = (),
    input_snapshot_fingerprint: str | None = None,
) -> CheckpointMetadata:
    return CheckpointMetadata(
        records_processed=100,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        pipeline_version=pipeline_version,
        effective_config_hash=effective_config_hash,
        composite_run_identity=composite_run_identity,
        execution_fingerprint=execution_fingerprint,
        manifest_id=manifest_id,
        contract_ref=contract_ref,
        contract_version=contract_version,
        git_commit=git_commit,
        dependency_lock_hash=dependency_lock_hash,
        normalization_profile_ref=normalization_profile_ref,
        normalization_profile_version=normalization_profile_version,
        normalization_profile_hash=normalization_profile_hash,
        effective_config_artifact_id=effective_config_artifact_id,
        input_snapshot_refs=input_snapshot_refs,
        input_snapshot_ids=input_snapshot_ids,
        input_snapshot_fingerprint=input_snapshot_fingerprint,
    )


def _identity(
    *,
    effective_config_hash: str = "a" * 64,
    composite_run_identity: str | None = None,
    execution_fingerprint: str | None = None,
    pipeline_version: str | None = None,
    manifest_id: str | None = None,
    contract_ref: str | None = None,
    contract_version: str | None = None,
    git_commit: str | None = None,
    dependency_lock_hash: str | None = None,
    normalization_profile_ref: str | None = None,
    normalization_profile_version: str | None = None,
    normalization_profile_hash: str | None = None,
    effective_config_artifact_id: str | None = None,
) -> CheckpointIdentity:
    return CheckpointIdentity(
        effective_config_hash=effective_config_hash,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",
        composite_run_identity=composite_run_identity,
        execution_fingerprint=execution_fingerprint,
        pipeline_version=pipeline_version,
        manifest_id=manifest_id,
        git_commit=git_commit,
        dependency_lock_hash=dependency_lock_hash,
        contract_ref=contract_ref,
        contract_version=contract_version,
        normalization_profile_ref=normalization_profile_ref,
        normalization_profile_version=normalization_profile_version,
        normalization_profile_hash=normalization_profile_hash,
        effective_config_artifact_id=effective_config_artifact_id,
    )


def test_legacy_and_v2_align_when_execution_fingerprint_matches() -> None:
    legacy = _legacy_service()
    v2 = _v2_service()

    current_metadata = _metadata(execution_fingerprint="fp-same")
    checkpoint_metadata = _metadata(execution_fingerprint="fp-same")
    current_identity = _identity(execution_fingerprint="fp-same")
    checkpoint_identity = _identity(execution_fingerprint="fp-same")

    legacy_result = legacy.validate_checkpoint_compatibility(
        current_metadata,
        checkpoint_metadata,
    )
    v2_result = v2.check_compatibility(current_identity, checkpoint_identity)

    assert legacy_result.compatible is True
    assert v2_result.verdict == CompatibilityVerdict.COMPATIBLE
    assert (
        v2_result.details["execution_identity_compatibility"]["reason"]
        == "identical_execution_fingerprint"
    )


def test_legacy_and_v2_align_when_execution_fingerprint_mismatches() -> None:
    legacy = _legacy_service()
    v2 = _v2_service()

    current_metadata = _metadata(execution_fingerprint="fp-current")
    checkpoint_metadata = _metadata(execution_fingerprint="fp-checkpoint")
    current_identity = _identity(execution_fingerprint="fp-current")
    checkpoint_identity = _identity(execution_fingerprint="fp-checkpoint")

    legacy_result = legacy.validate_checkpoint_compatibility(
        current_metadata,
        checkpoint_metadata,
    )
    v2_result = v2.check_compatibility(current_identity, checkpoint_identity)

    assert legacy_result.compatible is False
    assert legacy_result.execution_identity_compatible is False
    assert any(
        "Execution fingerprint mismatch" in msg for msg in legacy_result.messages
    )
    assert v2_result.verdict == CompatibilityVerdict.MAJOR_INCOMPATIBLE
    assert (
        v2_result.details["execution_identity_compatibility"]["reason"]
        == "execution_fingerprint_mismatch"
    )


def test_legacy_and_v2_align_when_runtime_anchor_fingerprint_mismatches() -> None:
    legacy = _legacy_service()
    v2 = _v2_service()

    current_metadata = _metadata(
        manifest_id="manifest-a",
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        effective_config_artifact_id="artifact-1",
    )
    checkpoint_metadata = _metadata(
        manifest_id="manifest-b",
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        effective_config_artifact_id="artifact-1",
    )
    current_identity = _identity(
        manifest_id="manifest-a",
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        effective_config_artifact_id="artifact-1",
    )
    checkpoint_identity = _identity(
        manifest_id="manifest-b",
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        effective_config_artifact_id="artifact-1",
    )

    legacy_result = legacy.validate_checkpoint_compatibility(
        current_metadata,
        checkpoint_metadata,
    )
    v2_result = v2.check_compatibility(current_identity, checkpoint_identity)

    assert legacy_result.compatible is False
    assert legacy_result.execution_identity_compatible is False
    assert any(
        "Degraded runtime-anchor fingerprint mismatch" in msg
        for msg in legacy_result.messages
    )
    assert v2_result.verdict == CompatibilityVerdict.MAJOR_INCOMPATIBLE
    assert (
        v2_result.details["execution_identity_compatibility"]["reason"]
        == "degraded_runtime_anchor_fingerprint_mismatch"
    )


def test_legacy_and_v2_align_when_composite_run_identity_mismatches() -> None:
    legacy = _legacy_service()
    v2 = _v2_service()

    current_metadata = _metadata(composite_run_identity="run-a")
    checkpoint_metadata = _metadata(composite_run_identity="run-b")
    current_identity = _identity(composite_run_identity="run-a")
    checkpoint_identity = _identity(composite_run_identity="run-b")

    legacy_result = legacy.validate_checkpoint_compatibility(
        current_metadata,
        checkpoint_metadata,
    )
    v2_result = v2.check_compatibility(current_identity, checkpoint_identity)

    assert legacy_result.compatible is True
    assert legacy_result.execution_identity_compatible is True
    assert any(
        "Checkpoint is compatible for resume" in msg for msg in legacy_result.messages
    )
    assert v2_result.verdict == CompatibilityVerdict.COMPATIBLE
    assert (
        v2_result.details["execution_identity_compatibility"]["reason"]
        == "identical_degraded_runtime_anchor_fingerprint"
    )


def test_legacy_blocks_when_composite_identity_is_the_only_resume_anchor() -> None:
    legacy = _legacy_service()

    current_metadata = CheckpointMetadata(
        records_processed=100,
        composite_run_identity="run-a",
    )
    checkpoint_metadata = CheckpointMetadata(
        records_processed=100,
        composite_run_identity="run-b",
    )

    legacy_result = legacy.validate_checkpoint_compatibility(
        current_metadata,
        checkpoint_metadata,
    )

    assert legacy_result.compatible is False
    assert legacy_result.execution_identity_compatible is False
    assert any(
        "Execution identity continuity not proven" in msg
        for msg in legacy_result.messages
    )


def test_legacy_and_v2_align_when_git_commit_and_profile_drift() -> None:
    legacy = _legacy_service()
    v2 = _v2_service()

    current_metadata = _metadata(
        pipeline_version="1.0.0",
        git_commit="commit-a",
        dependency_lock_hash="sha256:deps",
        normalization_profile_ref="chembl.activity",
        normalization_profile_version="2.0.0",
        normalization_profile_hash="a" * 64,
    )
    checkpoint_metadata = _metadata(
        pipeline_version="1.0.0",
        git_commit="commit-b",
        dependency_lock_hash="sha256:deps",
        normalization_profile_ref="chembl.activity",
        normalization_profile_version="2.0.0",
        normalization_profile_hash="a" * 64,
    )
    current_identity = _identity(
        pipeline_version="1.0.0",
        git_commit="commit-a",
        dependency_lock_hash="sha256:deps",
        normalization_profile_ref="chembl.activity",
        normalization_profile_version="2.0.0",
        normalization_profile_hash="a" * 64,
    )
    checkpoint_identity = _identity(
        pipeline_version="1.0.0",
        git_commit="commit-b",
        dependency_lock_hash="sha256:deps",
        normalization_profile_ref="chembl.activity",
        normalization_profile_version="2.0.0",
        normalization_profile_hash="a" * 64,
    )

    legacy_result = legacy.validate_checkpoint_compatibility(
        current_metadata,
        checkpoint_metadata,
    )
    v2_result = v2.check_compatibility(current_identity, checkpoint_identity)

    assert legacy_result.compatible is False
    assert legacy_result.execution_identity_compatible is False
    assert any("Git commit mismatch" in msg for msg in legacy_result.messages)
    assert v2_result.verdict == CompatibilityVerdict.MAJOR_INCOMPATIBLE
    assert (
        v2_result.details["execution_identity_compatibility"]["reason"]
        == "checkpoint_execution_identity_fallback_mismatch"
    )


def test_legacy_and_v2_align_when_fingerprint_matches_despite_composite_drift() -> None:
    legacy = _legacy_service()
    v2 = _v2_service()

    current_metadata = _metadata(
        execution_fingerprint="fp-shared",
        composite_run_identity="run-a",
    )
    checkpoint_metadata = _metadata(
        execution_fingerprint="fp-shared",
        composite_run_identity="run-b",
    )
    current_identity = _identity(
        execution_fingerprint="fp-shared",
        composite_run_identity="run-a",
    )
    checkpoint_identity = _identity(
        execution_fingerprint="fp-shared",
        composite_run_identity="run-b",
    )

    legacy_result = legacy.validate_checkpoint_compatibility(
        current_metadata,
        checkpoint_metadata,
    )
    v2_result = v2.check_compatibility(current_identity, checkpoint_identity)

    assert legacy_result.compatible is True
    assert legacy_result.execution_identity_compatible is True
    assert v2_result.verdict == CompatibilityVerdict.COMPATIBLE
    assert (
        v2_result.details["execution_identity_compatibility"]["reason"]
        == "identical_execution_fingerprint"
    )


def test_enrich_metadata_with_execution_identity_preserves_profile_and_snapshot_anchors() -> (
    None
):
    identity = _metadata(
        effective_config_hash="f" * 64,
        execution_fingerprint="fp-identity",
        manifest_id="manifest-identity",
        contract_ref="chembl.activity",
        contract_version="2.0.0",
        normalization_profile_ref="chembl.activity",
        normalization_profile_version="2.1.0",
        normalization_profile_hash="a" * 64,
        input_snapshot_refs=(
            {
                "snapshot_id": "sha256:snap-a",
                "content_hash": "snap-a",
                "immutable_uri": "bronze://2026-05-01/batch_a.jsonl.zst",
            },
        ),
        input_snapshot_ids=("sha256:snap-a",),
        input_snapshot_fingerprint="snap-fingerprint-a",
    )
    sparse = CheckpointMetadata(records_processed=100)

    enriched = enrich_metadata_with_execution_identity(sparse, identity=identity)

    assert enriched.normalization_profile_ref == "chembl.activity"
    assert enriched.normalization_profile_version == "2.1.0"
    assert enriched.normalization_profile_hash == "a" * 64
    assert enriched.input_snapshot_refs == identity.input_snapshot_refs
    assert enriched.input_snapshot_ids == ("sha256:snap-a",)
    assert enriched.input_snapshot_fingerprint == "snap-fingerprint-a"
    assert (
        enriched.checkpoint_execution_identity_fingerprint()
        == identity.checkpoint_execution_identity_fingerprint()
    )
