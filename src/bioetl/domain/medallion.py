"""Medallion layer policies (Domain layer - pure logic, no I/O)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, ClassVar

from bioetl.domain.exceptions import PolicyViolationError

if TYPE_CHECKING:
    from bioetl.domain.types import RunType


class Layer(StrEnum):
    """Medallion architecture layers."""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


class WriteMode(StrEnum):
    """Write mode for data operations."""

    APPEND = "append"
    MERGE = "merge"
    OVERWRITE = "overwrite"


class SilverWriteMode(StrEnum):
    """Allowed write modes for Silver layer."""

    MERGE = "merge"
    APPEND = "append"
    DELETE = "delete"

    @classmethod
    def from_string(cls, value: str) -> SilverWriteMode:
        """Convert string to SilverWriteMode with validation.

        Args:
            value: String value to convert (e.g., 'merge', 'append', 'delete').

        Returns:
            Matching SilverWriteMode enum member.
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid = ", ".join(m.value for m in cls)
            raise ValueError(
                f"Invalid Silver write mode: '{value}'. Valid modes: {valid}"
            ) from None


class GoldWriteMode(StrEnum):
    """Allowed write modes for Gold layer."""

    APPEND = "append"
    SCD2 = "scd2"
    OVERWRITE = "overwrite"

    @classmethod
    def from_string(cls, value: str) -> GoldWriteMode:
        """Convert string to GoldWriteMode with validation.

        Args:
            value: String value to convert (e.g., 'append', 'scd2', 'overwrite').

        Returns:
            Matching GoldWriteMode enum member.
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid = ", ".join(m.value for m in cls)
            raise ValueError(
                f"Invalid Gold write mode: '{value}'. Valid modes: {valid}"
            ) from None


class WriteModePolicy:
    """Validates write mode compliance with medallion layer policies."""

    ALLOWED_MODES: ClassVar[dict[Layer, set[WriteMode]]] = {
        Layer.BRONZE: {WriteMode.APPEND},
        Layer.SILVER: {WriteMode.MERGE, WriteMode.APPEND},
        Layer.GOLD: {WriteMode.MERGE, WriteMode.OVERWRITE, WriteMode.APPEND},
    }

    def validate(self, layer: Layer, mode: WriteMode) -> None:
        """Validate that write mode is allowed for the layer.

        Args:
            layer: Medallion layer to validate against (BRONZE, SILVER, or GOLD).
            mode: Write mode to check for compliance with layer policy.
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


class LoadingStrategy(StrEnum):
    """Loading strategy for pipeline data extraction."""

    FULL_SCAN_ONLY = "full_scan_only"
    """Full scan on each run. No checkpoint resume. Deduplication via content_hash."""

    @property
    def allows_checkpoint_resume(self) -> bool:
        """Check if this strategy allows checkpoint-based resume."""
        return False

    @classmethod
    def from_string(cls, value: str) -> LoadingStrategy:
        """Convert string to LoadingStrategy with validation.

        Args:
            value: String value to convert (e.g., 'full_scan_only').

        Returns:
            Matching LoadingStrategy enum member.
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid = ", ".join(s.value for s in cls)
            raise ValueError(
                f"Invalid loading strategy: '{value}'. Valid strategies: {valid}"
            ) from None


class ClearPolicy(StrEnum):
    """Policy for clearing medallion layers."""

    NEVER = "never"
    """Incremental runs - merge/upsert without clearing."""

    SILVER_ONLY = "silver"
    """Clear Silver only, preserve Gold."""

    SILVER_AND_GOLD = "both"
    """Full clear for rebuild/backfill."""


@dataclass(frozen=True, slots=True)
class MedallionPolicy:
    """Encapsulates medallion layer lifecycle policies."""

    clear_policy: ClearPolicy = ClearPolicy.NEVER
    vacuum_enabled: bool = False
    vacuum_retention_days: int = 7

    @classmethod
    def for_run_type(cls, run_type: RunType) -> MedallionPolicy:
        """Create policy based on run type.

        Args:
            run_type: Type of pipeline run (INCREMENTAL, BACKFILL, or REBUILD).

        Returns:
            MedallionPolicy with SILVER_AND_GOLD clear for rebuild/backfill, NEVER otherwise.
        """
        from bioetl.domain.types import RunType

        if run_type in (RunType.REBUILD, RunType.BACKFILL):
            return cls(clear_policy=ClearPolicy.SILVER_AND_GOLD)
        return cls(clear_policy=ClearPolicy.NEVER)

    @property
    def should_clear_silver(self) -> bool:
        """Check if Silver layer should be cleared."""
        return self.clear_policy in (
            ClearPolicy.SILVER_ONLY,
            ClearPolicy.SILVER_AND_GOLD,
        )

    @property
    def should_clear_gold(self) -> bool:
        """Check if Gold layer should be cleared."""
        return self.clear_policy == ClearPolicy.SILVER_AND_GOLD


__all__ = [
    "ClearPolicy",
    "GoldWriteMode",
    "Layer",
    "LoadingStrategy",
    "MedallionPolicy",
    "SilverWriteMode",
    "WriteMode",
    "WriteModePolicy",
]
