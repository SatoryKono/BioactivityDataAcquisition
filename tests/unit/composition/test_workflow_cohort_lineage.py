"""A cohort follows confirmed FK expiry without broadening producer ownership."""

import asyncio
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pyarrow as pa
import pytest

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunResult,
)
from bioetl.application.services.workflow.control_plane.execution_recording_payloads import (
    build_step_completion_details,
)
from bioetl.application.services.workflow.control_plane.selected_snapshot_resume import (
    restore_selected_snapshot_outputs,
)
from bioetl.application.services.workflow.workflow_runner_models import (
    WorkflowStepExecutionResult,
)
from bioetl.application.workflow.transforms.reconcile_foreign_keys import (
    _build_reconcile_payload,
)
from bioetl.composition.bootstrap.assembly.workflow_transforms import (
    WorkflowCohortResolver,
)
from bioetl.application.workflow.transforms.selected_snapshot_inputs import (
    resolve_cohort_lineage,
)
from bioetl.domain.control_plane import WorkflowStepState
from bioetl.domain.workflow import (
    TransformStepConfig,
    WorkflowConfig,
    WorkflowTransformSpec,
)
from bioetl.domain.workflow.config import (
    WorkflowReferenceCohort,
    WorkflowRunOptionsConfig,
    WorkflowStepConfig,
)
from bioetl.domain.workflow.foreign_key_reconciliation_models import (
    ForeignKeyReconciliationRequest,
)
from bioetl.infrastructure.storage.delta_reader import DeltaReader
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation import (
    StorageForeignKeyReconciliationAdapter,
)
from tests.unit.application.services.control_plane.workflow.test_execution_resume_support import (
    _state,
)

pytestmark = pytest.mark.unit


def test_complete_reference_cohort_legacy_resume_requires_producer_receipt():
    config = WorkflowConfig(
        "complete",
        steps=(
            WorkflowStepConfig("assay", "chembl_assay"),
            replace(
                _step(), depends_on=("assay",), run_options=WorkflowRunOptionsConfig()
            ),
        ),
    )
    state = replace(
        _state(),
        steps=(
            WorkflowStepState(
                "assay",
                "pipeline",
                "success",
                output_details={
                    "child_run_id": "producer",
                    "selected_snapshots": {"gold:chembl.assay": _pin()},
                },
            ),
        ),
    )
    with pytest.raises(ValueError, match="producer evidence receipt"):
        restore_selected_snapshot_outputs(config, state, frozenset({"assay"}))


def test_consecutive_source_expiries_require_each_exact_count_and_pin():
    first = _mutation()
    second = _mutation(first["selected_snapshots"]["gold:chembl.assay"])
    second.update(
        scanned_rows=550,
        retained_rows=500,
        orphan_rows_deleted=50,
        quarantine_rows_written=50,
    )
    upstream = {"assay": _source(), "second": second, "first": first}
    pin, count = resolve_cohort_lineage(
        upstream["assay"], upstream, "gold:chembl.assay"
    )
    assert pin["version"] == 2 and pin["ancestor_versions"] == [0, 1]
    assert count == 500 and upstream["assay"].records_gold == 983
    second["scanned_rows"] = 549
    with pytest.raises(ValueError, match="count or quarantine mismatch"):
        resolve_cohort_lineage(upstream["assay"], upstream, "gold:chembl.assay")


def _step():
    return WorkflowStepConfig(
        "publication",
        "chembl_publication",
        depends_on=("assay", "fk"),
        reference_cohort=WorkflowReferenceCohort(
            "assay", "chembl.assay", "publication_id", "document_id"
        ),
        run_options=WorkflowRunOptionsConfig(
            limit=1000, reconciliation_mode="selected-snapshot"
        ),
    )


def _pin(version=0):
    return {
        "version": version,
        "table_id": "table",
        "producer_pipeline": "chembl_assay",
        "run_ids": ["producer"],
        "ancestor_versions": list(range(version)),
        "ownership": "producer_delta_entities",
        "owned_entities": {str(i): f"h{i}" for i in range(983)},
    }


def _source(pin=None):
    return RunResult(
        PipelineRunResult.SUCCESS,
        "chembl_assay",
        "producer",
        "backfill",
        manifest_id="child",
        records_fetched=983,
        records_silver=983,
        records_gold=983,
        selected_snapshots={"gold:chembl.assay": pin or _pin()},
    )


def _mutation(pin=None):
    initial = pin or _pin()
    descendant = {
        **initial,
        "version": initial["version"] + 1,
        "ancestor_versions": [*initial["ancestor_versions"], initial["version"]],
    }
    return {
        "transform_name": "reconcile_foreign_keys",
        "source_layer": "gold",
        "source_table": "chembl.assay",
        "source_scope": "current_run",
        "reference_scope": "current_run",
        "source_run_ids": ["workflow", "producer"],
        "reconciliation_mode": "selected-snapshot",
        "reference_completeness": "unproven",
        "mutated": True,
        "dry_run": False,
        "would_mutate": False,
        "scanned_rows": 983,
        "retained_rows": 550,
        "orphan_rows_deleted": 433,
        "quarantine_rows_written": 433,
        "input_snapshots": {"gold:chembl.assay": initial},
        "selected_snapshots": {"gold:chembl.assay": descendant},
    }


@pytest.mark.parametrize(
    "fault",
    [
        "legacy",
        "schema",
        "pipeline",
        "run",
        "count_missing",
        "count_negative",
        "count_boolean",
        "pin_producer",
        "schema_missing",
        "status",
        "completed_status",
    ],
)
def test_resume_requires_recorded_typed_producer_identity_and_counts(fault):
    source = _source()
    details = build_step_completion_details(
        WorkflowStepExecutionResult(
            "assay",
            "pipeline",
            "success",
            payload=source,
            child_run_id=source.run_id,
            child_manifest_id=source.manifest_id,
        )
    )
    details = deepcopy(details)
    if fault == "legacy":
        details.pop("producer_result")
    elif fault == "schema":
        details["producer_result"]["schema_version"] = 2
    elif fault == "schema_missing":
        details["producer_result"].pop("schema_version")
    elif fault == "status":
        details["producer_result"]["status"] = "failed"
    elif fault == "completed_status":
        pass
    elif fault == "pipeline":
        details["producer_result"]["pipeline_name"] = "foreign"
    elif fault == "run":
        details["producer_result"]["run_id"] = "foreign"
    elif fault == "count_missing":
        details["producer_result"].pop("records_gold")
    elif fault == "count_negative":
        details["producer_result"]["records_gold"] = -1
    elif fault == "count_boolean":
        details["producer_result"]["records_gold"] = True
    else:
        details["selected_snapshots"]["gold:chembl.assay"]["producer_pipeline"] = (
            "foreign"
        )
    state = replace(
        _state(),
        steps=(
            WorkflowStepState(
                "assay",
                "pipeline",
                "failed" if fault == "completed_status" else "success",
                output_details=details,
            ),
        ),
    )
    config = WorkflowConfig(
        "resume",
        steps=(WorkflowStepConfig("assay", "chembl_assay"),),
        defaults=WorkflowRunOptionsConfig(reconciliation_mode="selected-snapshot"),
    )
    with pytest.raises(ValueError, match="producer|pin"):
        restore_selected_snapshot_outputs(config, state, frozenset({"assay"}))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fault",
    [
        None,
        "count",
        "membership",
        "producer",
        "reference_only",
        "dry_run",
        "ancestry",
        "foreign_table",
        "unconfirmed",
        "would_mutate",
        "run_ids_string",
        "run_ids_none",
        "run_ids_foreign",
    ],
)
async def test_descendant_requires_exact_source_mutation_count_and_identity(fault):
    mutation = deepcopy(_mutation())
    if fault == "count":
        mutation.update(
            retained_rows=549, orphan_rows_deleted=434, quarantine_rows_written=434
        )
    elif fault == "membership":
        mutation["selected_snapshots"]["gold:chembl.assay"]["owned_entities"][
            "foreign"
        ] = "hash"
    elif fault == "producer":
        mutation["selected_snapshots"]["gold:chembl.assay"]["producer_pipeline"] = (
            "foreign"
        )
    elif fault == "reference_only":
        mutation["source_table"] = "chembl.target"
    elif fault == "dry_run":
        mutation["dry_run"] = True
    elif fault == "ancestry":
        mutation["selected_snapshots"]["gold:chembl.assay"]["version"] = 2
    elif fault == "foreign_table":
        mutation["selected_snapshots"]["gold:chembl.assay"]["table_id"] = "foreign"
    elif fault == "unconfirmed":
        mutation["mutation_blocked_reason"] = "selected_snapshot_commit_ambiguous"
    elif fault == "would_mutate":
        mutation["would_mutate"] = True
    elif fault == "run_ids_string":
        mutation["source_run_ids"] = "workflow,producer"
    elif fault == "run_ids_none":
        mutation["source_run_ids"] = None
    elif fault == "run_ids_foreign":
        mutation["source_run_ids"] = ["foreign"]
    reader = MagicMock()
    reader.read_table = AsyncMock(
        return_value=pa.Table.from_pylist(
            [
                {
                    "entity_id": str(i),
                    "content_hash": f"h{i}",
                    "publication_id": f"P{i}",
                    "_is_current": i < 550,
                }
                for i in range(983)
            ]
            + [
                {
                    "entity_id": "foreign",
                    "content_hash": "foreign",
                    "publication_id": "FOREIGN",
                    "_is_current": True,
                }
            ]
        )
    )
    source = _source()
    upstream = {
        "assay": source,
        "fk": mutation,
        "reference_only": {
            "transform_name": "reconcile_foreign_keys",
            "source_layer": "gold",
            "source_table": "chembl.target",
            "mutated": False,
            "retained_rows": 1,
            "selected_snapshots": mutation["selected_snapshots"],
        },
    }
    if fault:
        with pytest.raises(ValueError):
            await WorkflowCohortResolver(reader)(_step(), upstream)
    else:
        actual = await WorkflowCohortResolver(reader)(_step(), upstream)
        assert len(actual.run_options.filter_ids) == 550
        assert "FOREIGN" not in actual.run_options.filter_ids
        reader.read_table.assert_awaited_once_with(
            "chembl/assay", snapshot_version=1, snapshot_table_id="table"
        )
    assert (
        source.records_gold == 983
        and source.selected_snapshots["gold:chembl.assay"]["version"] == 0
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("dry_run", [False, True])
async def test_non_mutating_result_never_changes_cohort_count(dry_run):
    source = _source()
    payload = {
        **_mutation(),
        "mutated": False,
        "dry_run": dry_run,
        "retained_rows": 550,
        "selected_snapshots": source.selected_snapshots,
    }
    reader = MagicMock()
    reader.read_table = AsyncMock(
        return_value=pa.Table.from_pylist(
            [{"publication_id": "P", "_run_id": "producer"}] * 550
        )
    )
    with pytest.raises(ValueError, match="count or run identity"):
        await WorkflowCohortResolver(reader)(_step(), {"assay": source, "fk": payload})
    assert reader.read_table.await_args.kwargs["snapshot_version"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("fault", [None, "external_version"])
async def test_real_gold_expiry_descendant_and_partial_resume_keep_scoped_history(
    tmp_path, fault
):
    from deltalake import DeltaTable, write_deltalake

    gold = tmp_path / "gold"
    source_path, target_path = gold / "chembl/assay", gold / "chembl/target"
    original_rows = [
        {
            "entity_id": str(i),
            "content_hash": f"h{i}",
            "target_id": f"T{i}",
            "publication_id": f"P{i}",
            "_is_current": True,
            "_valid_to": "",
        }
        for i in range(983)
    ]
    write_deltalake(str(source_path), pa.Table.from_pylist(original_rows))
    write_deltalake(
        str(target_path),
        pa.Table.from_pylist(
            [
                {
                    "entity_id": f"T{i}",
                    "content_hash": f"ht{i}",
                    "target_id": f"T{i}",
                    "_is_current": True,
                }
                for i in range(550)
            ]
        ),
    )
    source_pin = {**_pin(), "table_id": str(DeltaTable(str(source_path)).metadata().id)}
    reference_pin = {
        "version": 0,
        "table_id": str(DeltaTable(str(target_path)).metadata().id),
        "producer_pipeline": "chembl_target",
        "run_ids": ["target"],
        "ancestor_versions": [],
        "ownership": "producer_delta_entities",
        "owned_entities": {f"T{i}": f"ht{i}" for i in range(550)},
    }

    async def execute(fn, *args):
        return await asyncio.to_thread(fn, *args)

    adapter = StorageForeignKeyReconciliationAdapter(
        silver_writer=MagicMock(),
        gold_writer=SimpleNamespace(
            _resolve_table_path=lambda name: str(gold / name.replace(".", "/", 1)),
            _run_in_executor=execute,
        ),
        logger=MagicMock(),
        clock=SimpleNamespace(now=lambda: datetime(2026, 10, 3, tzinfo=UTC)),
        quarantine=SimpleNamespace(write_many=AsyncMock()),
    )
    request = ForeignKeyReconciliationRequest(
        workflow_run_id="00000000-0000-0000-0000-000000000001",
        manifest_id="00000000-0000-0000-0000-000000000002",
        step_id="fk",
        transform_name="reconcile_foreign_keys",
        source_table="chembl.assay",
        reference_table="chembl.target",
        source_key="target_id",
        reference_key="target_id",
        primary_keys=("entity_id",),
        source_layer="gold",
        reference_layer="gold",
        source_scope="current_run",
        source_run_ids=("producer", "target"),
        reconciliation_mode="selected-snapshot",
        selected_snapshots={
            "gold:chembl.assay": source_pin,
            "gold:chembl.target": reference_pin,
        },
    )
    result = await adapter.reconcile_foreign_keys(request)
    assert result.retained_rows == 550 and result.orphan_rows_deleted == 433
    actual_rows = DeltaTable(str(source_path)).to_pyarrow_table().to_pylist()
    assert len(actual_rows) == 983
    assert sum(row["_is_current"] for row in actual_rows) == 550
    assert sum(not row["_is_current"] for row in actual_rows) == 433
    adapter.quarantine.write_many.assert_awaited_once()
    source = _source(source_pin)
    spec = WorkflowTransformSpec.from_step(
        TransformStepConfig("fk", "reconcile_foreign_keys")
    )
    payload = _build_reconcile_payload(
        spec=spec, request=request, result=result, workflow_name="lineage"
    )
    producer_details = build_step_completion_details(
        WorkflowStepExecutionResult(
            "assay",
            "pipeline",
            "success",
            payload=source,
            child_run_id=source.run_id,
            child_manifest_id=source.manifest_id,
        )
    )
    transform_details = build_step_completion_details(
        WorkflowStepExecutionResult(
            "fk",
            "transform",
            "success",
            payload=SimpleNamespace(output=payload, fingerprint=spec.fingerprint),
        )
    )
    state = replace(
        _state(),
        steps=(
            WorkflowStepState(
                "assay", "pipeline", "success", output_details=producer_details
            ),
            WorkflowStepState(
                "fk",
                "transform",
                "success",
                output_details=transform_details,
            ),
        ),
    )
    config = WorkflowConfig(
        "lineage",
        steps=(
            WorkflowStepConfig(
                "assay",
                "chembl_assay",
                run_options=WorkflowRunOptionsConfig(
                    reconciliation_mode="selected-snapshot"
                ),
            ),
            TransformStepConfig("fk", "reconcile_foreign_keys", depends_on=("assay",)),
            _step(),
        ),
        defaults=WorkflowRunOptionsConfig(reconciliation_mode="selected-snapshot"),
    )
    restored = restore_selected_snapshot_outputs(
        config, type(state).from_dict(state.to_dict()), frozenset({"assay", "fk"})
    )
    assert isinstance(restored["assay"], RunResult)
    assert restored["assay"].records_gold == source.records_gold == 983
    assert restored["assay"].selected_snapshots == source.selected_snapshots
    if fault:
        write_deltalake(
            str(source_path), pa.Table.from_pylist(actual_rows), mode="overwrite"
        )
        with pytest.raises(ValueError, match="snapshot drift"):
            await WorkflowCohortResolver(DeltaReader(gold, MagicMock()))(
                _step(), restored
            )
    else:
        selected = await WorkflowCohortResolver(DeltaReader(gold, MagicMock()))(
            _step(), restored
        )
        assert len(selected.run_options.filter_ids) == 550
        assert "P982" not in selected.run_options.filter_ids
        assert DeltaTable(str(source_path)).version() == 1
