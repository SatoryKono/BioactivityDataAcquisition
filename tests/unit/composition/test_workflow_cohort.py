"""Bounded reference extraction is tied to actual upstream run rows."""

from unittest.mock import AsyncMock, MagicMock

import pyarrow as pa
import pytest

from bioetl.composition.bootstrap.assembly.workflow_transforms import (
    WorkflowCohortResolver,
)
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
