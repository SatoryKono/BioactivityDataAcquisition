"""Cleanup orchestration extracted from PostrunService."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, TracingPort


class PostrunCleanupService:
    """Handles shutdown-time cleanup without masking failures."""

    def __init__(
        self,
        *,
        logger: LoggerPort,
        warning_allowlist: tuple[type[BaseException], ...],
    ) -> None:
        self._logger = logger
        self._warning_allowlist = warning_allowlist

    async def cleanup_tracer(self, tracer: TracingPort | None) -> None:
        """Close tracing resources with warning-mode fallback.

        Args:
            tracer: Optional tracing port to close. If None, the method returns immediately.
        """
        await asyncio.sleep(0)
        if tracer is None:
            return
        try:
            tracer.close()
            self._logger.debug("Tracer closed successfully")
        except self._warning_allowlist as error:
            self._logger.warning(
                "Failed to close tracer",
                error=str(error),
                error_type=type(error).__name__,
                reason="tracer_close_failed",
                reason_code="POSTRUN_TRACER_CLOSE_FAILED",
            )


__all__ = ["PostrunCleanupService"]
