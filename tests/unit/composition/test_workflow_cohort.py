"""Bounded reference extraction is tied to actual upstream run rows."""

from unittest.mock import AsyncMock, MagicMock

import pyarrow as pa
import pytest

from bioetl.composition.workflow_cohort import WorkflowCohortResolver
from bioetl.application.services.execution.pipeline_runner_models import (
    RunResult,
    PipelineRunResult,
)
from bioetl.domain.workflow.config import (
    WorkflowStepConfig,
    WorkflowReferenceCohort,
    WorkflowRunOptionsConfig,
)


pytestmark = pytest.mark.unit


@pytest.mark.asyncio
@pytest.mark.parametrize("missing_reference", [False, True])
async def test_default_workflow_captures_actual_gold_cohort_producer(
    tmp_path, monkeypatch, missing_reference
):
    from types import SimpleNamespace
    from deltalake import write_deltalake
    from bioetl.application.services.workflow import workflow_runner_service as module
    from bioetl.application.workflow.transforms.reconcile_foreign_keys import (
        build_reconcile_foreign_keys_executor,
    )
    from bioetl.domain.workflow import TransformStepConfig, WorkflowTransformSpec
    from bioetl.domain.workflow.config import WorkflowConfig
    from bioetl.infrastructure.storage.delta_reader import DeltaReader
    from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation import (
        StorageForeignKeyReconciliationAdapter,
    )

    gold_root = tmp_path / "gold"
    adapter = StorageForeignKeyReconciliationAdapter(
        silver_writer=SimpleNamespace(
            _resolve_table_path=lambda name: str(
                tmp_path / "silver" / name.replace(".", "/", 1)
            )
        ),
        gold_writer=SimpleNamespace(
            _resolve_table_path=lambda name: str(gold_root / name.replace(".", "/", 1))
        ),
        logger=MagicMock(),
        clock=MagicMock(),
        quarantine=MagicMock(),
    )
    calls = []

    async def run(name, *, options):
        calls.append((name, options))
        if name == "chembl_assay":
            write_deltalake(
                str(gold_root / "chembl" / "assay"),
                pa.Table.from_pylist(
                    [
                        {
                            "entity_id": "a",
                            "content_hash": "ha",
                            "target_id": "T1",
                            "_is_current": True,
                        }
                    ]
                ),
            )
        else:
            assert options.filter_ids == ["T1"]
            write_deltalake(
                str(gold_root / "chembl" / "target"),
                pa.Table.from_pylist(
                    [
                        {
                            "entity_id": "t",
                            "content_hash": "ht",
                            "target_id": "missing" if missing_reference else "T1",
                            "_is_current": True,
                        }
                    ]
                ),
            )
        return RunResult(
            PipelineRunResult.SUCCESS, name, "producer", "backfill", records_gold=1
        )

    monkeypatch.setattr(
        module, "attach_workflow_run_report", lambda **kwargs: kwargs["result"]
    )
    monkeypatch.setattr(module, "archive_workflow_children", lambda *args: None)
    config = WorkflowConfig(
        name="closed",
        steps=(
            WorkflowStepConfig("assay", "chembl_assay"),
            WorkflowStepConfig(
                "target",
                "chembl_target",
                depends_on=("assay",),
                reference_cohort=WorkflowReferenceCohort(
                    "assay", "chembl.assay", "target_id", "target_id"
                ),
            ),
        ),
    )
    service = module.WorkflowRunnerService(
        pipeline_runner=SimpleNamespace(run=run),
        transform_service=SimpleNamespace(
            registry=SimpleNamespace(snapshot_reader=adapter.capture_pipeline_snapshots)
        ),
        metrics=MagicMock(),
        report_store=MagicMock(),
        cohort_resolver=WorkflowCohortResolver(DeltaReader(gold_root, MagicMock())),
    )
    result = await service.run_workflow(config, workflow_run_id="workflow")
    assert result.status == "success"
    assert [name for name, _ in calls] == ["chembl_assay", "chembl_target"]
    assert all(
        step.run_options.reconciliation_mode is None for step in config.pipeline_steps
    )
    source = result.steps[0].payload
    assert source.selected_snapshots["gold:chembl.assay"]["run_ids"] == ["producer"]
    assert source.selected_snapshots["gold:chembl.assay"]["owned_entities"] == {
        "a": "ha"
    }
    spec = WorkflowTransformSpec.from_step(
        TransformStepConfig(
            "fk",
            "reconcile_foreign_keys",
            config={
                "source_table": "chembl.assay",
                "reference_table": "chembl.target",
                "source_key": "target_id",
                "reference_key": "target_id",
                "source_layer": "gold",
                "reference_layer": "gold",
                "primary_keys": ["entity_id"],
                "action": "delete_orphans",
                "require_closed_cohort": True,
                "source_scope": "current_run",
            },
        )
    )
    executor = build_reconcile_foreign_keys_executor(adapter)
    outputs = {"assay": source, "target": result.steps[1].payload}
    if missing_reference:
        with pytest.raises(ValueError, match="cohort is not closed"):
            await executor(spec, upstream_outputs=outputs)
    else:
        payload = await executor(spec, upstream_outputs=outputs)
        assert payload["closed_cohort_verified"] is True
        assert payload["reference_completeness"] == "unproven"
        assert payload["orphan_rows_deleted"] == 0
        assert payload["mutated"] is False
    from deltalake import DeltaTable

    assert DeltaTable(str(gold_root / "chembl" / "assay")).version() == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fault",
    [None, "run", "count", "missing", "ownership", "version", "table_id", "pipeline"],
)
async def test_cohort_uses_pinned_producer_entities_when_gold_omits_run_id(
    tmp_path, fault
):
    from deltalake import DeltaTable, write_deltalake
    from bioetl.infrastructure.storage.delta_reader import DeltaReader

    path = tmp_path / "chembl" / "assay"
    rows = pa.Table.from_pylist(
        [
            {
                "entity_id": "a",
                "content_hash": "ha",
                "target_id": "T1",
                "_is_current": True,
            },
            {
                "entity_id": "b",
                "content_hash": "hb",
                "target_id": "T2",
                "_is_current": True,
            },
            {
                "entity_id": "older",
                "content_hash": "old",
                "target_id": "foreign",
                "_is_current": True,
            },
            {
                "entity_id": "a",
                "content_hash": "ha",
                "target_id": "history",
                "_is_current": False,
            },
        ]
    )
    write_deltalake(str(path), rows)
    entry = {
        "version": 0,
        "table_id": str(DeltaTable(str(path)).metadata().id),
        "producer_pipeline": "chembl_assay",
        "run_ids": ["run"],
        "ownership": "producer_delta_entities",
        "owned_entities": {"a": "ha", "b": "hb"},
    }
    if fault == "ownership":
        entry.pop("owned_entities")
    if fault == "version":
        write_deltalake(str(path), rows, mode="overwrite")
    if fault == "table_id":
        entry["table_id"] = "other-table"
    if fault == "pipeline":
        entry["producer_pipeline"] = "chembl_target"
    source = RunResult(
        PipelineRunResult.SUCCESS,
        "chembl_assay",
        "other" if fault == "run" else "run",
        "backfill",
        records_gold=3 if fault == "count" else 2,
        selected_snapshots={} if fault == "missing" else {"gold:chembl.assay": entry},
    )
    step = WorkflowStepConfig(
        "target",
        "chembl_target",
        depends_on=("assay",),
        reference_cohort=WorkflowReferenceCohort(
            "assay", "chembl.assay", "target_id", "target_id"
        ),
        run_options=WorkflowRunOptionsConfig(limit=1000),
    )
    resolver = WorkflowCohortResolver(DeltaReader(tmp_path, MagicMock()))
    if fault:
        with pytest.raises(ValueError):
            await resolver(step, {"assay": source})
    else:
        actual = await resolver(step, {"assay": source})
        assert actual.run_options.filter_ids == ("T1", "T2")
        assert actual.run_options.limit == 1000
        assert DeltaTable(str(path)).version() == 0


@pytest.mark.asyncio
async def test_cohort_without_row_run_identity_or_producer_pin_fails_closed():
    reader = MagicMock()
    reader.read_table = AsyncMock(
        return_value=pa.Table.from_pylist([{"target_id": "T1"}])
    )
    step = WorkflowStepConfig(
        "target",
        "chembl_target",
        depends_on=("assay",),
        reference_cohort=WorkflowReferenceCohort(
            "assay", "chembl.assay", "target_id", "target_id"
        ),
    )
    source = RunResult(
        PipelineRunResult.SUCCESS, "chembl_assay", "run", "backfill", records_gold=1
    )
    with pytest.raises(ValueError, match="snapshot identity mismatch"):
        await WorkflowCohortResolver(reader)(step, {"assay": source})
    reader.read_table.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("fault", [None, "wrong_run", "count", "limit", "empty"])
async def test_cohort_is_run_bound_and_never_silently_truncated(fault):
    rows = [
        {"target_id": "T2", "_run_id": "run"},
        {"target_id": "T1", "_run_id": "run"},
        {"target_id": "foreign", "_run_id": "older"},
    ]
    if fault == "empty":
        rows[0]["target_id"] = rows[1]["target_id"] = None
    reader = MagicMock()
    reader.read_table = AsyncMock(return_value=pa.Table.from_pylist(rows))
    step = WorkflowStepConfig(
        "target",
        "chembl_target",
        depends_on=("assay",),
        reference_cohort=WorkflowReferenceCohort(
            "assay", "chembl.assay", "target_id", "target_id"
        ),
        run_options=WorkflowRunOptionsConfig(limit=1 if fault == "limit" else 1000),
    )
    source = RunResult(
        PipelineRunResult.SUCCESS,
        "chembl_assay",
        "other" if fault == "wrong_run" else "run",
        "backfill",
        records_gold=3 if fault == "count" else 2,
        selected_snapshots={
            "gold:chembl.assay": {
                "version": 0,
                "table_id": "table",
                "producer_pipeline": "chembl_assay",
                "run_ids": ["run"],
            }
        },
    )
    resolver = WorkflowCohortResolver(reader)
    if fault:
        with pytest.raises(ValueError):
            await resolver(step, {"assay": source})
    else:
        actual = await resolver(step, {"assay": source})
        assert actual.run_options.filter_ids == ("T1", "T2")
        assert actual.run_options.limit == 1000
        assert actual.run_options.ignore_yaml_filter is True


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", [True, False])
async def test_closed_cohort_never_deletes_unmatched_rows(missing, monkeypatch):
    from bioetl.domain.ports import ForeignKeyReconciliationRequest
    from bioetl.infrastructure.storage import (
        workflow_foreign_key_reconciliation_loaded as module,
    )

    mutation = AsyncMock()
    monkeypatch.setattr(module, "apply_reconciliation_mutation", mutation)
    request = ForeignKeyReconciliationRequest(
        "chembl.assay",
        "chembl.target",
        "target_id",
        "target_id",
        ("assay_id",),
        require_closed_cohort=True,
    )
    call = module.reconcile_loaded_rows(
        MagicMock(),
        request,
        source_rows=[{"assay_id": "a", "target_id": "t"}],
        reference_rows=[] if missing else [{"target_id": "t"}],
    )
    if missing:
        with pytest.raises(ValueError, match="cohort is not closed"):
            await call
    else:
        result = await call
        assert result.retained_rows == 1
        assert result.mutated is False
    mutation.assert_not_called()


def test_limited_reconciliation_requires_an_explicit_bound_cohort():
    from bioetl.domain.workflow.config import WorkflowConfig, TransformStepConfig
    from bioetl.domain.workflow._delete_orphans_scope import (
        reject_delete_orphans_after_limited_extracts,
    )
    from dataclasses import replace

    source = WorkflowStepConfig(
        "assay", "chembl_assay", run_options=WorkflowRunOptionsConfig(limit=1000)
    )
    reference = WorkflowStepConfig(
        "target",
        "chembl_target",
        depends_on=("assay",),
        reference_cohort=WorkflowReferenceCohort(
            "assay", "chembl.assay", "target_id", "target_id"
        ),
    )
    transform = TransformStepConfig(
        "fk",
        "reconcile_foreign_keys",
        depends_on=("target",),
        config={
            "action": "delete_orphans",
            "source_table": "chembl.assay",
            "reference_table": "chembl.target",
            "source_key": "target_id",
            "reference_key": "target_id",
            "require_closed_cohort": True,
        },
    )
    config = WorkflowConfig(name="bounded", steps=(source, reference, transform))
    reject_delete_orphans_after_limited_extracts(config)
    independent = replace(
        config, steps=(source, replace(reference, reference_cohort=None), transform)
    )
    with pytest.raises(ValueError, match="independently bounded"):
        reject_delete_orphans_after_limited_extracts(independent)
