"""DQ report orchestration extracted from PostrunService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.exceptions import BioETLError

if TYPE_CHECKING:
    from bioetl.application.services.dq_report_service import (
        DQReportContext,
        DQReportResult,
        DQReportService,
    )
    from bioetl.domain.ports import (
        BronzeDQConfigPort,
        GoldDQConfigPort,
        LoggerPort,
        SilverDQConfigPort,
    )


class PostrunDQReportService:
    """Orchestrates optional DQ report generation with strict/warning mode."""

    def __init__(
        self,
        *,
        logger: LoggerPort,
        runtime: object,
        dq_report_service: DQReportService | None,
        bronze_dq_config: BronzeDQConfigPort | None,
        silver_dq_config: SilverDQConfigPort | None,
        gold_dq_config: GoldDQConfigPort | None,
        warning_allowlist: tuple[type[BaseException], ...],
    ) -> None:
        self._logger = logger
        self._runtime = runtime
        self._dq_report_service = dq_report_service
        self._bronze_dq_config = bronze_dq_config
        self._silver_dq_config = silver_dq_config
        self._gold_dq_config = gold_dq_config
        self._warning_allowlist = warning_allowlist

    async def generate_reports(
        self,
        context: DQReportContext | None,
    ) -> DQReportResult | None:
        """Generate DQ reports when service/config/context are available."""
        if self._dq_report_service is None:
            return None

        if context is None:
            self._logger.debug(
                "dq_report_skipped",
                reason="no context provided",
            )
            return None

        try:
            result = await self._dq_report_service.generate_reports(
                context=context,
                bronze_config=self._bronze_dq_config,
                silver_config=self._silver_dq_config,
                gold_config=self._gold_dq_config,
            )
            if result.any_generated:
                self._logger.info(
                    "dq_reports_completed",
                    reports_count=result.reports_count,
                    bronze_enabled=result.bronze_enabled,
                    silver_enabled=result.silver_enabled,
                    gold_enabled=result.gold_enabled,
                )
            return result
        except self._warning_allowlist as error:
            if self._is_strict_validation_enabled():
                self._logger.error(
                    "dq_report_generation_failed",
                    error=str(error),
                    error_type=type(error).__name__,
                    reason="dq_report_generation_failed_strict_mode",
                    reason_code="POSTRUN_DQ_REPORT_GENERATION_FAILED_STRICT",
                    strict_mode=True,
                )
                raise
            self._logger.error(
                "dq_report_generation_failed",
                error=str(error),
                error_type=type(error).__name__,
                reason="dq_report_generation_failed_warning_mode",
                reason_code="POSTRUN_DQ_REPORT_GENERATION_FAILED_WARNING",
                strict_mode=False,
            )
            self._logger.warning(
                "dq_report_generation_failed",
                error=str(error),
                error_type=type(error).__name__,
                reason="dq_report_generation_failed_warning_mode",
                reason_code="POSTRUN_DQ_REPORT_GENERATION_FAILED_WARNING",
                strict_mode=False,
            )
            return None
        except BioETLError as error:
            if self._is_strict_validation_enabled():
                self._logger.error(
                    "dq_report_generation_failed",
                    error=str(error),
                    error_type=type(error).__name__,
                    reason="dq_report_generation_failed_strict_mode",
                    reason_code="POSTRUN_DQ_REPORT_GENERATION_FAILED_STRICT",
                    strict_mode=True,
                )
                raise
            self._logger.error(
                "dq_report_generation_failed",
                error=str(error),
                error_type=type(error).__name__,
                reason="dq_report_generation_failed_warning_mode",
                reason_code="POSTRUN_DQ_REPORT_GENERATION_FAILED_WARNING",
                strict_mode=False,
            )
            self._logger.warning(
                "dq_report_generation_failed",
                error=str(error),
                error_type=type(error).__name__,
                reason="dq_report_generation_failed_warning_mode",
                reason_code="POSTRUN_DQ_REPORT_GENERATION_FAILED_WARNING",
                strict_mode=False,
            )
            return None

    def _is_strict_validation_enabled(self) -> bool:
        """Return True only when strict validation is explicitly enabled."""
        return getattr(self._runtime, "strict_validation", False) is True


__all__ = ["PostrunDQReportService"]
