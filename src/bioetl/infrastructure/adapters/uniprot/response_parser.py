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

__all__ = ["UniProtProteinPageError", "parse_uniprot_protein_response"]


class UniProtProteinPageError(RuntimeError):
    """Protein search page failed and must not be read as cursor exhaustion."""


def parse_uniprot_protein_response(
    response: httpx.Response,
) -> tuple[list[BronzeRecord], str | None]:
    """Parse UniProt protein search response.

    Args:
        response: HTTP response from the UniProt protein search endpoint.

    Returns:
        Tuple of (list of protein records, next cursor string or None if last page).

    Raises:
        UniProtProteinPageError: The page is not a successful object payload.
            ``None`` remains reserved for a real final cursor.
    """
    if response.status_code != 200:
        raise UniProtProteinPageError(
            f"UniProt protein page status {response.status_code} is not cursor exhaustion"
        )
    data = response.json()
    if not isinstance(data, dict):
        raise UniProtProteinPageError(
            "UniProt protein page payload is not an object and is not cursor exhaustion"
        )
    results = [
        record
        for record in extract_response_items(data, "results")
        if isinstance(record, dict)
    ]
    cursor = extract_response_text(data, "nextCursor")
    return results, cursor
