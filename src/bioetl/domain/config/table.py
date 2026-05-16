"""Table configuration object.

Defines the TableConfig value object for database table and key settings.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from bioetl.domain.config._converters import convert_write_mode, freeze_sequences
from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode

IdempotencyContract = Literal[
    "merge_upsert",
    "scd2",
    "overwrite_rebuild",
    "append_log",
    "partition_append_with_stable_partition_key",
    "occurrence_only",
    "disallowed",
]

IDEMPOTENCY_CONTRACT_VALUES: frozenset[str] = frozenset(
    {
        "merge_upsert",
        "scd2",
        "overwrite_rebuild",
        "append_log",
        "partition_append_with_stable_partition_key",
        "occurrence_only",
        "disallowed",
    }
)
APPEND_SAFE_IDEMPOTENCY_CONTRACTS: frozenset[str] = frozenset(
    {
        "append_log",
        "partition_append_with_stable_partition_key",
        "occurrence_only",
    }
)

__all__ = [
    "APPEND_SAFE_IDEMPOTENCY_CONTRACTS",
    "IDEMPOTENCY_CONTRACT_VALUES",
    "IdempotencyContract",
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
    silver_idempotency_contract: IdempotencyContract | None = None
    gold_idempotency_contract: IdempotencyContract | None = None
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
        object.__setattr__(
            self,
            "silver_idempotency_contract",
            _normalize_idempotency_contract(self.silver_idempotency_contract),
        )
        object.__setattr__(
            self,
            "gold_idempotency_contract",
            _normalize_idempotency_contract(self.gold_idempotency_contract),
        )


def _normalize_idempotency_contract(
    value: IdempotencyContract | str | None,
) -> IdempotencyContract | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if not normalized:
        return None
    if normalized not in IDEMPOTENCY_CONTRACT_VALUES:
        valid_values = ", ".join(sorted(IDEMPOTENCY_CONTRACT_VALUES))
        raise ValueError(
            f"Invalid idempotency contract: '{value}'. Valid values: {valid_values}"
        )
    return normalized  # type: ignore[return-value]
