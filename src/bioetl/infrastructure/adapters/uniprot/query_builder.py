"""UniProt query parameter builders."""

from __future__ import annotations

from bioetl.domain.types import JsonDict


def build_uniprot_protein_search_params(
    *,
    query: str,
    fetched: int,
    limit: int | None,
    cursor: str | None,
    size: int,
    fields: tuple[str, ...],
) -> JsonDict:  # Any: mixed query values (str|int)
    """Build UniProt protein search parameters."""
    params: JsonDict = {  # Any: dynamic payload or structural mixin boundary
        "query": query,
        "size": min(size, (limit - fetched) if limit else size),
        "format": "json",
        "fields": ",".join(fields),
    }
    if cursor:
        params["cursor"] = cursor
    return params


def build_uniprot_health_probe_params() -> dict[str, int | str]:
    """Build parameters for UniProt health probe search."""
    return {"query": "accession:P62988", "size": 1, "format": "json"}


__all__ = [
    "build_uniprot_health_probe_params",
    "build_uniprot_protein_search_params",
]
