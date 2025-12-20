"""PubChem API client adapter.

Implements RULES.md Appendix A - PubChem specifications.

Requirements:
- Uses pubchempy library (legacy sync)
- Rate limit: 5 req/sec (TokenBucket)
- Health: lightweight query
- Entities: compounds, substances, assays, bioassays

Documentation: https://pubchemdocs.ncbi.nlm.nih.gov/pug-rest
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Self

import pubchempy as pcp

from bioetl.domain.types import HealthStatus, Watermark
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.health import (
    assess_health_from_circuit_breaker,
)
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket

logger = logging.getLogger(__name__)


class PubChemClient:
    """PubChem API client implementing DataSourcePort.

    Provides access to chemical compound data from PubChem database.
    Uses pubchempy library which is synchronous, so runs in ThreadPoolExecutor.

    Example:
        >>> client = PubChemClient()
        >>> # Search compounds by name
        >>> async for compound in client.fetch("compound", query="aspirin", limit=10):
        ...     print(f"Compound: {compound['cid']}")
        >>> # Check health
        >>> status = await client.health_check()
        >>> print(f"PubChem is {status}")
    """

    provider_name: str = "pubchem"

    def __init__(
        self,
        rate: float = 5.0,  # 5 req/sec per RULES.md
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 300,
        max_workers: int = 4,
        strict_error_handling: bool = False,
    ) -> None:
        """Initialize PubChem client.

        Args:
            rate: Requests per second (default: 5.0 per RULES.md)
            circuit_breaker_threshold: Failures before opening circuit
            circuit_breaker_timeout: Recovery timeout in seconds
            max_workers: Thread pool size for sync operations
            strict_error_handling: Whether to raise exceptions (True) or log warnings (False)
        """
        self.provider_name = "pubchem"
        self.strict_error_handling = strict_error_handling

        # Rate limiter (5 req/sec)
        self.rate_limiter = TokenBucket(rate=rate, capacity=int(rate * 2))

        # Circuit breaker
        self.circuit_breaker = CircuitBreaker(
            provider=self.provider_name,
            failure_threshold=circuit_breaker_threshold,
            recovery_timeout=circuit_breaker_timeout,
        )

        # Thread pool for sync API calls
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self._fetch_strategies = {
            "compound": self._fetch_compounds,
            "substance": self._fetch_substances,
            "assay": self._fetch_assays,
        }

    async def __aenter__(self) -> Self:
        """Enter async context manager.

        Initializes resources if needed (currently just ThreadPool which is init in __init__).
        """
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager.

        Closes the thread pool.
        """
        await self.close()

    async def fetch(
        self,
        entity_type: str,
        query: str | None = None,
        watermark: Watermark | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records from PubChem."""
        # Apply rate limiting
        await self.rate_limiter.acquire()

        strategy = self._fetch_strategies.get(entity_type)
        if not strategy:
             raise ValueError(
                f"Unsupported entity type: {entity_type}. "
                f"Supported: {', '.join(self._fetch_strategies.keys())}"
            )

        # Pass arguments as keyword to avoid signature mismatch
        async for record in strategy(query=query, watermark=watermark, limit=limit):
             yield record

    async def _fetch_batch_safe(self, cid_batch: list[int]) -> list[Any]:
        """Fetch a batch of CIDs safely using circuit breaker."""
        try:
            return await self.circuit_breaker.call(
                self._run_in_executor, pcp.get_compounds, cid_batch, "cid"
            )
        except Exception:
            logger.error(
                "PubChem compound batch fetch failed",
                exc_info=True,
                extra={"batch_start": cid_batch[0], "batch_end": cid_batch[-1]},
            )
            if self.strict_error_handling:
                raise
            return []

    async def _fetch_compounds_incremental(
        self, watermark: Watermark, limit: int | None
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch compounds incrementally using a watermark."""
        fetched = 0
        start_cid = int(watermark) if watermark else 1
        batch_size = 100
        current_cid = start_cid

        while not limit or fetched < limit:
            await self.rate_limiter.acquire()
            cid_batch = list(range(current_cid, current_cid + batch_size))

            compounds = await self._fetch_batch_safe(cid_batch)
            if not compounds:
                # If safe fetch returns empty due to error (and not strict), we continue
                # But if it returns empty because no data? pcp returns [] if no data.
                # If error occurred and suppressed, we skip batch.
                pass

            for compound in compounds:
                if limit and fetched >= limit:
                    break
                yield self._compound_to_dict(compound)
                fetched += 1

            current_cid += batch_size

    async def _fetch_compounds(
        self,
        query: str | None,
        watermark: Watermark | None,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch compounds from PubChem."""
        if not query and watermark is None:
            raise ValueError("Either query or watermark must be provided for compound fetch")

        if query:
            async for record in self._fetch_by_query(query, limit):
                yield record
        else:
            async for record in self._fetch_compounds_incremental(watermark, limit):
                yield record

    async def _fetch_by_query(self, query: str, limit: int | None) -> AsyncIterator[dict[str, Any]]:
         """Fetch compounds by query."""
         await self.rate_limiter.acquire()
         compounds = await self.circuit_breaker.call(
            self._run_in_executor, pcp.get_compounds, query, "name"
         )
         for i, compound in enumerate(compounds or []):
            if limit and i >= limit:
                break
            yield self._compound_to_dict(compound)

    async def _fetch_substances(
        self,
        query: str | None,
        watermark: Watermark | None,
        limit: int | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch substances from PubChem."""
        if not query:
            raise ValueError("Query is required for substance search")

        # Watermark ignored

        fetched = 0
        await self.rate_limiter.acquire()

        substances = await self.circuit_breaker.call(
            self._run_in_executor,
            pcp.get_substances,
            query,
            "name",
        )

        for substance in substances or []:
            if limit and fetched >= limit:
                break
            yield self._substance_to_dict(substance)
            fetched += 1

    async def _fetch_assays(
        self,
        query: str | None,
        watermark: Watermark | None,
        limit: int | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch assays from PubChem."""
        if not query:
             raise ValueError("Query is required for assay search")

        # Watermark ignored

        fetched = 0
        await self.rate_limiter.acquire()

        assays = await self.circuit_breaker.call(
            self._run_in_executor,
            pcp.get_assays,
            query,
        )

        for assay in assays or []:
            if limit and fetched >= limit:
                break
            yield self._assay_to_dict(assay)
            fetched += 1

    def _compound_to_dict(self, compound: pcp.Compound) -> dict[str, Any]:
        """Convert pubchempy Compound to dictionary.

        Args:
            compound: PubChemPy Compound object

        Returns:
            Dictionary with compound data
        """
        return {
            "cid": compound.cid,
            "molecular_formula": compound.molecular_formula,
            "molecular_weight": compound.molecular_weight,
            "canonical_smiles": compound.canonical_smiles,
            "isomeric_smiles": compound.isomeric_smiles,
            "inchi": compound.inchi,
            "inchikey": compound.inchikey,
            "iupac_name": compound.iupac_name,
            "charge": compound.charge,
            "complexity": compound.complexity,
            "h_bond_acceptor_count": compound.h_bond_acceptor_count,
            "h_bond_donor_count": compound.h_bond_donor_count,
            "rotatable_bond_count": compound.rotatable_bond_count,
            "fingerprint": compound.fingerprint,
        }

    def _substance_to_dict(self, substance: pcp.Substance) -> dict[str, Any]:
        """Convert pubchempy Substance to dictionary.

        Args:
            substance: PubChemPy Substance object

        Returns:
            Dictionary with substance data
        """
        return {
            "sid": substance.sid,
            "source_name": substance.source_name,
            "source_id": substance.source_id,
            "cids": substance.standardized_cids,
            "synonyms": substance.synonyms,
        }

    def _assay_to_dict(self, assay: dict[str, Any]) -> dict[str, Any]:
        """Convert assay data to standardized dictionary.

        Args:
            assay: Raw assay data

        Returns:
            Dictionary with assay data
        """
        return {
            "aid": assay.get("aid"),
            "name": assay.get("name"),
            "description": assay.get("description"),
            "protocol": assay.get("protocol"),
            "target": assay.get("target"),
        }

    async def _run_in_executor(self, func: Any, *args: Any) -> Any:
        """Run synchronous function in thread pool.

        Args:
            func: Synchronous function to run
            *args: Arguments to pass to function

        Returns:
            Function result
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.thread_pool, func, *args)

    async def health_check(self) -> HealthStatus:
        """Check PubChem API health status.

        Implements DataSourcePort.health_check() interface.

        Performs lightweight query (fetch single compound) to test API availability.

        Returns:
            HealthStatus enum value

        Example:
            >>> client = PubChemClient()
            >>> status = await client.health_check()
            >>> print(f"PubChem is {status.value}")
        """
        try:
            # Lightweight query: fetch water (CID 962)
            await self.rate_limiter.acquire()

            compound = await self.circuit_breaker.call(
                self._run_in_executor,
                pcp.get_compounds,
                962,
                "cid",
            )

            if compound:
                return assess_health_from_circuit_breaker(self.circuit_breaker)
            else:
                return HealthStatus.DEGRADED

        except Exception:
            return HealthStatus.UNHEALTHY

    async def close(self) -> None:
        """Close thread pool."""
        self.thread_pool.shutdown(wait=True)

    async def aclose(self) -> None:
        """Gracefully close resources.

        Implements DataSourcePort.aclose().
        """
        await self.close()

    def __repr__(self) -> str:
        """String representation."""
        return f"PubChemClient(rate={self.rate_limiter.rate})"
