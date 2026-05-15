"""Shared fixtures and expectation helpers for run-manifest service tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from bioetl.domain.control_plane import (
    ReplayCapability,
    RunCodeProvenance,
    RunInputSnapshotRef,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.control_plane.reproducibility_profiles import (
    build_lineage_closure_boundary,
    build_replay_family_contract,
    resolve_reproducibility_family_profile,
)
from bioetl.domain.normalization import (
    build_execution_identity_payload,
    compute_execution_identity_fingerprint,
)
from bioetl.domain.types import RunID, RunType
from tests.helpers.deterministic_ids import deterministic_uuid
from tests.helpers.synthetic_paths import synthetic_test_root

FIXED_TIME = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)
VALID_CONFIG_HASH = "a" * 64
VALID_RESOLVED_CONFIG_HASH = "b" * 64
VALID_EFFECTIVE_CONFIG_HASH = "c" * 64
SNAPSHOT_IDENTITY_FINGERPRINT = (
    "273c9e5f598ea834b7fa778048db3ff57a0f73c9b406e4edd9db26ae9ae4fcf9"
)
TEST_ROOT = synthetic_test_root("run-manifest-test-support")
DEFAULT_BRONZE_BATCH_URI = (TEST_ROOT / "bronze" / "batch_1.jsonl.zst").as_uri()


def build_default_source_refs(
    *,
    bronze_batch_uri: str = DEFAULT_BRONZE_BATCH_URI,
) -> tuple[RunSourceRef, ...]:
    """Build the canonical immutable source snapshot used by exact-replay tests."""
    return (
        RunSourceRef(
            provider="chembl",
            entity="activity",
            pipeline_name="chembl_activity",
            input_snapshots=(
                RunInputSnapshotRef(
                    snapshot_id="snapshot-1",
                    content_hash="sha256:snapshot-1",
                    immutable_uri=bronze_batch_uri,
                    storage_provider="s3",
                    object_bucket="bioetl-bronze",
                    object_key="chembl/activity/batch_1.jsonl.zst",
                    object_version_id="snapshot-version-1",
                ),
            ),
        ),
    )


def build_source_refs(
    *,
    provider: str = "chembl",
    entity: str = "activity",
    pipeline_name: str = "chembl_activity",
    immutable_uri: str,
    query: str | None = None,
    query_fingerprint: str | None = None,
    storage_provider: str | None = None,
    object_bucket: str | None = None,
    object_key: str | None = None,
    object_version_id: str | None = None,
    etag: str | None = None,
    last_modified: datetime | None = None,
    captured_at: datetime | None = None,
) -> tuple[RunSourceRef, ...]:
    """Build a single-source immutable snapshot tuple with overridable fields."""
    return (
        RunSourceRef(
            provider=provider,
            entity=entity,
            pipeline_name=pipeline_name,
            query=query,
            input_snapshots=(
                RunInputSnapshotRef(
                    snapshot_id="snapshot-1",
                    content_hash="sha256:snapshot-1",
                    immutable_uri=immutable_uri,
                    query_fingerprint=query_fingerprint,
                    storage_provider=storage_provider,
                    object_bucket=object_bucket,
                    object_key=object_key,
                    object_version_id=object_version_id,
                    etag=etag,
                    last_modified=last_modified,
                    captured_at=captured_at,
                ),
            ),
        ),
    )


def build_published_silver_artifact(
    *,
    artifact_path: str,
    include_dataset_ref: bool = True,
    include_artifact_id: bool = True,
) -> dict[str, object]:
    """Build the canonical published silver artifact payload used in tests."""
    payload = {
        "event_type": "artifact_published",
        "stage": "silver",
        "lineage_fragment_id": "silver:fragment-1",
        "artifact_path": artifact_path,
    }
    if include_artifact_id:
        payload["artifact_id"] = "silver:chembl.activity@1"
    if include_dataset_ref:
        payload["dataset_ref"] = "silver:chembl.activity@1"
    return payload


@dataclass(frozen=True)
class RunManifestOverrides:
    resolved_config_hash: str | None = VALID_RESOLVED_CONFIG_HASH
    effective_config_hash: str | None = VALID_EFFECTIVE_CONFIG_HASH
    provider: str = "chembl"
    entity: str = "activity"
    pipeline_name: str = "chembl_activity"
    launch_context: dict[str, object] | None = None
    runtime_config: dict[str, object] | None = None
    resolved_config: dict[str, object] | None = None
    contract_ref: str = "chembl.activity"
    contract_version: str = "1.2.0"
    dq_policy_ref: str = "chembl_activity.gold"
    rule_bundle_version: str = "2026.03"
    dq_contract_compatibility_hash: str = "compat-hash-1"
    effective_config_artifact_id: str | None = "eca-123"
    dependency_lock_hash: str | None = None


def make_run_manifest(
    *,
    manifest_id: str = "manifest-diagnostics",
    run_id: RunID | None = None,
    run_type: RunType = RunType.INCREMENTAL,
    config_hash: str = VALID_CONFIG_HASH,
    limit: int = 25,
    execution_fingerprint: str | None = None,
    created_at: datetime | None = None,
    source_refs: tuple[RunSourceRef, ...] = (),
    replay_capability: ReplayCapability = ReplayCapability.REBUILD_ONLY,
    overrides: RunManifestOverrides | None = None,
) -> RunManifest:
    """Build a canonical run manifest for diagnostics/inspection test suites."""
    resolved_overrides = overrides or RunManifestOverrides()
    resolved_run_id = run_id or RunID(
        deterministic_uuid(f"run-manifest-support:{manifest_id}")
    )
    resolved_launch_context = {"limit": limit}
    if resolved_overrides.launch_context is not None:
        resolved_launch_context = dict(resolved_overrides.launch_context)
    resolved_runtime_config = {"run_type": run_type.value, "limit": limit}
    if resolved_overrides.runtime_config is not None:
        resolved_runtime_config = dict(resolved_overrides.runtime_config)
    return RunManifest(
        manifest_id=manifest_id,
        execution_fingerprint=execution_fingerprint or f"fingerprint-{manifest_id}",
        schema_version="1.0",
        created_at=created_at or FIXED_TIME,
        run_id=resolved_run_id,
        run_type=run_type,
        pipeline_name=resolved_overrides.pipeline_name,
        provider=resolved_overrides.provider,
        entity=resolved_overrides.entity,
        launch_context=resolved_launch_context,
        runtime_config=resolved_runtime_config,
        resolved_config=resolved_overrides.resolved_config
        or {
            "provider": resolved_overrides.provider,
            "entity_type": resolved_overrides.entity,
        },
        code_provenance=RunCodeProvenance(
            pipeline_version="1.0.0",
            git_commit="abc1234",
            source_revision_state="clean",
            dependency_lock_hash=resolved_overrides.dependency_lock_hash,
            config_hash=config_hash,
            resolved_config_hash=resolved_overrides.resolved_config_hash,
            effective_config_hash=resolved_overrides.effective_config_hash,
            contract_ref=resolved_overrides.contract_ref,
            contract_version=resolved_overrides.contract_version,
            dq_policy_ref=resolved_overrides.dq_policy_ref,
            rule_bundle_version=resolved_overrides.rule_bundle_version,
            dq_contract_compatibility_hash=(
                resolved_overrides.dq_contract_compatibility_hash
            ),
            effective_config_artifact_id=(
                resolved_overrides.effective_config_artifact_id
            ),
        ),
        replay_capability=replay_capability,
        source_refs=source_refs,
    )


def expected_canonical_execution_identity(
    manifest: RunManifest,
    *,
    requested_exact_replay: bool = False,
    snapshot_fingerprint: str | None = None,
) -> dict[str, object]:
    """Build the canonical execution-identity expectation payload."""
    payload = build_execution_identity_payload(
        pipeline_name=manifest.pipeline_name,
        run_type=manifest.run_type.value,
        pipeline_version=manifest.code_provenance.pipeline_version,
        git_commit=manifest.code_provenance.git_commit,
        dependency_lock_hash=manifest.code_provenance.dependency_lock_hash,
        effective_config_hash=manifest.code_provenance.effective_config_hash,
        dq_contract_compatibility_hash=(
            manifest.code_provenance.dq_contract_compatibility_hash
        ),
        contract_ref=manifest.code_provenance.contract_ref,
        contract_version=manifest.code_provenance.contract_version,
        normalization_profile_ref=manifest.code_provenance.normalization_profile_ref,
        normalization_profile_version=(
            manifest.code_provenance.normalization_profile_version
        ),
        normalization_profile_hash=manifest.code_provenance.normalization_profile_hash,
        effective_config_artifact_id=(
            manifest.code_provenance.effective_config_artifact_id
        ),
        exact_replay=requested_exact_replay,
        input_snapshot_fingerprint=snapshot_fingerprint,
        silver_filter_compatibility_mode=str(
            manifest.runtime_config.get(
                "silver_filter_compatibility_mode",
                "structural_only_auto_promote",
            )
        ),
    )
    return {
        "execution_fingerprint": manifest.execution_fingerprint,
        "payload": payload,
    }


def expected_degraded_runtime_anchor(manifest: RunManifest) -> dict[str, object]:
    """Build the degraded-runtime-anchor expectation payload."""
    payload = {
        "manifest_id": manifest.manifest_id,
        "effective_config_hash": manifest.code_provenance.effective_config_hash,
        "contract_ref": manifest.code_provenance.contract_ref,
        "contract_version": manifest.code_provenance.contract_version,
        "effective_config_artifact_id": (
            manifest.code_provenance.effective_config_artifact_id
        ),
    }
    filtered_payload = {
        key: value for key, value in payload.items() if value is not None
    }
    return {
        "compatibility_scope": "legacy_fallback_only",
        "fingerprint": (
            compute_execution_identity_fingerprint(filtered_payload)
            if filtered_payload
            else None
        ),
        "payload": filtered_payload,
    }


def expected_exact_replay_anchors(
    manifest: RunManifest,
    *,
    snapshot_fingerprint: str | None = None,
    published_artifact_ids: list[str] | None = None,
    published_artifact_paths: list[str] | None = None,
    lineage_fragment_ids: list[str] | None = None,
) -> dict[str, object]:
    """Build exact-replay anchor expectations for manifest diagnostics."""
    snapshot_ids = sorted(
        {
            snapshot.snapshot_id
            for source_ref in manifest.source_refs
            for snapshot in source_ref.input_snapshots
        }
    )
    snapshot_hashes = sorted(
        {
            snapshot.content_hash
            for source_ref in manifest.source_refs
            for snapshot in source_ref.input_snapshots
        }
    )
    anchors: dict[str, object] = {
        "semantic_identity_anchor": "execution_fingerprint",
        "execution_fingerprint": manifest.execution_fingerprint,
        "pipeline_name": manifest.pipeline_name,
        "run_type": manifest.run_type.value,
        "pipeline_version": manifest.code_provenance.pipeline_version,
        "git_commit": manifest.code_provenance.git_commit,
        "dependency_lock_state": (
            "present"
            if manifest.code_provenance.dependency_lock_hash is not None
            else "missing"
        ),
        "effective_config_hash": manifest.code_provenance.effective_config_hash,
        "dq_contract_compatibility_hash": (
            manifest.code_provenance.dq_contract_compatibility_hash
        ),
        "contract_ref": manifest.code_provenance.contract_ref,
        "contract_version": manifest.code_provenance.contract_version,
        "normalization_profile_ref": (
            manifest.code_provenance.normalization_profile_ref
        ),
        "normalization_profile_version": (
            manifest.code_provenance.normalization_profile_version
        ),
        "normalization_profile_hash": (
            manifest.code_provenance.normalization_profile_hash
        ),
        "effective_config_artifact_id": (
            manifest.code_provenance.effective_config_artifact_id
        ),
        "input_snapshot_identity_fingerprint": snapshot_fingerprint,
        "input_snapshot_ids": snapshot_ids,
        "input_snapshot_content_hashes": snapshot_hashes,
        "published_artifact_ids": published_artifact_ids or [],
        "published_artifact_paths": published_artifact_paths or [],
        "lineage_fragment_ids": lineage_fragment_ids or [],
    }
    if manifest.code_provenance.dependency_lock_hash is not None:
        anchors["dependency_lock_hash"] = manifest.code_provenance.dependency_lock_hash
    return anchors


def expected_produced_artifact_trace(
    manifest: RunManifest,
    *,
    ledger_entries_present: bool,
    artifacts: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Build produced-artifact-trace expectations for manifest diagnostics."""
    artifact_payload = artifacts or []
    missing_requirements: list[str] = []
    if not ledger_entries_present:
        missing_requirements.append("run_ledger_history")
    if not artifact_payload:
        missing_requirements.append("artifact_publication_event")
    return {
        "lookup": "run_ledger_by_manifest_id",
        "lookup_key": manifest.manifest_id,
        "manifest_id": manifest.manifest_id,
        "complete": not missing_requirements,
        "artifact_count": len(artifact_payload),
        "artifacts": artifact_payload,
        "missing_requirements": missing_requirements,
    }


def manifest_execution_context(manifest: RunManifest) -> str:
    """Return the effective execution context for a manifest."""
    return (
        "composite"
        if (
            str(manifest.launch_context.get("execution_context") or "") == "composite"
            or manifest.provider == "composite"
        )
        else "source"
    )


def resolve_checkpoint_policy(
    *,
    requested_exact_replay: bool,
    required_profile: str,
    requested_policy: str | None,
) -> str:
    """Resolve the checkpoint compatibility policy used in expectations."""
    if requested_policy not in {"observe", "soft_fail", "hard_fail"}:
        requested_policy = None
    if requested_exact_replay:
        return "hard_fail"
    if required_profile not in {"replay_ready", "forensic_grade"}:
        return requested_policy or "observe"
    return "hard_fail" if requested_policy != "hard_fail" else requested_policy


def _manifest_loading_strategy_values(manifest: RunManifest) -> tuple[object, ...]:
    runtime_pipeline = manifest.runtime_config.get("pipeline")
    resolved_pipeline = manifest.resolved_config.get("pipeline")
    return (
        manifest.runtime_config.get("loading_strategy"),
        runtime_pipeline.get("loading_strategy")
        if isinstance(runtime_pipeline, dict)
        else None,
        manifest.resolved_config.get("loading_strategy"),
        resolved_pipeline.get("loading_strategy")
        if isinstance(resolved_pipeline, dict)
        else None,
    )


def _manifest_requires_full_scan_rebuild(manifest: RunManifest) -> bool:
    return any(
        str(candidate or "").strip().lower() == "full_scan_only"
        for candidate in _manifest_loading_strategy_values(manifest)
    )


def _expected_continuation_mode(
    *,
    manifest: RunManifest,
    requested_exact_replay: bool,
    is_composite: bool,
) -> str:
    if (
        requested_exact_replay
        and manifest.replay_capability == ReplayCapability.EXACT_REPLAY_SUPPORTED
    ):
        return "exact_replay"
    if _manifest_requires_full_scan_rebuild(manifest):
        return "full_scan_idempotent_rebuild"
    if not (
        bool(manifest.launch_context.get("resume"))
        or manifest.replay_capability == ReplayCapability.RESUME_ONLY
    ):
        return "rebuild_only"
    return (
        "checkpoint_snapshot_plus_ledger_suffix_resume"
        if is_composite
        else "checkpoint_snapshot_only_resume"
    )


def expected_resume_contract(manifest: RunManifest) -> dict[str, object]:
    """Build resume-contract expectations for manifest diagnostics."""
    requested_exact_replay = bool(manifest.launch_context.get("exact_replay"))
    required_profile = str(
        manifest.launch_context.get("required_persistence_profile")
        or "degraded_observable"
    )
    requested_policy = manifest.launch_context.get("checkpoint_compatibility_policy")
    if not isinstance(requested_policy, str) or requested_policy not in {
        "observe",
        "soft_fail",
        "hard_fail",
    }:
        requested_policy = None
    applied_policy = resolve_checkpoint_policy(
        requested_exact_replay=requested_exact_replay,
        required_profile=required_profile,
        requested_policy=requested_policy,
    )
    execution_context = manifest_execution_context(manifest)
    is_composite = execution_context == "composite"
    profile = resolve_reproducibility_family_profile(
        provider=manifest.provider,
        entity=manifest.entity,
        contract_ref=manifest.code_provenance.contract_ref,
        execution_context=execution_context,
    )
    strict_replay_requested = requested_exact_replay or required_profile in {
        "replay_ready",
        "forensic_grade",
    }
    continuation_mode = _expected_continuation_mode(
        manifest=manifest,
        requested_exact_replay=requested_exact_replay,
        is_composite=is_composite,
    )
    return {
        "resume_requested": bool(manifest.launch_context.get("resume")),
        "requested_exact_replay": requested_exact_replay,
        "requested_checkpoint_compatibility_policy": requested_policy,
        "applied_checkpoint_compatibility_policy": applied_policy,
        "strict_replay_safe": (
            strict_replay_requested
            and applied_policy == "hard_fail"
            and profile.strict_exact_replay_supported
            and manifest.replay_capability == ReplayCapability.EXACT_REPLAY_SUPPORTED
            and bool(manifest.code_provenance.dependency_lock_hash)
        ),
        "execution_context": "composite" if is_composite else "ordinary",
        "resume_mode": (
            "checkpoint_snapshot_plus_ledger_suffix"
            if is_composite
            else "checkpoint_snapshot_only"
        ),
        "continuation_mode": continuation_mode,
        "semantic_identity_anchor": "execution_fingerprint",
        "occurrence_identity_anchor": "run_id",
    }


def expected_replay_parentage(manifest: RunManifest) -> dict[str, object]:
    """Build replay-parentage expectations for manifest diagnostics."""
    return {
        "is_exact_replay": (
            manifest.replay_of_run_id is not None
            or manifest.replay_of_manifest_id is not None
        ),
        "replay_of_run_id": manifest.replay_of_run_id,
        "replay_of_manifest_id": manifest.replay_of_manifest_id,
    }


def expected_lineage_closure_boundary(manifest: RunManifest) -> dict[str, object]:
    """Build lineage-closure-boundary expectations for manifest diagnostics."""
    return build_lineage_closure_boundary(
        provider=manifest.provider,
        entity=manifest.entity,
        contract_ref=manifest.code_provenance.contract_ref,
        execution_context=manifest_execution_context(manifest),
    )


def expected_replay_family_contract(manifest: RunManifest) -> dict[str, object]:
    """Build replay-family-contract expectations for manifest diagnostics."""
    return build_replay_family_contract(
        provider=manifest.provider,
        entity=manifest.entity,
        contract_ref=manifest.code_provenance.contract_ref,
        execution_context=manifest_execution_context(manifest),
    )
