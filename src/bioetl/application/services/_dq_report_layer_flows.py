"""Layer-specific DQ report generation flows."""

from __future__ import annotations

from collections.abc import Callable
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

_ANALYZER_OR_WRITER_UNAVAILABLE = "analyzer or writer not available"


async def generate_bronze_report(
    *,
    context: DQReportContext,
    config: BronzeDQConfigPort,
    analyzer: BronzeDQAnalyzerPort | None,
    report_writer: DQReportWriterPort | None,
    logger: LoggerPort,
    emit_skipped_metric: Callable[[str, str, str], None],
    emit_generated_metric: Callable[[str, str], None],
) -> Path | None:
    """Generate Bronze DQ report when analyzer and data are available."""
    if analyzer is None or report_writer is None:
        emit_skipped_metric(
            context.pipeline_name, "bronze", "analyzer_or_writer_unavailable"
        )
        logger.warning(
            "bronze_dq_report_skipped",
            reason=_ANALYZER_OR_WRITER_UNAVAILABLE,
            run_id=context.run_id,
        )
        return None

    if context.bronze_records is None or context.bronze_batch_id is None:
        emit_skipped_metric(context.pipeline_name, "bronze", "no_bronze_data")
        logger.warning(
            "bronze_dq_report_skipped",
            reason="no bronze data available",
            run_id=context.run_id,
        )
        return None

    try:
        report = analyzer.analyze(
            records=iter(context.bronze_records),
            run_id=context.run_id,
            pipeline=context.pipeline_name,
            batch_id=context.bronze_batch_id,
            source_file=context.bronze_source_file or "",
            config=config,
            timestamp=context.timestamp,
        )
        path = await report_writer.write_bronze_report(
            report=report,
            output_path=_resolve_output_path(
                context.bronze_output_path, config.output_path
            ),
            format=config.get_format_enum(),
            provider=context.provider,
            entity=context.entity,
            date_str=context.bronze_date_str,
        )
        logger.debug(
            "bronze_dq_report_generated",
            run_id=context.run_id,
            path=str(path),
            status=report.summary.overall_status.value,
        )
        emit_generated_metric(context.pipeline_name, "bronze")
        return path
    except _DQ_REPORT_ERRORS as exc:
        logger.error(
            "bronze_dq_report_failed",
            run_id=context.run_id,
            error=str(exc),
        )
        return None


async def generate_silver_report(
    *,
    context: DQReportContext,
    config: SilverDQConfigPort,
    analyzer: SilverDQAnalyzerPort | None,
    report_writer: DQReportWriterPort | None,
    logger: LoggerPort,
    emit_skipped_metric: Callable[[str, str, str], None],
    emit_generated_metric: Callable[[str, str], None],
) -> Path | None:
    """Generate Silver DQ report when analyzer and data are available."""
    if analyzer is None or report_writer is None:
        emit_skipped_metric(
            context.pipeline_name, "silver", "analyzer_or_writer_unavailable"
        )
        logger.warning(
            "silver_dq_report_skipped",
            reason=_ANALYZER_OR_WRITER_UNAVAILABLE,
            run_id=context.run_id,
        )
        return None

    if context.silver_data is None or context.silver_target_table is None:
        emit_skipped_metric(context.pipeline_name, "silver", "no_silver_data")
        logger.warning(
            "silver_dq_report_skipped",
            reason="no silver data available",
            run_id=context.run_id,
        )
        return None

    try:
        report = analyzer.analyze(
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
        path = await report_writer.write_silver_report(
            report=report,
            output_path=_resolve_output_path(
                context.silver_output_path, config.output_path
            ),
            format=config.get_format_enum(),
            provider=context.provider,
            entity=context.entity,
        )
        logger.debug(
            "silver_dq_report_generated",
            run_id=context.run_id,
            path=str(path),
            status=report.summary.overall_status.value,
        )
        emit_generated_metric(context.pipeline_name, "silver")
        return path
    except _DQ_REPORT_ERRORS as exc:
        logger.error(
            "silver_dq_report_failed",
            run_id=context.run_id,
            error=str(exc),
        )
        return None


async def generate_gold_report(
    *,
    context: DQReportContext,
    config: GoldDQConfigPort,
    analyzer: GoldDQAnalyzerPort | None,
    report_writer: DQReportWriterPort | None,
    logger: LoggerPort,
    emit_skipped_metric: Callable[[str, str, str], None],
    emit_generated_metric: Callable[[str, str], None],
) -> Path | None:
    """Generate Gold DQ report when analyzer and data are available."""
    if analyzer is None or report_writer is None:
        emit_skipped_metric(
            context.pipeline_name, "gold", "analyzer_or_writer_unavailable"
        )
        logger.warning(
            "gold_dq_report_skipped",
            reason=_ANALYZER_OR_WRITER_UNAVAILABLE,
            run_id=context.run_id,
        )
        return None

    if context.gold_data is None or context.gold_target_table is None:
        emit_skipped_metric(context.pipeline_name, "gold", "no_gold_data")
        logger.warning(
            "gold_dq_report_skipped",
            reason="no gold data available",
            run_id=context.run_id,
        )
        return None

    try:
        report = analyzer.analyze(
            data=context.gold_data,
            run_id=context.run_id,
            pipeline=context.pipeline_name,
            target_table=context.gold_target_table,
            config=config,
            timestamp=context.timestamp,
            required_fields=context.gold_required_fields,
            business_rules=context.gold_business_rules,
            baseline_stats=context.gold_baseline_stats,
            scd_config=context.gold_scd_config,
        )
        path = await report_writer.write_gold_report(
            report=report,
            output_path=_resolve_output_path(
                context.gold_output_path, config.output_path
            ),
            format=config.get_format_enum(),
            provider=context.provider,
            entity=context.entity,
        )
        logger.debug(
            "gold_dq_report_generated",
            run_id=context.run_id,
            path=str(path),
            status=report.summary.overall_status.value,
        )
        emit_generated_metric(context.pipeline_name, "gold")
        return path
    except _DQ_REPORT_ERRORS as exc:
        logger.error(
            "gold_dq_report_failed",
            run_id=context.run_id,
            error=str(exc),
        )
        return None


def _resolve_output_path(
    context_output_path: str | None,
    config_output_path: str | None,
) -> Path | None:
    """Resolve the explicit report output path when one is configured."""
    if context_output_path:
        return Path(context_output_path)
    if config_output_path:
        return Path(config_output_path)
    return None
