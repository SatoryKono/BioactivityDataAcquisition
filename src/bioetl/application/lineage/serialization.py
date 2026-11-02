"""Application-layer JSON-safe serialization helpers for lineage attributes.

Thin wrapper over the domain lineage serializer so application services keep a
stable import path without duplicating the JSON-plain conversion body.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from bioetl.domain.lineage._shared import mapping_to_plain as _domain_mapping_to_plain

__all__ = ["mapping_to_plain"]


def mapping_to_plain(values: Mapping[str, object]) -> dict[str, object]:
    """Return a JSON-safe deep plain-dict copy of a (possibly frozen) mapping."""
    plain = _domain_mapping_to_plain(values)
    if not isinstance(plain, dict):
        raise TypeError(
            "Lineage mapping_to_plain expected a mapping result; "
            f"got {type(plain).__name__}"
        )
    return cast(dict[str, object], plain)
