"""Progress and stop-decision service for dependency orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.composite.config_models import DependencyConfig
from bioetl.domain.composite.result import DependencyResult
from bioetl.domain.ports import LoggerPort

__all__ = ["DependencyProgressService"]


@dataclass(frozen=True, slots=True)
class DependencyProgressService:
    """Encapsulates progress bookkeeping for dependency execution."""

    logger: LoggerPort

    def maybe_store_completed_skip(
        self,
        *,
        dependency: DependencyConfig,
        completed: frozenset[str],
        results: dict[str, DependencyResult],
    ) -> bool:
        """Store skipped result for completed dependency and return handled flag."""
        if dependency.pipeline not in completed:
            return False
        self.logger.debug(
            "Skipping completed dependency",
            dependency=dependency.pipeline,
        )
        results[dependency.pipeline] = DependencyResult.skipped(
            pipeline_name=dependency.pipeline,
            reason="Already completed (resumed from checkpoint)",
        )
        return True

    def should_stop_after_result(
        self,
        *,
        dependency: DependencyConfig,
        result: DependencyResult,
    ) -> bool:
        """Return True when required dependency failure must stop execution."""
        if not dependency.required or result.is_success:
            return False
        self.logger.error(
            "Required dependency failed, stopping",
            dependency=dependency.pipeline,
            status=result.status.value,
            error=result.error_message,
        )
        return True
