"""Relation operator value object for activity measurements."""

from __future__ import annotations

from enum import StrEnum

__all__ = ["RelationOperator"]


class RelationOperator(StrEnum):
    """Comparison operators for activity values."""

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
            s: Operator symbol such as '=', '<', '<=', '>', '>=', '~'. None is accepted.

        Returns:
            Corresponding RelationOperator, or None if input is None or empty.
        """
        if s is None:
            return None
        normalized = s.strip()
        if not normalized:
            return None

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
        """Check if this is an exact equality operator."""
        return self == RelationOperator.EQUAL

    def is_upper_bound(self) -> bool:
        """Check if this represents an upper bound."""
        return self in {RelationOperator.LESS_THAN, RelationOperator.LESS_THAN_OR_EQUAL}

    def is_lower_bound(self) -> bool:
        """Check if this represents a lower bound."""
        return self in {
            RelationOperator.GREATER_THAN,
            RelationOperator.GREATER_THAN_OR_EQUAL,
        }
