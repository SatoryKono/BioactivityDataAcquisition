"""Integration tests for DQ report generation in pipeline.

Tests the end-to-end flow of DQ report generation including:
- DQ service creation via factory
- Report analysis and serialization
- File writing to filesystem
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioetl.application.services.dq_report_service import (
    DQReportContext,
    DQReportService,
)
from bioetl.composition.factories.dq.factory import DQServicesFactory
from bioetl.domain.value_objects.dq_report import DQReportFormat
from bioetl.infrastructure.schemas.dq_report_config import (
    BronzeDQReportConfig,
    GoldDQReportConfig,
    SilverDQReportConfig,
)

pytestmark = pytest.mark.usefixtures("strict_dq_env")


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create mock logger."""
    return MagicMock()


@pytest.fixture
def bronze_records() -> list[bytes]:
    """Sample Bronze records for testing."""
    return [
        b'{"id": 1, "name": "record1", "value": 100}',
        b'{"id": 2, "name": "record2", "value": 200}',
        b'{"id": 3, "name": "record3", "value": 300}',
    ]


@pytest.fixture
def dq_context(bronze_records: list[bytes]) -> DQReportContext:
    """Create DQ report context with test data."""
    return DQReportContext(
        run_id="test-run-001",
        pipeline_name="test_pipeline",
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        bronze_source_file="bronze/v1/test/entity/2025-01-15/batch_001.jsonl.zst",
        bronze_batch_id="batch-001",
        bronze_records=bronze_records,
        dq_soft_threshold=0.05,
        dq_hard_threshold=0.20,
    )


@pytest.mark.integration
class TestDQReportIntegration:
    """Integration tests for DQ report generation."""

    def test_dq_services_factory_creates_working_analyzers(self) -> None:
        """DQ services factory should create working analyzer instances."""
        bronze_analyzer = DQServicesFactory.create_bronze_analyzer()
        silver_analyzer = DQServicesFactory.create_silver_analyzer()
        gold_analyzer = DQServicesFactory.create_gold_analyzer()

        # All analyzers should have the analyze method
        assert hasattr(bronze_analyzer, "analyze")
        assert hasattr(silver_analyzer, "analyze")
        assert hasattr(gold_analyzer, "analyze")

    def test_dq_services_factory_creates_working_writer(
        self,
        tmp_path: Path,
        mock_logger: MagicMock,
    ) -> None:
        """DQ services factory should create working writer instance."""
        writer = DQServicesFactory.create_report_writer(
            base_path=tmp_path,
            logger=mock_logger,
        )

        # Writer should have all write methods
        assert hasattr(writer, "write_bronze_report")
        assert hasattr(writer, "write_silver_report")
        assert hasattr(writer, "write_gold_report")

    @pytest.mark.asyncio
    async def test_bronze_dq_report_generation_end_to_end(
        self,
        tmp_path: Path,
        mock_logger: MagicMock,
        bronze_records: list[bytes],
        dq_context: DQReportContext,
    ) -> None:
        """Bronze DQ report should be generated and written to file."""
        # Arrange
        bronze_analyzer = DQServicesFactory.create_bronze_analyzer()
        report_writer = DQServicesFactory.create_report_writer(
            base_path=tmp_path,
            logger=mock_logger,
        )

        service = DQReportService(
            logger=mock_logger,
            bronze_analyzer=bronze_analyzer,
            report_writer=report_writer,
        )

        config = BronzeDQReportConfig(
            enabled=True,
            format="json",
            checks=["record_count", "schema_snapshot"],
        )

        # Act
        result = await service.generate_reports(
            context=dq_context,
            bronze_config=config,
        )

        # Assert
        assert result.bronze_report_path is not None
        assert result.bronze_report_path.exists()
        assert result.bronze_enabled is True

        # Verify report content
        report_content = json.loads(result.bronze_report_path.read_text())
        assert report_content["layer"] == "bronze"
        assert report_content["run_id"] == "test-run-001"
        assert report_content["pipeline"] == "test_pipeline"
        assert report_content["batch_id"] == "batch-001"
        assert "checks" in report_content
        assert "summary" in report_content

    @pytest.mark.asyncio
    async def test_bronze_dq_report_respects_disabled_config(
        self,
        tmp_path: Path,
        mock_logger: MagicMock,
        dq_context: DQReportContext,
    ) -> None:
        """Bronze DQ report should NOT be generated when disabled."""
        # Arrange
        bronze_analyzer = DQServicesFactory.create_bronze_analyzer()
        report_writer = DQServicesFactory.create_report_writer(
            base_path=tmp_path,
            logger=mock_logger,
        )

        service = DQReportService(
            logger=mock_logger,
            bronze_analyzer=bronze_analyzer,
            report_writer=report_writer,
        )

        config = BronzeDQReportConfig(enabled=False)

        # Act
        result = await service.generate_reports(
            context=dq_context,
            bronze_config=config,
        )

        # Assert
        assert result.bronze_report_path is None
        assert result.bronze_enabled is False

    @pytest.mark.asyncio
    async def test_report_generation_without_config(
        self,
        tmp_path: Path,
        mock_logger: MagicMock,
        dq_context: DQReportContext,
    ) -> None:
        """No reports should be generated without configs."""
        # Arrange
        service = DQReportService(
            logger=mock_logger,
            bronze_analyzer=DQServicesFactory.create_bronze_analyzer(),
            silver_analyzer=DQServicesFactory.create_silver_analyzer(),
            gold_analyzer=DQServicesFactory.create_gold_analyzer(),
            report_writer=DQServicesFactory.create_report_writer(tmp_path, mock_logger),
        )

        # Act
        result = await service.generate_reports(context=dq_context)

        # Assert
        assert result.any_generated is False
        assert result.reports_count == 0

    @pytest.mark.asyncio
    async def test_bronze_report_yaml_format(
        self,
        tmp_path: Path,
        mock_logger: MagicMock,
        dq_context: DQReportContext,
    ) -> None:
        """Bronze DQ report should be generated in YAML format."""
        # Arrange
        service = DQReportService(
            logger=mock_logger,
            bronze_analyzer=DQServicesFactory.create_bronze_analyzer(),
            report_writer=DQServicesFactory.create_report_writer(tmp_path, mock_logger),
        )

        config = BronzeDQReportConfig(
            enabled=True,
            format="yaml",
            checks=["record_count"],
        )

        # Act
        result = await service.generate_reports(
            context=dq_context,
            bronze_config=config,
        )

        # Assert
        assert result.bronze_report_path is not None
        assert result.bronze_report_path.suffix == ".yaml"
        assert result.bronze_report_path.exists()

        # Verify it's valid YAML (contains expected markers)
        content = result.bronze_report_path.read_text()
        assert "layer: bronze" in content or 'layer: "bronze"' in content

    @pytest.mark.asyncio
    async def test_bronze_report_html_format(
        self,
        tmp_path: Path,
        mock_logger: MagicMock,
        dq_context: DQReportContext,
    ) -> None:
        """Bronze DQ report should be generated in HTML format."""
        # Arrange
        service = DQReportService(
            logger=mock_logger,
            bronze_analyzer=DQServicesFactory.create_bronze_analyzer(),
            report_writer=DQServicesFactory.create_report_writer(tmp_path, mock_logger),
        )

        config = BronzeDQReportConfig(
            enabled=True,
            format="html",
            checks=["record_count"],
        )

        # Act
        result = await service.generate_reports(
            context=dq_context,
            bronze_config=config,
        )

        # Assert
        assert result.bronze_report_path is not None
        assert result.bronze_report_path.suffix == ".html"
        assert result.bronze_report_path.exists()

        # Verify it's valid HTML
        content = result.bronze_report_path.read_text()
        assert "<html" in content  # Handles both <html> and <html lang="en">
        assert "bronze" in content.lower()

    @pytest.mark.asyncio
    async def test_report_path_structure(
        self,
        tmp_path: Path,
        mock_logger: MagicMock,
        dq_context: DQReportContext,
    ) -> None:
        """Report should be written to correct path structure."""
        # Arrange
        service = DQReportService(
            logger=mock_logger,
            bronze_analyzer=DQServicesFactory.create_bronze_analyzer(),
            report_writer=DQServicesFactory.create_report_writer(tmp_path, mock_logger),
        )

        config = BronzeDQReportConfig(enabled=True)

        # Act
        result = await service.generate_reports(
            context=dq_context,
            bronze_config=config,
        )

        # Assert
        assert result.bronze_report_path is not None
        # DQ reports are now in the same directory as data (no _dq_reports subdir)
        # Path should contain dq_report in filename
        assert "_dq_report" in str(result.bronze_report_path)
        # Path should contain batch_id in filename
        assert "batch-001" in result.bronze_report_path.name

    def test_is_any_report_enabled_detection(
        self,
        mock_logger: MagicMock,
    ) -> None:
        """is_any_report_enabled should correctly detect enabled configs."""
        service = DQReportService(logger=mock_logger)

        # No configs - should be False
        assert service.is_any_report_enabled() is False

        # Bronze enabled
        bronze_config = BronzeDQReportConfig(enabled=True)
        assert service.is_any_report_enabled(bronze_config=bronze_config) is True

        # Bronze disabled
        bronze_config_disabled = BronzeDQReportConfig(enabled=False)
        assert (
            service.is_any_report_enabled(bronze_config=bronze_config_disabled) is False
        )

        # Silver enabled
        silver_config = SilverDQReportConfig(enabled=True)
        assert service.is_any_report_enabled(silver_config=silver_config) is True

        # Gold enabled
        gold_config = GoldDQReportConfig(enabled=True)
        assert service.is_any_report_enabled(gold_config=gold_config) is True

        # Mixed - one enabled should return True
        assert (
            service.is_any_report_enabled(
                bronze_config=bronze_config_disabled,
                silver_config=silver_config,
            )
            is True
        )

    @pytest.mark.asyncio
    async def test_gold_dq_report_includes_rule_provenance_traceability(
        self,
        tmp_path: Path,
        mock_logger: MagicMock,
        dq_context: DQReportContext,
    ) -> None:
        """Gold DQ report JSON should include business rule provenance fields."""
        import polars as pl

        context = DQReportContext(
            run_id=dq_context.run_id,
            pipeline_name=dq_context.pipeline_name,
            timestamp=dq_context.timestamp,
            provider="chembl",
            entity="activity",
            gold_data=pl.DataFrame({"value": [-1.0, 2.0]}),
            gold_target_table="chembl.activity",
            gold_required_fields=["value"],
            gold_business_rules=[
                {
                    "rule_id": "R_TRACE_01",
                    "name": "non_negative",
                    "column": "value",
                    "condition": "range",
                    "min": 0,
                    "config_path": "configs/entities/chembl/activity.yaml",
                    "layer": "gold",
                    "field": "value",
                    "severity": "error",
                    "decision": "quarantine",
                }
            ],
            dq_soft_threshold=0.05,
            dq_hard_threshold=0.20,
        )

        service = DQReportService(
            logger=mock_logger,
            gold_analyzer=DQServicesFactory.create_gold_analyzer(),
            report_writer=DQServicesFactory.create_report_writer(tmp_path, mock_logger),
        )

        result = await service.generate_reports(
            context=context,
            gold_config=GoldDQReportConfig(enabled=True, format="json"),
        )

        assert result.gold_report_path is not None
        report_content = json.loads(result.gold_report_path.read_text())
        rules = report_content["checks"]["business_rules"]["rules"]
        assert len(rules) == 1
        assert rules[0]["rule_id"] == "R_TRACE_01"
        assert rules[0]["config_path"] == "configs/entities/chembl/activity.yaml"
        assert rules[0]["layer"] == "gold"
        assert rules[0]["field"] == "value"
        assert rules[0]["severity"] == "error"
        assert rules[0]["decision"] == "quarantine"


@pytest.mark.integration
class TestDQConfigParsing:
    """Integration tests for DQ config parsing from YAML structure."""

    def test_bronze_dq_report_config_defaults(self) -> None:
        """BronzeDQReportConfig should have correct defaults."""
        config = BronzeDQReportConfig()

        assert config.enabled is False
        assert config.format == "json"
        assert config.output_path is None
        # Default checks
        assert "record_count" in config.checks
        assert "file_integrity" in config.checks
        assert "schema_snapshot" in config.checks

    def test_silver_dq_report_config_defaults(self) -> None:
        """SilverDQReportConfig should have correct defaults."""
        config = SilverDQReportConfig()

        assert config.enabled is False
        assert config.format == "json"
        assert config.output_path is None
        # Default checks
        assert "record_count" in config.checks
        assert "null_rate" in config.checks
        assert "uniqueness" in config.checks

    def test_gold_dq_report_config_defaults(self) -> None:
        """GoldDQReportConfig should have correct defaults."""
        config = GoldDQReportConfig()

        assert config.enabled is False
        assert config.format == "json"
        assert config.output_path is None
        # Default checks
        assert "record_count" in config.checks
        assert "completeness" in config.checks
        assert "business_rules" in config.checks

    def test_bronze_config_get_format_enum(self) -> None:
        """BronzeDQReportConfig should convert format to enum."""
        config = BronzeDQReportConfig(format="json")
        assert config.get_format_enum() == DQReportFormat.JSON

        config_yaml = BronzeDQReportConfig(format="yaml")
        assert config_yaml.get_format_enum() == DQReportFormat.YAML

        config_html = BronzeDQReportConfig(format="html")
        assert config_html.get_format_enum() == DQReportFormat.HTML

    def test_bronze_config_get_checks_enums(self) -> None:
        """BronzeDQReportConfig should convert checks to enums."""
        config = BronzeDQReportConfig(
            checks=["record_count", "file_integrity", "invalid_check"]
        )
        enums = config.get_checks_enums()

        # Valid checks should be converted
        assert len(enums) == 2  # invalid_check should be filtered
        from bioetl.domain.value_objects.dq_report import BronzeDQCheckType

        assert BronzeDQCheckType.RECORD_COUNT in enums
        assert BronzeDQCheckType.FILE_INTEGRITY in enums
