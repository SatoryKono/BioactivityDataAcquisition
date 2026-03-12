"""Tests for CLI run orchestration request preparation and execution."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from bioetl.application.services import PipelineRunResult, RunResult
from bioetl.application.services.cli_run_orchestration_service import (
    CliRunOrchestrationService,
    RunExecutionRequest,
)


def _make_result(**kwargs: object) -> RunResult:
    defaults: dict[str, object] = {
        "status": PipelineRunResult.SUCCESS,
        "pipeline_name": "chembl_activity",
        "run_id": "run-001",
        "run_type": "incremental",
        "records_fetched": 0,
        "records_bronze": 0,
        "records_silver": 0,
        "records_gold": 0,
        "records_quarantined": 0,
        "error_message": None,
        "error_type": None,
    }
    defaults.update(kwargs)  # type: ignore[arg-type]
    return RunResult(**defaults)  # type: ignore[arg-type]


class TestPrepareExecutionRequest:
    """Tests for request preparation from raw CLI arguments."""

    def test_builds_prepared_request_for_valid_inputs(self) -> None:
        service = CliRunOrchestrationService()

        result = service.prepare_execution_request(
            pipeline="chembl_activity",
            run_type="incremental",
            resume=False,
            start_offset=10,
            limit=25,
            input_csv="filters.csv",
            filter_column="id",
            filter_field="molecule_id",
            dry_run=False,
            vacuum_after_run=True,
            vacuum_retention_days=7,
            debug=True,
            health_server=False,
            health_port=8081,
            use_cached_bronze=True,
            cached_bronze_date="2026-03-12",
            cached_bronze_path="/tmp/bronze",
        )

        assert result.is_valid is True
        assert result.request is not None
        assert result.request.pipeline == "chembl_activity"
        assert result.request.health_server is False
        assert result.request.health_port == 8081
        assert result.request.options.start_offset == 10
        assert result.request.options.limit == 25
        assert result.request.options.input_csv == "filters.csv"
        assert result.request.options.filter_column == "id"
        assert result.request.options.filter_field == "molecule_id"
        assert result.request.options.log_level == "DEBUG"
        assert result.request.options.use_cached_bronze is True

    def test_invalid_start_offset_returns_error_without_request(self) -> None:
        service = CliRunOrchestrationService()

        result = service.prepare_execution_request(
            pipeline="chembl_activity",
            run_type="backfill",
            resume=False,
            start_offset=5,
            limit=None,
            input_csv=None,
            filter_column=None,
            filter_field=None,
            dry_run=False,
            vacuum_after_run=None,
            vacuum_retention_days=None,
            debug=False,
            health_server=True,
            health_port=8080,
            use_cached_bronze=False,
            cached_bronze_date=None,
            cached_bronze_path=None,
        )

        assert result.is_valid is False
        assert result.request is None
        assert result.error_message == "--start-offset requires --run-type=incremental"


class TestExecutePipeline:
    """Tests for orchestration of prepared run requests."""

    def test_execute_pipeline_runs_request_and_flushes_metrics(self) -> None:
        service = CliRunOrchestrationService()
        request = RunExecutionRequest(
            pipeline="chembl_activity",
            options=MagicMock(name="run_options"),
            health_server=True,
            health_port=8080,
        )
        expected = _make_result()
        flushed = MagicMock()

        async def _run_pipeline(prepared: RunExecutionRequest) -> RunResult:
            assert prepared is request
            return expected

        result = service.execute_pipeline(
            request=request,
            run_pipeline_async=_run_pipeline,
            run_coroutine=asyncio.run,
            flush_metrics=flushed,
        )

        assert result is expected
        flushed.assert_called_once_with(pipeline_name="chembl_activity")
