"""Activity-related Value Objects for BioETL domain.

Contains Value Objects for bioactivity measurements:
- ConfidenceScore: ChEMBL assay confidence (0-9)
- RelationOperator: Comparison operators (=, <, >, <=, >=)
- ActivityValue: Composite value with magnitude, unit, and relation

These Value Objects encapsulate validation and comparison logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.value_objects.activity_values import Concentration


class RelationOperator(str, Enum):
    """Comparison operators for activity values.

    Used to express the relationship between a measured value
    and its reported magnitude (e.g., IC50 > 10 μM).

    Invariants:
        - Only valid comparison operators are allowed
        - Normalized to standard symbols
    """

    EQUAL = "="
    LESS_THAN = "<"
    LESS_THAN_OR_EQUAL = "<="
    GREATER_THAN = ">"
    GREATER_THAN_OR_EQUAL = ">="
    APPROXIMATELY = "~"

    @classmethod
    def from_string(cls, s: str | None) -> RelationOperator | None:
        """Parse relation operator from string.

        Args:
            s: Operator string (e.g., "=", "<", ">=").

        Returns:
            Corresponding RelationOperator or None if input is None.

        Raises:
            ValueError: If operator string is not recognized.
        """
        if s is None:
            return None

        normalized = s.strip()
        if not normalized:
            return None

        # Map variations to canonical forms
        operator_map = {
            "=": cls.EQUAL,
            "==": cls.EQUAL,
            "<": cls.LESS_THAN,
            "<=": cls.LESS_THAN_OR_EQUAL,
            "=<": cls.LESS_THAN_OR_EQUAL,
            ">": cls.GREATER_THAN,
            ">=": cls.GREATER_THAN_OR_EQUAL,
            "=>": cls.GREATER_THAN_OR_EQUAL,
            "~": cls.APPROXIMATELY,
            "≈": cls.APPROXIMATELY,
            "approx": cls.APPROXIMATELY,
        }

        operator = operator_map.get(normalized.lower())
        if operator is None:
            raise ValueError(f"Unknown relation operator: {s!r}")

        return operator

    def is_exact(self) -> bool:
        """Check if this is an exact equality operator.

        Returns:
            True for "=" operator only.
        """
        return self == RelationOperator.EQUAL

    def is_upper_bound(self) -> bool:
        """Check if this represents an upper bound.

        Returns:
            True for "<" and "<=" operators.
        """
        return self in {RelationOperator.LESS_THAN, RelationOperator.LESS_THAN_OR_EQUAL}

    def is_lower_bound(self) -> bool:
        """Check if this represents a lower bound.

        Returns:
            True for ">" and ">=" operators.
        """
        return self in {
            RelationOperator.GREATER_THAN,
            RelationOperator.GREATER_THAN_OR_EQUAL,
        }


@dataclass(frozen=True, slots=True)
class ConfidenceScore:
    """ChEMBL assay confidence score (0-9).

    The confidence score indicates the reliability of the
    target-activity relationship:
    - 9: Direct single protein target assigned
    - 8: Homologous single protein target assigned
    - 7: Direct complex protein target assigned
    - 6: Homologous complex target assigned
    - 5: Multiple direct targets assigned
    - 4: Multiple homologous targets assigned
    - 3: Target class assigned (e.g., kinase)
    - 2: Unchecked target assigned
    - 1: Phenotypic (no molecular target)
    - 0: No target assigned

    Invariants:
        - value must be integer 0-9
    """

    value: int

    def __post_init__(self) -> None:
        """Validate confidence score invariants."""
        if not isinstance(self.value, int):
            raise TypeError(f"ConfidenceScore must be int, got {type(self.value).__name__}")
        if not 0 <= self.value <= 9:
            raise ValueError(f"Confidence score must be 0-9, got {self.value}")

    @classmethod
    def from_value(cls, value: int | str | None) -> ConfidenceScore | None:
        """Create from raw value, returning None if input is None.

        Args:
            value: Raw confidence score value.

        Returns:
            ConfidenceScore or None if input is None.

        Raises:
            ValueError: If value is invalid.
        """
        if value is None:
            return None
        if isinstance(value, str):
            value = int(value.strip())
        return cls(value=value)

    @property
    def is_high_confidence(self) -> bool:
        """Check if this is a high-confidence assignment (7-9).

        High confidence means direct or homologous single/complex
        protein target has been assigned.

        Returns:
            True if confidence >= 7.
        """
        return self.value >= 7

    @property
    def is_molecular_target(self) -> bool:
        """Check if a molecular target is assigned (>= 3).

        Scores >= 3 indicate at least a target class was assigned,
        vs. purely phenotypic or no target.

        Returns:
            True if confidence >= 3.
        """
        return self.value >= 3

    @property
    def description(self) -> str:
        """Get human-readable description of the confidence level.

        Returns:
            Description string for the confidence score.
        """
        descriptions = {
            9: "Direct single protein target",
            8: "Homologous single protein target",
            7: "Direct complex protein target",
            6: "Homologous complex target",
            5: "Multiple direct targets",
            4: "Multiple homologous targets",
            3: "Target class assigned",
            2: "Unchecked target",
            1: "Phenotypic (no molecular target)",
            0: "No target assigned",
        }
        return descriptions.get(self.value, f"Unknown ({self.value})")

    def __str__(self) -> str:
        """Return string representation."""
        return str(self.value)

    def __eq__(self, other: object) -> bool:
        """Compare equality by value."""
        if not isinstance(other, ConfidenceScore):
            return NotImplemented
        return self.value == other.value

    def __hash__(self) -> int:
        """Hash based on value."""
        return hash(self.value)

    def __lt__(self, other: ConfidenceScore) -> bool:
        """Compare for ordering."""
        if not isinstance(other, ConfidenceScore):
            return NotImplemented
        return self.value < other.value


@dataclass(frozen=True, slots=True)
class ActivityValue:
    """Bioactivity measurement with value, unit, and relation.

    A composite Value Object representing a complete activity measurement,
    such as "IC50 = 100 nM" or "EC50 > 10 μM".

    This encapsulates:
    - The numeric value (magnitude)
    - The unit (concentration unit)
    - The relation operator (exact, upper/lower bound)

    Invariants:
        - value must be non-negative
        - unit must be a valid concentration unit string
        - relation defaults to "=" if not specified
    """

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
            value: Numeric value.
            unit: Unit string.
            relation: Optional relation operator string.

        Returns:
            ActivityValue or None if essential fields are missing.
        """
        if value is None or unit is None:
            return None

        rel = RelationOperator.from_string(relation) or RelationOperator.EQUAL

        return cls(value=value, unit=unit.strip(), relation=rel)

    def to_concentration(self) -> Concentration:
        """Convert to Concentration Value Object.

        Returns:
            Concentration with the same value and unit.

        Raises:
            ValueError: If unit is not a recognized concentration unit.
        """
        from bioetl.domain.value_objects.activity_values import (
            Concentration,
            ConcentrationUnit,
        )

        conc_unit = ConcentrationUnit.from_string(self.unit)
        return Concentration(value=self.value, unit=conc_unit)

    @property
    def is_exact(self) -> bool:
        """Check if this is an exact measurement (relation = "=").

        Returns:
            True if relation is EQUAL.
        """
        return self.relation.is_exact()

    @property
    def is_bounded(self) -> bool:
        """Check if this is a bounded measurement (< or >).

        Returns:
            True if relation is an inequality.
        """
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
