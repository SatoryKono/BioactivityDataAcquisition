"""DQ Report Service for orchestrating DQ report generation.

Application Service that handles DQ report generation across all Medallion layers.
Generates Bronze, Silver, and Gold DQ reports when enabled in configuration.

This service is called during the post-run phase and generates detailed
DQ analysis reports separate from the threshold-based DQ checks.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bioetl.application.services.dq_report_models import (
    _DQ_REPORT_ERRORS,
    DQReportContext,
    DQReportResult,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        BronzeDQAnalyzerPort,
        BronzeDQConfigPort,
        DQReportWriterPort,
        GoldDQAnalyzerPort,
        GoldDQConfigPort,
        LoggerPort,
        SilverDQAnalyzerPort,
        SilverDQConfigPort,
    )


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
        bronze_config: BronzeDQConfigPort | None = None,
        silver_config: SilverDQConfigPort | None = None,
        gold_config: GoldDQConfigPort | None = None,
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
        bronze_enabled = self._is_config_enabled(bronze_config)
        silver_enabled = self._is_config_enabled(silver_config)
        gold_enabled = self._is_config_enabled(gold_config)

        self._log_generation_start(
            context.run_id, bronze_enabled, silver_enabled, gold_enabled
        )

        bronze_path = await self._try_generate_bronze(
            context, bronze_config, bronze_enabled
        )
        silver_path = await self._try_generate_silver(
            context, silver_config, silver_enabled
        )
        gold_path = await self._try_generate_gold(context, gold_config, gold_enabled)

        result = DQReportResult(
            bronze_report_path=bronze_path,
            silver_report_path=silver_path,
            gold_report_path=gold_path,
            bronze_enabled=bronze_enabled,
            silver_enabled=silver_enabled,
            gold_enabled=gold_enabled,
        )

        self._log_generation_result(context.run_id, result)
        return result

    @staticmethod
    def _is_config_enabled(config: Any) -> bool:  # Any: heterogeneous DQ metric values
        """Check if a config is present and enabled."""
        return config is not None and config.enabled

    def _log_generation_start(
        self,
        run_id: str,
        bronze_enabled: bool,
        silver_enabled: bool,
        gold_enabled: bool,
    ) -> None:
        """Log the start of DQ report generation."""
        self._logger.debug(
            "dq_report_generation_started",
            run_id=run_id,
            bronze_enabled=bronze_enabled,
            silver_enabled=silver_enabled,
            gold_enabled=gold_enabled,
        )

    def _log_generation_result(self, run_id: str, result: DQReportResult) -> None:
        """Log the result of DQ report generation if any were generated."""
        if not result.any_generated:
            return
        self._logger.info(
            "dq_reports_generated",
            run_id=run_id,
            reports_count=result.reports_count,
            bronze_path=self._path_to_str(result.bronze_report_path),
            silver_path=self._path_to_str(result.silver_report_path),
            gold_path=self._path_to_str(result.gold_report_path),
        )

    @staticmethod
    def _path_to_str(path: Path | None) -> str | None:
        """Convert path to string or None."""
        return str(path) if path else None

    async def _try_generate_bronze(
        self,
        context: DQReportContext,
        config: BronzeDQConfigPort | None,
        enabled: bool,
    ) -> Path | None:
        """Try to generate Bronze report if enabled."""
        if enabled and config:
            return await self._generate_bronze_report(context, config)
        return None

    async def _try_generate_silver(
        self,
        context: DQReportContext,
        config: SilverDQConfigPort | None,
        enabled: bool,
    ) -> Path | None:
        """Try to generate Silver report if enabled."""
        if enabled and config:
            return await self._generate_silver_report(context, config)
        return None

    async def _try_generate_gold(
        self,
        context: DQReportContext,
        config: GoldDQConfigPort | None,
        enabled: bool,
    ) -> Path | None:
        """Try to generate Gold report if enabled."""
        if enabled and config:
            return await self._generate_gold_report(context, config)
        return None

    async def _generate_bronze_report(
        self,
        context: DQReportContext,
        config: BronzeDQConfigPort,
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

            # Write report - use context output_path if provided, else config
            output_path: Path | None = None
            if context.bronze_output_path:
                output_path = Path(context.bronze_output_path)
            elif config.output_path:
                output_path = Path(config.output_path)

            path = await self._report_writer.write_bronze_report(
                report=report,
                output_path=output_path,
                format=config.get_format_enum(),
                provider=context.provider,
                entity=context.entity,
                date_str=context.bronze_date_str,
            )

            self._logger.debug(
                "bronze_dq_report_generated",
                run_id=context.run_id,
                path=str(path),
                status=report.summary.overall_status.value,
            )

            return path

        except _DQ_REPORT_ERRORS as e:
            self._logger.error(
                "bronze_dq_report_failed",
                run_id=context.run_id,
                error=str(e),
            )
            return None

    async def _generate_silver_report(
        self,
        context: DQReportContext,
        config: SilverDQConfigPort,
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
                key_nullability_rules=context.silver_key_nullability_rules,
            )

            # Write report - use context output_path if provided, else config
            output_path: Path | None = None
            if context.silver_output_path:
                output_path = Path(context.silver_output_path)
            elif config.output_path:
                output_path = Path(config.output_path)

            path = await self._report_writer.write_silver_report(
                report=report,
                output_path=output_path,
                format=config.get_format_enum(),
                provider=context.provider,
                entity=context.entity,
            )

            self._logger.debug(
                "silver_dq_report_generated",
                run_id=context.run_id,
                path=str(path),
                status=report.summary.overall_status.value,
            )

            return path

        except _DQ_REPORT_ERRORS as e:
            self._logger.error(
                "silver_dq_report_failed",
                run_id=context.run_id,
                error=str(e),
            )
            return None

    async def _generate_gold_report(
        self,
        context: DQReportContext,
        config: GoldDQConfigPort,
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

            # Write report - use context output_path if provided, else config
            output_path: Path | None = None
            if context.gold_output_path:
                output_path = Path(context.gold_output_path)
            elif config.output_path:
                output_path = Path(config.output_path)

            path = await self._report_writer.write_gold_report(
                report=report,
                output_path=output_path,
                format=config.get_format_enum(),
                provider=context.provider,
                entity=context.entity,
            )

            self._logger.debug(
                "gold_dq_report_generated",
                run_id=context.run_id,
                path=str(path),
                status=report.summary.overall_status.value,
            )

            return path

        except _DQ_REPORT_ERRORS as e:
            self._logger.error(
                "gold_dq_report_failed",
                run_id=context.run_id,
                error=str(e),
            )
            return None

    def is_any_report_enabled(
        self,
        bronze_config: BronzeDQConfigPort | None = None,
        silver_config: SilverDQConfigPort | None = None,
        gold_config: GoldDQConfigPort | None = None,
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
