"""UniProt response parser helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.common.response_shapes import (
    extract_response_items,
    extract_response_text,
)

if TYPE_CHECKING:
    import httpx


def parse_uniprot_protein_response(
    response: httpx.Response,
) -> tuple[list[BronzeRecord], str | None]:
    """Parse UniProt protein search response.

    Args:
        response: HTTP response from the UniProt protein search endpoint.

    Returns:
        Tuple of (list of protein records, next cursor string or None if last page).
    """
    if response.status_code != 200:
        return [], None
    data = response.json()
    if not isinstance(data, dict):
        return [], None
    results = [
        record
        for record in extract_response_items(data, "results")
        if isinstance(record, dict)
    ]
    cursor = extract_response_text(data, "nextCursor")
    return results, cursor


__all__ = ["parse_uniprot_protein_response"]
