# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Layer-specific DQ report generation helpers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from bioetl.application.services.quality._dq_report_layer_flows import (
    generate_bronze_report,
    generate_gold_report,
    generate_silver_report,
)
from bioetl.application.services.quality.dq_report_models import (
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
        MetricsPort,
        SilverDQAnalyzerPort,
        SilverDQConfigPort,
    )

_SkippedMetricEmitter = Callable[[str, str, str], None]
_GeneratedMetricEmitter = Callable[[str, str], None]
_CheckFailureMetricEmitter = Callable[[str, str, str, str], None]
_DQLayerFlow = Callable[..., Awaitable[Path | None]]


class DQReportGenerationMixin:
    """Mixin with layer-specific DQ report generation flows."""

    _logger: LoggerPort = cast(Any, None)  # Any: host default (PD4)
    _metrics: MetricsPort | None = cast(Any, None)  # Any: host default (PD4)
    _bronze_analyzer: BronzeDQAnalyzerPort | None = cast(
        Any, None
    )  # Any: host default (PD4)
    _silver_analyzer: SilverDQAnalyzerPort | None = cast(
        Any, None
    )  # Any: host default (PD4)
    _gold_analyzer: GoldDQAnalyzerPort | None = cast(
        Any, None
    )  # Any: host default (PD4)
    _report_writer: DQReportWriterPort | None = cast(
        Any, None
    )  # Any: host default (PD4)

    @staticmethod
    def _path_to_str(path: Path | None) -> str | None:
        """Convert path to string or None."""
        return str(path) if path else None

    def _emit_dq_report_skipped_metric(
        self,
        *,
        pipeline: str,
        stage: str,
        reason: str,
    ) -> None:
        """Emit a bounded skip counter when metrics are available."""
        if self._metrics is None:
            return
        self._metrics.increment_counter(
            "bioetl_dq_report_skipped_total",
            1,
            {
                "pipeline": pipeline,
                "stage": stage,
                "reason": reason,
            },
        )

    def _emit_dq_report_generated_metric(
        self,
        *,
        pipeline: str,
        stage: str,
    ) -> None:
        """Emit a generated counter when metrics are available."""
        if self._metrics is None:
            return
        self._metrics.increment_counter(
            "bioetl_dq_report_generated_total",
            1,
            {
                "pipeline": pipeline,
                "stage": stage,
            },
        )

    def _emit_dq_check_failure_metric(
        self,
        *,
        pipeline: str,
        stage: str,
        check_type: str,
        severity: str,
    ) -> None:
        """Emit per-check DQ failure counters when metrics are available."""
        if self._metrics is None:
            return
        self._metrics.increment_counter(
            "bioetl_dq_check_failures_total",
            1,
            {
                "pipeline": pipeline,
                "stage": stage,
                "check_type": check_type,
                "severity": severity,
            },
        )

    def _dq_report_metric_emitters(
        self,
    ) -> tuple[
        _SkippedMetricEmitter,
        _GeneratedMetricEmitter,
        _CheckFailureMetricEmitter,
    ]:
        """Build reusable metric emitters for one DQ report generation call."""
        return (
            lambda pipeline, stage, reason: self._emit_dq_report_skipped_metric(
                pipeline=pipeline,
                stage=stage,
                reason=reason,
            ),
            lambda pipeline, stage: self._emit_dq_report_generated_metric(
                pipeline=pipeline,
                stage=stage,
            ),
            lambda pipeline, stage, check_type, severity: (
                self._emit_dq_check_failure_metric(
                    pipeline=pipeline,
                    stage=stage,
                    check_type=check_type,
                    severity=severity,
                )
            ),
        )

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
        return await self._generate_layer_report(
            context=context,
            config=config,
            analyzer=self._bronze_analyzer,
            flow=generate_bronze_report,
        )

    async def _generate_silver_report(
        self,
        context: DQReportContext,
        config: SilverDQConfigPort,
    ) -> Path | None:
        """Generate Silver DQ report."""
        return await self._generate_layer_report(
            context=context,
            config=config,
            analyzer=self._silver_analyzer,
            flow=generate_silver_report,
        )

    async def _generate_gold_report(
        self,
        context: DQReportContext,
        config: GoldDQConfigPort,
    ) -> Path | None:
        """Generate Gold DQ report."""
        return await self._generate_layer_report(
            context=context,
            config=config,
            analyzer=self._gold_analyzer,
            flow=generate_gold_report,
        )

    async def _generate_layer_report(
        self,
        *,
        context: DQReportContext,
        config: object,
        analyzer: object | None,
        flow: _DQLayerFlow,
    ) -> Path | None:
        """Run one layer-specific DQ report flow with shared emitters."""
        skipped_metric, generated_metric, check_failure_metric = (
            self._dq_report_metric_emitters()
        )
        return await flow(
            context=context,
            config=config,
            analyzer=analyzer,
            report_writer=self._report_writer,
            logger=self._logger,
            emit_skipped_metric=skipped_metric,
            emit_generated_metric=generated_metric,
            emit_check_failure_metric=check_failure_metric,
        )


__all__ = ["DQReportGenerationMixin"]
