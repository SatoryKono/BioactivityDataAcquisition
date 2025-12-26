"""Lifecycle Orchestrator for medallion layer operations.

Application Service that orchestrates clearing of Silver/Gold layers based on run type.
Extracted from PipelineRunner to follow Single Responsibility Principle.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.services.medallion_lifecycle import ClearResult
from bioetl.domain.medallion import MedallionPolicy

if TYPE_CHECKING:
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.ports import LoggerPort


@dataclass(frozen=True, slots=True)
class ClearDecision:
    """Result of lifecycle clear operation with policy context.

    Attributes:
        result: ClearResult from lifecycle service.
        policy: MedallionPolicy used for the operation.
    """

    result: ClearResult
    policy: MedallionPolicy


class LifecycleOrchestrator:
    """Orchestrates medallion layer lifecycle operations.

    Responsibilities:
    - Determine clear policy based on run type
    - Delegate clearing to MedallionLifecycleService
    - Log clear decisions

    Attributes:
        _config: Pipeline configuration.
        _runtime: Runtime configuration.
        _logger: Structured logger.
        _lifecycle_service: Medallion lifecycle service.
    """

    def __init__(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        logger: LoggerPort,
        lifecycle_service: MedallionLifecycleService,
    ) -> None:
        """Initialize lifecycle orchestrator.

        Args:
            config: Pipeline configuration.
            runtime: Runtime configuration.
            logger: Structured logger.
            lifecycle_service: Medallion lifecycle service for clearing.
        """
        self._config = config
        self._runtime = runtime
        self._logger = logger
        self._lifecycle_service = lifecycle_service

    async def clear_for_run(self) -> ClearDecision:
        """Clear exports based on run type policy.

        Delegates clear decision to MedallionPolicy (Single Source of Truth).
        The policy determines which layers to clear based on run type:
        - REBUILD/BACKFILL: Clear both Silver and Gold
        - INCREMENTAL: Never clear (merge/upsert behavior)

        Returns:
            ClearDecision with result and policy used.
        """
        policy = MedallionPolicy.for_run_type(self._runtime.run_type)

        gold_table = (
            self._config.gold_table
            or f"{self._config.provider}.{self._config.entity_type}"
        )

        result = await self._lifecycle_service.clear(
            policy=policy,
            silver_table=self._config.silver_table,
            gold_table=gold_table,
            dry_run=self._runtime.dry_run,
        )

        self._logger.debug(
            "Medallion clear completed",
            extra={
                "run_type": self._runtime.run_type.value,
                "clear_policy": policy.clear_policy.value,
                "silver_cleared": result.silver_cleared,
                "gold_cleared": result.gold_cleared,
            },
        )

        return ClearDecision(result=result, policy=policy)


__all__ = ["ClearDecision", "LifecycleOrchestrator"]
