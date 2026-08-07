"""Protein classification hierarchy value objects for ChEMBL targets."""

from __future__ import annotations

from collections.abc import Iterable
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
        _validate_level_id(self.id)
        _validate_empty_level_payload(self.id, self.name, self.desc)

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
    """Path-first protein classification hierarchy with L1-L5 projection."""

    l1: ProteinClassLevel
    l2: ProteinClassLevel
    l3: ProteinClassLevel
    l4: ProteinClassLevel
    l5: ProteinClassLevel
    leaf_id: int
    path: tuple[ProteinClassLevel, ...] | None = None

    def __post_init__(self) -> None:
        if self.leaf_id < 1:
            raise ValueError(f"leaf_id must be positive, got {self.leaf_id}")
        self._validate_no_gaps()
        self._validate_path()

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
    def path_levels(self) -> tuple[ProteinClassLevel, ...]:
        """Return the full hierarchy path in root-to-leaf order."""
        if self.path is not None:
            return self.path
        return tuple(level for level in self.levels if not level.is_empty)

    @property
    def level_ids(self) -> tuple[int | None, ...]:
        """Return level identifiers for deterministic hashing/projection."""
        return tuple(level.id for level in self.levels)

    @property
    def path_ids(self) -> tuple[int, ...]:
        """Return full hierarchy path identifiers in root-to-leaf order."""
        return tuple(_require_level_id(level.id) for level in self.path_levels)

    @property
    def path_names(self) -> tuple[str, ...]:
        """Return full hierarchy path names aligned to path_ids."""
        return tuple(level.name or "" for level in self.path_levels)

    @property
    def path_labels(self) -> tuple[str, ...]:
        """Return display labels aligned to path_ids."""
        return tuple(_path_label(level) for level in self.path_levels)

    @property
    def depth(self) -> int:
        """Return zero-based hierarchy depth for the leaf."""
        return max(len(self.path_ids) - 1, 0)

    @property
    def root_id(self) -> int | None:
        """Return the root protein classification identifier."""
        path_ids = self.path_ids
        return path_ids[0] if path_ids else None

    @property
    def is_leaf(self) -> bool:
        """Return True when hierarchy resolves to this leaf identifier."""
        if self.path is not None:
            if not self.path:
                return False
            last = self.path[-1]
            return last.id == self.leaf_id and not last.is_empty
        return (not self.l5.is_empty) and self.l5.id == self.leaf_id

    def _validate_path(self) -> None:
        if self.path is None:
            return
        _validate_path_levels(self.path, leaf_id=self.leaf_id)


def _validate_level_id(level_id: int | None) -> None:
    """Validate a non-empty protein classification level identifier."""
    if level_id is not None and level_id < 1:
        raise ValueError(f"protein class level id must be positive, got {level_id}")


def _validate_empty_level_payload(
    level_id: int | None,
    name: str | None,
    desc: str | None,
) -> None:
    """Ensure absent hierarchy levels do not carry descriptive payload."""
    if level_id is None and _has_level_payload(name=name, desc=desc):
        raise ValueError("empty protein class levels must not carry name or desc")


def _has_level_payload(*, name: str | None, desc: str | None) -> bool:
    """Return True when an optional hierarchy level carries display data."""
    return name is not None or desc is not None


def _validate_path_levels(
    path: Iterable[ProteinClassLevel],
    *,
    leaf_id: int,
) -> None:
    """Validate a full root-to-leaf classification path."""
    path_tuple = tuple(path)
    if not path_tuple:
        raise ValueError("protein class hierarchy path must not be empty")
    path_ids = tuple(_require_level_id(level.id) for level in path_tuple)
    if path_ids[-1] != leaf_id:
        raise ValueError("protein class hierarchy path must end at leaf_id")
    if len(set(path_ids)) != len(path_ids):
        raise ValueError("protein class hierarchy path must not contain cycles")


def _require_level_id(level_id: int | None) -> int:
    """Return a non-null level identifier or raise a contract error."""
    if level_id is None:
        raise ValueError("protein class path levels must carry identifiers")
    return level_id


def _path_label(level: ProteinClassLevel) -> str:
    """Return a deterministic human-readable label for one path level."""
    level_id = _require_level_id(level.id)
    return f"{level_id}:{level.name}" if level.name else str(level_id)
