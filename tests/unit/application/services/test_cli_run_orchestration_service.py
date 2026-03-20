"""Tests for CLI run orchestration request preparation and execution."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from bioetl.application.services import PipelineRunResult, RunResult
from bioetl.application.services.cli_run_orchestration_contracts import (
    MetricsFlushCallable as CanonicalMetricsFlushCallable,
    RunCoroutineCallable as CanonicalRunCoroutineCallable,
    RunPreparedPipelineCallable as CanonicalRunPreparedPipelineCallable,
)
from bioetl.application.services.cli_run_orchestration_models import (
    RunExecutionRequest as CanonicalRunExecutionRequest,
    RunPreparationResult as CanonicalRunPreparationResult,
    StartOffsetValidationResult as CanonicalStartOffsetValidationResult,
)
from bioetl.application.services.cli_run_orchestration_service import (
    CliRunOrchestrationService,
    MetricsFlushCallable,
    RunCoroutineCallable,
    RunExecutionRequest,
    RunPreparationResult,
    RunPreparedPipelineCallable,
    StartOffsetValidationResult,
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

    def test_service_module_re_exports_canonical_models_and_contracts(self) -> None:
        """Compatibility re-exports should stay identity-equal to canonical owners."""
        assert RunExecutionRequest is CanonicalRunExecutionRequest
        assert RunPreparationResult is CanonicalRunPreparationResult
        assert StartOffsetValidationResult is CanonicalStartOffsetValidationResult
        assert RunPreparedPipelineCallable is CanonicalRunPreparedPipelineCallable
        assert RunCoroutineCallable is CanonicalRunCoroutineCallable
        assert MetricsFlushCallable is CanonicalMetricsFlushCallable

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

    def test_validate_start_offset_rejects_negative_offset(self) -> None:
        service = CliRunOrchestrationService()

        result = service.validate_start_offset(
            start_offset=-1,
            run_type="incremental",
            resume=False,
        )

        assert result.is_valid is False
        assert result.error_message == "--start-offset must be non-negative"

    def test_validate_start_offset_rejects_resume_with_offset(self) -> None:
        service = CliRunOrchestrationService()

        result = service.validate_start_offset(
            start_offset=5,
            run_type="incremental",
            resume=True,
        )

        assert result.is_valid is False
        assert (
            result.error_message
            == "--start-offset and --resume cannot be used together"
        )

    def test_build_options_normalizes_false_vacuum_after_run_to_none(self) -> None:
        service = CliRunOrchestrationService()

        options = service.build_options(
            run_type="incremental",
            resume=False,
            start_offset=None,
            limit=10,
            input_csv=None,
            filter_column=None,
            filter_field=None,
            dry_run=False,
            vacuum_after_run=False,
            vacuum_retention_days=7,
            debug=False,
            use_cached_bronze=False,
            cached_bronze_date=None,
            cached_bronze_path=None,
        )

        assert options.vacuum_after_run is None


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

    def test_execute_pipeline_flushes_metrics_when_run_coroutine_raises(self) -> None:
        service = CliRunOrchestrationService()
        request = RunExecutionRequest(
            pipeline="chembl_activity",
            options=MagicMock(name="run_options"),
            health_server=True,
            health_port=8080,
        )
        flushed = MagicMock()

        async def _run_pipeline(prepared: RunExecutionRequest) -> RunResult:
            assert prepared is request
            return _make_result()

        def _raise_runtime_error(_coro: object) -> RunResult:
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            service.execute_pipeline(
                request=request,
                run_pipeline_async=_run_pipeline,
                run_coroutine=_raise_runtime_error,
                flush_metrics=flushed,
            )

        flushed.assert_called_once_with(pipeline_name="chembl_activity")

    def test_execute_pipeline_closes_created_coroutine_after_exception(self) -> None:
        service = CliRunOrchestrationService()
        request = RunExecutionRequest(
            pipeline="chembl_activity",
            options=MagicMock(name="run_options"),
            health_server=False,
            health_port=8081,
        )
        flushed = MagicMock()
        created: dict[str, object] = {}

        def _run_pipeline(_prepared: RunExecutionRequest) -> object:
            async def _inner() -> RunResult:
                return _make_result()

            coro = _inner()
            created["coro"] = coro
            return coro

        def _raise_runtime_error(_coro: object) -> RunResult:
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            service.execute_pipeline(
                request=request,
                run_pipeline_async=_run_pipeline,
                run_coroutine=_raise_runtime_error,
                flush_metrics=flushed,
            )

        created_coro = created["coro"]
        assert getattr(created_coro, "cr_frame", None) is None
        flushed.assert_called_once_with(pipeline_name="chembl_activity")
