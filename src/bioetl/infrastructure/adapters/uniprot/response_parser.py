"""UniProt response parser helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.types import BronzeRecord

if TYPE_CHECKING:
    import httpx


def parse_uniprot_protein_response(
    response: httpx.Response,
) -> tuple[list[BronzeRecord], str | None]:
    """Parse UniProt protein search response."""
    if response.status_code != 200:
        return [], None
    data = response.json()
    results = data.get("results", [])
    cursor = data.get("nextCursor")
    return results, cursor


__all__ = ["parse_uniprot_protein_response"]
