"""Unit tests for PostrunDQReportService.

Tests DQ report generation orchestration: happy path, missing service/context,
strict vs warning mode, BioETLError handling, allowlisted errors.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.postrun.dq_report_orchestrator import (
    PostrunDQReportService,
)
from bioetl.domain.exceptions import BioETLError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_dq_report_result(
    *,
    any_generated: bool = True,
    reports_count: int = 2,
    bronze_enabled: bool = True,
    silver_enabled: bool = True,
    gold_enabled: bool = False,
) -> MagicMock:
    """Build a mock DQReportResult."""
    result = MagicMock()
    result.any_generated = any_generated
    result.reports_count = reports_count
    result.bronze_enabled = bronze_enabled
    result.silver_enabled = silver_enabled
    result.gold_enabled = gold_enabled
    return result


def _make_dq_report_context() -> MagicMock:
    """Build a minimal mock DQReportContext."""
    ctx = MagicMock()
    ctx.run_id = "test-run-id"
    return ctx


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger."""
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture
def mock_runtime() -> MagicMock:
    """Create a mock runtime with strict_validation=False."""
    runtime = MagicMock()
    runtime.strict_validation = False
    return runtime


@pytest.fixture
def strict_runtime() -> MagicMock:
    """Create a mock runtime with strict_validation=True."""
    runtime = MagicMock()
    runtime.strict_validation = True
    return runtime


@pytest.fixture
def mock_dq_report_service() -> MagicMock:
    """Create a mock DQReportService."""
    service = MagicMock()
    service.generate_reports = AsyncMock(return_value=_make_dq_report_result())
    return service


@pytest.fixture
def mock_bronze_dq_config() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_silver_dq_config() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_gold_dq_config() -> MagicMock:
    return MagicMock()


@pytest.fixture
def postrun_dq_service(
    mock_logger: MagicMock,
    mock_runtime: MagicMock,
    mock_dq_report_service: MagicMock,
    mock_bronze_dq_config: MagicMock,
    mock_silver_dq_config: MagicMock,
    mock_gold_dq_config: MagicMock,
) -> PostrunDQReportService:
    """Create PostrunDQReportService with all dependencies."""
    return PostrunDQReportService(
        logger=mock_logger,
        runtime=mock_runtime,
        dq_report_service=mock_dq_report_service,
        bronze_dq_config=mock_bronze_dq_config,
        silver_dq_config=mock_silver_dq_config,
        gold_dq_config=mock_gold_dq_config,
        warning_allowlist=(RuntimeError, OSError),
    )


# ---------------------------------------------------------------------------
# Tests: Happy Path
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPostrunDQReportServiceHappyPath:
    """Tests for successful DQ report generation."""

    @pytest.mark.asyncio
    async def test_generate_reports_returns_result(
        self,
        postrun_dq_service: PostrunDQReportService,
        mock_dq_report_service: MagicMock,
    ) -> None:
        """Test that generate_reports returns the DQReportResult on success."""
        ctx = _make_dq_report_context()
        result = await postrun_dq_service.generate_reports(ctx)

        assert result is not None
        mock_dq_report_service.generate_reports.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_generate_reports_passes_configs(
        self,
        postrun_dq_service: PostrunDQReportService,
        mock_dq_report_service: MagicMock,
        mock_bronze_dq_config: MagicMock,
        mock_silver_dq_config: MagicMock,
        mock_gold_dq_config: MagicMock,
    ) -> None:
        """Test that all DQ configs are forwarded to generate_reports."""
        ctx = _make_dq_report_context()
        await postrun_dq_service.generate_reports(ctx)

        call_kwargs = mock_dq_report_service.generate_reports.call_args[1]
        assert call_kwargs["bronze_config"] is mock_bronze_dq_config
        assert call_kwargs["silver_config"] is mock_silver_dq_config
        assert call_kwargs["gold_config"] is mock_gold_dq_config

    @pytest.mark.asyncio
    async def test_generate_reports_logs_info_when_any_generated(
        self,
        postrun_dq_service: PostrunDQReportService,
        mock_logger: MagicMock,
    ) -> None:
        """Test that info is logged when reports are generated."""
        ctx = _make_dq_report_context()
        await postrun_dq_service.generate_reports(ctx)

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0]
        assert "dq_reports_completed" in call_args

    @pytest.mark.asyncio
    async def test_generate_reports_no_info_when_not_generated(
        self,
        mock_logger: MagicMock,
        mock_runtime: MagicMock,
    ) -> None:
        """Test that info is NOT logged when any_generated is False."""
        service_mock = MagicMock()
        service_mock.generate_reports = AsyncMock(
            return_value=_make_dq_report_result(any_generated=False, reports_count=0)
        )
        service = PostrunDQReportService(
            logger=mock_logger,
            runtime=mock_runtime,
            dq_report_service=service_mock,
            bronze_dq_config=None,
            silver_dq_config=None,
            gold_dq_config=None,
            warning_allowlist=(RuntimeError,),
        )
        ctx = _make_dq_report_context()
        await service.generate_reports(ctx)

        mock_logger.info.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: Early-exit Conditions
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPostrunDQReportServiceEarlyExit:
    """Tests for early-exit when service or context is missing."""

    @pytest.mark.asyncio
    async def test_returns_none_when_service_is_none(
        self, mock_logger: MagicMock, mock_runtime: MagicMock
    ) -> None:
        """Test that None is returned when dq_report_service is None."""
        service = PostrunDQReportService(
            logger=mock_logger,
            runtime=mock_runtime,
            dq_report_service=None,
            bronze_dq_config=None,
            silver_dq_config=None,
            gold_dq_config=None,
            warning_allowlist=(RuntimeError,),
        )
        ctx = _make_dq_report_context()
        result = await service.generate_reports(ctx)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_context_is_none(
        self,
        postrun_dq_service: PostrunDQReportService,
        mock_logger: MagicMock,
    ) -> None:
        """Test that None is returned and debug is logged when context is None."""
        result = await postrun_dq_service.generate_reports(None)

        assert result is None
        mock_logger.debug.assert_called_once()

    @pytest.mark.asyncio
    async def test_debug_log_on_missing_context(
        self,
        postrun_dq_service: PostrunDQReportService,
        mock_logger: MagicMock,
    ) -> None:
        """Test that debug log mentions reason when context is missing."""
        await postrun_dq_service.generate_reports(None)

        call_args = mock_logger.debug.call_args[0]
        assert "dq_report_skipped" in call_args


# ---------------------------------------------------------------------------
# Tests: Warning Mode Error Handling
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPostrunDQReportServiceWarningMode:
    """Tests for warning-mode error handling (strict_validation=False)."""

    @pytest.mark.asyncio
    async def test_allowlisted_error_returns_none_in_warning_mode(
        self,
        mock_logger: MagicMock,
        mock_runtime: MagicMock,
    ) -> None:
        """Test that allowlisted errors return None in warning mode."""
        service_mock = MagicMock()
        service_mock.generate_reports = AsyncMock(
            side_effect=RuntimeError("network failure")
        )
        service = PostrunDQReportService(
            logger=mock_logger,
            runtime=mock_runtime,
            dq_report_service=service_mock,
            bronze_dq_config=None,
            silver_dq_config=None,
            gold_dq_config=None,
            warning_allowlist=(RuntimeError,),
        )
        ctx = _make_dq_report_context()
        result = await service.generate_reports(ctx)

        assert result is None

    @pytest.mark.asyncio
    async def test_allowlisted_error_logs_error_and_warning_in_warning_mode(
        self,
        mock_logger: MagicMock,
        mock_runtime: MagicMock,
    ) -> None:
        """Test that both error and warning are logged in warning mode."""
        service_mock = MagicMock()
        service_mock.generate_reports = AsyncMock(side_effect=RuntimeError("io error"))
        service = PostrunDQReportService(
            logger=mock_logger,
            runtime=mock_runtime,
            dq_report_service=service_mock,
            bronze_dq_config=None,
            silver_dq_config=None,
            gold_dq_config=None,
            warning_allowlist=(RuntimeError,),
        )
        ctx = _make_dq_report_context()
        await service.generate_reports(ctx)

        mock_logger.error.assert_called_once()
        mock_logger.warning.assert_called_once()
        error_kwargs = mock_logger.error.call_args[1]
        assert error_kwargs.get("strict_mode") is False

    @pytest.mark.asyncio
    async def test_bioetl_error_returns_none_in_warning_mode(
        self,
        mock_logger: MagicMock,
        mock_runtime: MagicMock,
    ) -> None:
        """Test that BioETLError returns None in warning mode."""
        service_mock = MagicMock()
        service_mock.generate_reports = AsyncMock(side_effect=BioETLError("dq failed"))
        service = PostrunDQReportService(
            logger=mock_logger,
            runtime=mock_runtime,
            dq_report_service=service_mock,
            bronze_dq_config=None,
            silver_dq_config=None,
            gold_dq_config=None,
            warning_allowlist=(RuntimeError,),
        )
        ctx = _make_dq_report_context()
        result = await service.generate_reports(ctx)

        assert result is None
        mock_logger.error.assert_called_once()
        mock_logger.warning.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: Strict Mode Error Handling
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPostrunDQReportServiceStrictMode:
    """Tests for strict mode error handling (strict_validation=True)."""

    @pytest.mark.asyncio
    async def test_allowlisted_error_raises_in_strict_mode(
        self,
        mock_logger: MagicMock,
        strict_runtime: MagicMock,
    ) -> None:
        """Test that allowlisted errors re-raise in strict mode."""
        service_mock = MagicMock()
        service_mock.generate_reports = AsyncMock(
            side_effect=RuntimeError("storage error")
        )
        service = PostrunDQReportService(
            logger=mock_logger,
            runtime=strict_runtime,
            dq_report_service=service_mock,
            bronze_dq_config=None,
            silver_dq_config=None,
            gold_dq_config=None,
            warning_allowlist=(RuntimeError,),
        )
        ctx = _make_dq_report_context()

        with pytest.raises(RuntimeError, match="storage error"):
            await service.generate_reports(ctx)

    @pytest.mark.asyncio
    async def test_strict_mode_logs_error_with_strict_mode_true(
        self,
        mock_logger: MagicMock,
        strict_runtime: MagicMock,
    ) -> None:
        """Test that strict mode logs error with strict_mode=True."""
        service_mock = MagicMock()
        service_mock.generate_reports = AsyncMock(
            side_effect=RuntimeError("strict error")
        )
        service = PostrunDQReportService(
            logger=mock_logger,
            runtime=strict_runtime,
            dq_report_service=service_mock,
            bronze_dq_config=None,
            silver_dq_config=None,
            gold_dq_config=None,
            warning_allowlist=(RuntimeError,),
        )
        ctx = _make_dq_report_context()

        with pytest.raises(RuntimeError):
            await service.generate_reports(ctx)

        mock_logger.error.assert_called_once()
        error_kwargs = mock_logger.error.call_args[1]
        assert error_kwargs.get("strict_mode") is True
        assert (
            error_kwargs.get("reason_code")
            == "POSTRUN_DQ_REPORT_GENERATION_FAILED_STRICT"
        )

    @pytest.mark.asyncio
    async def test_bioetl_error_raises_in_strict_mode(
        self,
        mock_logger: MagicMock,
        strict_runtime: MagicMock,
    ) -> None:
        """Test that BioETLError re-raises in strict mode."""
        service_mock = MagicMock()
        service_mock.generate_reports = AsyncMock(
            side_effect=BioETLError("bioetl strict")
        )
        service = PostrunDQReportService(
            logger=mock_logger,
            runtime=strict_runtime,
            dq_report_service=service_mock,
            bronze_dq_config=None,
            silver_dq_config=None,
            gold_dq_config=None,
            warning_allowlist=(RuntimeError,),
        )
        ctx = _make_dq_report_context()

        with pytest.raises(BioETLError):
            await service.generate_reports(ctx)


# ---------------------------------------------------------------------------
# Tests: _is_strict_validation_enabled helper
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsStrictValidationEnabled:
    """Tests for _is_strict_validation_enabled private helper."""

    def test_returns_false_when_strict_validation_false(
        self, mock_logger: MagicMock
    ) -> None:
        """Test helper returns False when strict_validation is False."""
        runtime = MagicMock()
        runtime.strict_validation = False
        service = PostrunDQReportService(
            logger=mock_logger,
            runtime=runtime,
            dq_report_service=None,
            bronze_dq_config=None,
            silver_dq_config=None,
            gold_dq_config=None,
            warning_allowlist=(),
        )
        assert service._is_strict_validation_enabled() is False

    def test_returns_true_when_strict_validation_true(
        self, mock_logger: MagicMock
    ) -> None:
        """Test helper returns True when strict_validation is True."""
        runtime = MagicMock()
        runtime.strict_validation = True
        service = PostrunDQReportService(
            logger=mock_logger,
            runtime=runtime,
            dq_report_service=None,
            bronze_dq_config=None,
            silver_dq_config=None,
            gold_dq_config=None,
            warning_allowlist=(),
        )
        assert service._is_strict_validation_enabled() is True

    def test_returns_false_when_attribute_missing(self, mock_logger: MagicMock) -> None:
        """Test helper returns False when runtime lacks strict_validation."""
        runtime = object()  # has no strict_validation attribute
        service = PostrunDQReportService(
            logger=mock_logger,
            runtime=runtime,
            dq_report_service=None,
            bronze_dq_config=None,
            silver_dq_config=None,
            gold_dq_config=None,
            warning_allowlist=(),
        )
        assert service._is_strict_validation_enabled() is False

    def test_returns_false_when_attribute_is_truthy_non_bool(
        self, mock_logger: MagicMock
    ) -> None:
        """Test that non-True truthy value (e.g. 1) still returns False via 'is True'."""
        runtime = MagicMock()
        runtime.strict_validation = 1  # truthy but not True
        service = PostrunDQReportService(
            logger=mock_logger,
            runtime=runtime,
            dq_report_service=None,
            bronze_dq_config=None,
            silver_dq_config=None,
            gold_dq_config=None,
            warning_allowlist=(),
        )
        # Implementation uses "is True", so integer 1 should return False
        assert service._is_strict_validation_enabled() is False
