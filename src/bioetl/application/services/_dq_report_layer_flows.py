"""Layer-specific DQ report generation flows."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.services.dq_report_models import (
    _DQ_REPORT_ERRORS,
    DQReportContext,
)
from bioetl.domain.ports import SilverDQAnalyzeRequest

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
_NO_DATA_REASON_BY_STAGE = {
    "bronze": "no bronze data available",
    "silver": "no silver data available",
    "gold": "no gold data available",
}


def _skip_report_generation(
    *,
    context: DQReportContext,
    stage: str,
    reason_key: str,
    logger: LoggerPort,
    emit_skipped_metric: Callable[[str, str, str], None],
) -> None:
    """Emit shared skip metric and log entry for one DQ report stage."""
    emit_skipped_metric(context.pipeline_name, stage, reason_key)
    reason = (
        _ANALYZER_OR_WRITER_UNAVAILABLE
        if reason_key == "analyzer_or_writer_unavailable"
        else _NO_DATA_REASON_BY_STAGE[stage]
    )
    logger.warning(
        f"{stage}_dq_report_skipped",
        reason=reason,
        run_id=context.run_id,
    )


async def _finalize_generated_report(
    *,
    context: DQReportContext,
    stage: str,
    report: object,
    write_report: Callable[[object], object],
    logger: LoggerPort,
    emit_generated_metric: Callable[[str, str], None],
    emit_check_failure_metric: Callable[[str, str, str, str], None],
) -> Path:
    """Write one generated report and emit shared logging/metric side effects."""
    path = await write_report(report)
    logger.debug(
        f"{stage}_dq_report_generated",
        run_id=context.run_id,
        path=str(path),
        status=report.summary.overall_status.value,
    )
    _emit_check_failure_metrics(
        checks=getattr(report, "checks", None),
        pipeline=context.pipeline_name,
        stage=stage,
        emit_check_failure_metric=emit_check_failure_metric,
    )
    emit_generated_metric(context.pipeline_name, stage)
    return path


async def _generate_report_for_stage(
    *,
    context: DQReportContext,
    stage: str,
    analyzer_available: bool,
    report_writer_available: bool,
    data_available: bool,
    missing_data_reason_key: str,
    analyze_report: Callable[[], object],
    write_report: Callable[[object], Awaitable[Path]],
    logger: LoggerPort,
    emit_skipped_metric: Callable[[str, str, str], None],
    emit_generated_metric: Callable[[str, str], None],
    emit_check_failure_metric: Callable[[str, str, str, str], None],
) -> Path | None:
    """Run the shared DQ report generation flow for one pipeline stage."""
    if not analyzer_available or not report_writer_available:
        _skip_report_generation(
            context=context,
            stage=stage,
            reason_key="analyzer_or_writer_unavailable",
            logger=logger,
            emit_skipped_metric=emit_skipped_metric,
        )
        return None

    if not data_available:
        _skip_report_generation(
            context=context,
            stage=stage,
            reason_key=missing_data_reason_key,
            logger=logger,
            emit_skipped_metric=emit_skipped_metric,
        )
        return None

    try:
        report = analyze_report()
        return await _finalize_generated_report(
            context=context,
            stage=stage,
            report=report,
            write_report=write_report,
            logger=logger,
            emit_generated_metric=emit_generated_metric,
            emit_check_failure_metric=emit_check_failure_metric,
        )
    except _DQ_REPORT_ERRORS as exc:
        _log_report_generation_failure(
            context=context,
            stage=stage,
            error=exc,
            logger=logger,
        )
        return None


def _log_report_generation_failure(
    *,
    context: DQReportContext,
    stage: str,
    error: Exception,
    logger: LoggerPort,
) -> None:
    """Log one shared DQ report generation failure surface."""
    logger.error(
        f"{stage}_dq_report_failed",
        run_id=context.run_id,
        error=str(error),
    )


async def generate_bronze_report(
    *,
    context: DQReportContext,
    config: BronzeDQConfigPort,
    analyzer: BronzeDQAnalyzerPort | None,
    report_writer: DQReportWriterPort | None,
    logger: LoggerPort,
    emit_skipped_metric: Callable[[str, str, str], None],
    emit_generated_metric: Callable[[str, str], None],
    emit_check_failure_metric: Callable[[str, str, str, str], None],
) -> Path | None:
    """Generate Bronze DQ report when analyzer and data are available."""
    def _analyze_report() -> object:
        assert analyzer is not None
        return analyzer.analyze(
            records=iter(context.bronze_records),
            run_id=context.run_id,
            pipeline=context.pipeline_name,
            batch_id=context.bronze_batch_id,
            source_file=context.bronze_source_file or "",
            config=config,
            timestamp=context.timestamp,
        )

    async def _write_report(report: object) -> Path:
        assert report_writer is not None
        return await report_writer.write_bronze_report(
            report=report,
            output_path=_resolve_output_path(
                context.bronze_output_path, config.output_path
            ),
            report_format=config.get_format_enum(),
            provider=context.provider,
            entity=context.entity,
        )

    return await _generate_report_for_stage(
        context=context,
        stage="bronze",
        analyzer_available=analyzer is not None,
        report_writer_available=report_writer is not None,
        data_available=(
            context.bronze_records is not None and context.bronze_batch_id is not None
        ),
        missing_data_reason_key="no_bronze_data",
        analyze_report=_analyze_report,
        write_report=_write_report,
        logger=logger,
        emit_skipped_metric=emit_skipped_metric,
        emit_generated_metric=emit_generated_metric,
        emit_check_failure_metric=emit_check_failure_metric,
    )


async def generate_silver_report(
    *,
    context: DQReportContext,
    config: SilverDQConfigPort,
    analyzer: SilverDQAnalyzerPort | None,
    report_writer: DQReportWriterPort | None,
    logger: LoggerPort,
    emit_skipped_metric: Callable[[str, str, str], None],
    emit_generated_metric: Callable[[str, str], None],
    emit_check_failure_metric: Callable[[str, str, str, str], None],
) -> Path | None:
    """Generate Silver DQ report when analyzer and data are available."""
    def _analyze_report() -> object:
        assert analyzer is not None
        analyze_request = SilverDQAnalyzeRequest(
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
        return analyzer.analyze(analyze_request)

    async def _write_report(report: object) -> Path:
        assert report_writer is not None
        return await report_writer.write_silver_report(
            report=report,
            output_path=_resolve_output_path(
                context.silver_output_path, config.output_path
            ),
            report_format=config.get_format_enum(),
            provider=context.provider,
            entity=context.entity,
        )

    return await _generate_report_for_stage(
        context=context,
        stage="silver",
        analyzer_available=analyzer is not None,
        report_writer_available=report_writer is not None,
        data_available=(
            context.silver_data is not None
            and context.silver_target_table is not None
        ),
        missing_data_reason_key="no_silver_data",
        analyze_report=_analyze_report,
        write_report=_write_report,
        logger=logger,
        emit_skipped_metric=emit_skipped_metric,
        emit_generated_metric=emit_generated_metric,
        emit_check_failure_metric=emit_check_failure_metric,
    )


async def generate_gold_report(
    *,
    context: DQReportContext,
    config: GoldDQConfigPort,
    analyzer: GoldDQAnalyzerPort | None,
    report_writer: DQReportWriterPort | None,
    logger: LoggerPort,
    emit_skipped_metric: Callable[[str, str, str], None],
    emit_generated_metric: Callable[[str, str], None],
    emit_check_failure_metric: Callable[[str, str, str, str], None],
) -> Path | None:
    """Generate Gold DQ report when analyzer and data are available."""
    def _analyze_report() -> object:
        assert analyzer is not None
        return analyzer.analyze(
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

    async def _write_report(report: object) -> Path:
        assert report_writer is not None
        return await report_writer.write_gold_report(
            report=report,
            output_path=_resolve_output_path(
                context.gold_output_path, config.output_path
            ),
            report_format=config.get_format_enum(),
            provider=context.provider,
            entity=context.entity,
        )

    return await _generate_report_for_stage(
        context=context,
        stage="gold",
        analyzer_available=analyzer is not None,
        report_writer_available=report_writer is not None,
        data_available=(
            context.gold_data is not None and context.gold_target_table is not None
        ),
        missing_data_reason_key="no_gold_data",
        analyze_report=_analyze_report,
        write_report=_write_report,
        logger=logger,
        emit_skipped_metric=emit_skipped_metric,
        emit_generated_metric=emit_generated_metric,
        emit_check_failure_metric=emit_check_failure_metric,
    )


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


def _emit_check_failure_metrics(
    *,
    checks: object,
    pipeline: str,
    stage: str,
    emit_check_failure_metric: Callable[[str, str, str, str], None],
) -> None:
    """Emit one bounded metric for each failed or warning DQ check."""
    if not isinstance(checks, Mapping):
        return
    for check_type, payload in checks.items():
        severity = _metric_severity_for_check_payload(payload)
        if severity is None:
            continue
        emit_check_failure_metric(pipeline, stage, str(check_type), severity)


def _metric_severity_for_check_payload(payload: object) -> str | None:
    """Map serialized DQ check payload status to a metric severity label."""
    if not isinstance(payload, Mapping):
        return None
    raw_status = payload.get("status")
    if raw_status is None:
        return None
    status = str(raw_status).strip().lower()
    if status == "fail":
        return "hard_fail"
    if status == "warn":
        return "warning"
    if status == "error":
        return "error"
    return None
