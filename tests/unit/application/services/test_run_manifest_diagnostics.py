"""Unit tests for run-manifest diagnostics summary helpers."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from bioetl.application.services.run_ledger_service import RunLedgerService
from bioetl.application.services.run_manifest_diagnostics import (
    build_diagnostics_summary,
)
from bioetl.domain.control_plane import (
    ReplayCapability,
    RunCodeProvenance,
    RunInputSnapshotRef,
    RunLedgerEntry,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.normalization import (
    build_execution_identity_payload,
    compute_execution_identity_fingerprint,
)
from bioetl.domain.ports import RunLedgerPort
from bioetl.domain.types import RunID, RunType

_VALID_CONFIG_HASH = "a" * 64


class _InMemoryRunLedgerStore(RunLedgerPort):
    def __init__(self) -> None:
        self.items: list[RunLedgerEntry] = []

    def append(self, entry: RunLedgerEntry) -> None:
        self.items.append(entry)

    def list_entries(self, manifest_id: str) -> list[RunLedgerEntry]:
        return [item for item in self.items if item.manifest_id == manifest_id]

    def list_entries_by_run_id(self, run_id: RunID) -> list[RunLedgerEntry]:
        return [item for item in self.items if item.run_id == run_id]

    def list_entries_after(
        self,
        manifest_id: str,
        after_entry_id: str | None,
    ) -> list[RunLedgerEntry]:
        entries = self.list_entries(manifest_id)
        if after_entry_id is None:
            return entries
        for index, item in enumerate(entries):
            if item.entry_id == after_entry_id:
                return entries[index + 1 :]
        raise ValueError(f"missing watermark {after_entry_id!r}")


def _make_manifest() -> RunManifest:
    run_id = RunID(uuid4())
    return RunManifest(
        manifest_id="manifest-diagnostics",
        execution_fingerprint="fingerprint-diagnostics",
        schema_version="1.0",
        created_at=datetime.now(UTC),
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={"limit": 25},
        runtime_config={"run_type": "incremental", "limit": 25},
        resolved_config={"provider": "chembl", "entity_type": "activity"},
        code_provenance=RunCodeProvenance(
            pipeline_version="1.0.0",
            git_commit="abc1234",
            config_hash=_VALID_CONFIG_HASH,
            contract_ref="chembl.activity",
            contract_version="1.2.0",
            dq_policy_ref="chembl_activity.gold",
            rule_bundle_version="2026.03",
            dq_contract_compatibility_hash="compat-hash-1",
            effective_config_artifact_id="eca-123",
        ),
    )


def _expected_canonical_execution_identity(manifest: RunManifest) -> dict[str, object]:
    payload = build_execution_identity_payload(
        pipeline_name=manifest.pipeline_name,
        run_type=manifest.run_type.value,
        pipeline_version=manifest.code_provenance.pipeline_version,
        effective_config_hash=manifest.code_provenance.config_hash,
        dq_contract_compatibility_hash=(
            manifest.code_provenance.dq_contract_compatibility_hash
        ),
        contract_ref=manifest.code_provenance.contract_ref,
        contract_version=manifest.code_provenance.contract_version,
        effective_config_artifact_id=(
            manifest.code_provenance.effective_config_artifact_id
        ),
        exact_replay=False,
        input_snapshot_fingerprint=None,
    )
    return {
        "execution_fingerprint": manifest.execution_fingerprint,
        "payload": payload,
    }


def _expected_degraded_runtime_anchor(manifest: RunManifest) -> dict[str, object]:
    payload = {
        "manifest_id": manifest.manifest_id,
        "effective_config_hash": manifest.code_provenance.config_hash,
        "contract_ref": manifest.code_provenance.contract_ref,
        "contract_version": manifest.code_provenance.contract_version,
        "effective_config_artifact_id": (
            manifest.code_provenance.effective_config_artifact_id
        ),
    }
    filtered_payload = {key: value for key, value in payload.items() if value is not None}
    return {
        "compatibility_scope": "legacy_fallback_only",
        "fingerprint": (
            compute_execution_identity_fingerprint(filtered_payload)
            if filtered_payload
            else None
        ),
        "payload": filtered_payload,
    }


def _build_ledger_entries(
    manifest: RunManifest,
    *,
    terminal_status: str,
) -> tuple[RunLedgerEntry, ...]:
    store = _InMemoryRunLedgerStore()
    entry_counter = {"value": 0}

    def _entry_id_factory() -> str:
        entry_counter["value"] += 1
        return f"entry-{entry_counter['value']}"

    service = RunLedgerService(
        ledger_port=store,
        manifest_id=manifest.manifest_id,
        run_id=manifest.run_id,
        _entry_id_factory=_entry_id_factory,
    )
    service.record_manifest_created(manifest)
    service.record_run_started()
    service.record_stage_completed(
        stage="execute_pipeline",
        metrics_snapshot={"records_bronze": 5},
        details={"result": "ok"},
    )
    service.record_artifact_published(
        layer="silver",
        artifact_path="data/output/silver/chembl/activity",
        dataset_ref="silver:chembl.activity@1",
        lineage_fragment_id="silver:fragment-1",
    )
    if terminal_status == "success":
        service.record_run_finished(metrics_snapshot={"records_silver": 5})
    elif terminal_status == "failed":
        service.record_run_failed(
            message="boom",
            error_type="RuntimeError",
            metrics_snapshot={"records_silver": 3},
        )
    elif terminal_status == "shutdown":
        service.record_run_shutdown(metrics_snapshot={"records_silver": 2})
    else:
        raise AssertionError(f"unsupported terminal status {terminal_status!r}")
    return tuple(store.items)


def test_build_diagnostics_summary_without_ledger_returns_provenance_only() -> None:
    manifest = _make_manifest()

    summary = build_diagnostics_summary(manifest, ())

    assert summary == {
        "manifest_id": "manifest-diagnostics",
        "run_id": str(manifest.run_id),
        "pipeline_name": "chembl_activity",
        "provider": "chembl",
        "entity": "activity",
        "execution_fingerprint": "fingerprint-diagnostics",
        "config_hash": _VALID_CONFIG_HASH,
        "effective_config_hash": _VALID_CONFIG_HASH,
        "pipeline_version": "1.0.0",
        "contract_ref": "chembl.activity",
        "contract_version": "1.2.0",
        "dq_policy_ref": "chembl_activity.gold",
        "rule_bundle_version": "2026.03",
        "dq_contract_compatibility_hash": "compat-hash-1",
        "effective_config_artifact_id": "eca-123",
        "replay_capability": "rebuild_only",
        "requested_exact_replay": False,
        "exact_replay_support_boundary": "snapshot_backed_source_runs_only",
        "replay_capability_reason": "immutable_input_snapshots_missing",
        "exact_replay_eligible": False,
        "exact_replay_blockers": ["immutable_input_snapshots_missing"],
        "input_snapshot_ids": [],
        "input_snapshot_content_hashes": [],
        "input_snapshot_identity_fingerprint": None,
        "replay_mode": "live_fetch",
        "input_snapshot_count": 0,
        "input_snapshots": [],
        "planned_artifacts": [],
        "occurrence_only_diagnostics": [],
        "persistence_profile": {
            "attained_profile": "degraded_observable",
            "claims": {
                "degraded_observable": True,
                "replay_ready": False,
                "forensic_grade": False,
            },
            "surfaces": {
                "control_plane_manifest": True,
                "effective_config_artifact": True,
                "strict_replay_execution_context_support": True,
                "immutable_input_snapshots": False,
                "exact_replay_capability": False,
                "run_ledger_history": False,
                "artifact_lineage_links": True,
            },
            "replay_ready_missing_requirements": [
                "exact_replay_capability",
                "immutable_input_snapshots",
            ],
            "forensic_grade_missing_requirements": [
                "exact_replay_capability",
                "immutable_input_snapshots",
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
            },
        },
        "alert_signals": {
            "run_failed": False,
            "run_shutdown": False,
            "artifact_linkage_gap": False,
            "lineage_gap": False,
            "immutable_input_snapshot_gap": True,
            "strict_replay_boundary_gap": False,
            "composite_resume_reconstructability_gap": False,
            "replay_ready_gap": True,
            "forensic_grade_gap": True,
            "dq_signal_present": False,
            "cross_validation_signal_present": False,
        },
        "next_steps": [
            "Persist immutable cached Bronze input snapshots before treating this run as strict exact-replay capable.",
            "Review replay-ready persistence requirements before treating this run as exact-replay capable.",
            "Review forensic-grade persistence requirements before using this run for full trace/debug reconstruction.",
        ],
    }


def test_build_diagnostics_summary_distinguishes_resume_only_runs() -> None:
    manifest = replace(
        _make_manifest(),
        launch_context={"limit": 25, "resume": True, "exact_replay": False},
        replay_capability=ReplayCapability.RESUME_ONLY,
    )

    summary = build_diagnostics_summary(manifest, ())

    assert summary["replay_capability"] == "resume_only"
    assert summary["requested_exact_replay"] is False
    assert summary["exact_replay_support_boundary"] == "snapshot_backed_source_runs_only"
    assert (
        summary["replay_capability_reason"]
        == "resume_requested_without_snapshot_backed_inputs"
    )
    assert summary["exact_replay_eligible"] is False
    assert summary["exact_replay_blockers"] == ["immutable_input_snapshots_missing"]
    assert summary["input_snapshot_ids"] == []
    assert summary["input_snapshot_content_hashes"] == []
    assert summary["input_snapshot_identity_fingerprint"] is None
    assert summary["replay_mode"] == "resume"
    assert summary["input_snapshot_count"] == 0
    assert summary["input_snapshots"] == []


def test_build_diagnostics_summary_distinguishes_snapshot_backed_runs_from_exact_replay() -> None:
    manifest = replace(
        _make_manifest(),
        launch_context={"limit": 25, "resume": False, "exact_replay": False},
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
                        immutable_uri="file:///tmp/bronze/batch_1.jsonl.zst",
                    ),
                ),
            ),
        ),
    )

    summary = build_diagnostics_summary(manifest, ())

    assert summary["replay_capability"] == "exact_replay_supported"
    assert summary["requested_exact_replay"] is False
    assert summary["exact_replay_support_boundary"] == "snapshot_backed_source_runs_only"
    assert summary["exact_replay_eligible"] is True
    assert summary["replay_mode"] == "snapshot_backed_run"
    assert summary["exact_replay_blockers"] == []
    assert summary["input_snapshot_ids"] == ["snapshot-1"]


def test_build_diagnostics_summary_does_not_report_exact_replay_from_intent_alone() -> None:
    manifest = replace(
        _make_manifest(),
        launch_context={"limit": 25, "resume": False, "exact_replay": True},
        replay_capability=ReplayCapability.REBUILD_ONLY,
        source_refs=(),
    )

    summary = build_diagnostics_summary(manifest, ())

    assert summary["requested_exact_replay"] is True
    assert summary["exact_replay_support_boundary"] == "snapshot_backed_source_runs_only"
    assert summary["exact_replay_eligible"] is False
    assert summary["replay_mode"] == "live_fetch"
    assert summary["exact_replay_blockers"] == ["immutable_input_snapshots_missing"]


@pytest.mark.parametrize(
    ("terminal_status", "expected_event_type", "signal_key"),
    [
        ("success", "run_finished", None),
        ("failed", "run_failed", "run_failed"),
        ("shutdown", "run_shutdown", "run_shutdown"),
    ],
)
def test_build_diagnostics_summary_exposes_required_operator_fields(
    terminal_status: str,
    expected_event_type: str,
    signal_key: str | None,
) -> None:
    manifest = _make_manifest()
    ledger_entries = _build_ledger_entries(
        manifest,
        terminal_status=terminal_status,
    )

    summary = build_diagnostics_summary(manifest, ledger_entries)

    assert summary["latest_status"] == terminal_status
    assert summary["latest_event_type"] == expected_event_type
    assert summary["event_family_counts"] == {
        "artifact": 1,
        "diagnostic": 1,
        "pipeline.lifecycle": 2,
        "pipeline.phase": 1,
    }
    assert summary["event_type_counts"][expected_event_type] == 1
    assert summary["artifact_refs"] == [
        {
            "event_type": "artifact_published",
            "stage": "silver",
            "artifact_id": "silver:chembl.activity@1",
            "dataset_ref": "silver:chembl.activity@1",
            "lineage_fragment_id": "silver:fragment-1",
            "artifact_path": "data/output/silver/chembl/activity",
        }
    ]
    assert summary["planned_artifact_count"] == 0
    assert summary["published_artifact_count"] == 1
    assert summary["missing_artifact_links"] == 0
    assert summary["identity_graph_complete"] is True
    assert summary["identity_graph"] == {
        "run_id": str(manifest.run_id),
        "manifest_id": "manifest-diagnostics",
        "execution_fingerprint": "fingerprint-diagnostics",
        "effective_config_hash": _VALID_CONFIG_HASH,
        "contract_ref": "chembl.activity",
        "contract_version": "1.2.0",
        "canonical_execution_identity": _expected_canonical_execution_identity(
            manifest
        ),
        "degraded_runtime_anchor": _expected_degraded_runtime_anchor(manifest),
        "replay_capability": "rebuild_only",
        "requested_exact_replay": False,
        "exact_replay_support_boundary": "snapshot_backed_source_runs_only",
        "replay_capability_reason": "immutable_input_snapshots_missing",
        "exact_replay_eligible": False,
        "exact_replay_blockers": ["immutable_input_snapshots_missing"],
        "input_snapshot_ids": [],
        "input_snapshot_content_hashes": [],
        "input_snapshot_identity_fingerprint": None,
        "replay_mode": "live_fetch",
        "input_snapshot_count": 0,
        "input_snapshots": [],
        "planned_artifacts": [],
        "published_artifacts": [
            {
                "event_type": "artifact_published",
                "stage": "silver",
                "dataset_ref": "silver:chembl.activity@1",
                "lineage_fragment_id": "silver:fragment-1",
                "artifact_path": "data/output/silver/chembl/activity",
            }
        ],
        "occurrence_only_diagnostics": [],
    }
    assert summary["persistence_profile"] == {
        "attained_profile": "degraded_observable",
        "claims": {
            "degraded_observable": True,
            "replay_ready": False,
            "forensic_grade": False,
        },
            "surfaces": {
                "control_plane_manifest": True,
                "effective_config_artifact": True,
                "strict_replay_execution_context_support": True,
                "immutable_input_snapshots": False,
                "exact_replay_capability": False,
                "run_ledger_history": True,
            "artifact_lineage_links": True,
        },
        "replay_ready_missing_requirements": [
            "exact_replay_capability",
            "immutable_input_snapshots",
        ],
        "forensic_grade_missing_requirements": [
            "exact_replay_capability",
            "immutable_input_snapshots",
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
        },
    }
    assert summary["correlation_anchor_gaps"] == {
        "effective_config_hash": 0,
        "contract_ref": 0,
        "contract_version": 0,
        "composite_run_id": 0,
    }
    assert summary["cross_validation_signal_present"] is False
    assert summary["occurrence_only_diagnostics"] == []
    alert_signals = summary["alert_signals"]
    assert isinstance(alert_signals, dict)
    assert alert_signals["artifact_linkage_gap"] is False
    assert alert_signals["lineage_gap"] is False
    assert alert_signals["immutable_input_snapshot_gap"] is True
    assert alert_signals["strict_replay_boundary_gap"] is False
    assert alert_signals["composite_resume_reconstructability_gap"] is False
    assert alert_signals["replay_ready_gap"] is True
    assert alert_signals["forensic_grade_gap"] is True
    assert alert_signals["dq_signal_present"] is False
    assert alert_signals["cross_validation_signal_present"] is False
    if signal_key is None:
        assert alert_signals["run_failed"] is False
        assert alert_signals["run_shutdown"] is False
        assert summary["next_steps"] == [
            "Persist immutable cached Bronze input snapshots before treating this run as strict exact-replay capable.",
            "Review replay-ready persistence requirements before treating this run as exact-replay capable.",
            "Review forensic-grade persistence requirements before using this run for full trace/debug reconstruction.",
        ]
    else:
        assert alert_signals[signal_key] is True
        assert "No alert signals detected" not in summary["next_steps"]


def test_build_diagnostics_summary_accepts_legacy_data_contract_version_alias() -> None:
    manifest = _make_manifest()
    entry = RunLedgerEntry(
        entry_id="entry-legacy-alias",
        manifest_id=manifest.manifest_id,
        run_id=manifest.run_id,
        event_type="run_finished",
        event_family="pipeline.lifecycle",
        occurred_at=datetime.now(UTC),
        status="success",
        details={
            "_diagnostic": {
                "diagnostic_contract_version": "v1",
                "effective_config_hash": _VALID_CONFIG_HASH,
                "contract_ref": "chembl.activity",
                "data_contract_version": "1.2.0",
            }
        },
    )

    summary = build_diagnostics_summary(manifest, (entry,))

    assert summary["correlation_anchor_gaps"]["contract_version"] == 0


def test_build_diagnostics_summary_formalizes_composite_exact_replay_boundary() -> None:
    manifest = replace(
        _make_manifest(),
        provider="composite",
        entity="publications",
        pipeline_name="publications",
        launch_context={
            "resume": False,
            "exact_replay": False,
            "execution_context": "composite",
            "exact_replay_support_boundary": "composite_execution_unsupported",
        },
        replay_capability=ReplayCapability.REBUILD_ONLY,
        source_refs=(),
    )

    summary = build_diagnostics_summary(manifest, ())

    assert summary["exact_replay_support_boundary"] == "composite_execution_unsupported"
    assert (
        summary["replay_capability_reason"]
        == "exact_replay_not_supported_for_composite_execution"
    )
    assert summary["exact_replay_blockers"] == [
        "exact_replay_not_supported_for_composite_execution",
        "immutable_input_snapshots_missing",
    ]
    assert summary["persistence_profile"]["surfaces"] == {
        "control_plane_manifest": True,
        "effective_config_artifact": True,
        "strict_replay_execution_context_support": False,
        "immutable_input_snapshots": False,
        "exact_replay_capability": False,
        "run_ledger_history": False,
        "artifact_lineage_links": True,
    }
    assert summary["persistence_profile"]["replay_ready_missing_requirements"] == [
        "strict_replay_execution_context_support",
        "exact_replay_capability",
        "immutable_input_snapshots",
    ]
    assert summary["alert_signals"]["strict_replay_boundary_gap"] is True
    assert summary["alert_signals"]["composite_resume_reconstructability_gap"] is True
    assert summary["next_steps"] == [
        "Persist immutable cached Bronze input snapshots before treating this run as strict exact-replay capable.",
        "Treat this execution context as outside the strict exact-replay support boundary; use rebuild/resume semantics instead of exact replay.",
        "Treat composite resume as checkpoint snapshot plus ledger suffix replay only; do not expect per-provider result maps or other rich checkpoint payloads to be reconstructed.",
        "Review replay-ready persistence requirements before treating this run as exact-replay capable.",
        "Review forensic-grade persistence requirements before using this run for full trace/debug reconstruction.",
    ]
