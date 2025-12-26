"""Medallion layer write mode policies.

Validates that write operations comply with medallion architecture rules.
Per RULES.md §3 (Medallion Architecture):
- Bronze: Append-only (immutable raw data)
- Silver: Merge/Upsert or Append (idempotent transforms)
- Gold: Merge or Overwrite (aggregated/derived data)
"""

from __future__ import annotations

from enum import Enum
from typing import ClassVar

from bioetl.domain.exceptions import PolicyViolationError


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


class MedallionPolicy:
    """Validates write mode compliance with medallion layer policies.

    Enforces medallion architecture invariants:
    - Bronze: APPEND only (raw data immutability)
    - Silver: APPEND or MERGE (idempotent upserts)
    - Gold: MERGE or OVERWRITE (derived data)

    Example:
        >>> policy = MedallionPolicy()
        >>> policy.validate(Layer.BRONZE, WriteMode.APPEND)  # OK
        >>> policy.validate(Layer.BRONZE, WriteMode.OVERWRITE)  # Raises
        Traceback (most recent call last):
            ...
        PolicyViolationError: bronze does not allow overwrite. Allowed: {append}
    """

    ALLOWED_MODES: ClassVar[dict[Layer, set[WriteMode]]] = {
        Layer.BRONZE: {WriteMode.APPEND},
        Layer.SILVER: {WriteMode.MERGE, WriteMode.APPEND},
        Layer.GOLD: {WriteMode.MERGE, WriteMode.OVERWRITE},
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
            allowed_names = "{" + ", ".join(m.value for m in sorted(allowed, key=lambda x: x.value)) + "}"
            raise PolicyViolationError(
                f"{layer.value} does not allow {mode.value}. Allowed: {allowed_names}"
            )
