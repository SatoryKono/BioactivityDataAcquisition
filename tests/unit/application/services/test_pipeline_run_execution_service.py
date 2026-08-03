# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
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
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Focused unit tests for PipelineRunExecutionService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.services.execution.pipeline_run_execution_service import (
    PipelineExecutionResult,
    PipelineRunExecutionService,
)
from bioetl.domain.exceptions.pipeline_shutdown import PipelineShutdownError
from tests.helpers.clock import FixedClock


@pytest.fixture
def service() -> PipelineRunExecutionService:
    """Create the execution helper under test."""
    return PipelineRunExecutionService(
        clock=FixedClock(datetime(2026, 4, 13, 12, 0, tzinfo=UTC)),
    )


@pytest.fixture
def runner() -> MagicMock:
    """Create a metrics-capable async runner double."""
    candidate = MagicMock()
    candidate.run = AsyncMock()
    return candidate


@pytest.fixture
def run_logger() -> MagicMock:
    """Create a structured logger double."""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.exception = MagicMock()
    return logger


@pytest.fixture
def metrics_extractor() -> MagicMock:
    """Create a metrics extractor double."""
    extractor = MagicMock()
    extractor.extract_metrics.return_value = {"records_silver": 7}
    return extractor


@pytest.mark.unit
class TestPipelineRunExecutionService:
    """Direct branch coverage for execution helper behavior."""

    @pytest.mark.asyncio
    async def test_successful_execution_returns_normalized_result(
        self,
        service: PipelineRunExecutionService,
        runner: MagicMock,
        run_logger: MagicMock,
        metrics_extractor: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        started_at = datetime(2026, 4, 13, 12, 0, tzinfo=UTC)
        monkeypatch.setattr(
            "bioetl.application.services.execution.pipeline_run_execution_service.derive_completion_timestamp",
            MagicMock(return_value=(started_at + timedelta(seconds=5), 5.0)),
        )
        result = await service.execute(
            runner=runner,
            run_logger=run_logger,
            metrics_extractor=metrics_extractor,
            started_at=started_at,
            started_monotonic=100.0,
        )

        assert isinstance(result, PipelineExecutionResult)
        assert result.status == "success"
        assert result.error_message is None
        assert result.error_type is None
        assert result.metrics == {"records_silver": 7}
        assert result.completed_at.tzinfo is not None
        assert result.completed_at == started_at + timedelta(seconds=5)
        runner.run.assert_awaited_once()
        metrics_extractor.extract_metrics.assert_called_once_with(runner)
        run_logger.info.assert_called_once_with("Pipeline completed successfully")

    @pytest.mark.asyncio
    async def test_shutdown_error_maps_to_shutdown_status(
        self,
        service: PipelineRunExecutionService,
        runner: MagicMock,
        run_logger: MagicMock,
        metrics_extractor: MagicMock,
    ) -> None:
        runner.run.side_effect = PipelineShutdownError("stop")

        result = await service.execute(
            runner=runner,
            run_logger=run_logger,
            metrics_extractor=metrics_extractor,
        )

        assert result.status == "shutdown"
        assert result.error_message is None
        assert result.error_type is None
        metrics_extractor.extract_metrics.assert_called_once_with(runner)
        run_logger.warning.assert_called_once_with("Pipeline was gracefully shut down")

    @pytest.mark.asyncio
    async def test_expected_runtime_error_is_captured_and_logged(
        self,
        service: PipelineRunExecutionService,
        runner: MagicMock,
        run_logger: MagicMock,
        metrics_extractor: MagicMock,
    ) -> None:
        runner.run.side_effect = ValueError("bad config")

        result = await service.execute(
            runner=runner,
            run_logger=run_logger,
            metrics_extractor=metrics_extractor,
        )

        assert result.status == "failed"
        assert result.error_message == "bad config"
        assert result.error_type == "ValueError"
        metrics_extractor.extract_metrics.assert_called_once_with(runner)
        run_logger.exception.assert_called_once_with(
            "Pipeline failed with exception",
            error_type="ValueError",
        )

    @pytest.mark.asyncio
    async def test_unexpected_error_propagates_without_metrics_extraction(
        self,
        service: PipelineRunExecutionService,
        runner: MagicMock,
        run_logger: MagicMock,
        metrics_extractor: MagicMock,
    ) -> None:
        runner.run.side_effect = KeyError("unexpected")

        with pytest.raises(KeyError, match="unexpected"):
            await service.execute(
                runner=runner,
                run_logger=run_logger,
                metrics_extractor=metrics_extractor,
            )

        metrics_extractor.extract_metrics.assert_not_called()
        run_logger.exception.assert_not_called()

    @pytest.mark.asyncio
    async def test_metrics_extractor_failure_bubbles_after_successful_run(
        self,
        service: PipelineRunExecutionService,
        runner: MagicMock,
        run_logger: MagicMock,
        metrics_extractor: MagicMock,
    ) -> None:
        metrics_extractor.extract_metrics.side_effect = RuntimeError("metrics broken")

        with pytest.raises(RuntimeError, match="metrics broken"):
            await service.execute(
                runner=runner,
                run_logger=run_logger,
                metrics_extractor=metrics_extractor,
            )

        runner.run.assert_awaited_once()
        run_logger.info.assert_called_once_with("Pipeline completed successfully")
