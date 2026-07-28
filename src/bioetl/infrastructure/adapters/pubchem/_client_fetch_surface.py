# Host attrs/methods provided by concrete composition.
"""Internal fetch-routing surface for the PubChem adapter."""

from __future__ import annotations

__all__ = ["_PubChemClientFetchMixin"]

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.infrastructure.adapters.pubchem.fetch_strategies import (
        PubChemFetchStrategies,
    )


class _PubChemClientFetchMixin:
    """Fetch routing and filtered dispatch for the PubChem adapter."""

    _strategies: PubChemFetchStrategies = cast(Any, None)  # Any: host attr default (PD3)

    async def _fetch_compound(
        self, query: str | None, limit: int | None
    ) -> AsyncIterator[JsonDict]:
        """Fetch compounds by query."""
        if not query:
            raise ValueError("Query is required for compound fetch")
        async for record in self._strategies.fetch_by_query(query, limit):
            yield record

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        """Fetch records from PubChem via search or filter routes."""
        del offset
        if filter_ids and filter_field:
            async for record in self.fetch_filtered(
                entity_type, filter_ids, filter_field, limit
            ):
                yield record
            return

        fetch_methods: dict[str, Callable[[], AsyncIterator[JsonDict]]] = {
            "compound": lambda: self._fetch_compound(query, limit),
            "substance": lambda: self._strategies.fetch_substances(query, limit),
            "assay": lambda: self._strategies.fetch_assays(query, limit),
        }

        method = fetch_methods.get(entity_type)
        if method is None:
            raise ValueError(f"Unsupported entity type: {entity_type}")

        async for record in method():
            yield record

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        """Fetch PubChem records by filter ID list."""
        if entity_type != "compound":
            raise ValueError(
                f"fetch_filtered only supports 'compound', got: {entity_type}"
            )

        if filter_field in ("smiles", "canonical_smiles"):
            async for record in self._strategies.fetch_by_smiles(filter_ids, limit):
                yield record
        elif filter_field == "cid":
            async for record in self._strategies.fetch_by_cids(filter_ids, limit):
                yield record
        elif filter_field in ("inchikey", "inchi_key"):
            async for record in self._strategies.fetch_by_inchikey(filter_ids, limit):
                yield record
        else:
            raise ValueError(f"Unsupported filter_field: {filter_field}")
