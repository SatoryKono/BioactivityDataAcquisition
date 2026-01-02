"""PubChem fetch strategy helpers.

Extracted from pubchem/client.py to reduce class size.
Contains helper functions for different fetch modes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pubchempy as pcp

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
    from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
    from bioetl.infrastructure.adapters.pubchem.entity_mapper import PubChemEntityMapper


class PubChemFetchStrategies:
    """Helper class for PubChem fetch operations.

    Provides fetch methods for different entity types and fetch modes.
    Delegates entity conversion to PubChemEntityMapper.
    """

    def __init__(
        self,
        logger: LoggerPort,
        rate_limiter: TokenBucket,
        circuit_breaker: CircuitBreaker,
        mapper: PubChemEntityMapper,
        run_in_executor: Callable[..., Any],
        provider_name: str = "pubchem",
    ) -> None:
        """Initialize fetch strategies."""
        self._logger = logger
        self._rate_limiter = rate_limiter
        self._circuit_breaker = circuit_breaker
        self._mapper = mapper
        self._run_in_executor = run_in_executor
        self._provider_name = provider_name

    async def fetch_by_query(
        self, query: str, limit: int | None
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch compounds by query (name search)."""
        await self._rate_limiter.acquire()
        compounds = await self._circuit_breaker.call(
            self._run_in_executor, pcp.get_compounds, query, "name"
        )
        for i, compound in enumerate(compounds or []):
            if limit and i >= limit:
                break
            yield self._mapper.compound_to_dict(compound)

    async def _fetch_single_smiles(
        self, smiles: str
    ) -> list[dict[str, Any]]:
        """Fetch compounds for a single SMILES string."""
        await self._rate_limiter.acquire()
        compounds = await self._circuit_breaker.call(
            self._run_in_executor, pcp.get_compounds, smiles.strip(), "smiles"
        )
        return [self._mapper.compound_to_dict(c) for c in (compounds or [])]

    async def fetch_by_smiles(
        self, smiles_list: list[str], limit: int | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch compounds by SMILES strings."""
        fetched = 0
        for smiles in smiles_list:
            if limit and fetched >= limit:
                return
            if not smiles or not smiles.strip():
                continue

            try:
                records = await self._fetch_single_smiles(smiles)
                for record in records:
                    if limit and fetched >= limit:
                        return
                    yield record
                    fetched += 1
            except Exception as e:
                self._logger.warning(
                    "smiles_fetch_failed",
                    provider=self._provider_name,
                    smiles=smiles[:50],
                    error=str(e),
                )

    def _parse_valid_cids(self, cid_list: list[str]) -> list[int]:
        """Parse and validate CID list, returning only valid integers."""
        valid_cids: list[int] = []
        for cid in cid_list:
            try:
                valid_cids.append(int(cid))
            except (ValueError, TypeError):
                self._logger.warning(
                    "invalid_cid_skipped", provider=self._provider_name, cid=cid
                )
        return valid_cids

    async def _fetch_cid_batch(self, batch: list[int]) -> list[dict[str, Any]]:
        """Fetch a batch of compounds by CID."""
        await self._rate_limiter.acquire()
        compounds = await self._circuit_breaker.call(
            self._run_in_executor, pcp.get_compounds, batch, "cid"
        )
        return [self._mapper.compound_to_dict(c) for c in (compounds or [])]

    async def fetch_by_cids(
        self, cid_list: list[str], limit: int | None = None, batch_size: int = 50
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch compounds by CID list."""
        fetched = 0
        valid_cids = self._parse_valid_cids(cid_list)

        for i in range(0, len(valid_cids), batch_size):
            if limit and fetched >= limit:
                return
            batch = valid_cids[i : i + batch_size]

            try:
                records = await self._fetch_cid_batch(batch)
                for record in records:
                    if limit and fetched >= limit:
                        return
                    yield record
                    fetched += 1
            except Exception as e:
                self._logger.warning(
                    "cid_batch_fetch_failed",
                    provider=self._provider_name,
                    batch_start=batch[0] if batch else None,
                    batch_size=len(batch),
                    error=str(e),
                )

    async def fetch_substances(
        self, query: str | None, limit: int | None
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch substances from PubChem."""
        if not query:
            raise ValueError("Query is required for substance search")

        await self._rate_limiter.acquire()
        substances = await self._circuit_breaker.call(
            self._run_in_executor, pcp.get_substances, query, "name"
        )

        fetched = 0
        for substance in substances or []:
            if limit and fetched >= limit:
                break
            yield self._mapper.substance_to_dict(substance)
            fetched += 1

    async def fetch_assays(
        self, query: str | None, limit: int | None
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch assays from PubChem."""
        if not query:
            raise ValueError("Query is required for assay search")

        await self._rate_limiter.acquire()
        assays = await self._circuit_breaker.call(
            self._run_in_executor, pcp.get_assays, query
        )

        fetched = 0
        for assay in assays or []:
            if limit and fetched >= limit:
                break
            yield self._mapper.assay_to_dict(assay)
            fetched += 1
