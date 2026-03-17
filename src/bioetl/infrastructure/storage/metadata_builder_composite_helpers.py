"""Compatibility wrappers for composite metadata parsing helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.services.composite_metadata_helpers import (
    extract_composite_output_ext,
)
from bioetl.domain.services.composite_metadata_helpers import (
    parse_composite_list as _parse_composite_list,
)
from bioetl.domain.services.composite_metadata_helpers import (
    parse_composite_status as _parse_composite_status,
)
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import CompositeOutputExt


def parse_composite_list(value: object) -> list[str]:
    """Parse composite list metadata via shared domain helper."""
    return _parse_composite_list(value)


def parse_composite_status(value: object) -> dict[str, str]:
    """Parse enrichment status via shared domain helper."""
    return _parse_composite_status(value)


def build_composite_output_ext(
    records: list[JsonDict],  # Any: record/metadata values are heterogeneous
) -> CompositeOutputExt | None:
    """Build CompositeOutputExt via shared domain helper."""
    return extract_composite_output_ext(records)


__all__ = [
    "build_composite_output_ext",
    "parse_composite_list",
    "parse_composite_status",
]
