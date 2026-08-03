"""Typed mapping helpers for ChEMBL policy-family payloads."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType
from typing import Protocol


class _NamedFamily(Protocol):
    @property
    def family_name(self) -> str:
        """Return the stable family identifier used as the mapping key."""
        ...


def family_mapping_by_name[FamilyT: _NamedFamily](
    families: Iterable[FamilyT],
) -> Mapping[str, FamilyT]:
    """Index immutable family payloads by their declared family name."""
    return MappingProxyType({family.family_name: family for family in families})
