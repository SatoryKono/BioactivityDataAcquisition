"""DQ report orchestration extracted from PostrunService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.postrun._failure_policy import (
    PostrunFailureHandlingMixin,
    PostrunFailurePolicySpec,
)
from bioetl.domain.exceptions import BioETLError

if TYPE_CHECKING:
    from bioetl.application.services.dq_report_service import (
        DQReportContext,
        DQReportResult,
        DQReportService,
    )
    from bioetl.domain.config import RuntimeConfig
    from bioetl.domain.ports import (
        BronzeDQConfigPort,
        GoldDQConfigPort,
        LoggerPort,
        SilverDQConfigPort,
    )


class PostrunDQReportService(PostrunFailureHandlingMixin):
    """Orchestrates optional DQ report generation with strict/warning mode."""
    _FAILURE_POLICY = PostrunFailurePolicySpec(
        event="dq_report_generation_failed",
        strict_reason="dq_report_generation_failed_strict_mode",
        strict_reason_code="POSTRUN_DQ_REPORT_GENERATION_FAILED_STRICT",
        warning_reason="dq_report_generation_failed_warning_mode",
        warning_reason_code="POSTRUN_DQ_REPORT_GENERATION_FAILED_WARNING",
    )
    def __init__(
        self,
        *,
        logger: LoggerPort,
        runtime: RuntimeConfig,
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
        self._handled_failures: tuple[type[BaseException], ...] = (
            *warning_allowlist,
            BioETLError,
        )
    async def generate_reports(
        self,
        context: DQReportContext | None,
    ) -> DQReportResult | None:
        """Generate DQ reports when service/config/context are available.
        Args:
            context: DQ report context with run metadata and table references.
                If None, report generation is skipped and None is returned.
        Returns:
            DQReportResult with generation status for each layer, or None if
            the DQ report service is not configured or context was not provided.
        """
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
        except self._handled_failures as error:
            self._handle_allowlisted_failure(
                error,
                emit_warning_error_log=True,
            )
            return None


__all__ = ["PostrunDQReportService"]
