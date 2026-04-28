"""Unit tests for RunManifestInspectionService."""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from bioetl.application.services.effective_config_service import EffectiveConfigService
from bioetl.application.services.run_manifest_inspection_service import (
    RunManifestInspectionService,
)
from bioetl.application.services.run_ledger_service import RunLedgerService
from bioetl.application.services.run_manifest_service import (
    RunManifestCreateRequest,
    RunManifestService,
)
from bioetl.domain.config.dq import DQConfig
from bioetl.domain.control_plane import (
    ReplayCapability,
    RunArtifactRef,
    RunCodeProvenance,
    RunInputSnapshotRef,
    RunSourceRef,
    RunLedgerEntry,
    RunManifest,
)
from bioetl.domain.types import RunID, RunType
from tests.helpers.control_plane import InMemoryRunLedgerStore, InMemoryRunManifestStore
from bioetl.domain.types.dq_contracts import DQDisposition
from bioetl.domain.control_plane.effective_config_artifact import ConfigSourceRef
from bioetl.domain.control_plane.reproducibility_profiles import (
    build_lineage_closure_boundary,
    build_replay_family_contract,
    resolve_reproducibility_family_profile,
)
from bioetl.domain.normalization import (
    build_execution_identity_payload,
    compute_execution_identity_fingerprint,
)

_FIXED_TIME = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)
_VALID_CONFIG_HASH = "a" * 64
_VALID_RESOLVED_CONFIG_HASH = "b" * 64
_VALID_EFFECTIVE_CONFIG_HASH = "c" * 64
_SNAPSHOT_IDENTITY_FINGERPRINT = (
    "f29f1a5c18e94a4fe614b59ae8e68c5c65afd078155b95d1e7c4aa32f6291dcd"
)
TEST_ROOT = Path(tempfile.mkdtemp(prefix="bioetl-run-manifest-inspection-"))
BRONZE_BATCH_URI = (TEST_ROOT / "bronze" / "batch_1.jsonl.zst").as_uri()
SILVER_ARTIFACT_PATH = str(TEST_ROOT / "output" / "silver" / "chembl" / "activity")
GOLD_DQ_REPORT_PATH = str(TEST_ROOT / "reports" / "gold_dq.json")
COMPOSITE_CV_REPORT_PATH = str(TEST_ROOT / "reports" / "composite_cv.json")


def _expected_canonical_execution_identity(
    manifest: RunManifest,
    *,
    requested_exact_replay: bool,
    snapshot_fingerprint: str | None,
) -> dict[str, object]:
    payload = build_execution_identity_payload(
        pipeline_name=manifest.pipeline_name,
        run_type=manifest.run_type.value,
        pipeline_version=manifest.code_provenance.pipeline_version,
        git_commit=manifest.code_provenance.git_commit,
        effective_config_hash=manifest.code_provenance.effective_config_hash,
        dq_contract_compatibility_hash=(
            manifest.code_provenance.dq_contract_compatibility_hash
        ),
        contract_ref=manifest.code_provenance.contract_ref,
        contract_version=manifest.code_provenance.contract_version,
        effective_config_artifact_id=(
            manifest.code_provenance.effective_config_artifact_id
        ),
        exact_replay=requested_exact_replay,
        input_snapshot_fingerprint=snapshot_fingerprint,
    )
    return {
        "execution_fingerprint": manifest.execution_fingerprint,
        "payload": payload,
    }


def _expected_degraded_runtime_anchor(manifest: RunManifest) -> dict[str, object]:
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


def _expected_code_provenance_state(manifest: RunManifest) -> dict[str, object]:
    return {
        "git_commit": manifest.code_provenance.git_commit,
        "source_revision_state": manifest.code_provenance.source_revision_state,
        "strict_code_provenance_ready": bool(manifest.code_provenance.git_commit),
        "strict_code_provenance_blockers": [],
    }


def _manifest_execution_context(manifest: RunManifest) -> str:
    """Return the effective execution context for a manifest."""
    return (
        "composite"
        if (
            str(manifest.launch_context.get("execution_context") or "") == "composite"
            or manifest.provider == "composite"
        )
        else "source"
    )


def _resolve_checkpoint_policy(
    *,
    requested_exact_replay: bool,
    required_profile: str,
    requested_policy: str | None,
) -> str:
    """Resolve the checkpoint compatibility policy used in expectations."""
    if requested_exact_replay:
        return "hard_fail"
    if required_profile not in {"replay_ready", "forensic_grade"}:
        return requested_policy or "observe"
    if requested_policy in {"observe", "legacy_observe"}:
        return "soft_fail"
    return requested_policy or "soft_fail"


def _resume_contract_layout(
    manifest: RunManifest,
) -> tuple[str, str, str | None]:
    """Return the execution context, resume mode, and occurrence anchor."""
    is_composite = _manifest_execution_context(manifest) == "composite"
    return (
        "composite" if is_composite else "ordinary",
        "checkpoint_snapshot_plus_ledger_suffix"
        if is_composite
        else "checkpoint_snapshot_only",
        "composite_run_identity" if is_composite else None,
    )


def _strict_replay_requested(
    requested_exact_replay: bool,
    required_profile: str,
) -> bool:
    """Return whether the manifest is asking for strict replay semantics."""
    return requested_exact_replay or required_profile in {
        "replay_ready",
        "forensic_grade",
    }


def _expected_resume_contract(manifest: RunManifest) -> dict[str, object]:
    requested_exact_replay = bool(manifest.launch_context.get("exact_replay"))
    required_profile = str(
        manifest.launch_context.get("required_persistence_profile")
        or "degraded_observable"
    )
    requested_policy = manifest.launch_context.get("checkpoint_compatibility_policy")
    if not isinstance(requested_policy, str):
        requested_policy = None
    applied_policy = _resolve_checkpoint_policy(
        requested_exact_replay=requested_exact_replay,
        required_profile=required_profile,
        requested_policy=requested_policy,
    )
    profile = resolve_reproducibility_family_profile(
        provider=manifest.provider,
        entity=manifest.entity,
        contract_ref=manifest.code_provenance.contract_ref,
        execution_context=_manifest_execution_context(manifest),
    )
    execution_context, resume_mode, occurrence_identity_anchor = (
        _resume_contract_layout(manifest)
    )
    strict_replay_requested = _strict_replay_requested(
        requested_exact_replay,
        required_profile,
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
        ),
        "execution_context": execution_context,
        "resume_mode": resume_mode,
        "semantic_identity_anchor": "execution_fingerprint",
        "occurrence_identity_anchor": occurrence_identity_anchor,
    }


def _expected_replay_parentage(manifest: RunManifest) -> dict[str, object]:
    return {
        "is_exact_replay": (
            manifest.replay_of_run_id is not None
            or manifest.replay_of_manifest_id is not None
        ),
        "replay_of_run_id": manifest.replay_of_run_id,
        "replay_of_manifest_id": manifest.replay_of_manifest_id,
    }


def _expected_lineage_closure_boundary(manifest: RunManifest) -> dict[str, object]:
    execution_context = (
        "composite"
        if (
            str(manifest.launch_context.get("execution_context") or "") == "composite"
            or manifest.provider == "composite"
        )
        else "source"
    )
    return build_lineage_closure_boundary(
        provider=manifest.provider,
        entity=manifest.entity,
        contract_ref=manifest.code_provenance.contract_ref,
        execution_context=execution_context,
    )


def _expected_replay_family_contract(manifest: RunManifest) -> dict[str, object]:
    execution_context = (
        "composite"
        if (
            str(manifest.launch_context.get("execution_context") or "") == "composite"
            or manifest.provider == "composite"
        )
        else "source"
    )
    return build_replay_family_contract(
        provider=manifest.provider,
        entity=manifest.entity,
        contract_ref=manifest.code_provenance.contract_ref,
        execution_context=execution_context,
    )


_InMemoryRunManifestStore = InMemoryRunManifestStore
_InMemoryRunLedgerStore = InMemoryRunLedgerStore


def _make_manifest(
    *,
    manifest_id: str,
    run_id: RunID,
    run_type: RunType = RunType.INCREMENTAL,
    config_hash: str = _VALID_CONFIG_HASH,
    resolved_config_hash: str | None = _VALID_RESOLVED_CONFIG_HASH,
    effective_config_hash: str | None = _VALID_EFFECTIVE_CONFIG_HASH,
    limit: int = 100,
    execution_fingerprint: str | None = None,
    created_at: datetime | None = None,
    source_refs: tuple[RunSourceRef, ...] | None = None,
) -> RunManifest:
    return RunManifest(
        manifest_id=manifest_id,
        execution_fingerprint=execution_fingerprint or f"fingerprint-{manifest_id}",
        schema_version="1.0",
        created_at=created_at or _FIXED_TIME,
        run_id=run_id,
        run_type=run_type,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={"limit": limit, "exact_replay": True},
        runtime_config={
            "run_type": run_type.value,
            "limit": limit,
            "exact_replay": True,
        },
        resolved_config={"provider": "chembl", "entity_type": "activity"},
        code_provenance=RunCodeProvenance(
            pipeline_version="1.0.0",
            git_commit="abc1234",
            source_revision_state="clean",
            config_hash=config_hash,
            resolved_config_hash=resolved_config_hash,
            effective_config_hash=effective_config_hash,
            contract_ref="chembl.activity",
            contract_version="1.2.0",
            dq_policy_ref="chembl_activity.gold",
            rule_bundle_version="2026.03",
            dq_contract_compatibility_hash="compat-hash-1",
            effective_config_artifact_id="eca-123",
        ),
        replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED,
        source_refs=source_refs
        or (
            RunSourceRef(
                provider="chembl",
                entity="activity",
                pipeline_name="chembl_activity",
                input_snapshots=(
                    RunInputSnapshotRef(
                        snapshot_id="snapshot-1",
                        content_hash="sha256:snapshot-1",
                        immutable_uri=BRONZE_BATCH_URI,
                        storage_provider="s3",
                        object_bucket="bioetl-bronze",
                        object_key="chembl/activity/batch_1.jsonl.zst",
                        object_version_id="snapshot-version-1",
                    ),
                ),
            ),
        ),
    )


def test_show_resolves_manifest_by_run_id_and_includes_ledger_history() -> None:
    manifest_store = _InMemoryRunManifestStore()
    ledger_store = _InMemoryRunLedgerStore()
    run_id = RunID(uuid4())
    manifest = _make_manifest(manifest_id="manifest-1", run_id=run_id)
    manifest_store.save(manifest)
    ledger_entry = RunLedgerEntry(
        entry_id="entry-1",
        manifest_id="manifest-1",
        run_id=run_id,
        event_type="run_finished",
        occurred_at=_FIXED_TIME,
        status="success",
    )
    ledger_store.append(ledger_entry)
    service = RunManifestInspectionService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
    )

    result = service.show(str(run_id))

    assert result.manifest == manifest
    assert result.ledger_entries == (ledger_entry,)
    assert result.diagnostics["total_events"] == 1
    assert result.diagnostics["latest_event_type"] == "run_finished"
    assert result.diagnostics["latest_status"] == "success"
    assert result.diagnostics["event_family_counts"] == {"pipeline.lifecycle": 1}
    assert result.diagnostics["manifest_id"] == "manifest-1"
    assert result.diagnostics["run_id"] == str(run_id)
    assert result.diagnostics["config_hash"] == _VALID_CONFIG_HASH
    assert result.diagnostics["resolved_config_hash"] == _VALID_RESOLVED_CONFIG_HASH
    assert result.diagnostics["effective_config_hash"] == _VALID_EFFECTIVE_CONFIG_HASH
    assert result.diagnostics["contract_ref"] == "chembl.activity"
    assert result.diagnostics["contract_version"] == "1.2.0"
    assert result.identity_graph == {
        "run_id": str(run_id),
        "manifest_id": "manifest-1",
        "execution_fingerprint": "fingerprint-manifest-1",
        "config_hash": _VALID_CONFIG_HASH,
        "resolved_config_hash": _VALID_RESOLVED_CONFIG_HASH,
        "effective_config_hash": _VALID_EFFECTIVE_CONFIG_HASH,
        "git_commit": "abc1234",
        "source_revision_state": "clean",
        "code_provenance_state": _expected_code_provenance_state(manifest),
        "contract_ref": "chembl.activity",
        "contract_version": "1.2.0",
        "replay_of_run_id": None,
        "replay_of_manifest_id": None,
        "replay_parentage": _expected_replay_parentage(manifest),
        "canonical_execution_identity": _expected_canonical_execution_identity(
            manifest,
            requested_exact_replay=True,
            snapshot_fingerprint=_SNAPSHOT_IDENTITY_FINGERPRINT,
        ),
        "degraded_runtime_anchor": _expected_degraded_runtime_anchor(manifest),
        "replay_capability": "exact_replay_supported",
        "requested_exact_replay": True,
        "exact_replay_support_boundary": "snapshot_backed_source_runs_only",
        "replay_family_contract": _expected_replay_family_contract(manifest),
        "replay_capability_reason": "immutable_input_snapshots_present",
        "exact_replay_eligible": True,
        "exact_replay_blockers": [],
        "append_mode_semantic_sinks": [],
        "resume_contract": _expected_resume_contract(manifest),
        "resume_diagnostics": None,
        "lineage_closure_boundary": _expected_lineage_closure_boundary(manifest),
        "input_snapshot_ids": ["snapshot-1"],
        "input_snapshot_content_hashes": ["sha256:snapshot-1"],
        "input_snapshot_identity_fingerprint": _SNAPSHOT_IDENTITY_FINGERPRINT,
        "replay_mode": "exact_replay",
        "input_snapshot_count": 1,
        "input_snapshots": [
            {
                "provider": "chembl",
                "entity": "activity",
                "pipeline_name": "chembl_activity",
                "query": None,
                "snapshot_id": "snapshot-1",
                "content_hash": "sha256:snapshot-1",
                "immutable_uri": BRONZE_BATCH_URI,
                "query_fingerprint": None,
                "storage_provider": "s3",
                "object_bucket": "bioetl-bronze",
                "object_key": "chembl/activity/batch_1.jsonl.zst",
                "object_version_id": "snapshot-version-1",
                "etag": None,
                "last_modified": None,
                "captured_at": None,
            }
        ],
        "planned_artifacts": [],
        "published_artifacts": [],
        "occurrence_only_diagnostics": [],
    }
    assert result.diagnostics["identity_graph"]["manifest_id"] == "manifest-1"
    assert result.diagnostics["identity_graph"]["run_id"] == str(run_id)
    assert result.diagnostics["identity_graph"]["published_artifacts"] == []
    assert result.diagnostics["alert_signals"] == {
        "run_failed": False,
        "run_shutdown": False,
        "artifact_linkage_gap": False,
        "lineage_gap": False,
        "immutable_input_snapshot_gap": False,
        "strict_replay_boundary_gap": False,
        "lineage_closure_boundary_gap": False,
        "reproducible_semantic_output_mode_gap": False,
        "composite_resume_reconstructability_gap": False,
        "required_persistence_profile_gap": False,
        "replay_ready_gap": False,
        "forensic_grade_gap": False,
        "dq_signal_present": False,
        "cross_validation_signal_present": False,
    }
    assert (
        result.diagnostics["persistence_profile"]["attained_profile"]
        == "forensic_grade"
    )
    assert result.diagnostics["persistence_profile"]["claims"]["forensic_grade"] is True
    assert result.diagnostics["next_steps"] == [
        "No alert signals detected; continue routine monitoring.",
    ]


def _expected_input_snapshots() -> list[dict[str, object]]:
    return [
        {
            "provider": "chembl",
            "entity": "activity",
            "pipeline_name": "chembl_activity",
            "query": None,
            "snapshot_id": "snapshot-1",
            "content_hash": "sha256:snapshot-1",
            "immutable_uri": BRONZE_BATCH_URI,
            "query_fingerprint": None,
            "storage_provider": "s3",
            "object_bucket": "bioetl-bronze",
            "object_key": "chembl/activity/batch_1.jsonl.zst",
            "object_version_id": "snapshot-version-1",
            "etag": None,
            "last_modified": None,
            "captured_at": None,
        }
    ]


def _expected_identity_graph_without_ledger(
    manifest: RunManifest,
    *,
    run_id: RunID,
) -> dict[str, object]:
    return {
        "run_id": str(run_id),
        "manifest_id": "manifest-no-ledger",
        "execution_fingerprint": manifest.execution_fingerprint,
        "config_hash": _VALID_CONFIG_HASH,
        "resolved_config_hash": _VALID_RESOLVED_CONFIG_HASH,
        "effective_config_hash": _VALID_EFFECTIVE_CONFIG_HASH,
        "git_commit": "abc1234",
        "source_revision_state": "clean",
        "code_provenance_state": _expected_code_provenance_state(manifest),
        "contract_ref": "chembl.activity",
        "contract_version": "1.2.0",
        "replay_of_run_id": None,
        "replay_of_manifest_id": None,
        "replay_parentage": _expected_replay_parentage(manifest),
        "canonical_execution_identity": _expected_canonical_execution_identity(
            manifest,
            requested_exact_replay=True,
            snapshot_fingerprint=_SNAPSHOT_IDENTITY_FINGERPRINT,
        ),
        "degraded_runtime_anchor": _expected_degraded_runtime_anchor(manifest),
        "replay_capability": "exact_replay_supported",
        "requested_exact_replay": True,
        "exact_replay_support_boundary": "snapshot_backed_source_runs_only",
        "replay_family_contract": _expected_replay_family_contract(manifest),
        "replay_capability_reason": "immutable_input_snapshots_present",
        "exact_replay_eligible": True,
        "exact_replay_blockers": [],
        "append_mode_semantic_sinks": [],
        "resume_contract": _expected_resume_contract(manifest),
        "resume_diagnostics": None,
        "input_snapshot_ids": ["snapshot-1"],
        "input_snapshot_content_hashes": ["sha256:snapshot-1"],
        "input_snapshot_identity_fingerprint": _SNAPSHOT_IDENTITY_FINGERPRINT,
        "replay_mode": "exact_replay",
        "input_snapshot_count": 1,
        "input_snapshots": _expected_input_snapshots(),
        "planned_artifacts": [],
        "published_artifacts": [],
        "occurrence_only_diagnostics": [],
    }


def _expected_diagnostics_without_ledger(
    manifest: RunManifest,
    *,
    run_id: RunID,
    identity_graph: dict[str, object],
    reproducibility_audit_score: object,
) -> dict[str, object]:
    return {
        "manifest_id": "manifest-no-ledger",
        "manifest_created_at": manifest.created_at.isoformat(),
        "run_id": str(run_id),
        "pipeline_name": "chembl_activity",
        "provider": "chembl",
        "entity": "activity",
        "execution_fingerprint": manifest.execution_fingerprint,
        "config_hash": _VALID_CONFIG_HASH,
        "resolved_config_hash": _VALID_RESOLVED_CONFIG_HASH,
        "effective_config_hash": _VALID_EFFECTIVE_CONFIG_HASH,
        "pipeline_version": "1.0.0",
        "git_commit": "abc1234",
        "source_revision_state": "clean",
        "code_provenance_state": _expected_code_provenance_state(manifest),
        "contract_ref": "chembl.activity",
        "contract_version": "1.2.0",
        "replay_of_run_id": None,
        "replay_of_manifest_id": None,
        "replay_parentage": _expected_replay_parentage(manifest),
        "replay_capability": "exact_replay_supported",
        "required_persistence_profile": "degraded_observable",
        "requested_exact_replay": True,
        "exact_replay_support_boundary": "snapshot_backed_source_runs_only",
        "replay_family_contract": _expected_replay_family_contract(manifest),
        "replay_capability_reason": "immutable_input_snapshots_present",
        "exact_replay_eligible": True,
        "exact_replay_blockers": [],
        "append_mode_semantic_sinks": [],
        "resume_contract": _expected_resume_contract(manifest),
        "resume_diagnostics": None,
        "lineage_closure_boundary": _expected_lineage_closure_boundary(manifest),
        "input_snapshot_ids": ["snapshot-1"],
        "input_snapshot_content_hashes": ["sha256:snapshot-1"],
        "input_snapshot_identity_fingerprint": _SNAPSHOT_IDENTITY_FINGERPRINT,
        "replay_mode": "exact_replay",
        "input_snapshot_count": 1,
        "input_snapshots": _expected_input_snapshots(),
        "dq_policy_ref": "chembl_activity.gold",
        "rule_bundle_version": "2026.03",
        "dq_contract_compatibility_hash": "compat-hash-1",
        "effective_config_artifact_id": "eca-123",
        "planned_artifacts": [],
        "occurrence_only_diagnostics": [],
        "identity_graph": identity_graph,
        "persistence_profile": {
            "attained_profile": "replay_ready",
            "required_profile": "degraded_observable",
            "required_profile_satisfied": True,
            "claims": {
                "degraded_observable": True,
                "replay_ready": True,
                "forensic_grade": False,
            },
            "surfaces": {
                "control_plane_manifest": True,
                "effective_config_artifact": True,
                "strict_replay_execution_context_support": True,
                "immutable_input_snapshots": True,
                "exact_replay_capability": True,
                "reproducible_semantic_output_mode": True,
                "run_ledger_history": False,
                "artifact_lineage_links": True,
                "lineage_closure_boundary_support": True,
            },
            "required_profile_missing_requirements": [],
            "replay_ready_missing_requirements": [],
            "forensic_grade_missing_requirements": ["run_ledger_history"],
            "composite_resume_reconstructability": {
                "scope": "coarse_grained_composite_resume",
                "resume_model": "checkpoint_snapshot_plus_ledger_suffix",
                "reconstructs": [
                    "state",
                    "seed_completed",
                    "merge_completed",
                    "last_event_id",
                    "last_event_occurred_at",
                ],
                "does_not_reconstruct": [
                    "per_provider_result_maps",
                    "rich_checkpoint_payloads",
                ],
                "forensic_grade_supported": True,
            },
            "lineage_closure_boundary": _expected_lineage_closure_boundary(manifest),
        },
        "alert_signals": {
            "run_failed": False,
            "run_shutdown": False,
            "artifact_linkage_gap": False,
            "lineage_gap": False,
            "immutable_input_snapshot_gap": False,
            "strict_replay_boundary_gap": False,
            "lineage_closure_boundary_gap": False,
            "reproducible_semantic_output_mode_gap": False,
            "composite_resume_reconstructability_gap": False,
            "required_persistence_profile_gap": False,
            "replay_ready_gap": False,
            "forensic_grade_gap": True,
            "dq_signal_present": False,
            "cross_validation_signal_present": False,
        },
        "next_steps": [
            "Review forensic-grade persistence requirements before using this run for full trace/debug reconstruction."
        ],
        "reproducibility_audit_score": reproducibility_audit_score,
    }


def test_show_by_manifest_id_without_ledger_port_returns_base_summary() -> None:
    manifest_store = _InMemoryRunManifestStore()
    run_id = RunID(uuid4())
    manifest = _make_manifest(manifest_id="manifest-no-ledger", run_id=run_id)
    manifest_store.save(manifest)
    service = RunManifestInspectionService(manifest_port=manifest_store)
    result = service.show("manifest-no-ledger")
    assert result.manifest == manifest
    assert result.ledger_entries == ()
    assert result.identity_graph == _expected_identity_graph_without_ledger(
        manifest,
        run_id=run_id,
    )
    assert (
        result.diagnostics["persistence_profile"]["attained_profile"] == "replay_ready"
    )
    assert result.diagnostics["persistence_profile"]["claims"]["replay_ready"] is True
    assert result.diagnostics["persistence_profile"][
        "forensic_grade_missing_requirements"
    ] == ["run_ledger_history"]
    assert result.diagnostics == _expected_diagnostics_without_ledger(
        manifest,
        run_id=run_id,
        identity_graph=result.identity_graph,
        reproducibility_audit_score=result.diagnostics["reproducibility_audit_score"],
    )


def test_show_resume_only_manifest_reports_resume_mode() -> None:
    manifest_store = _InMemoryRunManifestStore()
    run_id = RunID(uuid4())
    manifest = replace(
        _make_manifest(manifest_id="manifest-resume", run_id=run_id),
        launch_context={"limit": 100, "resume": True, "exact_replay": False},
        runtime_config={"run_type": "incremental", "limit": 100},
        replay_capability=ReplayCapability.RESUME_ONLY,
        source_refs=(),
    )
    manifest_store.save(manifest)
    service = RunManifestInspectionService(manifest_port=manifest_store)

    result = service.show("manifest-resume")

    assert result.diagnostics["replay_capability"] == "resume_only"
    assert result.diagnostics["requested_exact_replay"] is False
    assert (
        result.diagnostics["exact_replay_support_boundary"]
        == "snapshot_backed_source_runs_only"
    )
    assert result.diagnostics[
        "replay_family_contract"
    ] == _expected_replay_family_contract(manifest)
    assert (
        result.diagnostics["replay_capability_reason"]
        == "resume_requested_without_snapshot_backed_inputs"
    )
    assert result.diagnostics["exact_replay_eligible"] is False
    assert result.diagnostics["exact_replay_blockers"] == [
        "immutable_input_snapshots_missing"
    ]
    assert result.diagnostics["input_snapshot_ids"] == []
    assert result.diagnostics["input_snapshot_content_hashes"] == []
    assert result.diagnostics["input_snapshot_identity_fingerprint"] is None
    assert result.diagnostics["replay_mode"] == "resume"
    assert result.identity_graph["replay_capability"] == "resume_only"
    assert result.identity_graph["requested_exact_replay"] is False
    assert (
        result.identity_graph["exact_replay_support_boundary"]
        == "snapshot_backed_source_runs_only"
    )
    assert result.identity_graph[
        "replay_family_contract"
    ] == _expected_replay_family_contract(manifest)
    assert (
        result.identity_graph["replay_capability_reason"]
        == "resume_requested_without_snapshot_backed_inputs"
    )
    assert result.identity_graph["replay_mode"] == "resume"
    assert result.identity_graph["resume_contract"] == _expected_resume_contract(
        manifest
    )
    assert result.identity_graph["resume_diagnostics"] is None
    assert result.identity_graph["exact_replay_blockers"] == [
        "immutable_input_snapshots_missing"
    ]


def test_diff_distinguishes_exact_replay_ancestry_from_semantic_equality() -> None:
    store = _InMemoryRunManifestStore()
    parent_run_id = RunID(uuid4())
    child_run_id = RunID(uuid4())
    parent = _make_manifest(
        manifest_id="manifest-parent",
        run_id=parent_run_id,
        execution_fingerprint="fp-stable",
    )
    child = replace(
        _make_manifest(
            manifest_id="manifest-child",
            run_id=child_run_id,
            execution_fingerprint="fp-stable",
        ),
        replay_of_run_id=str(parent_run_id),
        replay_of_manifest_id="manifest-parent",
    )
    store.save(parent)
    store.save(child)
    service = RunManifestInspectionService(manifest_port=store)

    result = service.diff("manifest-parent", "manifest-child")

    assert result.classification == "semantic_equivalent_with_noncanonical_differences"
    assert result.semantic_equivalent is True
    assert result.replay_relationship == "right_is_exact_replay_of_left"


def test_show_surfaces_persisted_resume_diagnostics() -> None:
    manifest_store = _InMemoryRunManifestStore()
    ledger_store = _InMemoryRunLedgerStore()
    run_id = RunID(uuid4())
    manifest = _make_manifest(manifest_id="manifest-resume-diagnostics", run_id=run_id)
    manifest_store.save(manifest)
    ledger_store.append(
        RunLedgerEntry(
            entry_id="entry-resume-rejected",
            manifest_id=manifest.manifest_id,
            run_id=run_id,
            event_type="checkpoint_resume_rejected",
            event_family="pipeline.lifecycle",
            occurred_at=_FIXED_TIME,
            status="rejected",
            details={
                "compatibility_disposition": "hard_fail",
                "resume_rejected": True,
                "execution_identity_compatible": False,
                "messages": ["execution identity mismatch"],
                "current_identity": {
                    "execution_fingerprint": manifest.execution_fingerprint,
                    "composite_run_identity": "current-identity",
                },
                "checkpoint_identity": {
                    "execution_fingerprint": manifest.execution_fingerprint,
                    "composite_run_identity": "checkpoint-identity",
                },
            },
        )
    )
    service = RunManifestInspectionService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
    )

    result = service.show("manifest-resume-diagnostics")

    assert result.diagnostics["resume_contract"] == _expected_resume_contract(manifest)
    assert result.diagnostics["resume_diagnostics"] == {
        "source_event_type": "checkpoint_resume_rejected",
        "source_status": "rejected",
        "compatibility_disposition": "hard_fail",
        "resume_rejected": True,
        "execution_identity_compatible": False,
        "messages": ["execution identity mismatch"],
        "current_identity": {
            "execution_fingerprint": manifest.execution_fingerprint,
            "composite_run_identity": "current-identity",
        },
        "checkpoint_identity": {
            "execution_fingerprint": manifest.execution_fingerprint,
            "composite_run_identity": "checkpoint-identity",
        },
    }
    assert result.identity_graph["resume_contract"] == _expected_resume_contract(
        manifest
    )
    assert (
        result.identity_graph["resume_diagnostics"]
        == result.diagnostics["resume_diagnostics"]
    )


def test_show_composite_manifest_surfaces_bounded_reconstructability_contract() -> None:
    manifest_store = _InMemoryRunManifestStore()
    run_id = RunID(uuid4())
    manifest = replace(
        _make_manifest(manifest_id="manifest-composite", run_id=run_id),
        provider="composite",
        entity="publications",
        pipeline_name="publications",
        launch_context={
            "resume": False,
            "exact_replay": False,
            "execution_context": "composite",
            "exact_replay_support_boundary": "composite_snapshot_backed_input_envelope",
        },
        runtime_config={"run_type": "incremental"},
        resolved_config={"composite": "publications"},
        replay_capability=ReplayCapability.REBUILD_ONLY,
        source_refs=(),
    )
    manifest_store.save(manifest)
    service = RunManifestInspectionService(manifest_port=manifest_store)

    result = service.show("manifest-composite")

    assert result.diagnostics["exact_replay_support_boundary"] == (
        "composite_snapshot_backed_input_envelope"
    )
    assert result.diagnostics[
        "replay_family_contract"
    ] == _expected_replay_family_contract(manifest)
    assert (
        result.diagnostics["alert_signals"]["composite_resume_reconstructability_gap"]
        is True
    )
    assert (
        result.diagnostics["persistence_profile"][
            "composite_resume_reconstructability"
        ]["scope"]
        == "coarse_grained_composite_resume"
    )
    assert any(
        "Treat composite resume as checkpoint snapshot plus ledger suffix replay only;"
        in step
        for step in result.diagnostics["next_steps"]
    )
    assert result.identity_graph["input_snapshot_ids"] == []
    assert result.identity_graph["input_snapshot_content_hashes"] == []
    assert result.identity_graph["input_snapshot_identity_fingerprint"] is None
    assert result.identity_graph["input_snapshot_count"] == 0


def test_show_snapshot_backed_manifest_reports_non_replay_snapshot_mode() -> None:
    manifest_store = _InMemoryRunManifestStore()
    run_id = RunID(uuid4())
    manifest = replace(
        _make_manifest(manifest_id="manifest-snapshot-backed", run_id=run_id),
        launch_context={"limit": 100, "resume": False, "exact_replay": False},
        replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED,
        source_refs=(
            RunSourceRef(
                provider="chembl",
                entity="activity",
                pipeline_name="chembl_activity",
                input_snapshots=(
                    RunInputSnapshotRef(
                        snapshot_id="snapshot-1",
                        content_hash="sha256:snapshot-1",
                        immutable_uri=BRONZE_BATCH_URI,
                    ),
                ),
            ),
        ),
    )
    manifest_store.save(manifest)
    service = RunManifestInspectionService(manifest_port=manifest_store)

    result = service.show("manifest-snapshot-backed")

    assert result.diagnostics["replay_capability"] == "exact_replay_supported"
    assert result.diagnostics["requested_exact_replay"] is False
    assert result.diagnostics["exact_replay_eligible"] is True
    assert result.diagnostics["replay_mode"] == "same_data_state_recovery"
    assert result.identity_graph["requested_exact_replay"] is False
    assert result.identity_graph["replay_mode"] == "same_data_state_recovery"
    assert result.diagnostics[
        "replay_family_contract"
    ] == _expected_replay_family_contract(manifest)
    assert result.identity_graph[
        "replay_family_contract"
    ] == _expected_replay_family_contract(manifest)


def test_show_does_not_report_exact_replay_from_intent_alone() -> None:
    manifest_store = _InMemoryRunManifestStore()
    run_id = RunID(uuid4())
    manifest = replace(
        _make_manifest(manifest_id="manifest-requested-replay", run_id=run_id),
        launch_context={"limit": 100, "resume": False, "exact_replay": True},
        replay_capability=ReplayCapability.REBUILD_ONLY,
        source_refs=(),
    )
    manifest_store.save(manifest)
    service = RunManifestInspectionService(manifest_port=manifest_store)

    result = service.show("manifest-requested-replay")

    assert result.diagnostics["requested_exact_replay"] is True
    assert result.diagnostics["exact_replay_eligible"] is False
    assert result.diagnostics["replay_mode"] == "rebuild"
    assert result.identity_graph["requested_exact_replay"] is True
    assert result.identity_graph["replay_mode"] == "rebuild"
    assert result.diagnostics[
        "replay_family_contract"
    ] == _expected_replay_family_contract(manifest)
    assert result.identity_graph[
        "replay_family_contract"
    ] == _expected_replay_family_contract(manifest)


def test_show_collects_artifact_diagnostic_links() -> None:
    manifest_store = _InMemoryRunManifestStore()
    ledger_store = _InMemoryRunLedgerStore()
    run_id = RunID(uuid4())
    manifest = _make_manifest(manifest_id="manifest-2", run_id=run_id)
    manifest_store.save(manifest)
    ledger_store.append(
        RunLedgerEntry(
            entry_id="entry-1",
            manifest_id="manifest-2",
            run_id=run_id,
            event_type="artifact_published",
            occurred_at=_FIXED_TIME,
            status="published",
            stage="silver",
            dataset_ref="silver:chembl.activity@1",
            lineage_fragment_id="silver:fragment-1",
            details={"artifact_path": SILVER_ARTIFACT_PATH},
        )
    )
    service = RunManifestInspectionService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
    )

    result = service.show("manifest-2")

    assert result.diagnostics["event_family_counts"] == {"artifact": 1}
    assert result.diagnostics["lineage_fragment_ids"] == ["silver:fragment-1"]
    assert result.diagnostics["missing_artifact_links"] == 0
    assert result.diagnostics["alert_signals"] == {
        "run_failed": False,
        "run_shutdown": False,
        "artifact_linkage_gap": False,
        "lineage_gap": False,
        "immutable_input_snapshot_gap": False,
        "strict_replay_boundary_gap": False,
        "lineage_closure_boundary_gap": False,
        "reproducible_semantic_output_mode_gap": False,
        "composite_resume_reconstructability_gap": False,
        "required_persistence_profile_gap": False,
        "replay_ready_gap": False,
        "forensic_grade_gap": False,
        "dq_signal_present": False,
        "cross_validation_signal_present": False,
    }
    assert result.diagnostics["artifact_refs"] == [
        {
            "event_type": "artifact_published",
            "stage": "silver",
            "artifact_id": "silver:chembl.activity@1",
            "dataset_ref": "silver:chembl.activity@1",
            "lineage_fragment_id": "silver:fragment-1",
            "artifact_path": SILVER_ARTIFACT_PATH,
        }
    ]
    assert result.identity_graph == result.diagnostics["identity_graph"]
    assert result.diagnostics["identity_graph"]["published_artifacts"] == [
        {
            "event_type": "artifact_published",
            "stage": "silver",
            "artifact_id": "silver:chembl.activity@1",
            "dataset_ref": "silver:chembl.activity@1",
            "lineage_fragment_id": "silver:fragment-1",
            "artifact_path": SILVER_ARTIFACT_PATH,
        }
    ]


def test_show_marks_artifact_linkage_gap_signal() -> None:
    manifest_store = _InMemoryRunManifestStore()
    ledger_store = _InMemoryRunLedgerStore()
    run_id = RunID(uuid4())
    manifest = _make_manifest(manifest_id="manifest-3", run_id=run_id)
    manifest_store.save(manifest)
    ledger_store.append(
        RunLedgerEntry(
            entry_id="entry-1",
            manifest_id="manifest-3",
            run_id=run_id,
            event_type="artifact_published",
            occurred_at=_FIXED_TIME,
            status="published",
            stage="silver",
            details={"artifact_path": SILVER_ARTIFACT_PATH},
        )
    )
    service = RunManifestInspectionService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
    )

    result = service.show("manifest-3")

    assert result.diagnostics["missing_artifact_links"] == 1
    assert (
        result.diagnostics["persistence_profile"]["attained_profile"] == "replay_ready"
    )
    assert (
        result.diagnostics["persistence_profile"]["claims"]["forensic_grade"] is False
    )
    assert result.diagnostics["alert_signals"]["artifact_linkage_gap"] is True
    assert result.diagnostics["next_steps"] == [
        "Validate artifact publication metadata and repair dataset/lineage links.",
        "Investigate lineage persistence for published artifacts before restart.",
        "Review forensic-grade persistence requirements before using this run for full trace/debug reconstruction.",
    ]


@pytest.mark.parametrize(
    (
        "dataset_ref",
        "lineage_fragment_id",
        "expected_missing_links",
        "expected_lineage_gap",
    ),
    [
        (None, "silver:fragment-1", 0, False),
        ("silver:chembl.activity@1", None, 0, True),
    ],
)
def test_show_distinguishes_partial_artifact_anchor_gaps(
    dataset_ref: str | None,
    lineage_fragment_id: str | None,
    expected_missing_links: int,
    expected_lineage_gap: bool,
) -> None:
    manifest_store = _InMemoryRunManifestStore()
    ledger_store = _InMemoryRunLedgerStore()
    run_id = RunID(uuid4())
    manifest = _make_manifest(manifest_id="manifest-partial-gap", run_id=run_id)
    manifest_store.save(manifest)
    ledger_store.append(
        RunLedgerEntry(
            entry_id="entry-1",
            manifest_id="manifest-partial-gap",
            run_id=run_id,
            event_type="artifact_published",
            occurred_at=_FIXED_TIME,
            status="published",
            stage="silver",
            dataset_ref=dataset_ref,
            lineage_fragment_id=lineage_fragment_id,
            details={"artifact_path": SILVER_ARTIFACT_PATH},
        )
    )
    service = RunManifestInspectionService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
    )

    result = service.show("manifest-partial-gap")

    assert result.diagnostics["missing_artifact_links"] == expected_missing_links
    assert result.diagnostics["alert_signals"]["artifact_linkage_gap"] is False
    assert result.diagnostics["alert_signals"]["lineage_gap"] is expected_lineage_gap


def test_show_collects_dq_trace_anchors() -> None:
    manifest_store = _InMemoryRunManifestStore()
    ledger_store = _InMemoryRunLedgerStore()
    run_id = RunID(uuid4())
    manifest = _make_manifest(manifest_id="manifest-dq", run_id=run_id)
    manifest_store.save(manifest)
    ledger_store.append(
        RunLedgerEntry(
            entry_id="entry-1",
            manifest_id="manifest-dq",
            run_id=run_id,
            event_type="dq_policy_applied",
            occurred_at=_FIXED_TIME,
            event_family="dq",
            status="failed",
            stage="gold",
            details={
                "rule_id": "gold.not_null.id",
                "disposition": "fail",
                "dq_report_path": GOLD_DQ_REPORT_PATH,
            },
        )
    )
    service = RunManifestInspectionService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
    )

    result = service.show("manifest-dq")

    assert result.diagnostics["dq_rule_ids"] == ["gold.not_null.id"]
    assert result.diagnostics["dq_dispositions"] == ["fail"]
    assert result.diagnostics["dq_report_paths"] == [GOLD_DQ_REPORT_PATH]
    assert result.diagnostics["dq_policy_ref"] == "chembl_activity.gold"
    assert result.diagnostics["rule_bundle_version"] == "2026.03"
    assert result.diagnostics["effective_config_artifact_id"] == "eca-123"
    assert result.diagnostics["dq_violation_kinds"] == []
    assert result.diagnostics["cross_validation_rule_ids"] == []
    assert result.diagnostics["cross_validation_config_paths"] == []
    assert result.diagnostics["alert_signals"] == {
        "run_failed": True,
        "run_shutdown": False,
        "artifact_linkage_gap": False,
        "lineage_gap": False,
        "immutable_input_snapshot_gap": False,
        "strict_replay_boundary_gap": False,
        "lineage_closure_boundary_gap": False,
        "reproducible_semantic_output_mode_gap": False,
        "composite_resume_reconstructability_gap": False,
        "required_persistence_profile_gap": False,
        "replay_ready_gap": False,
        "forensic_grade_gap": False,
        "dq_signal_present": True,
        "cross_validation_signal_present": False,
    }
    assert result.diagnostics["next_steps"] == [
        "Inspect failure classification and decide retry/quarantine/escalation.",
        "Review DQ report artifacts, rule IDs, and contract policy anchors before retry or escalation.",
    ]


def test_diff_reports_changed_top_level_fields() -> None:
    manifest_store = _InMemoryRunManifestStore()
    left_run_id = RunID(uuid4())
    right_run_id = RunID(uuid4())
    left = _make_manifest(
        manifest_id="manifest-left",
        run_id=left_run_id,
        run_type=RunType.INCREMENTAL,
        config_hash="hash-left",
        limit=100,
    )
    right = _make_manifest(
        manifest_id="manifest-right",
        run_id=right_run_id,
        run_type=RunType.REBUILD,
        config_hash="hash-right",
        limit=500,
    )
    manifest_store.save(left)
    manifest_store.save(right)
    service = RunManifestInspectionService(manifest_port=manifest_store)

    result = service.diff("manifest-left", "manifest-right")

    diff_fields = {entry.field for entry in result.differences}
    assert result.left_manifest_id == "manifest-left"
    assert result.right_manifest_id == "manifest-right"
    assert result.classification == "semantic_drift"
    assert result.semantic_equivalent is False
    assert result.occurrence_only is False
    assert "run_type" in result.semantic_difference_fields
    assert "manifest_id" in diff_fields
    assert "run_id" in diff_fields
    assert "run_type" in diff_fields
    assert "launch_context" in diff_fields
    assert "runtime_config" in diff_fields
    assert "code_provenance" in diff_fields


def test_diff_classifies_occurrence_only_replay_runs() -> None:
    manifest_store = _InMemoryRunManifestStore()
    created_at = datetime(2025, 1, 1, tzinfo=UTC)
    left = _make_manifest(
        manifest_id="manifest-left",
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000201")),
        execution_fingerprint="fingerprint-same",
        created_at=created_at,
    )
    right = _make_manifest(
        manifest_id="manifest-right",
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000202")),
        execution_fingerprint="fingerprint-same",
        created_at=created_at,
    )
    manifest_store.save(left)
    manifest_store.save(right)
    service = RunManifestInspectionService(manifest_port=manifest_store)

    result = service.diff("manifest-left", "manifest-right")

    assert result.classification == "occurrence_only"
    assert result.semantic_equivalent is True
    assert result.occurrence_only is True
    assert result.occurrence_difference_fields == ("manifest_id", "run_id")
    assert result.semantic_difference_fields == ()
    assert result.noncanonical_difference_fields == ()


def test_diff_classifies_semantic_equivalent_noncanonical_differences() -> None:
    manifest_store = _InMemoryRunManifestStore()
    created_at = datetime(2025, 1, 1, tzinfo=UTC)
    shared_fingerprint = "fingerprint-same"
    left = _make_manifest(
        manifest_id="manifest-left",
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000203")),
        execution_fingerprint=shared_fingerprint,
        created_at=created_at,
        source_refs=(
            RunSourceRef(
                provider="chembl",
                entity="activity",
                pipeline_name="chembl_activity",
                query="fixture://a",
            ),
            RunSourceRef(
                provider="pubchem",
                entity="activity",
                pipeline_name="chembl_activity",
                query="fixture://b",
            ),
        ),
    )
    right = _make_manifest(
        manifest_id="manifest-right",
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000204")),
        execution_fingerprint=shared_fingerprint,
        created_at=created_at,
        source_refs=tuple(reversed(left.source_refs)),
    )
    manifest_store.save(left)
    manifest_store.save(right)
    service = RunManifestInspectionService(manifest_port=manifest_store)

    result = service.diff("manifest-left", "manifest-right")

    assert result.classification == "semantic_equivalent_with_noncanonical_differences"
    assert result.semantic_equivalent is True
    assert result.occurrence_only is False
    assert result.noncanonical_difference_fields == ("source_refs",)


def test_control_plane_chain_surfaces_effective_config_and_artifact_links() -> None:
    manifest_store = _InMemoryRunManifestStore()
    ledger_store = _InMemoryRunLedgerStore()
    run_id = RunID(UUID("00000000-0000-0000-0000-000000000101"))

    effective_config_service = EffectiveConfigService()
    artifact = effective_config_service.create_effective_config_artifact(
        pipeline_name="chembl_activity",
        pipeline_kind="standard",
        resolved_config={"provider": "chembl", "entity_type": "activity"},
        runtime_overrides={"cli": {"limit": 25}},
        source_refs=[
            ConfigSourceRef(
                source_type="fixture",
                source_path="tests/fixtures/bronze/chembl/activity/sample.jsonl",
                source_hash="fixture-hash-1",
                priority=1,
            )
        ],
        dq_config=DQConfig(
            contract_ref="chembl.activity",
            contract_version="1.0.0",
            rule_bundle_version="dq-rules.v1",
            default_disposition_policy=DQDisposition.WARN,
        ),
        artifact_id="eca-chain-1",
    )
    manifest_service = RunManifestService(
        manifest_port=manifest_store,
        _manifest_id_factory=lambda: "manifest-chain-1",
    )
    manifest = manifest_service.create_manifest(
        RunManifestCreateRequest(
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            pipeline_name="chembl_activity",
            provider="chembl",
            entity="activity",
            launch_context={
                "fixture_path": "tests/fixtures/bronze/chembl/activity/sample.jsonl"
            },
            runtime_config={"run_type": "incremental", "limit": 25},
            resolved_config=artifact.effective_execution_config.config_data,
            source_refs=(
                RunSourceRef(
                    provider="chembl",
                    entity="activity",
                    pipeline_name="chembl_activity",
                    query="fixture://sample",
                ),
            ),
            planned_artifacts=(
                RunArtifactRef(
                    layer="silver",
                    path="data/output/silver/chembl/activity",
                ),
            ),
            pipeline_version="1.0.0",
            git_commit="abc1234",
            config_hash=artifact.resolved_config_hash,
            resolved_config_hash=artifact.resolved_config_hash,
            effective_config_hash=artifact.effective_config_hash,
            contract_ref="chembl.activity",
            contract_version="1.0.0",
            dq_policy_ref="chembl.activity.dq",
            rule_bundle_version="dq-rules.v1",
            dq_contract_compatibility_hash=artifact.dq_contract_compatibility_hash,
            effective_config_artifact_id=artifact.artifact_id,
        )
    )
    ledger_service = RunLedgerService(
        ledger_port=ledger_store,
        manifest_id=manifest.manifest_id,
        run_id=run_id,
        _entry_id_factory=lambda: "entry-chain-1",
    )
    ledger_service.record_manifest_created(manifest)
    ledger_service.record_artifact_published(
        layer="silver",
        artifact_path="data/output/silver/chembl/activity",
        dataset_ref="silver:chembl.activity@1",
        lineage_fragment_id="silver:fragment-chain-1",
        details={
            "dq_report_path": "data/output/silver/chembl/activity/_dq.json",
            "metadata_path": "data/output/silver/chembl/activity/_metadata.yaml",
        },
    )

    service = RunManifestInspectionService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
    )
    result = service.show(manifest.manifest_id)

    assert result.manifest.code_provenance.config_hash == artifact.resolved_config_hash
    assert (
        result.manifest.code_provenance.effective_config_hash
        == artifact.effective_config_hash
    )
    assert result.identity_graph == result.diagnostics["identity_graph"]
    assert result.diagnostics["config_hash"] == artifact.resolved_config_hash
    assert result.diagnostics["resolved_config_hash"] == artifact.resolved_config_hash
    assert result.diagnostics["effective_config_hash"] == artifact.effective_config_hash
    assert result.diagnostics["effective_config_artifact_id"] == "eca-chain-1"
    assert result.diagnostics["artifact_refs"] == [
        {
            "event_type": "artifact_published",
            "stage": "silver",
            "artifact_id": "silver:chembl.activity@1",
            "dataset_ref": "silver:chembl.activity@1",
            "lineage_fragment_id": "silver:fragment-chain-1",
            "artifact_path": "data/output/silver/chembl/activity",
            "metadata_path": "data/output/silver/chembl/activity/_metadata.yaml",
        }
    ]
    assert result.diagnostics["correlation_anchor_gaps"] == {
        "effective_config_hash": 0,
        "resolved_config_hash": 0,
        "contract_ref": 0,
        "contract_version": 0,
        "composite_run_id": 0,
    }
    assert result.diagnostics["dq_report_paths"] == [
        "data/output/silver/chembl/activity/_dq.json"
    ]


def test_control_plane_chain_surfaces_lifecycle_smoke_summary() -> None:
    manifest_store = _InMemoryRunManifestStore()
    ledger_store = _InMemoryRunLedgerStore()
    run_id = RunID(UUID("00000000-0000-0000-0000-000000000103"))

    manifest_service = RunManifestService(
        manifest_port=manifest_store,
        _manifest_id_factory=lambda: "manifest-chain-smoke",
    )
    manifest = manifest_service.create_manifest(
        RunManifestCreateRequest(
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            pipeline_name="chembl_activity",
            provider="chembl",
            entity="activity",
            launch_context={"limit": 25},
            runtime_config={"run_type": "incremental", "limit": 25},
            resolved_config={"provider": "chembl", "entity_type": "activity"},
            pipeline_version="1.0.0",
            git_commit="abc1234",
            config_hash="a" * 64,
            resolved_config_hash="b" * 64,
            effective_config_hash="c" * 64,
            contract_ref="chembl.activity",
            contract_version="1.0.0",
            dq_policy_ref="chembl.activity.dq",
            rule_bundle_version="dq-rules.v1",
            dq_contract_compatibility_hash="compat-hash-smoke",
            effective_config_artifact_id="eca-smoke-1",
        )
    )
    ledger_service = RunLedgerService(
        ledger_port=ledger_store,
        manifest_id=manifest.manifest_id,
        run_id=run_id,
        _entry_id_factory=lambda: f"entry-smoke-{len(ledger_store.items) + 1}",
    )
    ledger_service.record_manifest_created(manifest)
    ledger_service.record_run_started()
    ledger_service.record_stage_started(
        stage="execute_pipeline",
        details={"records": 5},
    )
    ledger_service.record_stage_completed(
        stage="execute_pipeline",
        metrics_snapshot={"records_bronze": 5},
        details={"result": "ok"},
    )
    ledger_service.record_artifact_published(
        layer="silver",
        artifact_path="data/output/silver/chembl/activity",
        dataset_ref="silver:chembl.activity@1",
        lineage_fragment_id="silver:fragment-smoke-1",
    )
    ledger_service.record_run_finished(metrics_snapshot={"records_silver": 5})

    service = RunManifestInspectionService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
    )
    result = service.show(manifest.manifest_id)

    assert result.diagnostics["total_events"] == 6
    assert result.diagnostics["latest_event_type"] == "run_finished"
    assert result.diagnostics["latest_status"] == "success"
    assert result.diagnostics["event_family_counts"] == {
        "artifact": 1,
        "diagnostic": 1,
        "pipeline.lifecycle": 2,
        "pipeline.phase": 2,
    }
    assert result.diagnostics["event_type_counts"] == {
        "artifact_published": 1,
        "manifest_created": 1,
        "run_finished": 1,
        "run_started": 1,
        "stage_completed": 1,
        "stage_started": 1,
    }
    assert result.diagnostics["missing_artifact_links"] == 0
    assert result.diagnostics["alert_signals"] == {
        "run_failed": False,
        "run_shutdown": False,
        "artifact_linkage_gap": False,
        "lineage_gap": False,
        "immutable_input_snapshot_gap": True,
        "strict_replay_boundary_gap": False,
        "lineage_closure_boundary_gap": False,
        "reproducible_semantic_output_mode_gap": False,
        "composite_resume_reconstructability_gap": False,
        "required_persistence_profile_gap": False,
        "replay_ready_gap": True,
        "forensic_grade_gap": True,
        "dq_signal_present": False,
        "cross_validation_signal_present": False,
    }
    assert result.diagnostics["next_steps"] == [
        "Persist immutable cached Bronze input snapshots before treating this run as strict exact-replay capable.",
        "Review replay-ready persistence requirements before treating this run as exact-replay capable.",
        "Review forensic-grade persistence requirements before using this run for full trace/debug reconstruction.",
    ]
    assert result.diagnostics["correlation_anchor_gaps"] == {
        "effective_config_hash": 0,
        "resolved_config_hash": 0,
        "contract_ref": 0,
        "contract_version": 0,
        "composite_run_id": 0,
    }


def test_control_plane_chain_surfaces_dq_failure_traceability() -> None:
    manifest_store = _InMemoryRunManifestStore()
    ledger_store = _InMemoryRunLedgerStore()
    run_id = RunID(UUID("00000000-0000-0000-0000-000000000102"))

    effective_config_service = EffectiveConfigService()
    artifact = effective_config_service.create_effective_config_artifact(
        pipeline_name="chembl_activity",
        pipeline_kind="standard",
        resolved_config={"provider": "chembl", "entity_type": "activity"},
        runtime_overrides={"cli": {"limit": 25}},
        source_refs=[
            ConfigSourceRef(
                source_type="fixture",
                source_path="tests/fixtures/bronze/chembl/activity/sample.jsonl",
                source_hash="fixture-hash-1",
                priority=1,
            )
        ],
        dq_config=DQConfig(
            contract_ref="chembl.activity",
            contract_version="1.0.0",
            rule_bundle_version="dq-rules.v1",
            default_disposition_policy=DQDisposition.FAIL,
        ),
        artifact_id="eca-chain-2",
    )
    manifest_service = RunManifestService(
        manifest_port=manifest_store,
        _manifest_id_factory=lambda: "manifest-chain-2",
    )
    manifest = manifest_service.create_manifest(
        RunManifestCreateRequest(
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            pipeline_name="chembl_activity",
            provider="chembl",
            entity="activity",
            launch_context={
                "fixture_path": "tests/fixtures/bronze/chembl/activity/sample.jsonl"
            },
            runtime_config={"run_type": "incremental", "limit": 25},
            resolved_config=artifact.effective_execution_config.config_data,
            source_refs=(
                RunSourceRef(
                    provider="chembl",
                    entity="activity",
                    pipeline_name="chembl_activity",
                    query="fixture://sample",
                ),
            ),
            pipeline_version="1.0.0",
            git_commit="abc1234",
            config_hash=artifact.resolved_config_hash,
            resolved_config_hash=artifact.resolved_config_hash,
            effective_config_hash=artifact.effective_config_hash,
            contract_ref="chembl.activity",
            contract_version="1.0.0",
            dq_policy_ref="chembl.activity.dq",
            rule_bundle_version="dq-rules.v1",
            dq_contract_compatibility_hash=artifact.dq_contract_compatibility_hash,
            effective_config_artifact_id=artifact.artifact_id,
        )
    )
    ledger_service = RunLedgerService(
        ledger_port=ledger_store,
        manifest_id=manifest.manifest_id,
        run_id=run_id,
        _entry_id_factory=lambda: "entry-chain-2",
    )
    ledger_service.record_dq_policy_applied(
        stage="gold",
        rule_id="gold.not_null.id",
        disposition=DQDisposition.FAIL,
        dq_report_path="data/output/gold/chembl/activity/_dq.json",
    )

    service = RunManifestInspectionService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
    )
    result = service.show(manifest.manifest_id)

    assert result.manifest.code_provenance.config_hash == artifact.resolved_config_hash
    assert (
        result.manifest.code_provenance.effective_config_hash
        == artifact.effective_config_hash
    )
    assert result.diagnostics["contract_version"] == "1.0.0"
    assert result.diagnostics["dq_policy_ref"] == "chembl.activity.dq"
    assert result.diagnostics["rule_bundle_version"] == "dq-rules.v1"
    assert result.diagnostics["effective_config_artifact_id"] == "eca-chain-2"
    assert result.diagnostics["dq_rule_ids"] == ["gold.not_null.id"]
    assert result.diagnostics["dq_dispositions"] == ["fail"]
    assert result.diagnostics["dq_report_paths"] == [
        "data/output/gold/chembl/activity/_dq.json"
    ]
    assert result.diagnostics["dq_violation_kinds"] == []
    assert result.diagnostics["cross_validation_rule_ids"] == []
    assert result.diagnostics["cross_validation_config_paths"] == []
    assert result.diagnostics["alert_signals"] == {
        "run_failed": True,
        "run_shutdown": False,
        "artifact_linkage_gap": False,
        "lineage_gap": False,
        "immutable_input_snapshot_gap": True,
        "strict_replay_boundary_gap": False,
        "lineage_closure_boundary_gap": False,
        "reproducible_semantic_output_mode_gap": False,
        "composite_resume_reconstructability_gap": False,
        "required_persistence_profile_gap": False,
        "replay_ready_gap": True,
        "forensic_grade_gap": True,
        "dq_signal_present": True,
        "cross_validation_signal_present": False,
    }
    assert result.diagnostics["next_steps"] == [
        "Inspect failure classification and decide retry/quarantine/escalation.",
        "Persist immutable cached Bronze input snapshots before treating this run as strict exact-replay capable.",
        "Review replay-ready persistence requirements before treating this run as exact-replay capable.",
        "Review forensic-grade persistence requirements before using this run for full trace/debug reconstruction.",
        "Review DQ report artifacts, rule IDs, and contract policy anchors before retry or escalation.",
    ]


def test_show_surfaces_supported_gold_trace_path_in_diagnostics() -> None:
    manifest_store = _InMemoryRunManifestStore()
    ledger_store = _InMemoryRunLedgerStore()
    run_id = RunID(UUID("00000000-0000-0000-0000-000000000151"))
    manifest = _make_manifest(manifest_id="manifest-gold-trace", run_id=run_id)
    manifest_store.save(manifest)
    ledger_store.append(
        RunLedgerEntry(
            entry_id="entry-gold-trace-1",
            manifest_id="manifest-gold-trace",
            run_id=run_id,
            event_type="artifact_published",
            occurred_at=datetime(2025, 1, 1, tzinfo=UTC),
            event_family="artifact",
            status="success",
            stage="gold",
            dataset_ref="gold:chembl.activity",
            lineage_fragment_id="gold:fragment-1",
            details={
                "artifact_path": "gold/chembl/activity",
                "metadata_path": "gold/chembl/activity/chembl_activity_metadata.yaml",
                "artifact_kind": "metadata_sidecar",
                "pipeline_name": "chembl_activity",
                "provider": "chembl",
                "entity": "activity",
                "run_id": str(run_id),
                "manifest_id": "manifest-gold-trace",
            },
        )
    )
    service = RunManifestInspectionService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
    )

    result = service.show("manifest-gold-trace")

    assert result.diagnostics["artifact_refs"] == [
        {
            "event_type": "artifact_published",
            "stage": "gold",
            "artifact_id": "gold:chembl.activity",
            "dataset_ref": "gold:chembl.activity",
            "lineage_fragment_id": "gold:fragment-1",
            "artifact_path": "gold/chembl/activity",
            "metadata_path": "gold/chembl/activity/chembl_activity_metadata.yaml",
            "artifact_kind": "metadata_sidecar",
            "pipeline_name": "chembl_activity",
            "provider": "chembl",
            "entity": "activity",
            "run_id": str(run_id),
            "manifest_id": "manifest-gold-trace",
        }
    ]
    assert result.diagnostics["lineage_fragment_ids"] == ["gold:fragment-1"]
    assert result.diagnostics["missing_artifact_links"] == 0
    assert result.diagnostics["alert_signals"] == {
        "run_failed": False,
        "run_shutdown": False,
        "artifact_linkage_gap": False,
        "lineage_gap": False,
        "immutable_input_snapshot_gap": False,
        "strict_replay_boundary_gap": False,
        "lineage_closure_boundary_gap": False,
        "reproducible_semantic_output_mode_gap": False,
        "composite_resume_reconstructability_gap": False,
        "required_persistence_profile_gap": False,
        "replay_ready_gap": False,
        "forensic_grade_gap": False,
        "dq_signal_present": False,
        "cross_validation_signal_present": False,
    }


def test_show_surfaces_cross_validation_traceability_in_diagnostics() -> None:
    manifest_store = _InMemoryRunManifestStore()
    ledger_store = _InMemoryRunLedgerStore()
    run_id = RunID(uuid4())
    manifest = _make_manifest(manifest_id="manifest-cv", run_id=run_id)
    manifest_store.save(manifest)
    ledger_store.append(
        RunLedgerEntry(
            entry_id="entry-cv-1",
            manifest_id="manifest-cv",
            run_id=run_id,
            event_type="dq_policy_applied",
            occurred_at=_FIXED_TIME,
            event_family="dq",
            status="failed",
            stage="cross_validation",
            details={
                "rule_id": "composite.cross_validation.quarantine",
                "disposition": "quarantine",
                "violation_kind": "cross_validation_mismatch",
                "config_path": "cross_validation",
                "artifact_policy": "occurrence_only_diagnostic",
                "replay_contract": "excluded_from_exact_replay",
                "diagnostic_scope": "composite_cross_validation_quarantine",
                "dq_report_path": COMPOSITE_CV_REPORT_PATH,
            },
        )
    )
    service = RunManifestInspectionService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
    )

    result = service.show("manifest-cv")

    assert result.diagnostics["dq_rule_ids"] == [
        "composite.cross_validation.quarantine"
    ]
    assert result.diagnostics["dq_dispositions"] == ["quarantine"]
    assert result.diagnostics["dq_violation_kinds"] == ["cross_validation_mismatch"]
    assert result.diagnostics["cross_validation_rule_ids"] == [
        "composite.cross_validation.quarantine"
    ]
    assert result.diagnostics["cross_validation_config_paths"] == ["cross_validation"]
    assert (
        result.diagnostics["cross_validation_quarantine_policy"]
        == "occurrence_only_diagnostic"
    )
    assert (
        result.diagnostics["cross_validation_quarantine_replay_contract"]
        == "excluded_from_exact_replay"
    )
    assert result.diagnostics["occurrence_only_diagnostics"] == [
        "composite_cross_validation_quarantine"
    ]
    assert result.diagnostics["cross_validation_signal_present"] is True
    assert result.identity_graph["occurrence_only_diagnostics"] == [
        "composite_cross_validation_quarantine"
    ]
    assert result.diagnostics["alert_signals"] == {
        "run_failed": True,
        "run_shutdown": False,
        "artifact_linkage_gap": False,
        "lineage_gap": False,
        "immutable_input_snapshot_gap": False,
        "strict_replay_boundary_gap": False,
        "lineage_closure_boundary_gap": False,
        "reproducible_semantic_output_mode_gap": False,
        "composite_resume_reconstructability_gap": False,
        "required_persistence_profile_gap": False,
        "replay_ready_gap": False,
        "forensic_grade_gap": False,
        "dq_signal_present": True,
        "cross_validation_signal_present": True,
    }
    assert result.diagnostics["next_steps"] == [
        "Inspect failure classification and decide retry/quarantine/escalation.",
        "Review DQ report artifacts, rule IDs, and contract policy anchors before retry or escalation.",
        "Review cross-validation mismatch outcomes and composite policy anchors before retry or quarantine changes.",
    ]
