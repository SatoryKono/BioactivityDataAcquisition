"""Table configuration object.

Defines the TableConfig value object for database table and key settings.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from bioetl.domain.config._converters import convert_write_mode, freeze_sequences
from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode

__all__ = [
    "TableConfig",
]


@dataclass(frozen=True, slots=True)
class TableConfig:
    """Configuration for database tables and keys.

    All collection fields are immutable tuples to ensure true immutability
    of the frozen dataclass. The __post_init__ converts any incoming lists
    to tuples for backward compatibility.

    Write modes are now typed using domain enums (SilverWriteMode, GoldWriteMode)
    instead of Literal strings for type safety and policy enforcement.
    """

    primary_keys: tuple[str, ...] = ("entity_id",)
    silver_table: str | None = None
    gold_table: str | None = None
    # Write modes using domain enums (R1 refactoring)
    silver_write_mode: SilverWriteMode = SilverWriteMode.MERGE
    gold_write_mode: GoldWriteMode = GoldWriteMode.SCD2
    partition_cols: tuple[str, ...] = ()
    # Schema drift handling for Silver layer
    on_schema_mismatch: Literal["error", "evolve", "ignore"] = "error"

    def __post_init__(self) -> None:
        """Convert incoming values to proper types for immutability."""
        freeze_sequences(self, ("primary_keys", "partition_cols"))
        # Convert string write modes to enums (backward compatibility)
        object.__setattr__(
            self,
            "silver_write_mode",
            convert_write_mode(self.silver_write_mode, SilverWriteMode),
        )
        object.__setattr__(
            self,
            "gold_write_mode",
            convert_write_mode(self.gold_write_mode, GoldWriteMode),
        )
