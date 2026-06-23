"""Unit tests for DQ report service.

Tests the DQReportService orchestration of DQ report generation.
"""

from __future__ import annotations

from datetime import datetime, UTC
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.services.dq_report_service import (
    DQReportContext,
    DQReportResult,
    DQReportService,
)
from bioetl.domain.value_objects.dq_report import (
    DQReportStatus,
    MedallionLayer,
)


pytestmark = pytest.mark.unit


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create mock logger."""
    return MagicMock()


@pytest.fixture
def mock_bronze_analyzer() -> MagicMock:
    """Create mock Bronze DQ analyzer."""
    analyzer = MagicMock()
    analyzer.analyze.return_value = MagicMock(
        layer=MedallionLayer.BRONZE,
        summary=MagicMock(overall_status=DQReportStatus.PASS),
        batch_id="batch-001",
    )
    return analyzer


@pytest.fixture
def mock_silver_analyzer() -> MagicMock:
    """Create mock Silver DQ analyzer."""
    analyzer = MagicMock()
    analyzer.analyze.return_value = MagicMock(
        layer=MedallionLayer.SILVER,
        summary=MagicMock(overall_status=DQReportStatus.WARNING),
        run_id="run-001",
    )
    return analyzer


@pytest.fixture
def mock_gold_analyzer() -> MagicMock:
    """Create mock Gold DQ analyzer."""
    analyzer = MagicMock()
    analyzer.analyze.return_value = MagicMock(
        layer=MedallionLayer.GOLD,
        summary=MagicMock(overall_status=DQReportStatus.PASS),
        run_id="run-001",
    )
    return analyzer


@pytest.fixture
def mock_report_writer(tmp_path: Path) -> AsyncMock:
    """Create mock DQ report writer."""
    writer = AsyncMock()
    writer.write_bronze_report.return_value = tmp_path / "bronze_dq_report.json"
    writer.write_silver_report.return_value = tmp_path / "silver_dq_report.json"
    writer.write_gold_report.return_value = tmp_path / "gold_dq_report.json"
    return writer


@pytest.fixture
def bronze_dq_config() -> MagicMock:
    """Create mock Bronze DQ config."""
    config = MagicMock()
    config.enabled = True
    config.output_path = None
    config.get_format_enum.return_value = MagicMock(value="json")
    return config


@pytest.fixture
def silver_dq_config() -> MagicMock:
    """Create mock Silver DQ config."""
    config = MagicMock()
    config.enabled = True
    config.output_path = None
    config.get_format_enum.return_value = MagicMock(value="json")
    return config


@pytest.fixture
def gold_dq_config() -> MagicMock:
    """Create mock Gold DQ config."""
    config = MagicMock()
    config.enabled = True
    config.output_path = None
    config.get_format_enum.return_value = MagicMock(value="json")
    return config


@pytest.fixture
def dq_context() -> DQReportContext:
    """Create DQ report context."""
    return DQReportContext(
        run_id="run-001",
        pipeline_name="test_pipeline",
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        bronze_source_file="bronze/test/batch_001.jsonl.zst",
        bronze_batch_id="batch-001",
        bronze_records=[b'{"id": 1}', b'{"id": 2}'],
        silver_data=MagicMock(),  # Mock DataFrame
        silver_target_table="silver/test_pipeline",
        silver_source_batch_ids=["batch-001"],
        silver_primary_keys=["id"],
        silver_input_count=100,
        silver_quarantined_count=5,
        gold_data=MagicMock(),  # Mock DataFrame
        gold_target_table="gold/test_pipeline",
        gold_required_fields=["id", "name"],
    )


class TestDQReportResult:
    """Tests for DQReportResult."""

    def test_any_generated_returns_true_when_bronze_generated(
        self, tmp_path: Path
    ) -> None:
        """any_generated should return True when bronze report is generated."""
        result = DQReportResult(
            bronze_report_path=tmp_path / "bronze.json",
            bronze_enabled=True,
        )

        assert result.any_generated is True

    def test_any_generated_returns_true_when_silver_generated(
        self, tmp_path: Path
    ) -> None:
        """any_generated should return True when silver report is generated."""
        result = DQReportResult(
            silver_report_path=tmp_path / "silver.json",
            silver_enabled=True,
        )

        assert result.any_generated is True

    def test_any_generated_returns_true_when_gold_generated(
        self, tmp_path: Path
    ) -> None:
        """any_generated should return True when gold report is generated."""
        result = DQReportResult(
            gold_report_path=tmp_path / "gold.json",
            gold_enabled=True,
        )

        assert result.any_generated is True

    def test_any_generated_returns_false_when_none_generated(self) -> None:
        """any_generated should return False when no reports generated."""
        result = DQReportResult()

        assert result.any_generated is False

    def test_reports_count_returns_correct_count(self, tmp_path: Path) -> None:
        """reports_count should return correct count of generated reports."""
        result = DQReportResult(
            bronze_report_path=tmp_path / "bronze.json",
            silver_report_path=tmp_path / "silver.json",
            bronze_enabled=True,
            silver_enabled=True,
        )

        assert result.reports_count == 2

    def test_reports_count_returns_zero_when_none_generated(self) -> None:
        """reports_count should return 0 when no reports generated."""
        result = DQReportResult()

        assert result.reports_count == 0


class TestDQReportContext:
    """Tests for DQReportContext."""

    def test_context_is_frozen(self) -> None:
        """DQReportContext should be frozen (immutable)."""
        context = DQReportContext(
            run_id="run-001",
            pipeline_name="test",
            timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        )

        with pytest.raises(AttributeError):
            context.run_id = "modified"  # type: ignore[misc]

    def test_context_default_values(self) -> None:
        """DQReportContext should have sensible defaults."""
        context = DQReportContext(
            run_id="run-001",
            pipeline_name="test",
            timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        )

        assert context.bronze_source_file is None
        assert context.bronze_batch_id is None
        assert context.bronze_records is None
        assert context.silver_data is None
        assert context.silver_target_table is None
        assert context.silver_quarantined_count == 0
        assert context.gold_data is None
        assert context.gold_target_table is None
        assert context.dq_soft_threshold == pytest.approx(0.05)
        assert context.dq_hard_threshold == pytest.approx(0.20)


class TestDQReportService:
    """Tests for DQReportService."""

    def test_init_with_all_services(
        self,
        mock_logger: MagicMock,
        mock_bronze_analyzer: MagicMock,
        mock_silver_analyzer: MagicMock,
        mock_gold_analyzer: MagicMock,
        mock_report_writer: AsyncMock,
    ) -> None:
        """DQReportService should initialize with all services."""
        service = DQReportService(
            logger=mock_logger,
            bronze_analyzer=mock_bronze_analyzer,
            silver_analyzer=mock_silver_analyzer,
            gold_analyzer=mock_gold_analyzer,
            report_writer=mock_report_writer,
        )

        assert service._bronze_analyzer is mock_bronze_analyzer
        assert service._silver_analyzer is mock_silver_analyzer
        assert service._gold_analyzer is mock_gold_analyzer
        assert service._report_writer is mock_report_writer

    def test_init_with_no_services(self, mock_logger: MagicMock) -> None:
        """DQReportService should initialize with no optional services."""
        service = DQReportService(logger=mock_logger)

        assert service._bronze_analyzer is None
        assert service._silver_analyzer is None
        assert service._gold_analyzer is None
        assert service._report_writer is None

    def test_is_any_report_enabled_returns_true_when_bronze_enabled(
        self,
        mock_logger: MagicMock,
        bronze_dq_config: MagicMock,
    ) -> None:
        """is_any_report_enabled should return True when Bronze is enabled."""
        service = DQReportService(logger=mock_logger)

        assert service.is_any_report_enabled(bronze_config=bronze_dq_config) is True

    def test_is_any_report_enabled_returns_true_when_silver_enabled(
        self,
        mock_logger: MagicMock,
        silver_dq_config: MagicMock,
    ) -> None:
        """is_any_report_enabled should return True when Silver is enabled."""
        service = DQReportService(logger=mock_logger)

        assert service.is_any_report_enabled(silver_config=silver_dq_config) is True

    def test_is_any_report_enabled_returns_true_when_gold_enabled(
        self,
        mock_logger: MagicMock,
        gold_dq_config: MagicMock,
    ) -> None:
        """is_any_report_enabled should return True when Gold is enabled."""
        service = DQReportService(logger=mock_logger)

        assert service.is_any_report_enabled(gold_config=gold_dq_config) is True

    def test_is_any_report_enabled_returns_false_when_none_enabled(
        self,
        mock_logger: MagicMock,
    ) -> None:
        """is_any_report_enabled should return False when no configs provided."""
        service = DQReportService(logger=mock_logger)

        assert service.is_any_report_enabled() is False

    def test_is_any_report_enabled_returns_false_when_all_disabled(
        self,
        mock_logger: MagicMock,
        bronze_dq_config: MagicMock,
        silver_dq_config: MagicMock,
        gold_dq_config: MagicMock,
    ) -> None:
        """is_any_report_enabled should return False when all disabled."""
        bronze_dq_config.enabled = False
        silver_dq_config.enabled = False
        gold_dq_config.enabled = False

        service = DQReportService(logger=mock_logger)

        result = service.is_any_report_enabled(
            bronze_config=bronze_dq_config,
            silver_config=silver_dq_config,
            gold_config=gold_dq_config,
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_generate_reports_returns_empty_when_none_enabled(
        self,
        mock_logger: MagicMock,
        dq_context: DQReportContext,
    ) -> None:
        """generate_reports should return empty result when none enabled."""
        service = DQReportService(logger=mock_logger)

        result = await service.generate_reports(context=dq_context)

        assert result.bronze_report_path is None
        assert result.silver_report_path is None
        assert result.gold_report_path is None
        assert result.any_generated is False

    @pytest.mark.asyncio
    async def test_generate_reports_bronze_when_enabled(
        self,
        mock_logger: MagicMock,
        mock_bronze_analyzer: MagicMock,
        mock_report_writer: AsyncMock,
        dq_context: DQReportContext,
        bronze_dq_config: MagicMock,
    ) -> None:
        """generate_reports should generate Bronze report when enabled."""
        service = DQReportService(
            logger=mock_logger,
            bronze_analyzer=mock_bronze_analyzer,
            report_writer=mock_report_writer,
        )

        result = await service.generate_reports(
            context=dq_context,
            bronze_config=bronze_dq_config,
        )

        assert result.bronze_report_path is not None
        assert result.bronze_enabled is True
        mock_bronze_analyzer.analyze.assert_called_once()
        mock_report_writer.write_bronze_report.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_reports_emits_dq_check_failure_metrics(
        self,
        mock_logger: MagicMock,
        mock_bronze_analyzer: MagicMock,
        mock_report_writer: AsyncMock,
        dq_context: DQReportContext,
        bronze_dq_config: MagicMock,
    ) -> None:
        """generate_reports should emit per-check DQ failure metrics."""
        mock_bronze_analyzer.analyze.return_value.checks = {
            "record_count": {"status": "warn"},
            "encoding_validation": {"status": "fail"},
            "schema_snapshot": {"status": "pass"},
            "raw_field_presence": {},
        }
        mock_metrics = MagicMock()
        service = DQReportService(
            logger=mock_logger,
            bronze_analyzer=mock_bronze_analyzer,
            report_writer=mock_report_writer,
            metrics=mock_metrics,
        )

        await service.generate_reports(
            context=dq_context,
            bronze_config=bronze_dq_config,
        )

        failure_calls = [
            call.args
            for call in mock_metrics.increment_counter.call_args_list
            if call.args[0] == "bioetl_dq_check_failures_total"
        ]
        assert failure_calls == [
            (
                "bioetl_dq_check_failures_total",
                1,
                {
                    "pipeline": "test_pipeline",
                    "stage": "bronze",
                    "check_type": "record_count",
                    "severity": "warning",
                },
            ),
            (
                "bioetl_dq_check_failures_total",
                1,
                {
                    "pipeline": "test_pipeline",
                    "stage": "bronze",
                    "check_type": "encoding_validation",
                    "severity": "hard_fail",
                },
            ),
        ]

    @pytest.mark.asyncio
    async def test_generate_reports_silver_when_enabled(
        self,
        mock_logger: MagicMock,
        mock_silver_analyzer: MagicMock,
        mock_report_writer: AsyncMock,
        dq_context: DQReportContext,
        silver_dq_config: MagicMock,
    ) -> None:
        """generate_reports should generate Silver report when enabled."""
        service = DQReportService(
            logger=mock_logger,
            silver_analyzer=mock_silver_analyzer,
            report_writer=mock_report_writer,
        )

        result = await service.generate_reports(
            context=dq_context,
            silver_config=silver_dq_config,
        )

        assert result.silver_report_path is not None
        assert result.silver_enabled is True
        mock_silver_analyzer.analyze.assert_called_once()
        mock_report_writer.write_silver_report.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_reports_gold_when_enabled(
        self,
        mock_logger: MagicMock,
        mock_gold_analyzer: MagicMock,
        mock_report_writer: AsyncMock,
        dq_context: DQReportContext,
        gold_dq_config: MagicMock,
    ) -> None:
        """generate_reports should generate Gold report when enabled."""
        service = DQReportService(
            logger=mock_logger,
            gold_analyzer=mock_gold_analyzer,
            report_writer=mock_report_writer,
        )

        result = await service.generate_reports(
            context=dq_context,
            gold_config=gold_dq_config,
        )

        assert result.gold_report_path is not None
        assert result.gold_enabled is True
        mock_gold_analyzer.analyze.assert_called_once()
        mock_report_writer.write_gold_report.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_reports_all_layers_when_enabled(
        self,
        mock_logger: MagicMock,
        mock_bronze_analyzer: MagicMock,
        mock_silver_analyzer: MagicMock,
        mock_gold_analyzer: MagicMock,
        mock_report_writer: AsyncMock,
        dq_context: DQReportContext,
        bronze_dq_config: MagicMock,
        silver_dq_config: MagicMock,
        gold_dq_config: MagicMock,
    ) -> None:
        """generate_reports should generate all reports when all enabled."""
        service = DQReportService(
            logger=mock_logger,
            bronze_analyzer=mock_bronze_analyzer,
            silver_analyzer=mock_silver_analyzer,
            gold_analyzer=mock_gold_analyzer,
            report_writer=mock_report_writer,
        )

        result = await service.generate_reports(
            context=dq_context,
            bronze_config=bronze_dq_config,
            silver_config=silver_dq_config,
            gold_config=gold_dq_config,
        )

        assert result.bronze_report_path is not None
        assert result.silver_report_path is not None
        assert result.gold_report_path is not None
        assert result.reports_count == 3

    @pytest.mark.asyncio
    async def test_generate_reports_skips_when_no_data(
        self,
        mock_logger: MagicMock,
        mock_bronze_analyzer: MagicMock,
        mock_report_writer: AsyncMock,
        bronze_dq_config: MagicMock,
    ) -> None:
        """generate_reports should skip Bronze when no bronze data."""
        context = DQReportContext(
            run_id="run-001",
            pipeline_name="test",
            timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            # No bronze data
        )

        service = DQReportService(
            logger=mock_logger,
            bronze_analyzer=mock_bronze_analyzer,
            report_writer=mock_report_writer,
        )

        result = await service.generate_reports(
            context=context,
            bronze_config=bronze_dq_config,
        )

        assert result.bronze_report_path is None
        mock_bronze_analyzer.analyze.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_reports_handles_analyzer_error(
        self,
        mock_logger: MagicMock,
        mock_bronze_analyzer: MagicMock,
        mock_report_writer: AsyncMock,
        dq_context: DQReportContext,
        bronze_dq_config: MagicMock,
    ) -> None:
        """generate_reports should handle analyzer errors gracefully."""
        mock_bronze_analyzer.analyze.side_effect = ValueError("Test error")

        service = DQReportService(
            logger=mock_logger,
            bronze_analyzer=mock_bronze_analyzer,
            report_writer=mock_report_writer,
        )

        result = await service.generate_reports(
            context=dq_context,
            bronze_config=bronze_dq_config,
        )

        assert result.bronze_report_path is None
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_generate_reports_skips_when_analyzer_missing(
        self,
        mock_logger: MagicMock,
        mock_report_writer: AsyncMock,
        dq_context: DQReportContext,
        bronze_dq_config: MagicMock,
    ) -> None:
        """generate_reports should skip when analyzer is missing."""
        service = DQReportService(
            logger=mock_logger,
            # No bronze_analyzer
            report_writer=mock_report_writer,
        )

        result = await service.generate_reports(
            context=dq_context,
            bronze_config=bronze_dq_config,
        )

        assert result.bronze_report_path is None
        mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_generate_reports_skips_when_writer_missing(
        self,
        mock_logger: MagicMock,
        mock_bronze_analyzer: MagicMock,
        dq_context: DQReportContext,
        bronze_dq_config: MagicMock,
    ) -> None:
        """generate_reports should skip when writer is missing."""
        service = DQReportService(
            logger=mock_logger,
            bronze_analyzer=mock_bronze_analyzer,
            # No report_writer
        )

        result = await service.generate_reports(
            context=dq_context,
            bronze_config=bronze_dq_config,
        )

        assert result.bronze_report_path is None
        mock_logger.warning.assert_called()
