"""Medallion layer policies (Domain layer - pure logic, no I/O).

Implements medallion architecture lifecycle policies per RULES.md §2.1-2.3.
These are pure domain objects with no dependencies on infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.types import RunType


class ClearPolicy(str, Enum):
    """Policy for clearing medallion layers.

    Determines which layers should be cleared before a pipeline run.

    Attributes:
        NEVER: Never clear (incremental runs) - merge/upsert behavior.
        SILVER_ONLY: Clear Silver, preserve Gold.
        SILVER_AND_GOLD: Clear both layers (rebuild/backfill runs).
    """

    NEVER = "never"
    """Инкрементальные запуски - merge/upsert без очистки."""

    SILVER_ONLY = "silver"
    """Очистить только Silver, сохранить Gold."""

    SILVER_AND_GOLD = "both"
    """Полная очистка для rebuild/backfill."""


@dataclass(frozen=True, slots=True)
class MedallionPolicy:
    """Encapsulates medallion layer lifecycle policies.

    Pure domain object that determines lifecycle behavior based on run type.
    No I/O operations - only policy decisions.

    Attributes:
        clear_policy: Which layers to clear before run.
        vacuum_enabled: Whether vacuum is enabled for this run.
        vacuum_retention_days: Days to retain for vacuum operation.

    Example:
        >>> from bioetl.domain.types import RunType
        >>> policy = MedallionPolicy.for_run_type(RunType.REBUILD)
        >>> policy.should_clear_silver
        True
        >>> policy.should_clear_gold
        True
    """

    clear_policy: ClearPolicy = ClearPolicy.NEVER
    vacuum_enabled: bool = False
    vacuum_retention_days: int = 7

    @classmethod
    def for_run_type(cls, run_type: RunType) -> MedallionPolicy:
        """Create policy based on run type.

        Factory method that maps run types to appropriate policies.

        Args:
            run_type: The type of pipeline run.

        Returns:
            MedallionPolicy configured for the run type.

        Medallion invariants:
            - REBUILD: Clear both Silver and Gold (full refresh)
            - BACKFILL: Clear both Silver and Gold (historical load)
            - INCREMENTAL: Never clear (merge/upsert)
        """
        from bioetl.domain.types import RunType

        if run_type in (RunType.REBUILD, RunType.BACKFILL):
            return cls(clear_policy=ClearPolicy.SILVER_AND_GOLD)
        return cls(clear_policy=ClearPolicy.NEVER)

    @property
    def should_clear_silver(self) -> bool:
        """Check if Silver layer should be cleared.

        Returns:
            True if Silver should be cleared before run.
        """
        return self.clear_policy in (
            ClearPolicy.SILVER_ONLY,
            ClearPolicy.SILVER_AND_GOLD,
        )

    @property
    def should_clear_gold(self) -> bool:
        """Check if Gold layer should be cleared.

        Returns:
            True if Gold should be cleared before run.
        """
        return self.clear_policy == ClearPolicy.SILVER_AND_GOLD
