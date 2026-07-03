"""Thin PubChem fetch facade; heavy query/search/flow logic lives in helpers."""

from __future__ import annotations

__all__ = ["PubChemFetchStrategies"]

import asyncio
from typing import TYPE_CHECKING

import pubchempy as pcp

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.common.error_bundles import (
    build_common_network_error_bundle,
)
from bioetl.infrastructure.adapters.pubchem._fetch_strategy_search import (
    _PubChemSearchFetchMixin,
)
from bioetl.infrastructure.adapters.pubchem.constants import PUBCHEM_API_BASE
from bioetl.infrastructure.adapters.pubchem.fetch_flow import PubChemFetchFlow
from bioetl.infrastructure.adapters.pubchem.policy_helper import (
    is_blank_value,
    is_limit_reached,
    is_valid_inchikey,
    iter_cid_batches,
    parse_valid_cids,
)
from bioetl.infrastructure.adapters.pubchem.query_builder import (
    build_cid_batch_endpoint,
    build_inchikey_endpoint,
    build_smiles_endpoint,
)
from bioetl.infrastructure.adapters.pubchem.response_mapper import (
    PubChemResponseMapper,
    normalize_pubchem_results,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
    from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter
    from bioetl.infrastructure.adapters.pubchem.entity_mapper import PubChemEntityMapper


class PubChemFetchStrategies(_PubChemSearchFetchMixin):
    """Helper class for PubChem fetch operations."""

    FETCH_STRATEGY_ERRORS = build_common_network_error_bundle(
        KeyError,
    )

    def __init__(
        self,
        logger: LoggerPort,
        rate_limiter: TokenBucketRateLimiter,
        circuit_breaker: CircuitBreakerGuard,
        mapper: PubChemEntityMapper,
        run_in_executor: Callable[..., Awaitable[object]],
        provider_name: str = "pubchem",
        request_collector: APIRequestCollector | None = None,
        response_mapper: PubChemResponseMapper | None = None,
        fetch_flow: PubChemFetchFlow | None = None,
    ) -> None:
        """Initialize fetch strategies."""
        self._logger = logger
        self._rate_limiter = rate_limiter
        self._circuit_breaker = circuit_breaker
        self._mapper = mapper
        self._run_in_executor = run_in_executor
        self._provider_name = provider_name
        self._request_collector = request_collector
        self._response_mapper = response_mapper or PubChemResponseMapper(mapper)
        self._fetch_flow = fetch_flow or PubChemFetchFlow(
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            run_in_executor=run_in_executor,
            record_request=self._record_request,
            normalize_results=self._normalize_results,
        )

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
        """Compatibility wrapper around normalized pubchempy responses."""
        return normalize_pubchem_results(results)

    async def _fetch_single_smiles(self, smiles: str) -> list[BronzeRecord]:
        """Fetch compounds for a single SMILES string."""
        compounds = await self._fetch_flow.execute(
            endpoint=build_smiles_endpoint(),
            pubchem_callable=pcp.get_compounds,
            pubchem_args=(smiles.strip(), "smiles"),
        )
        return self._response_mapper.map_compounds(compounds)

    def _warn_smiles_fetch_error(self, smiles: str, error: Exception) -> None:
        self._logger.warning(
            "smiles_fetch_failed",
            provider=self._provider_name,
            smiles=smiles[:50],
            error=str(error),
        )

    async def _iter_smiles_chunk_records(
        self,
        chunk: list[str],
    ) -> AsyncIterator[BronzeRecord]:
        tasks = [self._fetch_single_smiles(smiles) for smiles in chunk]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for smiles, result in zip(chunk, results, strict=True):
            if isinstance(result, self.FETCH_STRATEGY_ERRORS):
                self._warn_smiles_fetch_error(smiles, result)
                continue
            if isinstance(result, BaseException):
                raise result
            for record in result:
                yield record

    async def fetch_by_smiles(
        self,
        smiles_list: list[str],
        limit: int | None = None,
        batch_size: int = 10,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch compounds by SMILES strings."""
        fetched = 0
        valid_smiles = [s for s in smiles_list if not is_blank_value(s)]

        for i in range(0, len(valid_smiles), batch_size):
            if is_limit_reached(limit, fetched):
                break

            chunk_end = i + batch_size
            if limit is not None:
                chunk_end = i + min(batch_size, max(limit - fetched, 0))
            chunk = valid_smiles[i:chunk_end]
            async for record in self._iter_smiles_chunk_records(chunk):
                if is_limit_reached(limit, fetched):
                    return
                yield record
                fetched += 1

    def _parse_valid_cids(self, cid_list: list[str]) -> list[int]:
        """Parse and validate CID list, returning only valid integers."""
        return parse_valid_cids(
            cid_list,
            logger=self._logger,
            provider_name=self._provider_name,
        )

    async def _fetch_cid_batch(self, batch: list[int]) -> list[BronzeRecord]:
        """Fetch a batch of compounds by CID."""
        compounds = await self._fetch_flow.execute(
            endpoint=build_cid_batch_endpoint(batch),
            pubchem_callable=pcp.get_compounds,
            pubchem_args=(batch, "cid"),
        )
        return self._response_mapper.map_compounds(compounds)

    async def fetch_by_cids(
        self,
        cid_list: list[str],
        limit: int | None = None,
        batch_size: int = 50,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch compounds by CID list."""
        fetched = 0
        valid_cids = self._parse_valid_cids(cid_list)

        for batch in iter_cid_batches(valid_cids, batch_size):
            if is_limit_reached(limit, fetched):
                return

            try:
                records = await self._fetch_cid_batch(batch)
                for record in records:
                    if is_limit_reached(limit, fetched):
                        return
                    yield record
                    fetched += 1
            except self.FETCH_STRATEGY_ERRORS as error:
                self._logger.warning(
                    "molecule_id_batch_fetch_failed",
                    provider=self._provider_name,
                    batch_start=batch[0] if batch else None,
                    batch_size=len(batch),
                    error=str(error),
                )

    async def _fetch_single_inchikey(self, inchikey: str) -> list[BronzeRecord]:
        """Fetch compounds for a single InChIKey."""
        compounds = await self._fetch_flow.execute(
            endpoint=build_inchikey_endpoint(),
            pubchem_callable=pcp.get_compounds,
            pubchem_args=(inchikey.strip(), "inchikey"),
        )
        return self._response_mapper.map_compounds(compounds)

    def _filter_valid_inchikeys(self, inchikey_list: list[str]) -> list[str]:
        valid_keys = []
        for inchikey in inchikey_list:
            if is_blank_value(inchikey):
                continue
            cleaned = inchikey.strip()
            if not is_valid_inchikey(cleaned):
                self._logger.warning(
                    "invalid_inchikey_skipped",
                    provider=self._provider_name,
                    inchikey=cleaned[:30],
                    reason="invalid_format",
                )
                continue
            valid_keys.append(cleaned)
        return valid_keys

    def _warn_inchikey_fetch_error(self, inchikey: str, error: Exception) -> None:
        self._logger.warning(
            "inchikey_fetch_failed",
            provider=self._provider_name,
            inchikey=inchikey,
            error=str(error),
        )

    async def _iter_inchikey_chunk_records(
        self,
        chunk: list[str],
    ) -> AsyncIterator[BronzeRecord]:
        for cleaned in chunk:
            try:
                records = await self._fetch_single_inchikey(cleaned)
            except self.FETCH_STRATEGY_ERRORS as error:
                self._warn_inchikey_fetch_error(cleaned, error)
                continue
            for record in records:
                yield record

    async def fetch_by_inchikey(
        self,
        inchikey_list: list[str],
        limit: int | None = None,
        batch_size: int = 10,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch compounds by InChIKey list."""
        fetched = 0
        valid_keys = self._filter_valid_inchikeys(inchikey_list)

        for i in range(0, len(valid_keys), batch_size):
            if is_limit_reached(limit, fetched):
                break

            chunk = valid_keys[i : i + batch_size]
            async for record in self._iter_inchikey_chunk_records(chunk):
                if is_limit_reached(limit, fetched):
                    return
                yield record
                fetched += 1
