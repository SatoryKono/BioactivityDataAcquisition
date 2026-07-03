"""Activity measurement value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.domain.value_objects.activity_relation import RelationOperator

if TYPE_CHECKING:
    from bioetl.domain.value_objects.activity_concentration import Concentration

__all__ = ["ActivityValue"]


@dataclass(frozen=True, slots=True)
class ActivityValue:
    """Bioactivity measurement with value, unit, and relation."""

    value: float
    unit: str
    relation: RelationOperator = RelationOperator.EQUAL

    def __post_init__(self) -> None:
        """Validate activity value invariants."""
        if self.value < 0:
            raise ValueError(f"Activity value cannot be negative: {self.value}")
        if not self.unit:
            raise ValueError("Activity unit cannot be empty")

    @classmethod
    def from_raw(
        cls,
        value: float | None,
        unit: str | None,
        relation: str | None = None,
    ) -> ActivityValue | None:
        """Create from raw values, returning None if value or unit is None.

        Args:
            value: Numeric activity measurement. Returns None if None.
            unit: Unit string (e.g., 'nM', 'uM'). Returns None if None.
            relation: Optional comparison operator string (e.g., '=', '<'). Defaults to EQUAL.

        Returns:
            ActivityValue instance, or None if value or unit is absent.
        """
        if value is None or unit is None:
            return None
        rel = RelationOperator.from_string(relation) or RelationOperator.EQUAL
        return cls(value=value, unit=unit.strip(), relation=rel)

    def to_concentration(self) -> Concentration:
        """Convert to Concentration Value Object."""
        from bioetl.domain.value_objects.activity_concentration import (
            Concentration,
            ConcentrationUnit,
        )

        conc_unit = ConcentrationUnit.from_string(self.unit)
        return Concentration(value=self.value, unit=conc_unit)

    @property
    def is_exact(self) -> bool:
        """Check if this is an exact measurement (relation = '=')."""
        return self.relation.is_exact()

    @property
    def is_bounded(self) -> bool:
        """Check if this is a bounded measurement (< or >)."""
        return not self.is_exact

    def __str__(self) -> str:
        """Return string representation like '= 100 nM'."""
        return f"{self.relation.value} {self.value} {self.unit}"

    def __eq__(self, other: object) -> bool:
        """Compare equality by all fields."""
        if not isinstance(other, ActivityValue):
            return NotImplemented
        return (
            self.value == other.value
            and self.unit == other.unit
            and self.relation == other.relation
        )

    def __hash__(self) -> int:
        """Hash based on all fields."""
        return hash((self.value, self.unit, self.relation))
