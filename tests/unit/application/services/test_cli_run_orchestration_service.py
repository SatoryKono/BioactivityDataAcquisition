"""Tests for CLI run orchestration request preparation and execution."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunResult,
)
from bioetl.application.services.execution.cli_run_orchestration_contracts import (
    MetricsFlushCallable,
    RunCoroutineCallable,
    RunPreparedPipelineCallable,
)
from bioetl.application.services.execution.cli_run_orchestration_models import (
    CliRunOptionsInput,
    CliRunPreparationInput,
    RunExecutionRequest,
    RunPreparationResult,
    StartOffsetValidationResult,
)
from bioetl.application.services.execution.cli_run_orchestration_service import (
    CliRunOrchestrationService,
)
from tests.helpers.synthetic_paths import synthetic_test_root

TEST_ROOT = synthetic_test_root("cli-run-orchestration")
CACHED_BRONZE_PATH = str(TEST_ROOT / "bronze")


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
            CliRunPreparationInput(
                pipeline="chembl_activity",
                options=CliRunOptionsInput(
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
                    use_cached_bronze=True,
                    cached_bronze_date="2026-03-12",
                    cached_bronze_path=CACHED_BRONZE_PATH,
                ),
                health_server=False,
                health_port=8081,
            )
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

    def test_prepare_execution_request_preserves_exact_replay_only_with_cached_bronze(
        self,
    ) -> None:
        service = CliRunOrchestrationService()

        result = service.prepare_execution_request(
            CliRunPreparationInput(
                pipeline="chembl_activity",
                options=CliRunOptionsInput(
                    run_type="incremental",
                    resume=False,
                    start_offset=None,
                    limit=25,
                    input_csv=None,
                    filter_column=None,
                    filter_field=None,
                    dry_run=False,
                    vacuum_after_run=None,
                    vacuum_retention_days=None,
                    debug=False,
                    use_cached_bronze=True,
                    cached_bronze_date="2026-03-12",
                    cached_bronze_path=CACHED_BRONZE_PATH,
                    exact_replay=True,
                ),
                health_server=False,
                health_port=8081,
            )
        )

        assert result.is_valid is True
        assert result.request is not None
        assert result.request.options.use_cached_bronze is True
        assert result.request.options.cached_bronze_date == "2026-03-12"
        assert result.request.options.cached_bronze_path == CACHED_BRONZE_PATH
        assert result.request.options.exact_replay is True

    def test_invalid_start_offset_returns_error_without_request(self) -> None:
        service = CliRunOrchestrationService()

        result = service.prepare_execution_request(
            CliRunPreparationInput(
                pipeline="chembl_activity",
                options=CliRunOptionsInput(
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
                    use_cached_bronze=False,
                    cached_bronze_date=None,
                    cached_bronze_path=None,
                ),
                health_server=True,
                health_port=8080,
            )
        )

        assert result.is_valid is False
        assert result.request is None
        assert result.error_message == "--start-offset requires --run-type=incremental"

    def test_exact_replay_requires_cached_bronze(self) -> None:
        service = CliRunOrchestrationService()

        result = service.prepare_execution_request(
            CliRunPreparationInput(
                pipeline="chembl_activity",
                options=CliRunOptionsInput(
                    run_type="incremental",
                    resume=False,
                    start_offset=None,
                    limit=None,
                    input_csv=None,
                    filter_column=None,
                    filter_field=None,
                    dry_run=False,
                    vacuum_after_run=None,
                    vacuum_retention_days=None,
                    debug=False,
                    use_cached_bronze=False,
                    cached_bronze_date=None,
                    cached_bronze_path=None,
                    exact_replay=True,
                ),
                health_server=True,
                health_port=8080,
            )
        )

        assert result.is_valid is False
        assert result.request is None
        assert (
            result.error_message
            == "--exact-replay currently requires --use-cached-bronze with snapshot-backed Bronze inputs"
        )

    def test_replay_parentage_requires_exact_replay(self) -> None:
        service = CliRunOrchestrationService()

        result = service.prepare_execution_request(
            CliRunPreparationInput(
                pipeline="chembl_activity",
                options=CliRunOptionsInput(
                    run_type="incremental",
                    resume=False,
                    start_offset=None,
                    limit=None,
                    input_csv=None,
                    filter_column=None,
                    filter_field=None,
                    dry_run=False,
                    vacuum_after_run=None,
                    vacuum_retention_days=None,
                    debug=False,
                    use_cached_bronze=True,
                    cached_bronze_date="2026-03-12",
                    cached_bronze_path=CACHED_BRONZE_PATH,
                    replay_of_run_id="run-parent",
                    replay_of_manifest_id="manifest-parent",
                    exact_replay=False,
                ),
                health_server=True,
                health_port=8080,
            )
        )

        assert result.is_valid is False
        assert result.request is None
        assert (
            result.error_message
            == "--replay-of-run-id/--replay-of-manifest-id require --exact-replay"
        )

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
            CliRunOptionsInput(
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
        )

        assert options.vacuum_after_run is None

    def test_build_options_propagates_exact_replay(self) -> None:
        service = CliRunOrchestrationService()

        options = service.build_options(
            CliRunOptionsInput(
                run_type="incremental",
                resume=False,
                start_offset=None,
                limit=10,
                input_csv=None,
                filter_column=None,
                filter_field=None,
                dry_run=False,
                vacuum_after_run=None,
                vacuum_retention_days=None,
                debug=False,
                use_cached_bronze=True,
                cached_bronze_date="2026-03-12",
                cached_bronze_path=CACHED_BRONZE_PATH,
                exact_replay=True,
            )
        )

        assert options.use_cached_bronze is True
        assert options.exact_replay is True

    def test_build_options_propagates_replay_parentage(self) -> None:
        service = CliRunOrchestrationService()

        options = service.build_options(
            CliRunOptionsInput(
                run_type="incremental",
                resume=False,
                start_offset=None,
                limit=10,
                input_csv=None,
                filter_column=None,
                filter_field=None,
                dry_run=False,
                vacuum_after_run=None,
                vacuum_retention_days=None,
                debug=False,
                use_cached_bronze=True,
                cached_bronze_date="2026-03-12",
                cached_bronze_path=CACHED_BRONZE_PATH,
                replay_of_run_id="run-parent",
                replay_of_manifest_id="manifest-parent",
                exact_replay=True,
            )
        )

        assert options.replay_of_run_id == "run-parent"
        assert options.replay_of_manifest_id == "manifest-parent"

    def test_prepare_execution_request_propagates_replay_parentage(self) -> None:
        service = CliRunOrchestrationService()

        result = service.prepare_execution_request(
            CliRunPreparationInput(
                pipeline="chembl_activity",
                options=CliRunOptionsInput(
                    run_type="incremental",
                    resume=False,
                    start_offset=None,
                    limit=25,
                    input_csv=None,
                    filter_column=None,
                    filter_field=None,
                    dry_run=False,
                    vacuum_after_run=None,
                    vacuum_retention_days=None,
                    debug=False,
                    use_cached_bronze=True,
                    cached_bronze_date="2026-03-12",
                    cached_bronze_path=CACHED_BRONZE_PATH,
                    replay_of_run_id="run-parent",
                    replay_of_manifest_id="manifest-parent",
                    exact_replay=True,
                ),
                health_server=False,
                health_port=8081,
            )
        )

        assert result.is_valid is True
        assert result.request is not None
        assert result.request.options.replay_of_run_id == "run-parent"
        assert result.request.options.replay_of_manifest_id == "manifest-parent"


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
            await asyncio.sleep(0)
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
            await asyncio.sleep(0)
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
                await asyncio.sleep(0)
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
