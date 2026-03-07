"""Layer-specific DQ report generation helpers."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.services.dq_report_models import (
    _DQ_REPORT_ERRORS,
    DQReportContext,
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


class DQReportGenerationMixin:
    """Mixin with layer-specific DQ report generation flows."""

    _logger: LoggerPort
    _bronze_analyzer: BronzeDQAnalyzerPort | None
    _silver_analyzer: SilverDQAnalyzerPort | None
    _gold_analyzer: GoldDQAnalyzerPort | None
    _report_writer: DQReportWriterPort | None

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
        """Generate Bronze DQ report."""
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
            report = self._bronze_analyzer.analyze(
                records=iter(context.bronze_records),
                run_id=context.run_id,
                pipeline=context.pipeline_name,
                batch_id=context.bronze_batch_id,
                source_file=context.bronze_source_file or "",
                config=config,
                timestamp=context.timestamp,
            )

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
        """Generate Silver DQ report."""
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
        """Generate Gold DQ report."""
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


__all__ = ["DQReportGenerationMixin"]
