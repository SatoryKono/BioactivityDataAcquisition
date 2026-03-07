"""PubChem fetch strategy helpers.

Extracted from pubchem/client.py to reduce class size.
Contains helper functions for different fetch modes.
"""

from __future__ import annotations

__all__ = ["PubChemFetchStrategies"]

import time
from typing import TYPE_CHECKING

import pubchempy as pcp

from bioetl.domain.exceptions import BioETLError, NetworkError
from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.pubchem.constants import PUBCHEM_API_BASE

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
    from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
    from bioetl.infrastructure.adapters.pubchem.entity_mapper import PubChemEntityMapper


class _PubChemSearchFetchMixin:
    """Query-based PubChem fetch strategies (compound/substance/assay)."""

    _rate_limiter: TokenBucket
    _circuit_breaker: CircuitBreaker
    _run_in_executor: Callable[..., Awaitable[object]]
    _mapper: PubChemEntityMapper

    def _record_request(
        self,
        endpoint: str,
        duration_ms: float,
        status_code: int = 200,
        result_count: int = 0,
    ) -> None:
        """Record a PubChem API request."""
        raise NotImplementedError

    @staticmethod
    def _normalize_results(results: object) -> list[object]:
        """Normalize pubchempy responses to list."""
        raise NotImplementedError

    async def fetch_by_query(
        self, query: str, limit: int | None
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch compounds by query (name search)."""
        await self._rate_limiter.acquire()
        start_time = time.perf_counter()
        compounds = await self._circuit_breaker.call(
            self._run_in_executor, pcp.get_compounds, query, "name"
        )
        normalized_compounds = self._normalize_results(compounds)
        duration_ms = (time.perf_counter() - start_time) * 1000
        result_count = len(normalized_compounds)
        self._record_request(
            f"/compound/name/{query}/JSON", duration_ms, result_count=result_count
        )
        for i, compound in enumerate(normalized_compounds):
            if limit and i >= limit:
                break
            yield self._mapper.compound_to_dict(compound)

    async def fetch_substances(
        self, query: str | None, limit: int | None
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch substances from PubChem."""
        if not query:
            raise ValueError("Query is required for substance search")

        await self._rate_limiter.acquire()
        start_time = time.perf_counter()
        substances = await self._circuit_breaker.call(
            self._run_in_executor, pcp.get_substances, query, "name"
        )
        normalized_substances = self._normalize_results(substances)
        duration_ms = (time.perf_counter() - start_time) * 1000
        result_count = len(normalized_substances)
        self._record_request(
            f"/substance/name/{query}/JSON", duration_ms, result_count=result_count
        )

        fetched = 0
        for substance in normalized_substances:
            if limit and fetched >= limit:
                break
            yield self._mapper.substance_to_dict(substance)
            fetched += 1

    async def fetch_assays(
        self, query: str | None, limit: int | None
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch assays from PubChem."""
        if not query:
            raise ValueError("Query is required for assay search")

        await self._rate_limiter.acquire()
        start_time = time.perf_counter()
        assays = await self._circuit_breaker.call(
            self._run_in_executor, pcp.get_assays, query
        )
        normalized_assays = self._normalize_results(assays)
        duration_ms = (time.perf_counter() - start_time) * 1000
        result_count = len(normalized_assays)
        self._record_request(
            f"/assay/aid/{query}/JSON", duration_ms, result_count=result_count
        )

        fetched = 0
        for assay in normalized_assays:
            if limit and fetched >= limit:
                break
            yield self._mapper.assay_to_dict(assay)
            fetched += 1


class PubChemFetchStrategies(_PubChemSearchFetchMixin):
    """Helper class for PubChem fetch operations."""

    FETCH_STRATEGY_ERRORS = (
        BioETLError,
        NetworkError,
        ConnectionError,
        TimeoutError,
        OSError,
        ValueError,
        TypeError,
        RuntimeError,
        KeyError,
    )

    def __init__(
        self,
        logger: LoggerPort,
        rate_limiter: TokenBucket,
        circuit_breaker: CircuitBreaker,
        mapper: PubChemEntityMapper,
        run_in_executor: Callable[..., Awaitable[object]],
        provider_name: str = "pubchem",
        request_collector: APIRequestCollector | None = None,
    ) -> None:
        """Initialize fetch strategies."""
        self._logger = logger
        self._rate_limiter = rate_limiter
        self._circuit_breaker = circuit_breaker
        self._mapper = mapper
        self._run_in_executor = run_in_executor
        self._provider_name = provider_name
        self._request_collector = request_collector

    def _record_request(
        self,
        endpoint: str,
        duration_ms: float,
        status_code: int = 200,
        result_count: int = 0,
    ) -> None:
        """Record a PubChem API request for metadata enrichment."""
        if self._request_collector is None:
            return

        # Estimate response size based on result count (rough approximation)
        # Average compound JSON is ~2KB, substance ~1KB, assay ~3KB
        estimated_size = result_count * 2000

        self._request_collector.record_request(
            url=f"{PUBCHEM_API_BASE}{endpoint}",
            method="GET",
            response_size=estimated_size,
            duration_ms=duration_ms,
            status_code=status_code,
        )

    @staticmethod
    def _normalize_results(results: object) -> list[object]:
        """Normalize pubchempy responses to a concrete list.

        Returns:
            List of result objects, converting tuples to lists or returning empty list for other types.
        """
        if isinstance(results, list):
            return results
        if isinstance(results, tuple):
            return list(results)
        return []

    async def _fetch_single_smiles(self, smiles: str) -> list[BronzeRecord]:
        """Fetch compounds for a single SMILES string.

        Returns:
            List of compound record dictionaries matching the given SMILES structure.
        """
        await self._rate_limiter.acquire()
        start_time = time.perf_counter()
        compounds = await self._circuit_breaker.call(
            self._run_in_executor, pcp.get_compounds, smiles.strip(), "smiles"
        )
        normalized_compounds = self._normalize_results(compounds)
        duration_ms = (time.perf_counter() - start_time) * 1000
        result_count = len(normalized_compounds)
        self._record_request(
            "/compound/smiles/JSON", duration_ms, result_count=result_count
        )
        return [self._mapper.compound_to_dict(c) for c in normalized_compounds]

    async def fetch_by_smiles(
        self, smiles_list: list[str], limit: int | None = None
    ) -> AsyncIterator[BronzeRecord]:
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
            except self.FETCH_STRATEGY_ERRORS as e:
                self._logger.warning(
                    "smiles_fetch_failed",
                    provider=self._provider_name,
                    smiles=smiles[:50],
                    error=str(e),
                )

    def _parse_valid_cids(self, cid_list: list[str]) -> list[int]:
        """Parse and validate CID list, returning only valid integers.

        Returns:
            List of integer CIDs parsed from the input strings, skipping invalid values.
        """
        valid_cids: list[int] = []
        for cid in cid_list:
            try:
                valid_cids.append(int(cid))
            except (ValueError, TypeError):
                self._logger.warning(
                    "invalid_cid_skipped", provider=self._provider_name, cid=cid
                )
        return valid_cids

    def _parse_valid_molecule_ids(self, molecule_id_list: list[str]) -> list[int]:
        """Backward-compatible alias for CID parser.

        Returns:
            List of integer CIDs parsed from the input strings, skipping invalid values.
        """
        return self._parse_valid_cids(molecule_id_list)

    async def _fetch_cid_batch(self, batch: list[int]) -> list[BronzeRecord]:
        """Fetch a batch of compounds by CID.

        Returns:
            List of compound record dictionaries for the given CID batch.
        """
        await self._rate_limiter.acquire()
        start_time = time.perf_counter()
        compounds = await self._circuit_breaker.call(
            self._run_in_executor, pcp.get_compounds, batch, "cid"
        )
        normalized_compounds = self._normalize_results(compounds)
        duration_ms = (time.perf_counter() - start_time) * 1000
        result_count = len(normalized_compounds)
        self._record_request(
            f"/compound/cid/{','.join(map(str, batch[:3]))},.../JSON",
            duration_ms,
            result_count=result_count,
        )
        return [self._mapper.compound_to_dict(c) for c in normalized_compounds]

    async def fetch_by_cids(
        self, cid_list: list[str], limit: int | None = None, batch_size: int = 50
    ) -> AsyncIterator[BronzeRecord]:
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
            except self.FETCH_STRATEGY_ERRORS as e:
                self._logger.warning(
                    "molecule_id_batch_fetch_failed",
                    provider=self._provider_name,
                    batch_start=batch[0] if batch else None,
                    batch_size=len(batch),
                    error=str(e),
                )

    async def fetch_by_molecule_ids(
        self,
        molecule_id_list: list[str],
        limit: int | None = None,
        batch_size: int = 50,
    ) -> AsyncIterator[BronzeRecord]:
        """Backward-compatible alias for CID-based fetch."""
        async for record in self.fetch_by_cids(
            molecule_id_list, limit=limit, batch_size=batch_size
        ):
            yield record

    async def _fetch_single_inchikey(self, inchikey: str) -> list[BronzeRecord]:
        """Fetch compounds for a single InChIKey.

        Returns:
            List of compound record dictionaries matching the given InChIKey (usually 0 or 1 result).
        """
        await self._rate_limiter.acquire()
        start_time = time.perf_counter()
        compounds = await self._circuit_breaker.call(
            self._run_in_executor, pcp.get_compounds, inchikey.strip(), "inchikey"
        )
        normalized_compounds = self._normalize_results(compounds)
        duration_ms = (time.perf_counter() - start_time) * 1000
        result_count = len(normalized_compounds)
        self._record_request(
            "/compound/inchikey/JSON", duration_ms, result_count=result_count
        )
        return [self._mapper.compound_to_dict(c) for c in normalized_compounds]

    async def fetch_by_inchikey(
        self, inchikey_list: list[str], limit: int | None = None
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch compounds by InChIKey list."""
        fetched = 0
        for inchikey in inchikey_list:
            if limit and fetched >= limit:
                return
            if not inchikey or not inchikey.strip():
                continue

            # Basic InChIKey format validation (27 chars, NNNN-YYYY-Z pattern)
            cleaned = inchikey.strip()
            if len(cleaned) != 27 or cleaned.count("-") != 2:
                self._logger.warning(
                    "invalid_inchikey_skipped",
                    provider=self._provider_name,
                    inchikey=cleaned[:30],
                    reason="invalid_format",
                )
                continue

            try:
                records = await self._fetch_single_inchikey(cleaned)
                for record in records:
                    if limit and fetched >= limit:
                        return
                    yield record
                    fetched += 1
            except self.FETCH_STRATEGY_ERRORS as e:
                self._logger.warning(
                    "inchikey_fetch_failed",
                    provider=self._provider_name,
                    inchikey=cleaned,
                    error=str(e),
                )
