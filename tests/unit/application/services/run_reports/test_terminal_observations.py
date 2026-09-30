"""Terminal Data Validation and Workflow observations (#11795)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.application.services.execution._pipeline_runner_support import (
    finalize_pipeline_run_report,
)
from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunOptions,
    RunResult,
)
from bioetl.application.services.run_reports.observations import (
    bind_run_observations,
    record_run_observation,
    reset_run_observations,
    run_observations,
)
from tests.helpers.run_report_store import MemoryReportStore

pytestmark = pytest.mark.unit

_STARTED = datetime(2026, 9, 30, 6, 29, tzinfo=UTC)
_COMPLETED = datetime(2026, 9, 30, 6, 30, tzinfo=UTC)


def _result(
    *,
    status: PipelineRunResult,
    records_gold: int = 0,
    records_silver: int = 0,
    records_bronze: int = 0,
) -> RunResult:
    return RunResult(
        status=status,
        pipeline_name="chembl_publication_term",
        run_id="11111111-1111-4111-8111-111111111111",
        run_type="incremental",
        records_gold=records_gold,
        records_silver=records_silver,
        records_bronze=records_bronze,
        started_at=_STARTED,
        completed_at=_COMPLETED,
    )


def test_finalize_empty_success_records_no_gold_candidates() -> None:
    token = bind_run_observations()
    try:
        finalize_pipeline_run_report(
            result=_result(status=PipelineRunResult.SUCCESS), store=MemoryReportStore()
        )
        observation = run_observations()["Data Validation"]
        assert observation["verdict"] == "N/A"
        assert observation["reason"] == "no_gold_candidates"
        assert observation["facts"]["gold_candidates"] == 0
    finally:
        reset_run_observations(token)


def test_finalize_failed_run_records_gold_not_attempted() -> None:
    token = bind_run_observations()
    try:
        finalize_pipeline_run_report(
            result=_result(status=PipelineRunResult.FAILED),
            store=MemoryReportStore(),
        )
        observation = run_observations()["Data Validation"]
        assert observation["verdict"] == "INCOMPLETE"
        assert observation["reason"] == "gold_not_attempted"
    finally:
        reset_run_observations(token)


def test_finalize_child_records_workflow_parent_not_finalized() -> None:
    token = bind_run_observations()
    try:
        finalize_pipeline_run_report(
            result=_result(status=PipelineRunResult.FAILED),
            options=RunOptions(
                workflow_id="chembl_reference_pack",
                workflow_run_id="wf-run-1",
                workflow_step_id="publication_term",
            ),
            store=MemoryReportStore(),
        )
        observation = run_observations()["Workflow"]
        assert observation["verdict"] == "INCOMPLETE"
        assert observation["reason"] == "workflow_parent_not_finalized"
        assert observation["facts"]["workflow_run_id"] == "wf-run-1"
        assert observation["facts"]["workflow_id"] == "chembl_reference_pack"
        assert observation["facts"]["step_id"] == "publication_term"
    finally:
        reset_run_observations(token)


def test_finalize_does_not_erase_existing_data_validation() -> None:
    token = bind_run_observations()
    try:
        record_run_observation(
            "Data Validation",
            verdict="OK",
            reason="run_gold_schema_validation",
            facts={"valid": True, "records": 3},
        )
        finalize_pipeline_run_report(
            result=_result(status=PipelineRunResult.SUCCESS, records_gold=3),
            store=MemoryReportStore(),
        )
        observation = run_observations()["Data Validation"]
        assert observation["verdict"] == "OK"
        assert observation["reason"] == "run_gold_schema_validation"
    finally:
        reset_run_observations(token)
