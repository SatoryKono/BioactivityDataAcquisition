"""Pure helper branch coverage for control-plane identity and selector payloads."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from bioetl.domain.control_plane import RunCodeProvenance, RunLedgerEntry, RunManifest
from bioetl.domain.control_plane.run_ledger import (
    RUN_FAILED_EVENT,
    RUN_FINISHED_EVENT,
    RUN_STARTED_EVENT,
)
from bioetl.domain.types import RunType
from bioetl.interfaces.http import _control_plane_selector_payloads as selector_payloads
from bioetl.interfaces.http import _control_plane_selector_records as selector_records
from bioetl.interfaces.http.control_plane_identity import formatting
from bioetl.interfaces.http.control_plane_identity import payload as identity_payload
from tests.helpers.deterministic_ids import deterministic_run_uuid_from_callsite


pytestmark = pytest.mark.unit


_NOW = datetime(2026, 7, 6, 9, 15, tzinfo=UTC)


def _manifest(
    suffix: str,
    *,
    pipeline_name: str = "chembl_activity",
    run_type: RunType = RunType.INCREMENTAL,
    launch_context: dict[str, object] | None = None,
    runtime_config: dict[str, object] | None = None,
    resolved_config: dict[str, object] | None = None,
) -> RunManifest:
    return RunManifest(
        manifest_id=f"manifest-{suffix}",
        execution_fingerprint=f"fingerprint-{suffix}",
        schema_version="1.0",
        created_at=_NOW + timedelta(minutes=int(suffix)),
        run_id=deterministic_run_uuid_from_callsite(f"identity-helper-{suffix}"),
        run_type=run_type,
        pipeline_name=pipeline_name,
        provider=pipeline_name.split("_", 1)[0],
        entity=pipeline_name.split("_", 1)[-1],
        launch_context=launch_context or {},
        runtime_config=runtime_config or {},
        resolved_config=resolved_config or {},
        code_provenance=RunCodeProvenance(git_commit=f"commit-{suffix}"),
    )


def _ledger_entry(
    manifest: RunManifest,
    suffix: str,
    *,
    event_type: str = RUN_FINISHED_EVENT,
    occurred_offset: int = 0,
    status: str | None = "success",
) -> RunLedgerEntry:
    return RunLedgerEntry(
        entry_id=f"entry-{suffix}",
        manifest_id=manifest.manifest_id,
        run_id=manifest.run_id,
        event_type=event_type,
        occurred_at=manifest.created_at + timedelta(minutes=occurred_offset),
        status=status,
    )


class _LedgerLookup:
    def __init__(self, entries: dict[str, list[RunLedgerEntry]]) -> None:
        self._entries = entries

    def list_entries_by_run_id(self, run_id: object) -> list[RunLedgerEntry]:
        return list(self._entries.get(str(run_id), ()))


class _LedgerByManifest:
    def __init__(self, entries: dict[str, list[RunLedgerEntry]]) -> None:
        self._entries = entries

    def list_entries(self, manifest_id: str) -> list[RunLedgerEntry]:
        return list(self._entries.get(manifest_id, ()))


def test_identity_formatting_helpers_cover_absent_nested_and_validator_edges() -> None:
    assert formatting.stable_hash("") is None
    assert formatting.stable_hash({"b": 2, "a": 1}) == formatting.stable_hash(
        {"a": 1, "b": 2}
    )
    assert formatting.short_value(None) == ""
    assert formatting.short_value("a, b, , c") == "3 items"
    assert formatting.short_value("123456789012345") == "123456789012"
    assert formatting.short_value("short") == "short"

    assert formatting.format_full_value(None) == ""
    assert formatting.format_full_value(True) == "true"
    assert formatting.format_full_value(False) == "false"
    assert formatting.format_full_value(3.5) == "3.5"
    assert formatting.format_full_value(["a", None, " b "]) == "a,  b "
    assert formatting.format_full_value({"b": 2, "a": 1}) == '{"a": 1, "b": 2}'
    assert formatting.format_full_value(" value ") == "value"

    assert formatting.is_present(None) is False
    assert formatting.is_present(" none ") is False
    assert formatting.is_present(" null ") is False
    assert formatting.is_present(" value ") is True
    assert formatting.is_present(()) is False
    assert formatting.is_present(["value"]) is True
    assert formatting.is_present({}) is False
    assert formatting.is_present({"key": "value"}) is True
    assert formatting.is_present(0) is True

    values: list[str] = ["existing"]
    formatting.append_value(values, None)
    formatting.append_value(values, [" run-1 ", ("run-2", "", None)])
    assert values == ["existing", "run-1", "run-2"]
    assert formatting.dedupe([None, " a ", "a", "", "b"]) == ["a", "b"]
    assert formatting.join_non_empty([" run ", None, "manifest"], " / ") == (
        "run / manifest"
    )
    assert formatting.join_non_empty(["", None], " / ") is None
    assert formatting.mapping_value({"a": 1}, "a", "missing") == {}
    assert formatting.mapping_value({"a": {"x": 1}}, "a") == {"x": 1}
    assert formatting.validate_run_id_format(
        "00000000-0000-0000-0000-000000000000"
    )
    assert not formatting.validate_run_id_format("not-a-uuid")
    assert formatting.validate_manifest_id_format("manifest-1")
    assert not formatting.validate_manifest_id_format("manifest-")
    assert formatting.validate_provider_entity_format("chembl.activity")
    assert not formatting.validate_provider_entity_format("Chembl.activity")


def test_selector_record_helpers_cover_scope_terminal_and_workflow_edges() -> None:
    first = _manifest(
        "1",
        launch_context={"workflow_name": "wf-a", "workflow": "wf-a"},
        runtime_config={"workflow_name": "wf-runtime", "workflow": ""},
        resolved_config={"workflow": "wf-resolved"},
    )
    second = _manifest(
        "2",
        pipeline_name="pubchem_compound",
        run_type=RunType.BACKFILL,
        launch_context={"workflow": "wf-b"},
    )
    third = _manifest("3", pipeline_name="chembl_activity")
    finished = _ledger_entry(first, "finished", occurred_offset=5, status="success")
    failed_later = _ledger_entry(first, "failed", event_type=RUN_FAILED_EVENT, occurred_offset=6)
    started = _ledger_entry(first, "started", event_type=RUN_STARTED_EVENT)
    ledger = _LedgerLookup({str(first.run_id): [started, finished, failed_later]})

    records = selector_records.build_selector_records((first, second, third), ledger)
    selected = records[0]

    assert selected.workflow == "wf-a"
    assert selected.workflow_candidates == (
        "wf-a",
        "wf-runtime",
        "wf-resolved",
        "chembl_activity",
        "workflow_chembl_activity",
    )
    assert selected.completed_at == failed_later.occurred_at
    assert selected.completed_at_source == "run_ledger_terminal_event"
    assert selected.run_status == "success"
    assert selected.terminal_event_type == RUN_FAILED_EVENT

    no_terminal = selector_records.build_selector_records((second,), ledger)[0]
    assert no_terminal.completed_at == second.created_at
    assert no_terminal.completed_at_source == "manifest_created_at_fallback"
    assert no_terminal.run_status == "unknown"
    assert no_terminal.terminal_event_type is None

    assert selector_records.selected_pipeline_scope(("chembl_activity",), None) == (
        "chembl_activity",
    )
    assert selector_records.selected_pipeline_scope((), None) == ()
    assert selector_records.selected_pipeline_scope((), "$__all") == ()
    assert selector_records.selected_pipeline_scope((), "pubchem_compound") == (
        "pubchem_compound",
    )
    assert selector_records.narrow_manifest_catalog(
        (first, second, third),
        selected_workflows=(),
        selected_pipelines=("chembl_activity",),
        selected_run_types=(),
        selected_run_id=None,
    ) == (first, third)
    assert selector_records.narrow_manifest_catalog(
        (first, second, third),
        selected_workflows=(),
        selected_pipelines=(),
        selected_run_types=("backfill",),
        selected_run_id=None,
    ) == (second,)
    assert selector_records.narrow_manifest_catalog(
        (first, second, third),
        selected_workflows=("wf-resolved",),
        selected_pipelines=(),
        selected_run_types=(),
        selected_run_id=None,
    ) == (first,)
    assert selector_records.narrow_manifest_catalog(
        (first, second),
        selected_workflows=(),
        selected_pipelines=(),
        selected_run_types=(),
        selected_run_id=str(second.run_id),
    ) == (second,)
    assert selector_records.narrow_manifest_catalog(
        (first, second),
        selected_workflows=("missing",),
        selected_pipelines=(),
        selected_run_types=(),
        selected_run_id=None,
    ) == (first, second)
    assert selector_records.narrow_manifest_catalog(
        (first, second),
        selected_workflows=("missing",),
        selected_pipelines=(),
        selected_run_types=(),
        selected_run_id=None,
        fail_open_when_empty=False,
    ) == ()


def test_selector_payload_helpers_cover_empty_selected_and_ordering_edges() -> None:
    first = _manifest("1", launch_context={"workflow": "wf-a"})
    second = _manifest("2", launch_context={"workflow": "wf-b"})
    newer_duplicate = _manifest("3", launch_context={"workflow": "wf-a"})
    terminal = _ledger_entry(first, "terminal")
    ledger = _LedgerLookup({str(first.run_id): [terminal]})
    first_record, second_record, duplicate_record = selector_records.build_selector_records(
        (first, second, newer_duplicate),
        ledger,
    )

    assert selector_payloads.resolved_via(None, None) == "no_manifest_for_scope"
    assert selector_payloads.resolved_via(first_record, str(first.run_id)) == (
        "selected_run_id"
    )
    assert selector_payloads.resolved_via(first_record, None) == (
        "latest_terminal_run_for_scope"
    )
    assert selector_payloads.resolved_via(second_record, None) == (
        "latest_manifest_created_at_for_scope"
    )

    assert selector_payloads.selected_payload(None) == {
        "workflow": "All",
        "pipeline": "unknown",
        "run_type": "All",
        "run_id": "-",
        "run_status": "unknown",
        "provider": "unknown",
        "entity": "unknown",
        "manifest_id": "",
        "completed_at": "",
        "completed_at_source": "none",
        "terminal_event_type": "",
    }
    payload = selector_payloads.selected_payload(first_record)
    assert payload["workflow"] == "wf-a"
    assert payload["terminal_event_type"] == RUN_FINISHED_EVENT
    assert payload["completed_at"] == terminal.occurred_at.isoformat()

    options = selector_payloads.options_payload(
        (first_record, second_record, duplicate_record)
    )
    assert options["workflow"] == ["wf-a", "wf-b"]
    assert options["run_id"] == [
        str(first.run_id),
        str(second.run_id),
        str(newer_duplicate.run_id),
    ]
    assert options["run_status"] == ["unknown", "success"]

    assert selector_payloads.exact_run_only_fallback_values(None) == []
    assert selector_payloads.exact_run_only_fallback_values("  ") == []
    assert selector_payloads.exact_run_only_fallback_values(" run-1 ") == ["run-1"]

    mixed = selector_payloads._latest_ordered_values(
        (first_record, second_record),
        lambda record: ("unknown", record.workflow),
    )
    assert mixed == ["wf-b", "wf-a"]
    with_unknown = selector_payloads._latest_ordered_values(
        (first_record,),
        lambda _record: ("unknown",),
        skip_unknown=False,
    )
    assert with_unknown == ["unknown"]
    assert selector_payloads._manifest_ordered_values(
        (first_record, first_record, second_record),
        lambda record: record.run_id,
    ) == [first_record.run_id, second_record.run_id]


def test_identity_payload_helpers_cover_validation_rows_and_summary_edges() -> None:
    manifest = _manifest("4", launch_context={"exact_replay": True})
    entry = _ledger_entry(manifest, "identity")
    ledger = _LedgerByManifest({manifest.manifest_id: [entry]})

    assert identity_payload.validate_identity_payload({}) == (
        False,
        [
            "missing required identity field: run_id",
            "missing required identity field: manifest_id",
            "missing required identity field: pipeline_name",
        ],
    )
    assert identity_payload.validate_identity_payload(
        {
            "run_id": str(manifest.run_id),
            "manifest_id": manifest.manifest_id,
            "pipeline_name": manifest.pipeline_name,
        }
    ) == (True, [])
    assert identity_payload.ledger_entries_for(None, ledger) == ()
    assert identity_payload.ledger_entries_for(manifest, None) == ()
    assert identity_payload.ledger_entries_for(manifest, ledger) == (entry,)

    anchors = [
        {
            "name": "run_id",
            "priority": "P0",
            "identity_gap": True,
            "missing_severity": "FAILING",
            "ui_status": "CRIT",
            "copy": True,
        },
        {
            "name": "resolved_config_hash",
            "priority": "P1",
            "identity_gap": True,
            "missing_severity": "WARNING",
            "ui_status": "WARN",
            "copy": False,
        },
        {
            "name": "identity_graph_complete",
            "priority": "P0",
            "identity_gap": True,
            "missing_severity": "FAILING",
            "ui_status": "CRIT",
            "copy": False,
        },
    ]
    assert [row["name"] for row in identity_payload.identity_graph_gap_rows(anchors)] == [
        "run_id"
    ]
    assert [row["name"] for row in identity_payload.identity_evidence_gap_rows(anchors)] == [
        "run_id",
        "resolved_config_hash",
    ]
    assert identity_payload.gap_count_from_mapping(None) == 0
    assert identity_payload.gap_count_from_mapping(
        {"numeric": 2, "boolean": True, "empty": [], "text": "gap"}
    ) == 4

    summary = identity_payload.build_summary(
        manifest=manifest,
        anchors=anchors,
        values={
            "correlation_anchor_gaps": {"input_snapshot": 2},
            "identity_graph_complete": False,
            "exact_replay_blockers": ["checkpoint"],
        },
        checkpoint_status="PARTIAL",
        resolved_via="selected_run_id",
    )
    assert summary["overall_status"] == "CRIT"
    assert summary["identity_graph_complete"] is False
    assert summary["identity_gap_count"] == 3
    assert summary["evidence_gap_count"] == 4
    assert summary["replay_mode"] == "exact_replay"

    unknown_summary = identity_payload.build_summary(
        manifest=None,
        anchors=[],
        values={},
        checkpoint_status="UNKNOWN",
        resolved_via="no_manifest_for_scope",
    )
    assert unknown_summary["overall_status"] == "UNKNOWN"
    assert unknown_summary["replay_mode"] is None

    diagnostics = identity_payload.build_identity_diagnostics(
        anchors=anchors,
        values={"correlation_anchor_gaps": {"a": 1}},
        checkpoint_status="OK",
    )
    assert diagnostics["identity_gap_names"] == ["run_id", "resolved_config_hash"]
    assert diagnostics["identity_gap_count"] == 3

    assert [row["name"] for row in identity_payload.select_rows(
        view=" gaps ",
        priority=None,
        anchors=anchors,
        checkpoint_rows=[],
    )] == ["run_id", "resolved_config_hash", "identity_graph_complete"]
    assert identity_payload.select_rows(
        view="copy_values",
        priority="p0",
        anchors=anchors,
        checkpoint_rows=[],
    ) == [anchors[0]]
    assert identity_payload.select_rows(
        view="checkpoint_compare",
        priority=None,
        anchors=anchors,
        checkpoint_rows=[{"status": "OK"}],
    ) == [{"status": "OK"}]
    assert identity_payload.select_rows(
        view="checkpoint_compare",
        priority=None,
        anchors=anchors,
        checkpoint_rows={"status": "OK"},
    ) == []
