"""DQ report orchestration service.

Application service that coordinates layer-specific DQ report generation for
Bronze, Silver, and Gold.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.services.quality.dq_report_generation_mixin import (
    DQReportGenerationMixin,
)
from bioetl.application.services.quality.dq_report_models import (
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
        MetricsPort,
        SilverDQAnalyzerPort,
        SilverDQConfigPort,
    )


class DQReportService(DQReportGenerationMixin):
    """Orchestrate DQ report generation across Medallion layers."""

    _logger: LoggerPort
    _metrics: MetricsPort | None
    _bronze_analyzer: BronzeDQAnalyzerPort | None
    _silver_analyzer: SilverDQAnalyzerPort | None
    _gold_analyzer: GoldDQAnalyzerPort | None
    _report_writer: DQReportWriterPort | None

    def __init__(
        self,
        logger: LoggerPort,
        bronze_analyzer: BronzeDQAnalyzerPort | None = None,
        silver_analyzer: SilverDQAnalyzerPort | None = None,
        gold_analyzer: GoldDQAnalyzerPort | None = None,
        report_writer: DQReportWriterPort | None = None,
        metrics: MetricsPort | None = None,
    ) -> None:
        self._logger = logger
        self._metrics = metrics
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
            context: DQ report context with run_id, provider, and entity metadata.
            bronze_config: Optional Bronze layer DQ config port. If None or
                config.enabled is False, Bronze report is skipped.
            silver_config: Optional Silver layer DQ config port. If None or
                config.enabled is False, Silver report is skipped.
            gold_config: Optional Gold layer DQ config port. If None or
                config.enabled is False, Gold report is skipped.

        Returns:
            DQReportResult with paths of generated reports and per-layer enabled flags.
        """
        bronze_enabled = self._is_config_enabled(bronze_config)
        silver_enabled = self._is_config_enabled(silver_config)
        gold_enabled = self._is_config_enabled(gold_config)
        self._log_generation_start(
            context.run_id,
            bronze_enabled=bronze_enabled,
            silver_enabled=silver_enabled,
            gold_enabled=gold_enabled,
        )

        bronze_path = await self._try_generate_bronze(
            context=context,
            config=bronze_config,
            enabled=bronze_enabled,
        )
        silver_path = await self._try_generate_silver(
            context=context,
            config=silver_config,
            enabled=silver_enabled,
        )
        gold_path = await self._try_generate_gold(
            context=context,
            config=gold_config,
            enabled=gold_enabled,
        )

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
        """Return True when config exists and report generation is enabled."""
        return config is not None and config.enabled

    def _log_generation_start(
        self,
        run_id: str,
        bronze_enabled: bool,
        silver_enabled: bool,
        gold_enabled: bool,
    ) -> None:
        """Log DQ report generation start."""
        self._logger.debug(
            "dq_report_generation_started",
            run_id=run_id,
            bronze_enabled=bronze_enabled,
            silver_enabled=silver_enabled,
            gold_enabled=gold_enabled,
        )

    def _log_generation_result(self, run_id: str, result: DQReportResult) -> None:
        """Log DQ report generation result when any layer produced a report."""
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

    def is_any_report_enabled(
        self,
        bronze_config: BronzeDQConfigPort | None = None,
        silver_config: SilverDQConfigPort | None = None,
        gold_config: GoldDQConfigPort | None = None,
    ) -> bool:
        """Check whether at least one layer has DQ report generation enabled.

        Args:
            bronze_config: Optional Bronze layer DQ config port.
            silver_config: Optional Silver layer DQ config port.
            gold_config: Optional Gold layer DQ config port.

        Returns:
            True if at least one non-None config has enabled=True, False otherwise.
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
