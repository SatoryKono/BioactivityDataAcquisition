"""Composite children retain real terminal evidence before propagating failure."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from bioetl.application.services.execution.pipeline_run_context_service import (
    PipelineRunContextService,
)
from bioetl.application.services.execution.pipeline_run_execution_service import (
    PipelineRunExecutionService,
)
from bioetl.application.services.execution.pipeline_runner_models import RunOptions
from bioetl.application.services.execution.pipeline_runner_service import (
    PipelineRunnerService,
)
from bioetl.application.services.run_reports.observations import record_run_observation
from bioetl.composition.bootstrap.runtime.composite_child_runner import (
    build_reported_child_runner,
)
from bioetl.composition.bootstrap.runtime.pipeline_context_builder import (
    build_pipeline_context,
)
from bioetl.composition.factories.pipeline.runner import create_metrics_extractor
from bioetl.domain.exceptions.pipeline_shutdown import PipelineShutdownError
from bioetl.infrastructure.storage.run_report_store_adapter import (
    FileRunReportStoreAdapter,
)
from bioetl.infrastructure.time import SystemClock


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "outcome", ["success", "failure", "shutdown", "cancel", "constructor"]
)
async def test_terminal_child_report_survives_all_outcomes(
    tmp_path, monkeypatch, outcome
):
    clock = SystemClock()
    audit = MagicMock()
    audit.log_event = AsyncMock()
    service = PipelineRunnerService(
        runner_factory=MagicMock(),
        metrics_extractor=create_metrics_extractor(),
        logger=MagicMock(),
        metrics=MagicMock(),
        audit=audit,
        clock=clock,
        _context_service=PipelineRunContextService(),
        _execution_service=PipelineRunExecutionService(clock=clock),
        report_store=FileRunReportStoreAdapter(),
        report_root=tmp_path,
    )
    monkeypatch.setattr(
        "bioetl.composition.bootstrap.runtime.composite_child_runner.bootstrap_pipeline_runner_service",
        lambda: service,
    )
    options = RunOptions(
        limit=1000,
        skip_gold=True,
        ignore_yaml_filter=True,
        execution_context="dependency",
        multi_filter_ids={"target_id": ("CHEMBL1",), "component_id": ("2",)},
    )
    context = build_pipeline_context(
        "chembl_target",
        options,
        clock=clock,
        run_id=UUID("00000000-0000-0000-0000-000000000120"),
    )

    class Runner:
        run_id = str(context.run_id)
        shutdown_signal = None
        execution_metrics = {
            "records_fetched": 1,
            "records_bronze": 1,
            "records_silver": 1,
            "records_gold": 0,
            "records_quarantined": 0,
            "records_gold_excluded_by_contract": 0,
        }

        async def run(self):
            if outcome == "failure":
                raise ValueError("provider failed")
            if outcome == "shutdown":
                raise PipelineShutdownError("stop")
            if outcome == "cancel":
                raise asyncio.CancelledError()

    def builder(actual):
        assert actual.limit == 1000
        assert actual.skip_gold and actual.ignore_yaml_filter
        assert actual.execution_context.value == "dependency"
        assert actual.input_filter.multi_filter_ids == options.multi_filter_ids
        record_run_observation(
            "Provider", verdict="OK", reason="constructor_probe", facts={}
        )
        if outcome == "constructor":
            raise ValueError("bad construction")
        return Runner()

    runner = build_reported_child_runner(
        context=context, options=options, runner_builder=builder
    )
    if outcome == "success":
        await runner.run()
        assert runner.execution_metrics["records_silver"] == 1
    else:
        expected = {
            "failure": RuntimeError,
            "shutdown": PipelineShutdownError,
            "cancel": asyncio.CancelledError,
            "constructor": ValueError,
        }[outcome]
        with pytest.raises(expected):
            await runner.run()
    reports = [json.loads(p.read_text()) for p in tmp_path.rglob("*.json")]
    reports = [
        r for r in reports if r.get("schema_version") == "pipeline_run_report_v2"
    ]
    assert reports
    expected_status = (
        "success"
        if outcome == "success"
        else "shutdown"
        if outcome in {"cancel", "shutdown"}
        else "failed"
    )
    assert all(r["identity"]["status"] == expected_status for r in reports)
    assert all(r["identity"]["run_id"] == runner.run_id for r in reports)
    assert all(
        r["observations"]["Provider"]["reason"] == "constructor_probe" for r in reports
    )
