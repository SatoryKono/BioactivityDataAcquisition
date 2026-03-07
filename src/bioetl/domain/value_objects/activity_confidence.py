"""Confidence score value object for activity records."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ConfidenceScore"]


@dataclass(frozen=True, slots=True)
class ConfidenceScore:
    """ChEMBL assay confidence score (0-9)."""

    value: int

    def __post_init__(self) -> None:
        """Validate confidence score invariants."""
        if not isinstance(self.value, int):
            raise TypeError(
                f"ConfidenceScore must be int, got {type(self.value).__name__}"
            )
        if not 0 <= self.value <= 9:
            raise ValueError(f"Confidence score must be 0-9, got {self.value}")

    @classmethod
    def from_value(cls, value: int | str | None) -> ConfidenceScore | None:
        """Create from raw value, returning None if input is None.

        Args:
            value: Raw confidence score as integer, string, or None.

        Returns:
            ConfidenceScore instance, or None if value is None.
        """
        if value is None:
            return None
        if isinstance(value, str):
            value = int(value.strip())
        return cls(value=value)

    @property
    def is_high_confidence(self) -> bool:
        """Check if this is a high-confidence assignment (7-9)."""
        return self.value >= 7

    @property
    def is_molecular_target(self) -> bool:
        """Check if a molecular target is assigned (>= 3)."""
        return self.value >= 3

    @property
    def description(self) -> str:
        """Get human-readable description of the confidence level."""
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
