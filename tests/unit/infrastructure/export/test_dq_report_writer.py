"""Unit tests for DQ report writer infrastructure.

Tests cover: write_bronze_report, write_silver_report, write_gold_report,
_build_layer_filename, _resolve_layer_output_path, _get_extension, _write_report.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioetl.application.services.dq.bronze_analyzer import BronzeDQAnalyzer
from bioetl.domain.medallion import Layer as MedallionLayer
from bioetl.domain.value_objects.dq_report import (
    BronzeDQReport,
    DQCheckStatus,
    DQReportFormat,
    DQReportStatus,
    DQReportSummary,
    DQThresholds,
    GoldDQReport,
    SilverDQReport,
)
from bioetl.infrastructure.export.dq_report_writer import DQReportWriter
from bioetl.infrastructure.schemas.dq_report_config import BronzeDQReportConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_bronze_report(
    batch_id: str = "batch-1",
    source_file: str = "chembl/target/2026-03-02/batch_1.jsonl.zst",
) -> BronzeDQReport:
    analyzer = BronzeDQAnalyzer()
    config = BronzeDQReportConfig(
        enabled=True,
        format="json",
        checks=["record_count", "file_integrity", "schema_snapshot"],
    )
    return analyzer.analyze(
        records=iter([b'{"id": 1}', b'{"id": 2}']),
        run_id="run-1",
        pipeline="chembl_target",
        batch_id=batch_id,
        source_file=source_file,
        config=config,
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )


def _build_silver_report(
    target_table: str = "chembl_activity",
    run_id: str = "run-silver-1",
) -> SilverDQReport:
    return SilverDQReport(
        layer=MedallionLayer.SILVER,
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        run_id=run_id,
        pipeline="chembl_activity",
        source_batch_ids=("batch-1", "batch-2"),
        target_table=target_table,
        checks={"completeness": {"status": "pass"}},
        thresholds=DQThresholds(
            soft_fail_threshold=0.05,
            hard_fail_threshold=0.1,
            current_error_rate=0.01,
            threshold_status=DQCheckStatus.PASS,
        ),
        summary=DQReportSummary(
            total_checks=1,
            passed=1,
            failed=0,
            warnings=0,
            overall_status=DQReportStatus.PASS,
        ),
    )


def _build_gold_report(
    target_table: str = "chembl_activity",
    run_id: str = "run-gold-1",
) -> GoldDQReport:
    return GoldDQReport(
        layer=MedallionLayer.GOLD,
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        run_id=run_id,
        pipeline="chembl_activity",
        target_table=target_table,
        checks={"completeness": {"status": "pass"}},
        data_freshness=None,
        summary=DQReportSummary(
            total_checks=1,
            passed=1,
            failed=0,
            warnings=0,
            overall_status=DQReportStatus.PASS,
        ),
    )


# ---------------------------------------------------------------------------
# _get_extension
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetExtension:
    """Tests for _get_extension method."""

    def test_json_extension(self, tmp_path: Path) -> None:
        """Should return .json for JSON format."""
        writer = DQReportWriter(base_path=tmp_path, logger=MagicMock())
        assert writer._get_extension(DQReportFormat.JSON) == ".json"

    def test_yaml_extension(self, tmp_path: Path) -> None:
        """Should return .yaml for YAML format."""
        writer = DQReportWriter(base_path=tmp_path, logger=MagicMock())
        assert writer._get_extension(DQReportFormat.YAML) == ".yaml"

    def test_html_extension(self, tmp_path: Path) -> None:
        """Should return .html for HTML format."""
        writer = DQReportWriter(base_path=tmp_path, logger=MagicMock())
        assert writer._get_extension(DQReportFormat.HTML) == ".html"


# ---------------------------------------------------------------------------
# _build_layer_filename
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuildLayerFilename:
    """Tests for _build_layer_filename method."""

    def test_with_provider_and_entity(self, tmp_path: Path) -> None:
        """Should build filename with provider and entity."""
        writer = DQReportWriter(base_path=tmp_path, logger=MagicMock())
        result = writer._build_layer_filename(
            "silver", ".json", "chembl", "activity", "chembl_activity"
        )
        assert result == "silver_chembl_activity_dq_report.json"

    def test_without_provider_entity_flat_structure(self, tmp_path: Path) -> None:
        """Should use table name in flat mode."""
        writer = DQReportWriter(
            base_path=tmp_path, logger=MagicMock(), flat_structure=True
        )
        result = writer._build_layer_filename(
            "silver", ".json", None, None, "chembl.activity"
        )
        assert result == "silver_chembl_activity_dq_report.json"

    def test_without_provider_entity_non_flat(self, tmp_path: Path) -> None:
        """Should use normalized table name in non-flat mode without provider/entity."""
        writer = DQReportWriter(base_path=tmp_path, logger=MagicMock())
        result = writer._build_layer_filename("gold", ".yaml", None, None, "some_table")
        assert result == "gold_some_table_dq_report.yaml"


# ---------------------------------------------------------------------------
# _resolve_layer_output_path
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestResolveLayerOutputPath:
    """Tests for _resolve_layer_output_path method."""

    def test_with_explicit_output_path(self, tmp_path: Path) -> None:
        """Should create dir and append filename when output_path given."""
        writer = DQReportWriter(base_path=tmp_path, logger=MagicMock())
        output_dir = tmp_path / "custom" / "output"
        result = writer._resolve_layer_output_path(
            "silver", output_dir, ".json", "chembl", "activity", "tbl"
        )
        assert result == output_dir / "silver_chembl_activity_dq_report.json"
        assert output_dir.is_dir()

    def test_flat_structure_no_output_path(self, tmp_path: Path) -> None:
        """Should place file directly in base_path in flat mode."""
        writer = DQReportWriter(
            base_path=tmp_path, logger=MagicMock(), flat_structure=True
        )
        result = writer._resolve_layer_output_path(
            "silver", None, ".json", "chembl", "activity", "tbl"
        )
        assert result == tmp_path / "silver_chembl_activity_dq_report.json"

    def test_with_provider_entity_structured(self, tmp_path: Path) -> None:
        """Should use layer/provider/entity directory structure."""
        writer = DQReportWriter(base_path=tmp_path, logger=MagicMock())
        result = writer._resolve_layer_output_path(
            "gold", None, ".json", "chembl", "activity", "tbl"
        )
        expected = (
            tmp_path
            / "gold"
            / "chembl"
            / "activity"
            / "gold_chembl_activity_dq_report.json"
        )
        assert result == expected

    def test_without_provider_entity_table_with_underscore(
        self, tmp_path: Path
    ) -> None:
        """Should split table name by underscore for directory structure."""
        writer = DQReportWriter(base_path=tmp_path, logger=MagicMock())
        result = writer._resolve_layer_output_path(
            "silver", None, ".json", None, None, "chembl_activity"
        )
        expected = (
            tmp_path
            / "silver"
            / "chembl"
            / "activity"
            / "silver_chembl_activity_dq_report.json"
        )
        assert result == expected

    def test_without_provider_entity_simple_table(self, tmp_path: Path) -> None:
        """Should use table name as single directory."""
        writer = DQReportWriter(base_path=tmp_path, logger=MagicMock())
        result = writer._resolve_layer_output_path(
            "silver", None, ".json", None, None, "simpletable"
        )
        expected = (
            tmp_path / "silver" / "simpletable" / "silver_simpletable_dq_report.json"
        )
        assert result == expected


# ---------------------------------------------------------------------------
# write_bronze_report
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestWriteBronzeReport:
    """Tests for write_bronze_report method."""

    async def test_write_with_output_path_as_directory(self, tmp_path: Path) -> None:
        """Should treat output_path as directory and append filename."""
        writer = DQReportWriter(base_path=tmp_path, logger=MagicMock())
        report = _build_bronze_report()
        output_dir = tmp_path / "data" / "output" / "bronze" / "chembl" / "target"

        report_path = await writer.write_bronze_report(
            report=report,
            output_path=output_dir,
            report_format=DQReportFormat.JSON,
            provider="chembl",
            entity="target",
        )

        assert output_dir.is_dir()
        assert report_path == output_dir / "bronze_chembl_target_dq_report.json"
        assert report_path.exists()

    async def test_write_without_output_path_structured(self, tmp_path: Path) -> None:
        """Should build structured path when output_path is None."""
        writer = DQReportWriter(base_path=tmp_path, logger=MagicMock())
        report = _build_bronze_report()

        report_path = await writer.write_bronze_report(
            report=report,
            provider="chembl",
            entity="target",
        )

        expected = (
            tmp_path
            / "bronze"
            / "chembl"
            / "target"
            / "bronze_chembl_target_dq_report.json"
        )
        assert report_path == expected
        assert report_path.exists()

    async def test_write_without_provider_entity(self, tmp_path: Path) -> None:
        """Should use batch_id in filename when no provider/entity."""
        writer = DQReportWriter(base_path=tmp_path, logger=MagicMock())
        report = _build_bronze_report(batch_id="batch-abc")

        report_path = await writer.write_bronze_report(
            report=report,
        )

        assert "batch-abc" in report_path.name
        assert report_path.exists()

    async def test_write_flat_structure(self, tmp_path: Path) -> None:
        """Should place file directly in base_path in flat mode."""
        writer = DQReportWriter(
            base_path=tmp_path, logger=MagicMock(), flat_structure=True
        )
        report = _build_bronze_report()

        report_path = await writer.write_bronze_report(
            report=report,
            provider="chembl",
            entity="target",
        )

        assert report_path == tmp_path / "bronze_chembl_target_dq_report.json"
        assert report_path.exists()

    async def test_write_yaml_format(self, tmp_path: Path) -> None:
        """Should write YAML format with .yaml extension."""
        writer = DQReportWriter(base_path=tmp_path, logger=MagicMock())
        report = _build_bronze_report()

        report_path = await writer.write_bronze_report(
            report=report,
            report_format=DQReportFormat.YAML,
            provider="chembl",
            entity="target",
        )

        assert report_path.suffix == ".yaml"
        assert report_path.exists()


# ---------------------------------------------------------------------------
# write_silver_report
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestWriteSilverReport:
    """Tests for write_silver_report method."""

    async def test_write_default_json(self, tmp_path: Path) -> None:
        """Should write Silver report in JSON format by default."""
        writer = DQReportWriter(base_path=tmp_path, logger=MagicMock())
        report = _build_silver_report()

        report_path = await writer.write_silver_report(
            report=report,
            provider="chembl",
            entity="activity",
        )

        expected = (
            tmp_path
            / "silver"
            / "chembl"
            / "activity"
            / "silver_chembl_activity_dq_report.json"
        )
        assert report_path == expected
        assert report_path.exists()

    async def test_write_with_output_path(self, tmp_path: Path) -> None:
        """Should use explicit output_path when provided."""
        writer = DQReportWriter(base_path=tmp_path, logger=MagicMock())
        report = _build_silver_report()
        output_dir = tmp_path / "custom"

        report_path = await writer.write_silver_report(
            report=report,
            output_path=output_dir,
            provider="chembl",
            entity="activity",
        )

        assert report_path.parent == output_dir
        assert report_path.exists()

    async def test_write_silver_report__write_yaml_format__f9f443a4(self, tmp_path: Path) -> None:
        """Should write Silver report in YAML format."""
        writer = DQReportWriter(base_path=tmp_path, logger=MagicMock())
        report = _build_silver_report()

        report_path = await writer.write_silver_report(
            report=report,
            report_format=DQReportFormat.YAML,
            provider="chembl",
            entity="activity",
        )

        assert report_path.suffix == ".yaml"
        assert report_path.exists()


# ---------------------------------------------------------------------------
# write_gold_report
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestWriteGoldReport:
    """Tests for write_gold_report method."""

    async def test_write_gold_report__write_default_json__d5e46117(self, tmp_path: Path) -> None:
        """Should write Gold report in JSON format by default."""
        writer = DQReportWriter(base_path=tmp_path, logger=MagicMock())
        report = _build_gold_report()

        report_path = await writer.write_gold_report(
            report=report,
            provider="chembl",
            entity="activity",
        )

        expected = (
            tmp_path
            / "gold"
            / "chembl"
            / "activity"
            / "gold_chembl_activity_dq_report.json"
        )
        assert report_path == expected
        assert report_path.exists()

    async def test_write_gold_report__with_output_path__aba59b37(self, tmp_path: Path) -> None:
        """Should use explicit output_path when provided."""
        writer = DQReportWriter(base_path=tmp_path, logger=MagicMock())
        report = _build_gold_report()
        output_dir = tmp_path / "gold_reports"

        report_path = await writer.write_gold_report(
            report=report,
            output_path=output_dir,
            provider="chembl",
            entity="activity",
        )

        assert report_path.parent == output_dir
        assert report_path.exists()

    async def test_write_html_format(self, tmp_path: Path) -> None:
        """Should write Gold report in HTML format."""
        writer = DQReportWriter(base_path=tmp_path, logger=MagicMock())
        report = _build_gold_report()

        report_path = await writer.write_gold_report(
            report=report,
            report_format=DQReportFormat.HTML,
            provider="chembl",
            entity="activity",
        )

        assert report_path.suffix == ".html"
        assert report_path.exists()

    async def test_logger_called_on_write(self, tmp_path: Path) -> None:
        """Should call logger.info after writing report."""
        logger = MagicMock()
        writer = DQReportWriter(base_path=tmp_path, logger=logger)
        report = _build_gold_report()

        await writer.write_gold_report(
            report=report,
            provider="chembl",
            entity="activity",
        )

        logger.info.assert_called_once()
        call_kwargs = logger.info.call_args
        assert call_kwargs[0][0] == "dq_report_written"
