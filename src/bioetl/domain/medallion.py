"""Medallion layer policies (Domain layer - pure logic, no I/O).

Implements medallion architecture lifecycle policies per RULES.md §2.1-2.3.
These are pure domain objects with no dependencies on infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, ClassVar

from bioetl.domain.exceptions import PolicyViolationError

if TYPE_CHECKING:
    from bioetl.domain.types import RunType


class Layer(str, Enum):
    """Medallion architecture layers.

    Attributes:
        BRONZE: Raw data layer (immutable, append-only).
        SILVER: Cleansed/normalized data layer.
        GOLD: Business-ready aggregated data layer.
    """

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


class WriteMode(str, Enum):
    """Write mode for data operations.

    Attributes:
        APPEND: Add new records without modifying existing.
        MERGE: Upsert records based on key (Delta Lake merge).
        OVERWRITE: Replace entire dataset.
    """

    APPEND = "append"
    MERGE = "merge"
    OVERWRITE = "overwrite"


class SilverWriteMode(str, Enum):
    """Allowed write modes for Silver layer.

    Domain enum consolidating Silver layer write semantics.
    Used by domain/config.py and infrastructure storage adapters.

    Values:
        MERGE: Upsert records based on primary keys (default, idempotent)
        APPEND: Add records without deduplication
        DELETE: Delete and replace all data in the table (rebuild only)
    """

    MERGE = "merge"
    APPEND = "append"
    DELETE = "delete"

    @classmethod
    def from_string(cls, value: str) -> SilverWriteMode:
        """Convert string to SilverWriteMode with validation.

        Args:
            value: String value (e.g., "merge", "append", "delete")

        Returns:
            Corresponding SilverWriteMode enum value

        Raises:
            ValueError: If value is not a valid Silver write mode
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid = ", ".join(m.value for m in cls)
            raise ValueError(
                f"Invalid Silver write mode: '{value}'. Valid modes: {valid}"
            ) from None


class GoldWriteMode(str, Enum):
    """Allowed write modes for Gold layer.

    Domain enum consolidating Gold layer write semantics.
    Used by domain/config.py and infrastructure storage adapters.

    Values:
        APPEND: Add records without deduplication (default, incremental)
        SCD2: Slowly Changing Dimension Type 2 (history tracking)
        OVERWRITE: Replace all data in the table (rebuild only, requires confirmation)
    """

    APPEND = "append"
    SCD2 = "scd2"
    OVERWRITE = "overwrite"

    @classmethod
    def from_string(cls, value: str) -> GoldWriteMode:
        """Convert string to GoldWriteMode with validation.

        Args:
            value: String value (e.g., "append", "scd2", "overwrite")

        Returns:
            Corresponding GoldWriteMode enum value

        Raises:
            ValueError: If value is not a valid Gold write mode
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid = ", ".join(m.value for m in cls)
            raise ValueError(
                f"Invalid Gold write mode: '{value}'. Valid modes: {valid}"
            ) from None


class WriteModePolicy:
    """Validates write mode compliance with medallion layer policies.

    Enforces medallion architecture invariants:
    - Bronze: APPEND only (raw data immutability)
    - Silver: APPEND or MERGE (idempotent upserts)
    - Gold: MERGE, OVERWRITE, or APPEND (derived data)

    Example:
        >>> policy = WriteModePolicy()
        >>> policy.validate(Layer.BRONZE, WriteMode.APPEND)  # OK
        >>> policy.validate(Layer.BRONZE, WriteMode.OVERWRITE)  # Raises
        Traceback (most recent call last):
            ...
        PolicyViolationError: bronze does not allow overwrite. Allowed: {append}
    """

    ALLOWED_MODES: ClassVar[dict[Layer, set[WriteMode]]] = {
        Layer.BRONZE: {WriteMode.APPEND},
        Layer.SILVER: {WriteMode.MERGE, WriteMode.APPEND},
        Layer.GOLD: {WriteMode.MERGE, WriteMode.OVERWRITE, WriteMode.APPEND},
    }

    def validate(self, layer: Layer, mode: WriteMode) -> None:
        """Validate that write mode is allowed for the layer.

        Args:
            layer: Target medallion layer.
            mode: Requested write mode.

        Raises:
            PolicyViolationError: If mode is not allowed for the layer.
        """
        allowed = self.ALLOWED_MODES[layer]
        if mode not in allowed:
            allowed_names = (
                "{"
                + ", ".join(m.value for m in sorted(allowed, key=lambda x: x.value))
                + "}"
            )
            raise PolicyViolationError(
                f"{layer.value} does not allow {mode.value}. Allowed: {allowed_names}"
            )


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
