# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Pure helper branch coverage for control-plane identity and selector payloads."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from bioetl.domain.control_plane import (
    RunArtifactRef,
    RunCodeProvenance,
    RunInputSnapshotRef,
    RunLedgerEntry,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.control_plane.run_ledger import (
    ARTIFACT_PUBLISHED_EVENT,
    COMPOSITE_DEPENDENCY_COMPLETED_EVENT,
    RUN_FAILED_EVENT,
    RUN_FINISHED_EVENT,
    RUN_STARTED_EVENT,
)
from bioetl.domain.types import RunType
from bioetl.interfaces.http import _control_plane_selector_payloads as selector_payloads
from bioetl.interfaces.http import _control_plane_selector_records as selector_records
from bioetl.interfaces.http.control_plane_identity import formatting
from bioetl.interfaces.http.control_plane_identity import payload as identity_payload
from bioetl.interfaces.http.control_plane_identity import checkpoint
from bioetl.interfaces.http.control_plane_identity import checkpoint_extractors
from bioetl.interfaces.http.control_plane_identity import ledger_extractors
from bioetl.interfaces.http.control_plane_identity import manifest_extractors
from bioetl.interfaces.http.control_plane_identity import severity
from bioetl.interfaces.http.control_plane_identity.specs import SPEC_BY_NAME
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
    code_provenance: RunCodeProvenance | None = None,
    source_refs: tuple[RunSourceRef, ...] = (),
    planned_artifacts: tuple[RunArtifactRef, ...] = (),
    replay_of_run_id: str | None = None,
    replay_of_manifest_id: str | None = None,
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
        code_provenance=code_provenance
        or RunCodeProvenance(git_commit=f"commit-{suffix}"),
        replay_of_run_id=replay_of_run_id,
        replay_of_manifest_id=replay_of_manifest_id,
        source_refs=source_refs,
        planned_artifacts=planned_artifacts,
    )


def _ledger_entry(
    manifest: RunManifest,
    suffix: str,
    *,
    event_type: str = RUN_FINISHED_EVENT,
    occurred_offset: int = 0,
    status: str | None = "success",
    details: dict[str, object] | None = None,
    lineage_fragment_id: str | None = None,
) -> RunLedgerEntry:
    return RunLedgerEntry(
        entry_id=f"entry-{suffix}",
        manifest_id=manifest.manifest_id,
        run_id=manifest.run_id,
        event_type=event_type,
        occurred_at=manifest.created_at + timedelta(minutes=occurred_offset),
        status=status,
        details=details,
        lineage_fragment_id=lineage_fragment_id,
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
    # UUID v4 only (nil UUID is version 0 and must be rejected).
    assert formatting.validate_run_id_format("550e8400-e29b-41d4-a716-446655440000")
    assert not formatting.validate_run_id_format("00000000-0000-0000-0000-000000000000")
    assert not formatting.validate_run_id_format("not-a-uuid")
    # Equal sets must hash identically regardless of construction order.
    assert formatting.stable_hash({"a", "b"}) == formatting.stable_hash({"b", "a"})
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
    failed_later = _ledger_entry(
        first, "failed", event_type=RUN_FAILED_EVENT, occurred_offset=6
    )
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
    assert (
        selector_records.narrow_manifest_catalog(
            (first, second),
            selected_workflows=("missing",),
            selected_pipelines=(),
            selected_run_types=(),
            selected_run_id=None,
            fail_open_when_empty=False,
        )
        == ()
    )


def test_selector_payload_helpers_cover_empty_selected_and_ordering_edges() -> None:
    first = _manifest("1", launch_context={"workflow": "wf-a"})
    second = _manifest("2", launch_context={"workflow": "wf-b"})
    newer_duplicate = _manifest("3", launch_context={"workflow": "wf-a"})
    terminal = _ledger_entry(first, "terminal")
    ledger = _LedgerLookup({str(first.run_id): [terminal]})
    first_record, second_record, duplicate_record = (
        selector_records.build_selector_records(
            (first, second, newer_duplicate),
            ledger,
        )
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
        "run_type": "backfill",
        "run_id": "-",
        "run_status": "unknown",
        "provider": "unknown",
        "entity": "unknown",
        "manifest_id": "",
        "started_at": "",
        "started_at_source": "none",
        "completed_at": "",
        "completed_at_source": "none",
        "terminal_event_type": "",
    }
    payload = selector_payloads.selected_payload(first_record)
    assert payload["workflow"] == "wf-a"
    assert payload["terminal_event_type"] == RUN_FINISHED_EVENT
    assert payload["completed_at"] == terminal.occurred_at.isoformat()
    assert payload["started_at"] == first.created_at.isoformat()
    assert payload["started_at_source"] == "manifest_created_at_fallback"

    options = selector_payloads.options_payload(
        (first_record, second_record, duplicate_record)
    )
    assert options["workflow"] == ["wf-a", "wf-b"]
    # Newest started_at first (manifest suffix minutes 3, 2, 1).
    assert options["run_id"] == [
        str(newer_duplicate.run_id),
        str(second.run_id),
        str(first.run_id),
    ]
    assert options["run_status"] == ["unknown", "success"]
    assert selector_payloads.defaults_payload()["run_type_fallback"] == "backfill"
    assert (
        selector_payloads.defaults_payload()["run_id_list_order"] == "started_at_desc"
    )

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
    ) == [second_record.run_id, first_record.run_id]


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
    assert [
        row["name"] for row in identity_payload.identity_graph_gap_rows(anchors)
    ] == ["run_id"]
    assert [
        row["name"] for row in identity_payload.identity_evidence_gap_rows(anchors)
    ] == [
        "run_id",
        "resolved_config_hash",
    ]
    assert identity_payload.gap_count_from_mapping(None) == 0
    assert (
        identity_payload.gap_count_from_mapping(
            {"numeric": 2, "boolean": True, "empty": [], "text": "gap"}
        )
        == 4
    )

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

    assert [
        row["name"]
        for row in identity_payload.select_rows(
            view=" gaps ",
            priority=None,
            anchors=anchors,
            checkpoint_rows=[],
        )
    ] == ["run_id", "resolved_config_hash", "identity_graph_complete"]
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
    assert (
        identity_payload.select_rows(
            view="checkpoint_compare",
            priority=None,
            anchors=anchors,
            checkpoint_rows={"status": "OK"},
        )
        == []
    )


def _identity_edge_fixture() -> tuple[
    RunManifest,
    RunLedgerEntry,
    RunLedgerEntry,
    RunInputSnapshotRef,
    RunSourceRef,
]:
    snapshot = RunInputSnapshotRef(
        snapshot_id="snapshot-1",
        content_hash="hash-1",
        immutable_uri="s3://bucket/key",
        query_fingerprint="query-1",
    )
    source_ref = RunSourceRef(
        provider="chembl",
        entity="activity",
        pipeline_name="chembl_activity",
        input_snapshots=(snapshot,),
    )
    manifest = _manifest(
        "5",
        pipeline_name="composite_activity",
        launch_context={
            "exact_replay": True,
            "identity_graph": {"launch_only": "yes"},
            "dq_report_path": "dq-launch.json",
        },
        runtime_config={
            "workflow": "wf-runtime",
            "checkpoint_metadata": {
                "records_processed": 10,
                "manifest_id": "manifest-5",
                "execution_fingerprint": "fingerprint-5",
                "effective_config_hash": "config-hash",
                "effective_config_artifact_id": "artifact-5",
                "composite_run_identity": "composite-5",
            },
        },
        resolved_config={
            "identity_graph_diagnostics": {
                "identity_graph_complete": False,
                "correlation_anchor_gaps": {"run_id": 1},
                "exact_replay_blockers": ["input_snapshot_ids"],
            },
            "reproducibility": {
                "checkpoint_anchors": {
                    "checkpoint": {
                        "records_processed": 11,
                        "manifest_id": "manifest-nested",
                    }
                }
            },
        },
        code_provenance=RunCodeProvenance(
            git_commit="commit-5",
            effective_config_hash="config-hash",
            effective_config_artifact_id="artifact-5",
            contract_ref="chembl.activity",
            contract_version="2026.07",
            contract_schema_hash="schema-hash",
        ),
        source_refs=(source_ref,),
        planned_artifacts=(RunArtifactRef(layer="gold", path="gold/activity"),),
        replay_of_run_id="run-parent",
    )
    composite_entry = _ledger_entry(
        manifest,
        "composite",
        event_type=COMPOSITE_DEPENDENCY_COMPLETED_EVENT,
        details={
            "artifact_ref": "gold/activity",
            "artifact_path": ["silver/activity", ""],
            "component_run_id": "component-1",
            "component_run_ids": ["component-2", "component-1"],
            "dq_report_paths": ["dq-ledger.json"],
            "bronze_batch_ids": ["batch-ledger"],
        },
        lineage_fragment_id="lineage-1",
    )
    plain_entry = _ledger_entry(
        manifest,
        "plain",
        event_type=RUN_STARTED_EVENT,
        status="running",
        details={"uri": "ignored/for/component", "source_batch_ids": ["batch-2"]},
    )
    return manifest, composite_entry, plain_entry, snapshot, source_ref


def test_manifest_extractor_helpers_cover_identity_edges() -> None:
    manifest, _, _, snapshot, source_ref = _identity_edge_fixture()
    diagnostics = manifest_extractors.identity_graph_diagnostics(manifest)
    assert diagnostics["launch_only"] == "yes"
    assert diagnostics["identity_graph_complete"] is False
    assert manifest_extractors.diagnostic_value(
        diagnostics, "missing", "launch_only"
    ) == ("yes")
    assert manifest_extractors.diagnostic_value({"empty": ""}, "empty") is None
    assert manifest_extractors.correlation_anchor_gaps(diagnostics) == {"run_id": 1}
    assert (
        manifest_extractors.correlation_anchor_gaps({"correlation_anchor_gaps": []})
        == {}
    )
    assert manifest_extractors.input_snapshots(manifest) == (snapshot,)
    assert manifest_extractors.input_snapshot_fingerprint((snapshot,)) is not None
    assert manifest_extractors.input_snapshot_fingerprint(()) is None
    assert manifest_extractors.source_ref_values((source_ref,)) == [
        "chembl/activity/chembl_activity"
    ]
    assert manifest_extractors.artifact_ref_values(manifest.planned_artifacts) == [
        "gold:gold/activity"
    ]
    assert (
        len(
            manifest_extractors.extract_manifest_anchors(
                {
                    "run_id": "run-1",
                    "manifest_id": "manifest-1",
                    "pipeline_name": "chembl_activity",
                    "provider": "chembl",
                    "entity": "activity",
                }
            )
        )
        == 4
    )


def test_checkpoint_extractor_helpers_cover_metadata_edges() -> None:
    manifest, _, _, _, _ = _identity_edge_fixture()
    assert checkpoint_extractors.checkpoint_anchor_payload(manifest)["manifest_id"] == (
        "manifest-5"
    )
    fallback_manifest = _manifest(
        "6",
        resolved_config={
            "reproducibility": {
                "checkpoint_anchors": {
                    "records_processed": 1,
                    "manifest_id": "manifest-fallback",
                }
            }
        },
    )
    assert (
        checkpoint_extractors.checkpoint_anchor_payload(fallback_manifest)[
            "manifest_id"
        ]
        == "manifest-fallback"
    )
    assert checkpoint_extractors.normalize_checkpoint_metadata_payload([]) == {}
    assert (
        checkpoint_extractors.checkpoint_value(
            manifest,
            "missing",
            "manifest_id",
        )
        == "manifest-5"
    )
    assert (
        checkpoint_extractors.first_payload_value(
            manifest,
            "missing",
            "workflow",
        )
        == "wf-runtime"
    )
    assert checkpoint_extractors.first_payload_value(manifest, "missing") is None
    assert (
        len(
            checkpoint_extractors.extract_checkpoint_anchors(
                {
                    "run_id": "run-1",
                    "manifest_id": "manifest-1",
                    "checkpoint_id": "checkpoint-1",
                    "execution_fingerprint": "fingerprint",
                }
            )
        )
        == 4
    )


def test_ledger_extractor_helpers_cover_composite_edges() -> None:
    manifest, composite_entry, plain_entry, _, _ = _identity_edge_fixture()
    # published_artifacts only considers ARTIFACT_PUBLISHED_EVENT entries.
    published_entry = _ledger_entry(
        manifest,
        "published",
        event_type=ARTIFACT_PUBLISHED_EVENT,
        details={
            "artifact_ref": "gold/activity",
            "artifact_path": ["silver/activity", ""],
            "uri": "ignored/for/component",
        },
    )
    assert ledger_extractors.published_artifacts(
        (composite_entry, plain_entry, published_entry)
    ) == [
        "gold/activity",
        "silver/activity",
        "ignored/for/component",
    ]
    assert ledger_extractors.artifact_refs(manifest, ()) == ["gold:gold/activity"]
    assert ledger_extractors.lineage_fragment_ids((composite_entry, plain_entry)) == [
        "lineage-1"
    ]
    assert ledger_extractors.component_run_ids((plain_entry, composite_entry)) == [
        "component-1",
        "component-2",
    ]
    assert ledger_extractors.dq_report_paths(manifest, (composite_entry,)) == [
        "dq-launch.json",
        "dq-ledger.json",
    ]
    assert ledger_extractors.bronze_batch_ids(
        manifest, (composite_entry, plain_entry)
    ) == [
        "snapshot-1",
        "batch-ledger",
        "batch-2",
    ]
    assert (
        len(
            ledger_extractors.extract_ledger_anchors(
                {
                    "run_id": "run-1",
                    "manifest_id": "manifest-1",
                    "latest_event_id": "entry-1",
                }
            )
        )
        == 3
    )


def test_checkpoint_compare_helpers_cover_status_edges() -> None:
    manifest, _, _, _, _ = _identity_edge_fixture()
    assert checkpoint.build_checkpoint_compare(None) == {
        "status": "UNKNOWN",
        "rows": [],
    }
    assert checkpoint.checkpoint_pair_status(None, None) == "N/A"
    assert checkpoint.checkpoint_pair_status("a", None) == "MISSING"
    assert checkpoint.checkpoint_pair_status("a", "b") == "MISMATCH"
    assert (
        checkpoint.checkpoint_row("anchor", "current", "checkpoint", "CUSTOM")[
            "ui_status"
        ]
        == "WARN"
    )
    missing_compare = checkpoint.build_checkpoint_compare(
        manifest,
        checkpoint_metadata={},
    )
    assert missing_compare["status"] == "MISSING"
    mismatch_compare = checkpoint.build_checkpoint_compare(
        manifest,
        checkpoint_metadata={"records_processed": 1, "manifest_id": "different"},
    )
    assert mismatch_compare["status"] == "MISMATCH"
    partial_compare = checkpoint.build_checkpoint_compare(
        manifest,
        checkpoint_metadata={
            "records_processed": 1,
            "manifest_id": "manifest-5",
        },
    )
    assert partial_compare["status"] == "PARTIAL"
    ok_compare = checkpoint.build_checkpoint_compare(
        manifest,
        checkpoint_metadata=checkpoint.current_checkpoint_anchors(manifest),
    )
    assert ok_compare["status"] == "OK"


def test_identity_severity_helpers_cover_applicability_and_missing_edges() -> None:
    exact_manifest = _manifest(
        "7",
        launch_context={"exact_replay": True},
        replay_of_run_id="run-parent",
    )
    normal_manifest = _manifest("8")
    terminal_entry = _ledger_entry(
        exact_manifest,
        "terminal",
        event_type=RUN_FINISHED_EVENT,
        status="success",
    )

    assert (
        severity.domain_severity(
            SPEC_BY_NAME["run_id"],
            value=None,
            present=False,
            manifest=normal_manifest,
            ledger_entries=(),
            checkpoint_status="OK",
            applicable=False,
        )
        == "N/A"
    )
    assert (
        severity.domain_severity(
            SPEC_BY_NAME["checkpoint_anchor_status"],
            value="MISMATCH",
            present=True,
            manifest=normal_manifest,
            ledger_entries=(),
            checkpoint_status="MISMATCH",
            applicable=True,
        )
        == "FAILING"
    )
    assert (
        severity.domain_severity(
            SPEC_BY_NAME["identity_graph_complete"],
            value="complete (0 gaps)",
            present=True,
            manifest=normal_manifest,
            ledger_entries=(),
            checkpoint_status="OK",
            applicable=True,
        )
        == "OK"
    )
    assert (
        severity.domain_severity(
            SPEC_BY_NAME["identity_graph_complete"],
            value="missing run_id",
            present=True,
            manifest=normal_manifest,
            ledger_entries=(),
            checkpoint_status="OK",
            applicable=True,
        )
        == "FAILING"
    )
    assert (
        severity.domain_severity(
            SPEC_BY_NAME["exact_replay_eligible"],
            value=False,
            present=True,
            manifest=exact_manifest,
            ledger_entries=(),
            checkpoint_status="OK",
            applicable=True,
        )
        == "FAILING"
    )
    assert (
        severity.domain_severity(
            SPEC_BY_NAME["manifest_id"],
            value=None,
            present=False,
            manifest=exact_manifest,
            ledger_entries=(terminal_entry,),
            checkpoint_status="OK",
            applicable=True,
        )
        == "FAILING"
    )
    assert (
        severity.domain_severity(
            SPEC_BY_NAME["replay_of_manifest_id"],
            value=None,
            present=False,
            manifest=exact_manifest,
            ledger_entries=(),
            checkpoint_status="OK",
            applicable=True,
        )
        == "FAILING"
    )
    assert (
        severity.domain_severity(
            SPEC_BY_NAME["input_snapshot_ids"],
            value=None,
            present=False,
            manifest=exact_manifest,
            ledger_entries=(),
            checkpoint_status="OK",
            applicable=True,
        )
        == "FAILING"
    )
    assert severity.ui_status("DEGRADED") == "WARN"
    assert severity.ui_status("OK") == "OK"
    assert severity.is_identity_gap("WARNING") is True
    assert severity.is_identity_gap("OK") is False
    assert severity.applicability("run_id", None) == "not available for current scope"
    assert severity.applicability("replay_of_run_id", normal_manifest) == "N/A"
    assert severity.applicability("replay_of_run_id", exact_manifest) == "APPLICABLE"
    assert severity.applicability("component_run_ids", normal_manifest) == "N/A"
    composite_manifest = _manifest("9", pipeline_name="composite_activity")
    assert severity.applicability("component_run_ids", composite_manifest) == (
        "APPLICABLE"
    )
