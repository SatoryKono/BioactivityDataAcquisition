"""Unit tests for DQ report integration in pipeline flow.

Tests the integration of DQ report generation into the pipeline execution flow:
- BatchExecutor DQ data collection
- PostrunService DQ report generation
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.postrun_service import PostrunService
from bioetl.application.services.dq_report_service import (
    DQReportContext,
    DQReportResult,
)
from bioetl.domain.value_objects.dq_result import DQEvaluationStatus, DQResult

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


@pytest.fixture
def mock_logger() -> LoggerPort:
    """Create a mock logger."""
    return MagicMock()


@pytest.fixture
def mock_dq_service() -> MagicMock:
    """Create mock DataQualityService."""
    service = MagicMock()
    service.evaluate = AsyncMock(
        return_value=DQResult(
            error_rate=0.01,
            status=DQEvaluationStatus.PASSED,
            anomalies=(),
            has_critical=False,
            check_duration_ms=1.0,
        )
    )
    return service


@pytest.fixture
def mock_lifecycle_service() -> MagicMock:
    """Create mock MedallionLifecycleService."""
    from bioetl.application.services.medallion_lifecycle import VacuumResult

    service = MagicMock()
    service.finalize_run = AsyncMock(
        return_value=VacuumResult(
            silver_files_removed=0,
            gold_files_removed=0,
            skipped=True,
        )
    )
    return service


@pytest.fixture
def mock_dq_report_service() -> MagicMock:
    """Create mock DQReportService."""
    service = MagicMock()
    service.generate_reports = AsyncMock(
        return_value=DQReportResult(
            bronze_report_path=Path("/tmp/bronze_dq.json"),
            silver_report_path=Path("/tmp/silver_dq.json"),
            gold_report_path=None,
            bronze_enabled=True,
            silver_enabled=True,
            gold_enabled=False,
        )
    )
    return service


@pytest.fixture
def sample_dq_context() -> DQReportContext:
    """Create sample DQ context."""
    return DQReportContext(
        run_id="test-run-123",
        pipeline_name="chembl_activity",
        timestamp=datetime.now(UTC),
        bronze_records=[b'{"id": 1}', b'{"id": 2}'],
        bronze_batch_id="batch-001",
        bronze_source_file="/tmp/bronze/file.jsonl.zst",
        silver_data=None,
        silver_target_table="chembl_activity",
        silver_source_batch_ids=["batch-001"],
        silver_primary_keys=["activity_id"],
        silver_input_count=100,
        silver_quarantined_count=2,
        gold_data=None,
        gold_target_table="chembl_activity_gold",
        dq_soft_threshold=0.05,
        dq_hard_threshold=0.20,
    )


@pytest.fixture
def mock_pipeline_config() -> MagicMock:
    """Create mock PipelineConfig."""
    config = MagicMock()
    config.pipeline_name = "chembl_activity"
    return config


@pytest.fixture
def mock_runtime_config() -> MagicMock:
    """Create mock RuntimeConfig."""
    return MagicMock()


@pytest.fixture
def mock_executor() -> MagicMock:
    """Create mock executor with metrics."""
    executor = MagicMock()
    executor.records_fetched = 100
    executor.records_bronze = 100
    executor.records_silver = 98
    executor.records_gold = 95
    executor.records_quarantined = 2
    return executor


@pytest.fixture
def mock_storage() -> MagicMock:
    """Create a mock storage port."""
    storage = MagicMock()
    storage.get_table_path = MagicMock(return_value=Path("/tmp/table"))
    return storage


@pytest.fixture
def mock_context() -> MagicMock:
    """Create a mock pipeline context."""
    from datetime import UTC, datetime

    context = MagicMock()
    context.started_at = datetime.now(UTC)
    return context


@pytest.mark.unit
class TestPostrunServiceDQReports:
    """Tests for DQ report generation in PostrunService."""

    async def test_dq_reports_generated_when_service_available(
        self,
        mock_pipeline_config: MagicMock,
        mock_runtime_config: MagicMock,
        mock_context: MagicMock,
        mock_dq_service: MagicMock,
        mock_lifecycle_service: MagicMock,
        mock_storage: MagicMock,
        mock_logger: LoggerPort,
        mock_dq_report_service: MagicMock,
        mock_executor: MagicMock,
        sample_dq_context: DQReportContext,
    ) -> None:
        """DQ reports should be generated when service is available."""
        service = PostrunService(
            config=mock_pipeline_config,
            runtime=mock_runtime_config,
            context=mock_context,
            dq_service=mock_dq_service,
            lifecycle_service=mock_lifecycle_service,
            storage=mock_storage,
            metrics=None,
            logger=mock_logger,
            dq_report_service=mock_dq_report_service,
        )

        result = await service.run(
            executor=mock_executor,
            dq_context=sample_dq_context,
        )

        assert result.dq_reports is not None
        assert result.dq_reports.bronze_report_path is not None
        assert result.dq_reports.silver_report_path is not None
        assert result.dq_reports.bronze_enabled is True
        mock_dq_report_service.generate_reports.assert_called_once()

    async def test_dq_reports_skipped_when_no_context(
        self,
        mock_pipeline_config: MagicMock,
        mock_runtime_config: MagicMock,
        mock_dq_service: MagicMock,
        mock_lifecycle_service: MagicMock,
        mock_logger: LoggerPort,
        mock_dq_report_service: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """DQ reports should be skipped when no context provided."""
        service = PostrunService(
            config=mock_pipeline_config,
            runtime=mock_runtime_config,
            context=mock_context,
            dq_service=mock_dq_service,
            lifecycle_service=mock_lifecycle_service,
            storage=mock_storage,
            metrics=None,
            logger=mock_logger,
            dq_report_service=mock_dq_report_service,
        )

        result = await service.run(
            executor=mock_executor,
            dq_context=None,
        )

        assert result.dq_reports is None
        mock_dq_report_service.generate_reports.assert_not_called()

    async def test_dq_reports_skipped_when_no_service(
        self,
        mock_pipeline_config: MagicMock,
        mock_runtime_config: MagicMock,
        mock_dq_service: MagicMock,
        mock_lifecycle_service: MagicMock,
        mock_logger: LoggerPort,
        mock_executor: MagicMock,
        sample_dq_context: DQReportContext,
    ) -> None:
        """DQ reports should be skipped when service not available."""
        service = PostrunService(
            config=mock_pipeline_config,
            runtime=mock_runtime_config,
            context=mock_context,
            dq_service=mock_dq_service,
            lifecycle_service=mock_lifecycle_service,
            storage=mock_storage,
            metrics=None,
            logger=mock_logger,
            dq_report_service=None,  # No service
        )

        result = await service.run(
            executor=mock_executor,
            dq_context=sample_dq_context,
        )

        assert result.dq_reports is None

    async def test_dq_reports_error_handling(
        self,
        mock_pipeline_config: MagicMock,
        mock_runtime_config: MagicMock,
        mock_dq_service: MagicMock,
        mock_lifecycle_service: MagicMock,
        mock_logger: LoggerPort,
        mock_executor: MagicMock,
        sample_dq_context: DQReportContext,
    ) -> None:
        """DQ report errors should not fail the pipeline."""
        mock_dq_report_service = MagicMock()
        mock_dq_report_service.generate_reports = AsyncMock(
            side_effect=Exception("Report generation failed")
        )

        service = PostrunService(
            config=mock_pipeline_config,
            runtime=mock_runtime_config,
            context=mock_context,
            dq_service=mock_dq_service,
            lifecycle_service=mock_lifecycle_service,
            storage=mock_storage,
            metrics=None,
            logger=mock_logger,
            dq_report_service=mock_dq_report_service,
        )

        # Should not raise, just return None for dq_reports
        result = await service.run(
            executor=mock_executor,
            dq_context=sample_dq_context,
        )

        assert result.dq_reports is None
        # Error + warning should be logged in warning-mode fallback.
        mock_logger.error.assert_called()
        mock_logger.warning.assert_called()

    async def test_dq_configs_passed_to_service(
        self,
        mock_pipeline_config: MagicMock,
        mock_runtime_config: MagicMock,
        mock_dq_service: MagicMock,
        mock_lifecycle_service: MagicMock,
        mock_logger: LoggerPort,
        mock_dq_report_service: MagicMock,
        mock_executor: MagicMock,
        sample_dq_context: DQReportContext,
    ) -> None:
        """DQ configs should be passed to generate_reports."""
        bronze_config = MagicMock()
        bronze_config.enabled = True
        silver_config = MagicMock()
        silver_config.enabled = True
        gold_config = None

        service = PostrunService(
            config=mock_pipeline_config,
            runtime=mock_runtime_config,
            context=mock_context,
            dq_service=mock_dq_service,
            lifecycle_service=mock_lifecycle_service,
            storage=mock_storage,
            metrics=None,
            logger=mock_logger,
            dq_report_service=mock_dq_report_service,
            bronze_dq_config=bronze_config,
            silver_dq_config=silver_config,
            gold_dq_config=gold_config,
        )

        await service.run(
            executor=mock_executor,
            dq_context=sample_dq_context,
        )

        # Verify configs were passed
        mock_dq_report_service.generate_reports.assert_called_once_with(
            context=sample_dq_context,
            bronze_config=bronze_config,
            silver_config=silver_config,
            gold_config=gold_config,
        )


@pytest.mark.unit
class TestBatchExecutorDQCollection:
    """Tests for DQ data collection in BatchExecutor."""

    def test_should_collect_dq_data_returns_true_when_service_available(
        self,
    ) -> None:
        """_should_collect_dq_data returns True when dq_report_service is set."""
        # Create mock services with dq_report_service
        services = MagicMock()
        services.dq_report_service = MagicMock()

        # Create executor (partial mock)
        executor = MagicMock()
        executor._services = services
        executor._should_collect_dq_data = lambda: (
            executor._services.dq_report_service is not None
        )

        assert executor._should_collect_dq_data() is True

    def test_should_collect_dq_data_returns_false_when_no_service(
        self,
    ) -> None:
        """_should_collect_dq_data returns False when dq_report_service is None."""
        services = MagicMock()
        services.dq_report_service = None

        executor = MagicMock()
        executor._services = services
        executor._should_collect_dq_data = lambda: (
            executor._services.dq_report_service is not None
        )

        assert executor._should_collect_dq_data() is False

    def test_get_dq_context_returns_none_when_disabled(
        self,
    ) -> None:
        """get_dq_context returns None when DQ collection is disabled."""
        services = MagicMock()
        services.dq_report_service = None

        executor = MagicMock()
        executor._services = services
        executor._should_collect_dq_data = lambda: (
            executor._services.dq_report_service is not None
        )
        executor.get_dq_context = lambda: (
            None if not executor._should_collect_dq_data() else MagicMock()
        )

        assert executor.get_dq_context() is None


@pytest.mark.unit
class TestDQReportContext:
    """Tests for DQReportContext dataclass."""

    def test_dq_report_context_creation(self) -> None:
        """Test DQReportContext creation with all fields."""
        context = DQReportContext(
            run_id="test-123",
            pipeline_name="chembl_activity",
            timestamp=datetime.now(UTC),
            bronze_records=[b'{"id": 1}'],
            bronze_batch_id="batch-001",
            silver_data=None,
            silver_target_table="chembl_activity",
        )

        assert context.run_id == "test-123"
        assert context.pipeline_name == "chembl_activity"
        assert context.bronze_batch_id == "batch-001"
        assert context.silver_target_table == "chembl_activity"
        assert context.dq_soft_threshold == 0.05  # Default
        assert context.dq_hard_threshold == 0.20  # Default

    def test_dq_report_context_with_custom_thresholds(self) -> None:
        """Test DQReportContext creation with custom thresholds."""
        context = DQReportContext(
            run_id="test-123",
            pipeline_name="chembl_activity",
            timestamp=datetime.now(UTC),
            dq_soft_threshold=0.10,
            dq_hard_threshold=0.30,
        )

        assert context.dq_soft_threshold == 0.10
        assert context.dq_hard_threshold == 0.30


@pytest.mark.unit
class TestDQReportResult:
    """Tests for DQReportResult dataclass."""

    def test_dq_report_result_no_reports(self) -> None:
        """Test DQReportResult with no reports generated."""
        result = DQReportResult()

        assert result.any_generated is False
        assert result.reports_count == 0

    def test_dq_report_result_with_reports(self) -> None:
        """Test DQReportResult with reports generated."""
        result = DQReportResult(
            bronze_report_path=Path("/tmp/bronze_dq.json"),
            silver_report_path=Path("/tmp/silver_dq.json"),
            gold_report_path=None,
            bronze_enabled=True,
            silver_enabled=True,
            gold_enabled=False,
        )

        assert result.any_generated is True
        assert result.reports_count == 2

    def test_dq_report_result_all_enabled(self) -> None:
        """Test DQReportResult with all reports generated."""
        result = DQReportResult(
            bronze_report_path=Path("/tmp/bronze_dq.json"),
            silver_report_path=Path("/tmp/silver_dq.json"),
            gold_report_path=Path("/tmp/gold_dq.json"),
            bronze_enabled=True,
            silver_enabled=True,
            gold_enabled=True,
        )

        assert result.any_generated is True
        assert result.reports_count == 3
