"""DQ Report Service for orchestrating DQ report generation.

Application Service that handles DQ report generation across all Medallion layers.
Generates Bronze, Silver, and Gold DQ reports when enabled in configuration.

This service is called during the post-run phase and generates detailed
DQ analysis reports separate from the threshold-based DQ checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        BronzeDQAnalyzerPort,
        DQReportWriterPort,
        GoldDQAnalyzerPort,
        LoggerPort,
        SilverDQAnalyzerPort,
    )
    from bioetl.infrastructure.schemas.dq_report_config import (
        BronzeDQReportConfig,
        GoldDQReportConfig,
        SilverDQReportConfig,
    )


@dataclass(frozen=True, slots=True)
class DQReportResult:
    """Result of DQ report generation for all layers.

    Attributes:
        bronze_report_path: Path to Bronze DQ report (if generated).
        silver_report_path: Path to Silver DQ report (if generated).
        gold_report_path: Path to Gold DQ report (if generated).
        bronze_enabled: Whether Bronze DQ report was enabled.
        silver_enabled: Whether Silver DQ report was enabled.
        gold_enabled: Whether Gold DQ report was enabled.
    """

    bronze_report_path: Path | None = None
    silver_report_path: Path | None = None
    gold_report_path: Path | None = None
    bronze_enabled: bool = False
    silver_enabled: bool = False
    gold_enabled: bool = False

    @property
    def any_generated(self) -> bool:
        """Check if any report was generated."""
        return any(
            [
                self.bronze_report_path is not None,
                self.silver_report_path is not None,
                self.gold_report_path is not None,
            ]
        )

    @property
    def reports_count(self) -> int:
        """Count of generated reports."""
        return sum(
            [
                self.bronze_report_path is not None,
                self.silver_report_path is not None,
                self.gold_report_path is not None,
            ]
        )


@dataclass(frozen=True, slots=True)
class DQReportContext:
    """Context for DQ report generation.

    Contains all metadata and data needed for generating DQ reports.

    Attributes:
        run_id: Pipeline run identifier.
        pipeline_name: Name of the pipeline.
        timestamp: Report generation timestamp (UTC).
        bronze_source_file: Path to Bronze source file (for Bronze report).
        bronze_batch_id: Bronze batch identifier.
        bronze_records: Raw Bronze records (bytes iterator, consumed only once).
        silver_data: Silver layer DataFrame (Polars).
        silver_target_table: Silver target table path.
        silver_source_batch_ids: List of Bronze batch IDs processed.
        silver_primary_keys: Primary key columns.
        silver_input_count: Total records before transformation.
        silver_quarantined_count: Quarantined records count.
        gold_data: Gold layer DataFrame (Polars).
        gold_target_table: Gold target table path.
        gold_required_fields: Required fields for completeness check.
        dq_soft_threshold: Soft fail threshold for DQ checks.
        dq_hard_threshold: Hard fail threshold for DQ checks.
    """

    run_id: str
    pipeline_name: str
    timestamp: datetime

    # Bronze context
    bronze_source_file: str | None = None
    bronze_batch_id: str | None = None
    bronze_records: list[bytes] | None = None

    # Silver context
    silver_data: Any | None = None  # pl.DataFrame
    silver_target_table: str | None = None
    silver_source_batch_ids: list[str] | None = None
    silver_primary_keys: list[str] | None = None
    silver_input_count: int | None = None
    silver_quarantined_count: int = 0
    silver_previous_schema: dict[str, str] | None = None

    # Gold context
    gold_data: Any | None = None  # pl.DataFrame
    gold_target_table: str | None = None
    gold_required_fields: list[str] | None = None
    gold_business_rules: list[dict[str, Any]] | None = None
    gold_baseline_stats: dict[str, Any] | None = None

    # DQ thresholds
    dq_soft_threshold: float = 0.05
    dq_hard_threshold: float = 0.20


class DQReportService:
    """Service for orchestrating DQ report generation.

    Generates detailed DQ analysis reports for Bronze, Silver, and Gold layers
    when enabled in the pipeline configuration.

    Attributes:
        _bronze_analyzer: Bronze layer DQ analyzer (optional).
        _silver_analyzer: Silver layer DQ analyzer (optional).
        _gold_analyzer: Gold layer DQ analyzer (optional).
        _report_writer: DQ report writer (optional).
        _logger: Structured logger for observability.
    """

    def __init__(
        self,
        logger: LoggerPort,
        bronze_analyzer: BronzeDQAnalyzerPort | None = None,
        silver_analyzer: SilverDQAnalyzerPort | None = None,
        gold_analyzer: GoldDQAnalyzerPort | None = None,
        report_writer: DQReportWriterPort | None = None,
    ) -> None:
        """Initialize DQ report service.

        Args:
            logger: Structured logger for observability.
            bronze_analyzer: Optional Bronze layer DQ analyzer.
            silver_analyzer: Optional Silver layer DQ analyzer.
            gold_analyzer: Optional Gold layer DQ analyzer.
            report_writer: Optional DQ report writer.
        """
        self._logger = logger
        self._bronze_analyzer = bronze_analyzer
        self._silver_analyzer = silver_analyzer
        self._gold_analyzer = gold_analyzer
        self._report_writer = report_writer

    async def generate_reports(
        self,
        context: DQReportContext,
        bronze_config: BronzeDQReportConfig | None = None,
        silver_config: SilverDQReportConfig | None = None,
        gold_config: GoldDQReportConfig | None = None,
    ) -> DQReportResult:
        """Generate DQ reports for all enabled layers.

        Args:
            context: DQ report context with data and metadata.
            bronze_config: Bronze DQ report configuration (optional).
            silver_config: Silver DQ report configuration (optional).
            gold_config: Gold DQ report configuration (optional).

        Returns:
            DQReportResult with paths to generated reports.
        """
        bronze_path: Path | None = None
        silver_path: Path | None = None
        gold_path: Path | None = None

        bronze_enabled = bronze_config is not None and bronze_config.enabled
        silver_enabled = silver_config is not None and silver_config.enabled
        gold_enabled = gold_config is not None and gold_config.enabled

        self._logger.debug(
            "dq_report_generation_started",
            run_id=context.run_id,
            bronze_enabled=bronze_enabled,
            silver_enabled=silver_enabled,
            gold_enabled=gold_enabled,
        )

        # Generate Bronze report if enabled
        if bronze_enabled and bronze_config:
            bronze_path = await self._generate_bronze_report(context, bronze_config)

        # Generate Silver report if enabled
        if silver_enabled and silver_config:
            silver_path = await self._generate_silver_report(context, silver_config)

        # Generate Gold report if enabled
        if gold_enabled and gold_config:
            gold_path = await self._generate_gold_report(context, gold_config)

        result = DQReportResult(
            bronze_report_path=bronze_path,
            silver_report_path=silver_path,
            gold_report_path=gold_path,
            bronze_enabled=bronze_enabled,
            silver_enabled=silver_enabled,
            gold_enabled=gold_enabled,
        )

        if result.any_generated:
            self._logger.info(
                "dq_reports_generated",
                run_id=context.run_id,
                reports_count=result.reports_count,
                bronze_path=str(bronze_path) if bronze_path else None,
                silver_path=str(silver_path) if silver_path else None,
                gold_path=str(gold_path) if gold_path else None,
            )

        return result

    async def _generate_bronze_report(
        self,
        context: DQReportContext,
        config: BronzeDQReportConfig,
    ) -> Path | None:
        """Generate Bronze DQ report.

        Args:
            context: DQ report context.
            config: Bronze DQ report configuration.

        Returns:
            Path to the generated report, or None if generation failed.
        """
        if not self._bronze_analyzer or not self._report_writer:
            self._logger.warning(
                "bronze_dq_report_skipped",
                reason="analyzer or writer not available",
                run_id=context.run_id,
            )
            return None

        if context.bronze_records is None or context.bronze_batch_id is None:
            self._logger.warning(
                "bronze_dq_report_skipped",
                reason="no bronze data available",
                run_id=context.run_id,
            )
            return None

        try:
            # Analyze Bronze data
            report = self._bronze_analyzer.analyze(
                records=iter(context.bronze_records),
                run_id=context.run_id,
                pipeline=context.pipeline_name,
                batch_id=context.bronze_batch_id,
                source_file=context.bronze_source_file or "",
                config=config,
                timestamp=context.timestamp,
            )

            # Write report
            output_path = Path(config.output_path) if config.output_path else None
            path = await self._report_writer.write_bronze_report(
                report=report,
                output_path=output_path,
                format=config.get_format_enum(),
            )

            self._logger.debug(
                "bronze_dq_report_generated",
                run_id=context.run_id,
                path=str(path),
                status=report.summary.overall_status.value,
            )

            return path

        except Exception as e:
            self._logger.error(
                "bronze_dq_report_failed",
                run_id=context.run_id,
                error=str(e),
            )
            return None

    async def _generate_silver_report(
        self,
        context: DQReportContext,
        config: SilverDQReportConfig,
    ) -> Path | None:
        """Generate Silver DQ report.

        Args:
            context: DQ report context.
            config: Silver DQ report configuration.

        Returns:
            Path to the generated report, or None if generation failed.
        """
        if not self._silver_analyzer or not self._report_writer:
            self._logger.warning(
                "silver_dq_report_skipped",
                reason="analyzer or writer not available",
                run_id=context.run_id,
            )
            return None

        if context.silver_data is None or context.silver_target_table is None:
            self._logger.warning(
                "silver_dq_report_skipped",
                reason="no silver data available",
                run_id=context.run_id,
            )
            return None

        try:
            # Analyze Silver data
            report = self._silver_analyzer.analyze(
                data=context.silver_data,
                run_id=context.run_id,
                pipeline=context.pipeline_name,
                target_table=context.silver_target_table,
                source_batch_ids=context.silver_source_batch_ids or [],
                config=config,
                timestamp=context.timestamp,
                primary_keys=context.silver_primary_keys or [],
                soft_fail_threshold=context.dq_soft_threshold,
                hard_fail_threshold=context.dq_hard_threshold,
                input_record_count=context.silver_input_count,
                quarantined_count=context.silver_quarantined_count,
                previous_schema=context.silver_previous_schema,
            )

            # Write report
            output_path = Path(config.output_path) if config.output_path else None
            path = await self._report_writer.write_silver_report(
                report=report,
                output_path=output_path,
                format=config.get_format_enum(),
            )

            self._logger.debug(
                "silver_dq_report_generated",
                run_id=context.run_id,
                path=str(path),
                status=report.summary.overall_status.value,
            )

            return path

        except Exception as e:
            self._logger.error(
                "silver_dq_report_failed",
                run_id=context.run_id,
                error=str(e),
            )
            return None

    async def _generate_gold_report(
        self,
        context: DQReportContext,
        config: GoldDQReportConfig,
    ) -> Path | None:
        """Generate Gold DQ report.

        Args:
            context: DQ report context.
            config: Gold DQ report configuration.

        Returns:
            Path to the generated report, or None if generation failed.
        """
        if not self._gold_analyzer or not self._report_writer:
            self._logger.warning(
                "gold_dq_report_skipped",
                reason="analyzer or writer not available",
                run_id=context.run_id,
            )
            return None

        if context.gold_data is None or context.gold_target_table is None:
            self._logger.warning(
                "gold_dq_report_skipped",
                reason="no gold data available",
                run_id=context.run_id,
            )
            return None

        try:
            # Analyze Gold data
            report = self._gold_analyzer.analyze(
                data=context.gold_data,
                run_id=context.run_id,
                pipeline=context.pipeline_name,
                target_table=context.gold_target_table,
                config=config,
                timestamp=context.timestamp,
                required_fields=context.gold_required_fields,
                business_rules=context.gold_business_rules,
                baseline_stats=context.gold_baseline_stats,
            )

            # Write report
            output_path = Path(config.output_path) if config.output_path else None
            path = await self._report_writer.write_gold_report(
                report=report,
                output_path=output_path,
                format=config.get_format_enum(),
            )

            self._logger.debug(
                "gold_dq_report_generated",
                run_id=context.run_id,
                path=str(path),
                status=report.summary.overall_status.value,
            )

            return path

        except Exception as e:
            self._logger.error(
                "gold_dq_report_failed",
                run_id=context.run_id,
                error=str(e),
            )
            return None

    def is_any_report_enabled(
        self,
        bronze_config: BronzeDQReportConfig | None = None,
        silver_config: SilverDQReportConfig | None = None,
        gold_config: GoldDQReportConfig | None = None,
    ) -> bool:
        """Check if any DQ report generation is enabled.

        Args:
            bronze_config: Bronze DQ report configuration.
            silver_config: Silver DQ report configuration.
            gold_config: Gold DQ report configuration.

        Returns:
            True if any layer has DQ report enabled.
        """
        return (
            (bronze_config is not None and bronze_config.enabled)
            or (silver_config is not None and silver_config.enabled)
            or (gold_config is not None and gold_config.enabled)
        )


__all__ = [
    "DQReportContext",
    "DQReportResult",
    "DQReportService",
]
