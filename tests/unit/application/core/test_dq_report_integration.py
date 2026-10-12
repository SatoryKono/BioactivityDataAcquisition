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
"""Unit tests for DQ report integration in pipeline flow.

Tests the integration of DQ report generation into the pipeline execution flow:
- BatchExecutor DQ data collection
- PostrunService DQ report generation
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.batch_execution import (
    BatchExecutionLifecycleService,
    BatchExecutionRunService,
    BatchExecutionStateService,
)
from bioetl.application.core.batch_executor import BatchExecutor
from bioetl.application.core.batch_extraction_loop_service import (
    BatchExtractionLoopService,
)
from bioetl.application.core.batch_processing_contracts import BatchProcessingOutcome
from bioetl.application.services.quality.dq_report_service import (
    DQReportContext,
    DQReportResult,
)
from tests.unit.application.core.postrun_test_support import (
    build_test_postrun_service as _make_postrun_service,
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
    service.evaluate = MagicMock(
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
    from bioetl.application.services.medallion.medallion_lifecycle import VacuumResult

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
def mock_dq_report_service(tmp_path: Path) -> MagicMock:
    """Create mock DQReportService."""
    service = MagicMock()
    service.generate_reports = AsyncMock(
        return_value=DQReportResult(
            bronze_report_path=tmp_path / "bronze_dq.json",
            silver_report_path=tmp_path / "silver_dq.json",
            gold_report_path=None,
            bronze_enabled=True,
            silver_enabled=True,
            gold_enabled=False,
        )
    )
    return service


@pytest.fixture
def sample_dq_context(tmp_path: Path) -> DQReportContext:
    """Create sample DQ context."""
    return DQReportContext(
        run_id="test-run-123",
        pipeline_name="chembl_activity",
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        bronze_records=[b'{"id": 1}', b'{"id": 2}'],
        bronze_batch_id="batch-001",
        bronze_source_file=str(tmp_path / "bronze" / "file.jsonl.zst"),
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
def mock_storage(tmp_path: Path) -> MagicMock:
    """Create a mock storage port."""
    storage = MagicMock()
    storage.get_table_path = MagicMock(return_value=tmp_path / "table")
    return storage


@pytest.fixture
def mock_context() -> MagicMock:
    """Create a mock pipeline context."""
    from datetime import UTC, datetime

    context = MagicMock()
    context.started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
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
        mock_logger: MagicMock,
        mock_dq_report_service: MagicMock,
        mock_executor: MagicMock,
        sample_dq_context: DQReportContext,
    ) -> None:
        """DQ reports should be generated when service is available."""
        service = _make_postrun_service(
            config=mock_pipeline_config,
            runtime=mock_runtime_config,
            context=mock_context,
            dq_service=mock_dq_service,
            lifecycle_service=mock_lifecycle_service,
            storage=mock_storage,
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
        mock_context: MagicMock,
        mock_dq_service: MagicMock,
        mock_lifecycle_service: MagicMock,
        mock_storage: MagicMock,
        mock_logger: MagicMock,
        mock_dq_report_service: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """DQ reports should be skipped when no context provided."""
        service = _make_postrun_service(
            config=mock_pipeline_config,
            runtime=mock_runtime_config,
            context=mock_context,
            dq_service=mock_dq_service,
            lifecycle_service=mock_lifecycle_service,
            storage=mock_storage,
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
        mock_context: MagicMock,
        mock_dq_service: MagicMock,
        mock_lifecycle_service: MagicMock,
        mock_storage: MagicMock,
        mock_logger: MagicMock,
        mock_executor: MagicMock,
        sample_dq_context: DQReportContext,
    ) -> None:
        """DQ reports should be skipped when service not available."""
        service = _make_postrun_service(
            config=mock_pipeline_config,
            runtime=mock_runtime_config,
            context=mock_context,
            dq_service=mock_dq_service,
            lifecycle_service=mock_lifecycle_service,
            storage=mock_storage,
            logger=mock_logger,
            dq_report_service=None,
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
        mock_context: MagicMock,
        mock_dq_service: MagicMock,
        mock_lifecycle_service: MagicMock,
        mock_storage: MagicMock,
        mock_logger: MagicMock,
        mock_executor: MagicMock,
        sample_dq_context: DQReportContext,
    ) -> None:
        """DQ report errors should not fail the pipeline."""
        mock_dq_report_service = MagicMock()
        mock_dq_report_service.generate_reports = AsyncMock(
            side_effect=RuntimeError("Report generation failed")
        )

        service = _make_postrun_service(
            config=mock_pipeline_config,
            runtime=mock_runtime_config,
            context=mock_context,
            dq_service=mock_dq_service,
            lifecycle_service=mock_lifecycle_service,
            storage=mock_storage,
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
        mock_context: MagicMock,
        mock_dq_service: MagicMock,
        mock_lifecycle_service: MagicMock,
        mock_storage: MagicMock,
        mock_logger: MagicMock,
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

        service = _make_postrun_service(
            config=mock_pipeline_config,
            runtime=mock_runtime_config,
            context=mock_context,
            dq_service=mock_dq_service,
            lifecycle_service=mock_lifecycle_service,
            storage=mock_storage,
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

    @staticmethod
    def _make_executor(*, dq_report_service: object | None) -> BatchExecutor:
        """Build a minimal concrete BatchExecutor with DQ-related dependencies."""
        from bioetl.application.core.batch_executor import BatchExecutorDependencies
        from bioetl.application.core.lifecycle.batch_fsm import BatchExecutionFSM

        services = SimpleNamespace(
            dq_report_service=dq_report_service,
            dq_monitor=MagicMock(),
            metrics=MagicMock(),
            logger=MagicMock(),
        )
        config = SimpleNamespace(
            dq_config=None,
            table_config=SimpleNamespace(
                primary_keys=["activity_id"],
                silver_table="chembl_activity",
                gold_table="chembl_activity_gold",
            ),
            entity_type="activity",
            pipeline_name="chembl_activity",
            provider="chembl",
            bronze_output_path="bronze/path",
            silver_output_path="silver/path",
            gold_output_path="gold/path",
            flat_structure=False,
            scd_config=None,
        )
        context = SimpleNamespace(
            run_id="run-123",
            started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            replay_timestamp_anchor=None,
        )
        batch_processing_service = MagicMock()
        execution_lifecycle_service = BatchExecutionLifecycleService(
            progress_service=MagicMock(),
            tracing_manager=MagicMock(),
            checkpoint_recovery_service=MagicMock(),
        )

        deps = BatchExecutorDependencies(
            memory_manager=MagicMock(),
            execution_run_service=BatchExecutionRunService(
                execution_lifecycle_service=execution_lifecycle_service
            ),
            extraction_loop_service=BatchExtractionLoopService(
                batch_processing_service=batch_processing_service,
                shutdown_signal=MagicMock(),
                memory_manager=MagicMock(),
                progress_service=MagicMock(),
                checkpoint_recovery_service=MagicMock(),
                checkpoint_interval=BatchExecutor.DEFAULT_CHECKPOINT_INTERVAL,
            ),
            execution_state_service=BatchExecutionStateService(),
            processing_port=batch_processing_service,
            fsm=BatchExecutionFSM(),
        )

        return BatchExecutor(
            services=services,  # type: ignore[arg-type]
            context=context,  # type: ignore[arg-type]
            config=config,  # type: ignore[arg-type]
            dependencies=deps,
            logger=MagicMock(),
        )

    def test_should_collect_dq_data_returns_true_when_service_available(
        self,
    ) -> None:
        """_should_collect_dq_data returns True when dq_report_service is set."""
        executor = self._make_executor(dq_report_service=MagicMock())

        assert executor._should_collect_dq_data() is True

    def test_should_collect_dq_data_returns_false_when_no_service(
        self,
    ) -> None:
        """_should_collect_dq_data returns False when dq_report_service is None."""
        executor = self._make_executor(dq_report_service=None)

        assert executor._should_collect_dq_data() is False

    def test_get_dq_context_returns_none_when_disabled(
        self,
    ) -> None:
        """get_dq_context returns None when DQ collection is disabled."""
        executor = self._make_executor(dq_report_service=None)

        assert executor.get_dq_context() is None

    def test_get_dq_context_returns_context_when_enabled(self) -> None:
        """get_dq_context should build a real DQReportContext when enabled."""
        executor = self._make_executor(dq_report_service=MagicMock())
        executor._bronze_records_for_dq = [b'{"id": 1}']
        executor.source_batch_ids = ["batch-001"]
        executor._last_bronze_path = "bronze/file.jsonl.zst"
        executor.records_fetched = 100
        executor.records_quarantined = 2
        executor._build_dataframe_from_records = MagicMock(return_value=None)

        context = executor.get_dq_context()

        assert context is not None
        assert context.run_id == "run-123"
        assert context.pipeline_name == "chembl_activity"
        assert context.provider == "chembl"
        # extract_dq_entity keeps the table entity segment (underscores intact).
        assert context.entity == "chembl_activity"
        assert context.bronze_batch_id == "batch-001"
        assert context.bronze_source_file == "bronze/file.jsonl.zst"
        assert context.silver_target_table == "chembl_activity"
        assert context.silver_input_count == 100
        assert context.silver_quarantined_count == 2

    @pytest.mark.asyncio
    async def test_process_collects_dq_data_via_batch_executor_hook(self) -> None:
        """process() should trigger DQ collection through the production hook path."""
        executor = self._make_executor(dq_report_service=MagicMock())
        bronze_result = SimpleNamespace(path="bronze/file.jsonl.zst")
        records = [{"activity_id": "A1"}]
        executor._processing_port.process_batch = AsyncMock(
            return_value=BatchProcessingOutcome(
                batch_id="batch-001",  # type: ignore[arg-type]
                bronze_result=bronze_result,  # type: ignore[arg-type]
                silver_records=[{"activity_id": "A1"}],
                gold_records=[],
                quarantined_count=2,
                filtered_out_count=0,
            )
        )

        result = await executor.process(records=records, start_index=0)

        assert result.bronze_count == 1
        assert result.silver_count == 1
        assert result.gold_count == 0
        assert result.quarantined_count == 2
        assert executor.source_batch_ids == ["batch-001"]
        assert executor._last_bronze_path == "bronze/file.jsonl.zst"
        assert len(executor._bronze_records_for_dq) == 1
        assert executor._silver_records_for_dq == [{"activity_id": "A1"}]
        assert executor.records_quarantined == 2


@pytest.mark.unit
class TestDQReportContext:
    """Tests for DQReportContext dataclass."""

    def test_dq_report_context_creation(self) -> None:
        """Test DQReportContext creation with all fields."""
        context = DQReportContext(
            run_id="test-123",
            pipeline_name="chembl_activity",
            timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            bronze_records=[b'{"id": 1}'],
            bronze_batch_id="batch-001",
            silver_data=None,
            silver_target_table="chembl_activity",
        )

        assert context.run_id == "test-123"
        assert context.pipeline_name == "chembl_activity"
        assert context.bronze_batch_id == "batch-001"
        assert context.silver_target_table == "chembl_activity"
        assert context.dq_soft_threshold == pytest.approx(0.05)  # Default
        assert context.dq_hard_threshold == pytest.approx(0.20)  # Default

    def test_dq_report_context_with_custom_thresholds(self) -> None:
        """Test DQReportContext creation with custom thresholds."""
        context = DQReportContext(
            run_id="test-123",
            pipeline_name="chembl_activity",
            timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            dq_soft_threshold=0.10,
            dq_hard_threshold=0.30,
        )

        assert context.dq_soft_threshold == pytest.approx(0.10)
        assert context.dq_hard_threshold == pytest.approx(0.30)


@pytest.mark.unit
class TestDQReportResult:
    """Tests for DQReportResult dataclass."""

    def test_dq_report_result_no_reports(self) -> None:
        """Test DQReportResult with no reports generated."""
        result = DQReportResult()

        assert result.any_generated is False
        assert result.reports_count == 0

    def test_dq_report_result_with_reports(self, tmp_path: Path) -> None:
        """Test DQReportResult with reports generated."""
        result = DQReportResult(
            bronze_report_path=tmp_path / "bronze_dq.json",
            silver_report_path=tmp_path / "silver_dq.json",
            gold_report_path=None,
            bronze_enabled=True,
            silver_enabled=True,
            gold_enabled=False,
        )

        assert result.any_generated is True
        assert result.reports_count == 2

    def test_dq_report_result_all_enabled(self, tmp_path: Path) -> None:
        """Test DQReportResult with all reports generated."""
        result = DQReportResult(
            bronze_report_path=tmp_path / "bronze_dq.json",
            silver_report_path=tmp_path / "silver_dq.json",
            gold_report_path=tmp_path / "gold_dq.json",
            bronze_enabled=True,
            silver_enabled=True,
            gold_enabled=True,
        )

        assert result.any_generated is True
        assert result.reports_count == 3
