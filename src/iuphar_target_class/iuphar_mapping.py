"""Approved direct mapping and family graph for a single GtoPdb release."""

from __future__ import annotations

from collections.abc import Mapping
from functools import cache
from types import MappingProxyType

from .gtopdb_2026_3_1 import FAMILY_ROWS, RELEASE, TYPE_CLASS_PAIRS


def require_mapping_release(release: str) -> None:
    """Do not reuse approved mapping rules with data from another version."""
    if release != RELEASE:
        message = (
            f"GtoPdb release {release!r} does not match approved mapping {RELEASE}"
        )
        raise ValueError(message)


@cache
def _approved_maps() -> tuple[Mapping[str, str], Mapping[str, str]]:
    types = dict(TYPE_CLASS_PAIRS)
    families = {
        str(family_id): types[source_type]
        for family_id, source_type, _parents in FAMILY_ROWS
        if source_type != "grouping"
    }
    return MappingProxyType(types), MappingProxyType(families)


def approved_class_mappings(
    release: str,
) -> tuple[Mapping[str, str], Mapping[str, str]]:
    """Return immutable exact type and direct-family-ID mappings."""
    require_mapping_release(release)
    return _approved_maps()
