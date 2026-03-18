"""Typed protocol surface for declarative publication extraction blocks."""

from __future__ import annotations

from typing import Protocol

from bioetl.domain.types import BronzeRecord, JsonDict


class _ExtractionBlock(Protocol):
    """Protocol for block-style publication extraction helpers."""

    def extract(self, record: BronzeRecord) -> JsonDict:
        """Extract provider-specific fields from a bronze record."""
        ...


# Public type alias keeps existing imports stable while avoiding another
# top-level class name that would count as a naming-convention surface.
ExtractionBlock = _ExtractionBlock


__all__ = ["ExtractionBlock"]
