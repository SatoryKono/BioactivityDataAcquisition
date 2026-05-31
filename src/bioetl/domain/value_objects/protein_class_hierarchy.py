"""Protein classification hierarchy value objects for ChEMBL targets."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "ProteinClassHierarchy",
    "ProteinClassLevel",
    "ProteinClassificationResolutionError",
]


class ProteinClassificationResolutionError(ValueError):
    """Raised when a protein classification hierarchy cannot be resolved."""


@dataclass(frozen=True, slots=True)
class ProteinClassLevel:
    """One optional level in a protein classification hierarchy."""

    id: int | None
    name: str | None
    desc: str | None

    def __post_init__(self) -> None:
        if self.id is not None and self.id < 1:
            raise ValueError(f"protein class level id must be positive, got {self.id}")
        if self.id is None and (self.name is not None or self.desc is not None):
            raise ValueError("empty protein class levels must not carry name or desc")

    @classmethod
    def empty(cls) -> ProteinClassLevel:
        """Return a canonical empty level."""
        return cls(id=None, name=None, desc=None)

    @property
    def is_empty(self) -> bool:
        """Return True when the level is absent from the hierarchy."""
        return self.id is None


@dataclass(frozen=True, slots=True)
class ProteinClassHierarchy:
    """L1-L5 projection of a protein classification hierarchy."""

    l1: ProteinClassLevel
    l2: ProteinClassLevel
    l3: ProteinClassLevel
    l4: ProteinClassLevel
    l5: ProteinClassLevel
    leaf_id: int

    def __post_init__(self) -> None:
        if self.leaf_id < 1:
            raise ValueError(f"leaf_id must be positive, got {self.leaf_id}")
        self._validate_no_gaps()

    def _validate_no_gaps(self) -> None:
        seen_empty = False
        for level in self.levels:
            if level.is_empty:
                seen_empty = True
                continue
            if seen_empty:
                raise ValueError("protein class hierarchy levels must be contiguous")

    @property
    def levels(self) -> tuple[ProteinClassLevel, ...]:
        """Return levels in stable L1-L5 order."""
        return (self.l1, self.l2, self.l3, self.l4, self.l5)

    @property
    def level_ids(self) -> tuple[int | None, ...]:
        """Return level identifiers for deterministic hashing/projection."""
        return tuple(level.id for level in self.levels)
