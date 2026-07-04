"""Internal search-oriented helpers for PubChem fetch strategies."""

from __future__ import annotations

__all__ = ["_PubChemSearchFetchMixin"]

from typing import TYPE_CHECKING

import pubchempy as pcp

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.pubchem.policy_helper import is_limit_reached
from bioetl.infrastructure.adapters.pubchem.query_builder import (
    build_assay_endpoint,
    build_compound_name_endpoint,
    build_substance_name_endpoint,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.infrastructure.adapters.pubchem.fetch_flow import (
        PubChemFetchFlow,
    )
    from bioetl.infrastructure.adapters.pubchem.response_mapper import (
        PubChemResponseMapper,
    )


class _PubChemSearchFetchMixin:
    """Query-based PubChem fetch strategies for compounds, substances, and assays."""

    _fetch_flow: PubChemFetchFlow
    _response_mapper: PubChemResponseMapper

    async def fetch_by_query(
        self,
        query: str,
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch compounds by query (name search)."""
        compounds = await self._fetch_flow.execute(
            endpoint=build_compound_name_endpoint(query),
            pubchem_callable=pcp.get_compounds,
            pubchem_args=(query, "name"),
        )
        for index, record in enumerate(self._response_mapper.map_compounds(compounds)):
            if is_limit_reached(limit, index):
                break
            yield record

    async def fetch_substances(
        self,
        query: str | None,
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch substances from PubChem."""
        if not query:
            raise ValueError("Query is required for substance search")

        substances = await self._fetch_flow.execute(
            endpoint=build_substance_name_endpoint(query),
            pubchem_callable=pcp.get_substances,
            pubchem_args=(query, "name"),
        )
        fetched = 0
        for record in self._response_mapper.map_substances(substances):
            if is_limit_reached(limit, fetched):
                break
            yield record
            fetched += 1

    async def fetch_assays(
        self,
        query: str | None,
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch assays from PubChem."""
        if not query:
            raise ValueError("Query is required for assay search")

        assays = await self._fetch_flow.execute(
            endpoint=build_assay_endpoint(query),
            pubchem_callable=pcp.get_assays,
            pubchem_args=(query,),
        )
        fetched = 0
        for record in self._response_mapper.map_assays(assays):
            if is_limit_reached(limit, fetched):
                break
            yield record
            fetched += 1
