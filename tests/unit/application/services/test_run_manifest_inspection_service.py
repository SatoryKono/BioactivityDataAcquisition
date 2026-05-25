"""Unit tests for RunManifestInspectionService."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

import pytest

from bioetl.application.services.control_plane.effective_config_service import (
    EffectiveConfigService,
)
from bioetl.application.services.control_plane.run_manifest_inspection_service import (
    RunManifestInspectionCorruptionError,
    RunManifestInspectionService,
)
from bioetl.application.services.control_plane import RunLedgerService
from bioetl.application.services.control_plane.run_manifest_service import (
    RunManifestCreateSpec as RunManifestCreateRequest,
    RunManifestService,
)
from bioetl.domain.config.dq import DQConfig
from bioetl.domain.control_plane import (
    ReplayCapability,
    RunArtifactRef,
    RunSourceRef,
    RunLedgerEntry,
    RunManifest,
)
from bioetl.domain.types import RunID, RunType
from tests.helpers.control_plane import InMemoryRunLedgerStore, InMemoryRunManifestStore
from bioetl.domain.types.dq_contracts import DQDisposition
from bioetl.domain.control_plane.effective_config_artifact import ConfigSourceRef
from tests.unit.application.services.run_manifest_test_support import (
    FIXED_TIME as _FIXED_TIME,
    RunManifestOverrides,
    VALID_CONFIG_HASH as _VALID_CONFIG_HASH,
    VALID_EFFECTIVE_CONFIG_HASH as _VALID_EFFECTIVE_CONFIG_HASH,
    VALID_RESOLVED_CONFIG_HASH as _VALID_RESOLVED_CONFIG_HASH,
    build_default_source_refs,
    build_published_silver_artifact,
    build_source_refs,
    expected_canonical_execution_identity as _expected_canonical_execution_identity,
    expected_degraded_runtime_anchor as _expected_degraded_runtime_anchor,
    expected_exact_replay_anchors as _expected_exact_replay_anchors,
    expected_input_snapshot_identity_fingerprint as _expected_input_snapshot_identity_fingerprint,
    expected_lineage_closure_boundary as _expected_lineage_closure_boundary,
    expected_produced_artifact_trace as _expected_produced_artifact_trace,
    expected_replay_family_contract as _expected_replay_family_contract,
    expected_replay_parentage as _expected_replay_parentage,
    expected_resume_contract as _expected_resume_contract,
    make_run_manifest,
)
from tests.helpers.deterministic_ids import deterministic_uuid
from tests.helpers.synthetic_paths import synthetic_test_root

TEST_ROOT = synthetic_test_root("run-manifest-inspection")
BRONZE_BATCH_URI = (TEST_ROOT / "bronze" / "batch_1.jsonl.zst").as_uri()
SILVER_ARTIFACT_PATH = str(TEST_ROOT / "output" / "silver" / "chembl" / "activity")
GOLD_DQ_REPORT_PATH = str(TEST_ROOT / "reports" / "gold_dq.json")
COMPOSITE_CV_REPORT_PATH = str(TEST_ROOT / "reports" / "composite_cv.json")
pytestmark = pytest.mark.unit


def _expected_code_provenance_state(manifest: RunManifest) -> dict[str, object]:
    blockers = []
    if not manifest.code_provenance.git_commit:
        blockers.append("git_commit_missing")
    if (
        str(manifest.code_provenance.source_revision_state or "").strip().lower()
        != "clean"
    ):
        blockers.append("source_revision_state_not_clean")
    if not manifest.code_provenance.dependency_lock_hash:
        blockers.append("dependency_lock_hash_missing")
    state: dict[str, object] = {
        "git_commit": manifest.code_provenance.git_commit,
        "source_revision_state": manifest.code_provenance.source_revision_state,
        "dependency_lock_state": (
            "present"
            if manifest.code_provenance.dependency_lock_hash is not None
            else "missing"
        ),
        "strict_code_provenance_ready": not blockers,
        "strict_code_provenance_blockers": blockers,
    }
    if manifest.code_provenance.dependency_lock_hash is not None:
        state["dependency_lock_hash"] = manifest.code_provenance.dependency_lock_hash
    return state


_InMemoryRunManifestStore = InMemoryRunManifestStore
_InMemoryRunLedgerStore = InMemoryRunLedgerStore


def _run_id(label: str) -> RunID:
    return RunID(deterministic_uuid(f"run-manifest-inspection:{label}"))


class _InMemoryEffectiveConfigArtifactStore:
    def __init__(self) -> None:
        self._artifacts_by_run_id: dict[RunID, dict[str, object]] = {}
        self._occurrences_by_run_id: dict[RunID, dict[str, object]] = {}

    def save(
        self,
        *,
        artifact_id: str,
        run_id: RunID,
        payload: dict[str, object],
        occurrence: dict[str, object] | None = None,
    ) -> None:
        self._artifacts_by_run_id[run_id] = {
            "artifact_id": artifact_id,
            **payload,
        }
        self._occurrences_by_run_id[run_id] = occurrence or {
            "artifact_id": artifact_id,
            "run_id": str(run_id),
            "occurrence_envelope": {},
        }

    def get(self, artifact_id: str) -> dict[str, object] | None:
        for payload in self._artifacts_by_run_id.values():
            if payload.get("artifact_id") == artifact_id:
                return payload
        return None

    def get_by_run_id(self, run_id: RunID) -> dict[str, object] | None:
        return self._artifacts_by_run_id.get(run_id)

    def get_occurrence_by_run_id(self, run_id: RunID) -> dict[str, object] | None:
        return self._occurrences_by_run_id.get(run_id)

    def diff_occurrences_by_run_id(
        self,
        left_run_id: RunID,
        right_run_id: RunID,
    ) -> dict[str, object]:
        left_artifact = self.get_by_run_id(left_run_id)
        right_artifact = self.get_by_run_id(right_run_id)
        left_occurrence = self.get_occurrence_by_run_id(left_run_id)
        right_occurrence = self.get_occurrence_by_run_id(right_run_id)
        semantic_equivalent = left_artifact == right_artifact
        differences: list[dict[str, object]] = []
        if left_occurrence != right_occurrence:
            differences.append(
                {
                    "field": "occurrence_envelope",
                    "left": left_occurrence,
                    "right": right_occurrence,
                }
            )
        return {
            "left_run_id": str(left_run_id),
            "right_run_id": str(right_run_id),
            "left_artifact_present": left_artifact is not None,
            "right_artifact_present": right_artifact is not None,
            "left_occurrence_present": left_occurrence is not None,
            "right_occurrence_present": right_occurrence is not None,
            "semantic_equivalent": semantic_equivalent,
            "occurrence_only": semantic_equivalent and bool(differences),
            "differences": differences,
        }


class _StaticHistoricalReplayUniverseReportLoader:
    def __init__(self, report: dict[str, object] | None) -> None:
        self._report = report

    def load_latest_report(self) -> dict[str, object] | None:
        return self._report


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
    return make_run_manifest(
        manifest_id=manifest_id,
        run_id=run_id,
        run_type=run_type,
        config_hash=config_hash,
        limit=limit,
        execution_fingerprint=execution_fingerprint,
        created_at=created_at or _FIXED_TIME,
        replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED,
        source_refs=source_refs
        or build_default_source_refs(
            bronze_batch_uri=BRONZE_BATCH_URI,
        ),
        overrides=RunManifestOverrides(
            resolved_config_hash=resolved_config_hash,
            effective_config_hash=effective_config_hash,
            dependency_lock_hash="sha256:deps-inspection",
            launch_context={"limit": limit, "exact_replay": True},
            runtime_config={
                "run_type": run_type.value,
                "limit": limit,
                "exact_replay": True,
            },
        ),
    )


def test_show_resolves_manifest_by_run_id_and_includes_ledger_history() -> None:
    manifest_store = _InMemoryRunManifestStore()
    ledger_store = _InMemoryRunLedgerStore()
    run_id = _run_id("show-run-id-history")
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
    snapshot_fingerprint = _expected_input_snapshot_identity_fingerprint(manifest)

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
        "source_fingerprint": manifest.code_provenance.source_fingerprint,
        "git_commit": "abc1234",
        "source_revision_state": "clean",
        "dependency_lock_state": "present",
        "dependency_lock_hash": "sha256:deps-inspection",
        "code_provenance_state": _expected_code_provenance_state(manifest),
        "contract_ref": "chembl.activity",
        "contract_version": "1.2.0",
        "normalization_profile_ref": None,
        "normalization_profile_version": None,
        "normalization_profile_hash": None,
        "replay_of_run_id": None,
        "replay_of_manifest_id": None,
        "replay_parentage": _expected_replay_parentage(manifest),
        "canonical_execution_identity": _expected_canonical_execution_identity(
            manifest,
            requested_exact_replay=True,
            snapshot_fingerprint=snapshot_fingerprint,
        ),
        "exact_replay_anchors": _expected_exact_replay_anchors(
            manifest,
            snapshot_fingerprint=snapshot_fingerprint,
        ),
        "degraded_runtime_anchor": _expected_degraded_runtime_anchor(manifest),
        "replay_capability": "exact_replay_supported",
        "requested_exact_replay": True,
        "exact_replay_support_boundary": "snapshot_backed_source_runs_only",
        "replay_family_contract": _expected_replay_family_contract(manifest),
        "replay_support_state": "exact_replay_supported",
        "source_posture": "immutable_snapshot_envelope",
        "input_snapshot_missing_source_refs": [],
        "historical_live_run_upgrade_policy": (
            "input_snapshot_published_ledger_evidence_only"
        ),
        "historical_live_run_upgrade_boundary": (
            "input_snapshot_published_ledger_evidence"
        ),
        "historical_live_run_upgrade_reason": (
            "historical_live_runs_require_input_snapshot_published_ledger_evidence_before_parent_promotion"
        ),
        "broader_historical_exact_replay_policy": (
            "certified_historical_exact_replay_tranche_supported"
        ),
        "broader_historical_exact_replay_boundary": (
            "historical_source_snapshot_certification"
        ),
        "broader_historical_exact_replay_reason": (
            "retained_historical_source_runs_can_gain_certified_exact_replay_parent_evidence_via_backfilled_snapshot_certification"
        ),
        "broader_historical_exact_replay_state": (
            "within_launch_time_snapshot_boundary"
        ),
        "historical_live_run_upgrade_state": ("not_needed_snapshot_backed_at_launch"),
        "replay_occurrence_kind": "launch_time_snapshot_backed_run",
        "post_capture_replayable_parent_supported": True,
        "post_capture_replayable_parent_boundary": (
            "ledger_materialized_live_capture_parent"
        ),
        "replay_capability_reason": ("full_immutable_input_snapshot_envelope_present"),
        "exact_replay_eligible": True,
        "exact_replay_blockers": [],
        "replay_readiness_verdict": "exact_replay_ready",
        "replay_resume_rebuild_verdict": "exact_replay_ready",
        "replay_next_action": (
            "Use exact replay with manifest, execution fingerprint, "
            "and input snapshots."
        ),
        "append_mode_semantic_sinks": [],
        "resume_contract": _expected_resume_contract(manifest),
        "resume_diagnostics": None,
        "lineage_closure_boundary": _expected_lineage_closure_boundary(manifest),
        "input_snapshot_ids": ["snapshot-1"],
        "input_snapshot_content_hashes": ["sha256:snapshot-1"],
        "input_snapshot_identity_fingerprint": snapshot_fingerprint,
        "replay_mode": "exact_replay",
        "operator_replay_mode": "Exact Replay",
        "snapshot_status": "full",
        "continuation_mode": "exact_replay",
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
        "produced_artifact_trace": _expected_produced_artifact_trace(
            manifest,
            ledger_entries_present=True,
        ),
        "occurrence_only_diagnostics": [],
        "authoritative_replay_dossier": _expected_authoritative_replay_dossier(
            manifest,
            planned_artifact_count=0,
            published_artifact_count=0,
            identity_graph_complete=False,
        ),
    }
    assert result.diagnostics["identity_graph"]["manifest_id"] == "manifest-1"
    assert result.diagnostics["identity_graph"]["run_id"] == str(run_id)
    assert result.diagnostics["identity_graph"]["published_artifacts"] == []
    assert result.diagnostics["produced_artifact_trace"] == (
        _expected_produced_artifact_trace(manifest, ledger_entries_present=True)
    )
    assert result.diagnostics["alert_signals"] == {
        "run_failed": False,
        "run_shutdown": False,
        "artifact_linkage_gap": False,
        "lineage_gap": False,
        "immutable_input_snapshot_gap": False,
        "strict_replay_boundary_gap": False,
        "lineage_closure_boundary_gap": False,
        "reproducible_semantic_output_mode_gap": False,
        "produced_artifact_trace_gap": True,
        "composite_resume_reconstructability_gap": False,
        "required_persistence_profile_gap": True,
        "replay_ready_gap": True,
        "forensic_grade_gap": True,
        "dq_signal_present": False,
        "cross_validation_signal_present": False,
    }
    assert (
        result.diagnostics["persistence_profile"]["attained_profile"]
        == "degraded_observable"
    )
    assert (
        result.diagnostics["persistence_profile"]["claims"]["forensic_grade"] is False
    )
    assert result.diagnostics["next_steps"] == [
        "Resolve concrete produced artifacts from the run ledger before claiming replay-ready reproducibility.",
        "Current persisted surfaces do not satisfy the declared required persistence profile for this run.",
        "Review replay-ready persistence requirements before treating this run as exact-replay capable.",
        "Review forensic-grade persistence requirements before using this run for full trace/debug reconstruction.",
    ]


def test_show_attaches_latest_historical_replay_universe_claim_to_score() -> None:
    manifest_store = _InMemoryRunManifestStore()
    run_id = _run_id("show-global-claim")
    manifest = _make_manifest(manifest_id="manifest-global-claim", run_id=run_id)
    manifest_store.save(manifest)
    loader = _StaticHistoricalReplayUniverseReportLoader(
        {
            "_artifact_path": "data/output/control/historical_replay_universe/latest.json",
            "report_id": "historical-replay-universe-latest",
            "universal_claim": {
                "claimed": True,
                "verdict": "claim_supported",
                "reason": "all_known_historical_runs_are_exact_replayable",
                "scope": "all_known_historical_runs",
                "blocked_manifest_ids": [],
            },
            "durable_evidence_coverage_claim": {
                "claimed": True,
                "verdict": "claim_supported",
                "reason": "every_known_historical_run_has_durable_evidence_coverage",
                "scope": "all_known_historical_runs",
                "blocked_manifest_ids": [],
            },
            "governed_full_corpus_gate": {
                "gate_kind": "universal_historical_exact_replay",
                "scope": "all_known_historical_runs",
                "authoritative_truth_surface": "historical_replay_universe_closure_report",
                "required_claims": {
                    "universal_claim": True,
                    "durable_evidence_coverage_claim": True,
                },
                "satisfied": True,
                "verdict": "gate_satisfied",
                "reason": "authoritative_full_corpus_gate_satisfied",
            },
        }
    )
    service = RunManifestInspectionService(
        manifest_port=manifest_store,
        historical_replay_universe_report_loader=loader,
    )

    result = service.show("manifest-global-claim")

    score = result.diagnostics["reproducibility_audit_score"]
    historical_claim = score["historical_replay_universe_exact_replay_claim"]
    executable_claim = score["executable_run_contract_claim"]
    assert result.diagnostics["historical_replay_universe_claim"]["claimed"] is True
    assert (
        result.diagnostics["historical_replay_universe_claim_source"]
        == "data/output/control/historical_replay_universe/latest.json"
    )
    assert (
        result.diagnostics["historical_replay_universe_durable_evidence_claimed"]
        is True
    )
    assert historical_claim["claimed"] is True
    assert (
        result.diagnostics["historical_replay_universe_exact_replay_claim"]["claimed"]
        is True
    )
    assert executable_claim["claimed"] is True
    assert executable_claim["verdict"] == "prospective_executable_run_contract_claimed"
    assert historical_claim["verdict"] == "historical_universe_exact_replay_claimed"
    assert historical_claim["governed_full_corpus_gate"]["satisfied"] is True
    assert (
        result.diagnostics["historical_replay_universe_governed_full_corpus_gate"][
            "verdict"
        ]
        == "gate_satisfied"
    )
    assert (
        historical_claim["reason"]
        == "latest_historical_replay_universe_artifact_supports_universal_claim"
    )
    assert (
        historical_claim["claim_source_artifact_path"]
        == "data/output/control/historical_replay_universe/latest.json"
    )
    dossier = result.diagnostics["authoritative_replay_dossier"]
    assert dossier["manifest_id"] == "manifest-global-claim"
    assert dossier["execution_fingerprint"] == manifest.execution_fingerprint
    assert "run_manifest" in dossier["authoritative_replay_artifacts"]


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


def _expected_authoritative_replay_dossier(
    manifest: RunManifest,
    *,
    planned_artifact_count: int | None,
    published_artifact_count: int,
    identity_graph_complete: bool | None,
) -> dict[str, object]:
    snapshot_fingerprint = _expected_input_snapshot_identity_fingerprint(manifest)
    return {
        "truth_boundary": "authoritative_replay_artifacts_only",
        "authoritative_replay_artifacts": [
            "run_manifest",
            "effective_config_artifact",
            "lineage_fragment",
            "layer_metadata",
            "checkpoint_metadata",
            "input_snapshot_envelope",
        ],
        "manifest_id": manifest.manifest_id,
        "run_id": str(manifest.run_id),
        "execution_fingerprint": manifest.execution_fingerprint,
        "git_commit": "abc1234",
        "effective_config_artifact_id": "eca-123",
        "effective_config_hash": _VALID_EFFECTIVE_CONFIG_HASH,
        "contract_ref": "chembl.activity",
        "contract_version": "1.2.0",
        "required_persistence_profile": "replay_ready",
        "exact_replay_support_boundary": "snapshot_backed_source_runs_only",
        "snapshot_status": "full",
        "input_snapshot_ids": ["snapshot-1"],
        "input_snapshot_content_hashes": ["sha256:snapshot-1"],
        "input_snapshot_identity_fingerprint": snapshot_fingerprint,
        "lineage_fragment_ids": [],
        "published_artifact_refs": [],
        "planned_artifact_count": planned_artifact_count,
        "published_artifact_count": published_artifact_count,
        "identity_graph_complete": identity_graph_complete,
        "checkpoint_identity": {
            "required_persistence_profile": "replay_ready",
            "execution_fingerprint": manifest.execution_fingerprint,
            "effective_config_hash": _VALID_EFFECTIVE_CONFIG_HASH,
            "effective_config_artifact_id": "eca-123",
            "contract_ref": "chembl.activity",
            "contract_version": "1.2.0",
            "input_snapshot_identity_fingerprint": snapshot_fingerprint,
            "input_snapshot_ids": ["snapshot-1"],
        },
        "canonical_execution_identity": _expected_canonical_execution_identity(
            manifest,
            requested_exact_replay=True,
            snapshot_fingerprint=snapshot_fingerprint,
        ),
    }


def _expected_identity_graph_without_ledger(
    manifest: RunManifest,
    *,
    run_id: RunID,
) -> dict[str, object]:
    snapshot_fingerprint = _expected_input_snapshot_identity_fingerprint(manifest)
    return {
        "run_id": str(run_id),
        "manifest_id": "manifest-no-ledger",
        "execution_fingerprint": manifest.execution_fingerprint,
        "config_hash": _VALID_CONFIG_HASH,
        "resolved_config_hash": _VALID_RESOLVED_CONFIG_HASH,
        "effective_config_hash": _VALID_EFFECTIVE_CONFIG_HASH,
        "source_fingerprint": manifest.code_provenance.source_fingerprint,
        "git_commit": "abc1234",
        "source_revision_state": "clean",
        "dependency_lock_state": "present",
        "dependency_lock_hash": "sha256:deps-inspection",
        "code_provenance_state": _expected_code_provenance_state(manifest),
        "contract_ref": "chembl.activity",
        "contract_version": "1.2.0",
        "normalization_profile_ref": None,
        "normalization_profile_version": None,
        "normalization_profile_hash": None,
        "replay_of_run_id": None,
        "replay_of_manifest_id": None,
        "replay_parentage": _expected_replay_parentage(manifest),
        "canonical_execution_identity": _expected_canonical_execution_identity(
            manifest,
            requested_exact_replay=True,
            snapshot_fingerprint=snapshot_fingerprint,
        ),
        "exact_replay_anchors": _expected_exact_replay_anchors(
            manifest,
            snapshot_fingerprint=snapshot_fingerprint,
        ),
        "degraded_runtime_anchor": _expected_degraded_runtime_anchor(manifest),
        "replay_capability": "exact_replay_supported",
        "requested_exact_replay": True,
        "exact_replay_support_boundary": "snapshot_backed_source_runs_only",
        "replay_family_contract": _expected_replay_family_contract(manifest),
        "replay_support_state": "exact_replay_supported",
        "source_posture": "immutable_snapshot_envelope",
        "input_snapshot_missing_source_refs": [],
        "historical_live_run_upgrade_policy": (
            "input_snapshot_published_ledger_evidence_only"
        ),
        "historical_live_run_upgrade_boundary": (
            "input_snapshot_published_ledger_evidence"
        ),
        "historical_live_run_upgrade_reason": (
            "historical_live_runs_require_input_snapshot_published_ledger_evidence_before_parent_promotion"
        ),
        "broader_historical_exact_replay_policy": (
            "certified_historical_exact_replay_tranche_supported"
        ),
        "broader_historical_exact_replay_boundary": (
            "historical_source_snapshot_certification"
        ),
        "broader_historical_exact_replay_reason": (
            "retained_historical_source_runs_can_gain_certified_exact_replay_parent_evidence_via_backfilled_snapshot_certification"
        ),
        "broader_historical_exact_replay_state": (
            "within_launch_time_snapshot_boundary"
        ),
        "historical_live_run_upgrade_state": ("not_needed_snapshot_backed_at_launch"),
        "replay_occurrence_kind": "launch_time_snapshot_backed_run",
        "post_capture_replayable_parent_supported": True,
        "post_capture_replayable_parent_boundary": (
            "ledger_materialized_live_capture_parent"
        ),
        "replay_capability_reason": ("full_immutable_input_snapshot_envelope_present"),
        "exact_replay_eligible": True,
        "exact_replay_blockers": [],
        "replay_readiness_verdict": "exact_replay_ready",
        "replay_resume_rebuild_verdict": "exact_replay_ready",
        "replay_next_action": (
            "Use exact replay with manifest, execution fingerprint, "
            "and input snapshots."
        ),
        "append_mode_semantic_sinks": [],
        "resume_contract": _expected_resume_contract(manifest),
        "resume_diagnostics": None,
        "lineage_closure_boundary": _expected_lineage_closure_boundary(manifest),
        "input_snapshot_ids": ["snapshot-1"],
        "input_snapshot_content_hashes": ["sha256:snapshot-1"],
        "input_snapshot_identity_fingerprint": snapshot_fingerprint,
        "replay_mode": "exact_replay",
        "operator_replay_mode": "Exact Replay",
        "snapshot_status": "full",
        "continuation_mode": "exact_replay",
        "input_snapshot_count": 1,
        "input_snapshots": _expected_input_snapshots(),
        "planned_artifacts": [],
        "published_artifacts": [],
        "produced_artifact_trace": _expected_produced_artifact_trace(
            manifest,
            ledger_entries_present=False,
        ),
        "occurrence_only_diagnostics": [],
        "authoritative_replay_dossier": _expected_authoritative_replay_dossier(
            manifest,
            planned_artifact_count=None,
            published_artifact_count=0,
            identity_graph_complete=None,
        ),
    }


def _expected_diagnostics_without_ledger(
    manifest: RunManifest,
    *,
    run_id: RunID,
    identity_graph: dict[str, object],
    reproducibility_audit_score: object,
) -> dict[str, object]:
    snapshot_fingerprint = _expected_input_snapshot_identity_fingerprint(manifest)
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
        "source_fingerprint": manifest.code_provenance.source_fingerprint,
        "pipeline_version": "1.0.0",
        "git_commit": "abc1234",
        "source_revision_state": "clean",
        "dependency_lock_state": "present",
        "dependency_lock_hash": "sha256:deps-inspection",
        "code_provenance_state": _expected_code_provenance_state(manifest),
        "contract_ref": "chembl.activity",
        "contract_version": "1.2.0",
        "normalization_profile_ref": None,
        "normalization_profile_version": None,
        "normalization_profile_hash": None,
        "replay_of_run_id": None,
        "replay_of_manifest_id": None,
        "replay_parentage": _expected_replay_parentage(manifest),
        "replay_capability": "exact_replay_supported",
        "required_persistence_profile": "replay_ready",
        "requested_exact_replay": True,
        "exact_replay_support_boundary": "snapshot_backed_source_runs_only",
        "replay_control_plane_state": "exact_replay_supported",
        "replay_family_contract": _expected_replay_family_contract(manifest),
        "replay_support_state": "exact_replay_supported",
        "source_posture": "immutable_snapshot_envelope",
        "input_snapshot_missing_source_refs": [],
        "historical_live_run_upgrade_policy": (
            "input_snapshot_published_ledger_evidence_only"
        ),
        "historical_live_run_upgrade_boundary": (
            "input_snapshot_published_ledger_evidence"
        ),
        "historical_live_run_upgrade_reason": (
            "historical_live_runs_require_input_snapshot_published_ledger_evidence_before_parent_promotion"
        ),
        "broader_historical_exact_replay_policy": (
            "certified_historical_exact_replay_tranche_supported"
        ),
        "broader_historical_exact_replay_boundary": (
            "historical_source_snapshot_certification"
        ),
        "broader_historical_exact_replay_reason": (
            "retained_historical_source_runs_can_gain_certified_exact_replay_parent_evidence_via_backfilled_snapshot_certification"
        ),
        "broader_historical_exact_replay_state": (
            "within_launch_time_snapshot_boundary"
        ),
        "historical_live_run_upgrade_state": ("not_needed_snapshot_backed_at_launch"),
        "identity_graph_complete": None,
        "replay_occurrence_kind": "launch_time_snapshot_backed_run",
        "post_capture_replayable_parent_supported": True,
        "post_capture_replayable_parent_boundary": (
            "ledger_materialized_live_capture_parent"
        ),
        "replay_capability_reason": ("full_immutable_input_snapshot_envelope_present"),
        "exact_replay_eligible": True,
        "exact_replay_blockers": [],
        "replay_readiness_verdict": "exact_replay_ready",
        "replay_resume_rebuild_verdict": "exact_replay_ready",
        "replay_next_action": (
            "Use exact replay with manifest, execution fingerprint, "
            "and input snapshots."
        ),
        "append_mode_semantic_sinks": [],
        "resume_contract": _expected_resume_contract(manifest),
        "resume_diagnostics": None,
        "lineage_closure_boundary": _expected_lineage_closure_boundary(manifest),
        "input_snapshot_ids": ["snapshot-1"],
        "input_snapshot_content_hashes": ["sha256:snapshot-1"],
        "input_snapshot_identity_fingerprint": snapshot_fingerprint,
        "replay_mode": "exact_replay",
        "operator_replay_mode": "Exact Replay",
        "snapshot_status": "full",
        "continuation_mode": "exact_replay",
        "input_snapshot_count": 1,
        "input_snapshots": _expected_input_snapshots(),
        "dq_policy_ref": "chembl_activity.gold",
        "rule_bundle_version": "2026.03",
        "dq_contract_compatibility_hash": "compat-hash-1",
        "effective_config_artifact_id": "eca-123",
        "planned_artifacts": [],
        "occurrence_only_diagnostics": [],
        "artifact_refs": [],
        "lineage_fragment_ids": [],
        "published_artifact_count": 0,
        "exact_replay_anchors": _expected_exact_replay_anchors(
            manifest,
            snapshot_fingerprint=snapshot_fingerprint,
        ),
        "produced_artifact_trace": _expected_produced_artifact_trace(
            manifest,
            ledger_entries_present=False,
        ),
        "artifact_publication_closure": "disabled",
        "identity_graph": identity_graph,
        "authoritative_replay_dossier": _expected_authoritative_replay_dossier(
            manifest,
            planned_artifact_count=None,
            published_artifact_count=0,
            identity_graph_complete=None,
        ),
        "persistence_profile": {
            "attained_profile": "degraded_observable",
            "required_profile": "replay_ready",
            "required_profile_satisfied": False,
            "claims": {
                "degraded_observable": True,
                "replay_ready": False,
                "forensic_grade": False,
            },
            "surfaces": {
                "control_plane_manifest": True,
                "effective_config_artifact": True,
                "dependency_lock_provenance": True,
                "strict_replay_execution_context_support": True,
                "immutable_input_snapshots": True,
                "exact_replay_capability": True,
                "produced_artifact_trace": False,
                "reproducible_semantic_output_mode": True,
                "run_ledger_history": False,
                "artifact_lineage_links": True,
                "lineage_closure_boundary_support": True,
            },
            "required_profile_missing_requirements": [
                "produced_artifact_trace",
            ],
            "replay_ready_missing_requirements": [
                "produced_artifact_trace",
            ],
            "forensic_grade_missing_requirements": [
                "produced_artifact_trace",
                "run_ledger_history",
            ],
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
            "produced_artifact_trace_gap": True,
            "composite_resume_reconstructability_gap": False,
            "required_persistence_profile_gap": True,
            "replay_ready_gap": True,
            "forensic_grade_gap": True,
            "dq_signal_present": False,
            "cross_validation_signal_present": False,
        },
        "next_steps": [
            "Resolve concrete produced artifacts from the run ledger before claiming replay-ready reproducibility.",
            "Current persisted surfaces do not satisfy the declared required persistence profile for this run.",
            "Review replay-ready persistence requirements before treating this run as exact-replay capable.",
            "Review forensic-grade persistence requirements before using this run for full trace/debug reconstruction.",
        ],
        "reproducibility_audit_score": reproducibility_audit_score,
        "historical_replay_universe_exact_replay_claim": (
            reproducibility_audit_score.get(
                "historical_replay_universe_exact_replay_claim", {}
            )
            if isinstance(reproducibility_audit_score, dict)
            else {}
        ),
        "executable_run_contract_claim": (
            reproducibility_audit_score.get("executable_run_contract_claim", {})
            if isinstance(reproducibility_audit_score, dict)
            else {}
        ),
    }


def test_show_by_manifest_id_without_ledger_port_returns_base_summary() -> None:
    manifest_store = _InMemoryRunManifestStore()
    run_id = _run_id("execution-identity-mismatch")
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
        result.diagnostics["persistence_profile"]["attained_profile"]
        == "degraded_observable"
    )
    assert result.diagnostics["persistence_profile"]["claims"]["replay_ready"] is False
    assert result.diagnostics["persistence_profile"][
        "forensic_grade_missing_requirements"
    ] == [
        "produced_artifact_trace",
        "run_ledger_history",
    ]
    diagnostics_without_unified = {
        key: value
        for key, value in result.diagnostics.items()
        if key
        not in {
            "reproducibility_diagnostics",
            "replay_capability_assessment",
        }
    }
    assert result.diagnostics["replay_capability_assessment"] == {
        "required_persistence_profile": "replay_ready",
        "replay_capability": "exact_replay_supported",
        "strict_requirement_requested": True,
        "strict_exact_replay_supported": True,
        "replay_readiness_verdict": "exact_replay_ready",
        "required_profile_satisfied": True,
        "blocking_gaps": [],
        "snapshot_envelope": {
            "source_count": 1,
            "sources_with_snapshots": 1,
            "any_input_snapshots": True,
            "full_snapshot_envelope": True,
            "require_full_snapshot_envelope": False,
            "missing_snapshot_source_refs": [],
        },
    }
    assert (
        result.diagnostics["reproducibility_diagnostics"]["policy"]["replay_capability"]
        == "exact_replay_supported"
    )
    assert (
        result.diagnostics["reproducibility_diagnostics"]["policy"][
            "capability_assessment"
        ]
        == result.diagnostics["replay_capability_assessment"]
    )
    assert (
        result.diagnostics["reproducibility_diagnostics"]["occurrence_identity"][
            "manifest_id"
        ]
        == "manifest-no-ledger"
    )
    assert diagnostics_without_unified == _expected_diagnostics_without_ledger(
        manifest,
        run_id=run_id,
        identity_graph=result.identity_graph,
        reproducibility_audit_score=result.diagnostics["reproducibility_audit_score"],
    )


def test_show_surfaces_manifest_store_corruption_as_forensic_error() -> None:
    class _CorruptManifestStore:
        def get(self, manifest_id: str) -> RunManifest | None:
            raise ValueError("Run manifest index corruption: indexed manifest mismatch")

        def get_by_run_id(self, run_id: RunID) -> RunManifest | None:
            raise AssertionError("run-id fallback should not hide corruption")

        def save(self, manifest: RunManifest) -> None:
            raise AssertionError("not used")

    service = RunManifestInspectionService(
        manifest_port=_CorruptManifestStore(),
    )

    with pytest.raises(RunManifestInspectionCorruptionError) as exc_info:
        service.show("manifest-corrupt")

    assert exc_info.value.identifier == "manifest-corrupt"
    assert "indexed manifest mismatch" in exc_info.value.reason
    assert "Run manifest store corruption" in str(exc_info.value)


def test_show_resume_only_manifest_reports_resume_mode() -> None:
    manifest_store = _InMemoryRunManifestStore()
    run_id = _run_id("effective-config-hash-mismatch")
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
    assert result.diagnostics["continuation_mode"] == "checkpoint_snapshot_only_resume"
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
    assert (
        result.identity_graph["continuation_mode"] == "checkpoint_snapshot_only_resume"
    )
    assert result.identity_graph["resume_contract"] == _expected_resume_contract(
        manifest
    )
    assert result.identity_graph["resume_diagnostics"] is None
    assert result.identity_graph["exact_replay_blockers"] == [
        "immutable_input_snapshots_missing"
    ]


def test_diff_distinguishes_exact_replay_ancestry_from_semantic_equality() -> None:
    store = _InMemoryRunManifestStore()
    parent_run_id = _run_id("resume-parent")
    child_run_id = _run_id("resume-child")
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
    run_id = _run_id("missing-artifact-dataset-ref")
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
    run_id = _run_id("missing-artifact-id")
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
        "Treat composite resume as checkpoint snapshot plus ledger suffix replay only"
        in step
        for step in result.diagnostics["next_steps"]
    )
    assert result.identity_graph["input_snapshot_ids"] == []
    assert result.identity_graph["input_snapshot_content_hashes"] == []
    assert result.identity_graph["input_snapshot_identity_fingerprint"] is None
    assert result.identity_graph["input_snapshot_count"] == 0


def test_show_snapshot_backed_manifest_reports_non_replay_snapshot_mode() -> None:
    manifest_store = _InMemoryRunManifestStore()
    run_id = _run_id("missing-exact-replay-source-identity")
    manifest = replace(
        _make_manifest(manifest_id="manifest-snapshot-backed", run_id=run_id),
        launch_context={"limit": 100, "resume": False, "exact_replay": False},
        replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED,
        source_refs=build_source_refs(
            immutable_uri=BRONZE_BATCH_URI,
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
    run_id = _run_id("missing-source-storage-identity")
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
    run_id = _run_id("missing-effective-config-occurrence")
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
        "produced_artifact_trace_gap": False,
        "composite_resume_reconstructability_gap": False,
        "required_persistence_profile_gap": False,
        "replay_ready_gap": False,
        "forensic_grade_gap": False,
        "dq_signal_present": False,
        "cross_validation_signal_present": False,
    }
    assert result.diagnostics["artifact_refs"] == [
        build_published_silver_artifact(artifact_path=SILVER_ARTIFACT_PATH)
    ]
    assert result.diagnostics["produced_artifact_trace"] == (
        _expected_produced_artifact_trace(
            manifest,
            ledger_entries_present=True,
            artifacts=[
                build_published_silver_artifact(artifact_path=SILVER_ARTIFACT_PATH)
            ],
        )
    )
    assert service.resolve_produced_artifacts("manifest-2") == (
        result.diagnostics["produced_artifact_trace"]["artifacts"][0],
    )
    assert result.identity_graph == result.diagnostics["identity_graph"]
    assert result.diagnostics["identity_graph"]["published_artifacts"] == [
        build_published_silver_artifact(artifact_path=SILVER_ARTIFACT_PATH)
    ]


def test_show_marks_artifact_linkage_gap_signal() -> None:
    manifest_store = _InMemoryRunManifestStore()
    ledger_store = _InMemoryRunLedgerStore()
    run_id = _run_id("missing-snapshot-fingerprint")
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
        result.diagnostics["persistence_profile"]["attained_profile"]
        == "degraded_observable"
    )
    assert result.diagnostics["persistence_profile"]["claims"]["replay_ready"] is False
    assert (
        result.diagnostics["persistence_profile"]["claims"]["forensic_grade"] is False
    )
    assert result.diagnostics["alert_signals"]["artifact_linkage_gap"] is True
    assert result.diagnostics["next_steps"] == [
        "Validate artifact publication metadata and repair dataset/lineage links.",
        "Investigate lineage persistence for published artifacts before restart.",
        "Current persisted surfaces do not satisfy the declared required persistence profile for this run.",
        "Review replay-ready persistence requirements before treating this run as exact-replay capable.",
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
    run_id = _run_id("missing-dependency-lock-hash")
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
    run_id = _run_id("effective-config-occurrence-diff")
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
        "produced_artifact_trace_gap": True,
        "composite_resume_reconstructability_gap": False,
        "required_persistence_profile_gap": True,
        "replay_ready_gap": True,
        "forensic_grade_gap": True,
        "dq_signal_present": True,
        "cross_validation_signal_present": False,
    }
    assert result.diagnostics["next_steps"] == [
        "Inspect failure classification and decide retry/quarantine/escalation.",
        "Resolve concrete produced artifacts from the run ledger before claiming replay-ready reproducibility.",
        "Current persisted surfaces do not satisfy the declared required persistence profile for this run.",
        "Review replay-ready persistence requirements before treating this run as exact-replay capable.",
        "Review forensic-grade persistence requirements before using this run for full trace/debug reconstruction.",
        "Review DQ report artifacts, rule IDs, and contract policy anchors before retry or escalation.",
    ]
















