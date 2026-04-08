"""Unit tests for run-manifest diagnostics summary helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from bioetl.application.services.run_ledger_service import RunLedgerService
from bioetl.application.services.run_manifest_diagnostics import (
    build_diagnostics_summary,
)
from bioetl.domain.control_plane import RunCodeProvenance, RunLedgerEntry, RunManifest
from bioetl.domain.ports import RunLedgerPort
from bioetl.domain.types import RunID, RunType


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
            config_hash="deadbeef",
            contract_ref="chembl.activity",
            contract_version="1.2.0",
            dq_policy_ref="chembl_activity.gold",
            rule_bundle_version="2026.03",
            dq_contract_compatibility_hash="compat-hash-1",
            effective_config_artifact_id="eca-123",
        ),
    )


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
        "execution_fingerprint": "fingerprint-diagnostics",
        "config_hash": "deadbeef",
        "effective_config_hash": "deadbeef",
        "contract_ref": "chembl.activity",
        "contract_version": "1.2.0",
        "dq_policy_ref": "chembl_activity.gold",
        "rule_bundle_version": "2026.03",
        "dq_contract_compatibility_hash": "compat-hash-1",
        "effective_config_artifact_id": "eca-123",
    }


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
            "dataset_ref": "silver:chembl.activity@1",
            "lineage_fragment_id": "silver:fragment-1",
            "artifact_path": "data/output/silver/chembl/activity",
        }
    ]
    assert summary["missing_artifact_links"] == 0
    assert summary["correlation_anchor_gaps"] == {
        "effective_config_hash": 0,
        "contract_ref": 0,
        "data_contract_version": 0,
        "composite_run_id": 0,
    }
    assert summary["cross_validation_signal_present"] is False
    alert_signals = summary["alert_signals"]
    assert isinstance(alert_signals, dict)
    assert alert_signals["artifact_linkage_gap"] is False
    assert alert_signals["lineage_gap"] is False
    assert alert_signals["dq_signal_present"] is False
    assert alert_signals["cross_validation_signal_present"] is False
    if signal_key is None:
        assert alert_signals["run_failed"] is False
        assert alert_signals["run_shutdown"] is False
        assert summary["next_steps"] == [
            "No alert signals detected; continue routine monitoring."
        ]
    else:
        assert alert_signals[signal_key] is True
        assert "No alert signals detected" not in summary["next_steps"]
