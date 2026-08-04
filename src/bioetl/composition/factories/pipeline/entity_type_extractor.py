"""Typed protocol for deriving entity type from pipeline names."""

from __future__ import annotations

from typing import Protocol


class EntityTypeExtractor(Protocol):
    """Callable contract for deriving entity type from pipeline name."""

    def __call__(self, pipeline_name: str) -> str | None: ...

__all__ = ["EntityTypeExtractor"]
