"""Stream A domain coverage for #10469 / #10519 (bundle, json, accounting)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest

from bioetl.domain.control_plane.workflow_execution_state import (
    WorkflowExecutionState,
    WorkflowStepState,
    _deserialize_optional_datetime,
    _load_list,
    _load_list_of_dicts,
    _load_mutation_details,
    _load_optional_int,
    _load_transform_fingerprints,
    _serialize_optional_datetime,
)
from bioetl.domain.lineage.metadata_bundle import (
    _attach_fragment_anchor,
    _non_empty_mismatch,
    _produced_artifact_id_for_edge,
    _require_non_empty_artifact_id,
    _require_runtime_run_id,
    _resolve_primary_artifact_id,
    _set_missing_anchor,
    _validate_runtime_manifest_matches_fragment,
    _validate_runtime_run_id_matches_fragment,
)
from bioetl.domain.lineage.models import (
    LineageEdge,
    LineageEdgeType,
    LineageGraphFragment,
    LineageNodeRef,
    LineageNodeType,
)
from bioetl.domain.normalization import json as json_normalization
from bioetl.domain.normalization.json import (
    lookup_mapping_path,
    serialize_json_canonical,
    to_jsonable,
)
from bioetl.domain.run_reports.accounting import StageAccountingAccumulator
from bioetl.domain.run_reports.models import StageId
from bioetl.domain.run_reports.reason_catalog import default_reason_catalog
from bioetl.domain.run_reports.workflow_builder import build_workflow_run_report
from bioetl.domain.types import RunID
from bioetl.domain.types.dq_contracts import DQDisposition

pytestmark = pytest.mark.unit

_TEST_RUN_ID = RunID(UUID("12345678-1234-5678-1234-567812345678"))


def _node(node_type: LineageNodeType, node_id: str) -> LineageNodeRef:
    return LineageNodeRef(node_type=node_type, node_id=node_id)


def _fragment(
    *edges: LineageEdge,
    nodes: tuple[LineageNodeRef, ...] | None = None,
    fragment_id: str = "frag-1",
    run_id: str | None = "run-1",
    manifest_id: str | None = "manifest-1",
) -> LineageGraphFragment:
    inferred = nodes
    if inferred is None:
        seen: dict[str, LineageNodeRef] = {}
        for edge in edges:
            for node in (edge.source, edge.target):
                seen[str(node.node_id)] = node
        inferred = tuple(seen.values())
    return LineageGraphFragment(
        fragment_id=fragment_id,
        nodes=inferred,
        edges=edges,
        run_id=run_id,
        manifest_id=manifest_id,
    )


def test_metadata_bundle_helpers_cover_artifact_and_identity_branches() -> None:
    batch = _node(LineageNodeType.BRONZE_BATCH, "bronze_batch:b1")
    dataset = _node(LineageNodeType.DATASET, "gold:activity")
    run = _node(LineageNodeType.RUN, "run:run-1")
    schema = _node(LineageNodeType.SCHEMA, "schema:x")
    produced = LineageEdge(LineageEdgeType.PRODUCED_BY, source=batch, target=run)
    derived = LineageEdge(LineageEdgeType.DERIVED_FROM, source=dataset, target=run)
    schema_edge = LineageEdge(LineageEdgeType.PRODUCED_BY, source=schema, target=run)
    dangling = LineageEdge(
        LineageEdgeType.PRODUCED_BY,
        source=_node(LineageNodeType.DATASET, "missing"),
        target=run,
    )

    index = {batch.node_id: batch, run.node_id: run, schema.node_id: schema}
    assert _produced_artifact_id_for_edge(derived, index) is None
    assert _produced_artifact_id_for_edge(dangling, index) is None
    assert _produced_artifact_id_for_edge(schema_edge, index) is None
    assert _produced_artifact_id_for_edge(produced, index) == "bronze_batch:b1"

    with pytest.raises(ValueError, match="does not expose a produced artifact"):
        _resolve_primary_artifact_id(_fragment(derived, schema_edge))
    with pytest.raises(ValueError, match="multiple produced artifacts"):
        _resolve_primary_artifact_id(
            _fragment(
                produced,
                LineageEdge(LineageEdgeType.PRODUCED_BY, source=dataset, target=run),
            )
        )

    output = SimpleNamespace(lineage_fragment_id="keep", artifact_id="")
    _set_missing_anchor(output, "lineage_fragment_id", "frag-2")
    assert output.lineage_fragment_id == "keep"
    _attach_fragment_anchor(SimpleNamespace(output=None), "frag-1", "art-1")
    _attach_fragment_anchor(SimpleNamespace(output=object()), "frag-1", "art-1")
    _attach_fragment_anchor(SimpleNamespace(output=output), "frag-1", "art-1")
    assert output.artifact_id == "art-1"

    with pytest.raises(ValueError, match="runtime.run_id"):
        _require_runtime_run_id(None)
    with pytest.raises(ValueError, match="runtime.run_id"):
        _require_runtime_run_id(SimpleNamespace(run_id="  "))
    with pytest.raises(ValueError, match="does not match lineage fragment run_id"):
        _validate_runtime_run_id_matches_fragment("run-other", _fragment(produced))
    _validate_runtime_run_id_matches_fragment("run-1", _fragment(produced, run_id=""))

    with pytest.raises(ValueError, match="does not match lineage fragment manifest_id"):
        _validate_runtime_manifest_matches_fragment(
            SimpleNamespace(manifest_id="other"),
            _fragment(produced),
            strict_manifest_id_required=False,
        )
    assert _non_empty_mismatch("", "x") is False
    with pytest.raises(ValueError, match="canonical artifact_id"):
        _require_non_empty_artifact_id("  ")


def test_json_helpers_cover_lookup_to_jsonable_and_stdlib_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nested = {"a": {"b": [1, {"c": 2}]}}
    assert lookup_mapping_path(nested, "a", "b") == [1, {"c": 2}]
    assert lookup_mapping_path(nested, "a", "b", "missing") is None
    assert lookup_mapping_path(nested, "a", "missing", "c") is None

    @dataclass
    class _Payload:
        when: datetime
        disposition: DQDisposition
        nested: dict[str, object]

    converted = to_jsonable(
        _Payload(
            when=datetime(2026, 1, 1, tzinfo=UTC),
            disposition=DQDisposition.PASS,
            nested={"z": (1, 2), "a": b"raw"},
        )
    )
    assert converted["when"].startswith("2026-01-01")
    assert converted["disposition"] == "pass"
    assert converted["nested"]["z"] == [1, 2]
    assert to_jsonable("plain") == "plain"
    with pytest.raises(TypeError, match="JSON-compatible"):
        serialize_json_canonical(object())  # type: ignore[arg-type]

    monkeypatch.setattr(json_normalization, "_orjson_available", False)
    assert serialize_json_canonical({"b": 1, "a": 2}) == '{"a":2,"b":1}'
    assert json_normalization.deserialize_json_value('{"k":1}') == {"k": 1}
    with pytest.raises(ValueError, match="Invalid JSON"):
        json_normalization.deserialize_json_value("{")


def test_workflow_execution_state_from_dict_covers_optional_and_invalid_payloads() -> (
    None
):
    started = datetime(2026, 1, 1, tzinfo=UTC)
    step = WorkflowStepState(
        step_id="extract",
        step_kind="pipeline",
        status="success",
        mutation_details={"deleted": 1},
    )
    state = WorkflowExecutionState(
        workflow_run_id=_TEST_RUN_ID,
        manifest_id="manifest-1",
        workflow_name="demo",
        execution_fingerprint="fp",
        status="running",
        started_at=started,
        updated_at=started,
        completed_at=None,
        selected_step_ids=("extract",),
        steps=(step,),
        completed_transform_fingerprints={"t": "abc"},
        last_start_offset=2,
        last_limit=10,
    )
    restored = WorkflowExecutionState.from_dict(state.to_dict())
    assert restored.completed_at is None
    assert restored.steps[0].mutation_details == {"deleted": 1}

    payload = state.to_dict()
    payload["completed_at"] = started.isoformat()
    payload["last_start_offset"] = "nope"
    payload["last_limit"] = None
    payload["mutation_details"] = "skip"
    payload["completed_transform_fingerprints"] = "skip"
    payload["selected_step_ids"] = "extract"
    payload["ambiguous_step_ids"] = None
    payload["steps"] = [
        step.to_dict(),
        "skip",
        {"step_id": 1, "step_kind": 2, "status": 3},
    ]
    payload["last_event_id"] = None
    hydrated = WorkflowExecutionState.from_dict(payload)
    assert hydrated.last_start_offset is None
    assert hydrated.last_limit is None
    assert hydrated.selected_step_ids == ()
    assert hydrated.completed_transform_fingerprints == {}
    assert len(hydrated.steps) == 2
    assert hydrated.completed_at == started

    assert _load_optional_int({"n": object()}, "n") is None
    assert _load_mutation_details("x") is None
    assert _load_transform_fingerprints([1]) == {}
    assert _load_list("x") == []
    assert _load_list_of_dicts([{"a": 1}, "x"]) == [{"a": 1}]
    assert _serialize_optional_datetime(None) is None
    assert _deserialize_optional_datetime(None) is None


def test_stage_accounting_covers_overflow_zero_counts_and_seed_guards() -> None:
    catalog = default_reason_catalog()
    acc = StageAccountingAccumulator(catalog=catalog)
    acc.record_in(StageId.BRONZE.value, 0)
    acc.record_out(StageId.BRONZE.value, -3)
    acc.record_removal(
        StageId.SILVER.value,
        outcome="quarantined",
        reason_code="SCHEMA_VALIDATION_FAILURE",
        count=0,
    )
    acc.record_in(StageId.BRONZE.value, 4)
    acc.apply_layer_totals(bronze=99, silver_valid=2, gold_written=1, records_fetched=8)
    assert acc._stages[StageId.BRONZE.value].records_in == 4

    acc.record_removal(
        StageId.SILVER.value,
        outcome="not-a-real-outcome",
        reason_code=catalog.unknown_code,
        count=1,
        sample_ref=None,
    )
    acc.record_removal(
        StageId.SILVER.value,
        outcome="quarantined",
        reason_code="",
        count=1,
        sample_ref="row-1",
    )
    acc.record_removal(
        StageId.SILVER.value,
        outcome="quarantined",
        reason_code="",
        count=1,
        sample_ref="row-1",
    )
    assert acc.unmapped_reason_count >= 1
    assert acc.sum_outcome("missing", "quarantined") == 0
    acc.mark_instrumented(StageId.GOLD.value)
    assert acc.reason_catalog_version == catalog.version

    for index in range(64):
        acc.record_gold_filter_rejection(
            {
                "reason_code": f"r{index}",
                "rule_type": "range",
                "field": "x",
                "operator": ">",
            }
        )
    acc.record_gold_filter_rejection({"reason_code": "overflow"})
    snapshot = acc.snapshot_gold_filter_rejections()
    assert any(item["reason_code"] == "other" for item in snapshot)
    assert snapshot == sorted(
        snapshot,
        key=lambda item: tuple(
            item[k] for k in ("reason_code", "rule_type", "field", "operator")
        ),
    )


def test_workflow_builder_covers_object_payload_and_report_ref_defaults() -> None:
    class _Step:
        step_id = "seed"
        step_kind = "pipeline"
        status = "success"
        pipeline_name = "chembl_activity"
        records_extracted = 3
        child_run_id = "run-9"
        child_manifest_id = "man-9"
        pipeline_report_ref = ""
        error_type = ""
        skip_reason = ""
        gold_excluded_by_contract = 2
        payload = SimpleNamespace(records_bronze=3, records_silver=2, records_gold=1)

    report = build_workflow_run_report(
        identity={"workflow_name": "demo"},
        plan_steps=[{"step_id": "seed"}],
        execution_steps=[
            _Step(),
            {
                "step_id": "seed-2",
                "pipeline_name": "chembl_activity",
                "status": "failed",
                "payload": {"records_extracted": 7, "records_bronze": 6},
            },
            {
                "step_id": "reconcile",
                "kind": "transform",
                "status": "success",
                "payload": {
                    "transform_name": "reconcile_foreign_keys",
                    "source_table": "activity",
                    "orphan_rows_deleted": 1,
                    "ignored": True,
                },
            },
            {
                "step_id": "other",
                "status": "skipped",
                "payload": {"transform_name": "noop"},
            },
        ],
    )
    seed = report.execution[0]
    assert seed.pipeline_report_ref is not None
    assert seed.pipeline_report_ref.endswith("pipeline-run-report.json")
    assert seed.records_extracted == 3
    assert seed.gold_excluded_by_contract == 2
    assert report.execution[1].records_extracted == 7
    assert report.execution[2].reconciliation == {
        "source_table": "activity",
        "orphan_rows_deleted": 1,
    }
    assert report.execution[3].reconciliation is None
    assert report.index["chembl_activity"]["records_extracted"] == 10
    assert report.plan_steps[0]["kind"] == "pipeline"
