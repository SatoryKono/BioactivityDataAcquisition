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
from typing import Any

import pubchempy as pcp

from bioetl.config import get_settings
from bioetl.domain.types import HealthStatus, Watermark
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
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

    def __init__(
        self,
        rate: float = 5.0,  # 5 req/sec per RULES.md
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 300,
        max_workers: int = 4,
    ) -> None:
        """Initialize PubChem client.

        Args:
            rate: Requests per second (default: 5.0 per RULES.md)
            circuit_breaker_threshold: Failures before opening circuit
            circuit_breaker_timeout: Recovery timeout in seconds
            max_workers: Thread pool size for sync operations
        """
        self.provider_name = "pubchem"

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

    async def fetch(
        self,
        entity_type: str,
        query: str | None = None,
        watermark: Watermark | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records from PubChem.

        Implements DataSourcePort.fetch() interface.

        Args:
            entity_type: Type of entity ('compound', 'substance', 'assay')
            query: Search query (name, formula, SMILES, etc.)
            watermark: Last checkpoint (CID for incremental load)
            limit: Maximum number of records

        Yields:
            Raw records as dictionaries

        Raises:
            ValueError: If entity_type is not supported
            CircuitBreakerOpenError: If circuit breaker is open

        Example:
            >>> client = PubChemClient()
            >>> # Search by name
            >>> async for compound in client.fetch("compound", query="caffeine", limit=5):
            ...     print(f"CID: {compound['cid']}, Name: {compound.get('iupac_name')}")
            >>> # Fetch by CID range (incremental)
            >>> async for compound in client.fetch("compound", watermark=1000, limit=100):
            ...     print(f"CID: {compound['cid']}")
        """
        # Apply rate limiting
        await self.rate_limiter.acquire()

        if entity_type == "compound":
            async for record in self._fetch_compounds(query, watermark, limit):
                yield record
        elif entity_type == "substance":
            async for record in self._fetch_substances(query, limit):
                yield record
        elif entity_type == "assay":
            async for record in self._fetch_assays(query, limit):
                yield record
        else:
            raise ValueError(
                f"Unsupported entity type: {entity_type}. "
                f"Supported: compound, substance, assay"
            )

    async def _fetch_compounds_incremental(
        self, watermark: Watermark, limit: int | None
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch compounds incrementally using a watermark."""
        fetched = 0
        start_cid = int(watermark) if isinstance(watermark, (int, str)) else 1
        batch_size = 100
        current_cid = start_cid

        while not limit or fetched < limit:
            await self.rate_limiter.acquire()
            cid_batch = list(range(current_cid, current_cid + batch_size))
            try:
                compounds = await self.circuit_breaker.call(
                    self._run_in_executor, pcp.get_compounds, cid_batch, "cid"
                )
                if not compounds:
                    break
                for compound in compounds:
                    if limit and fetched >= limit:
                        break
                    yield self._compound_to_dict(compound)
                    fetched += 1
                current_cid += batch_size
            except Exception as e:
                logger.error(
                    "PubChem compound batch fetch failed",
                    extra={
                        "cid_range_start": current_cid,
                        "cid_range_end": current_cid + batch_size,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                if get_settings().strict_error_handling:
                    raise
                current_cid += batch_size
                continue

    async def _fetch_compounds(
        self,
        query: str | None,
        watermark: Watermark | None,
        limit: int | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch compounds from PubChem."""
        if query:
            await self.rate_limiter.acquire()
            compounds = await self.circuit_breaker.call(
                self._run_in_executor, pcp.get_compounds, query, "name"
            )
            for i, compound in enumerate(compounds or []):
                if limit and i >= limit:
                    break
                yield self._compound_to_dict(compound)
        elif watermark:
            async for compound in self._fetch_compounds_incremental(watermark, limit):
                yield compound
        else:
            raise ValueError("Either query or watermark must be provided for compounds")

    async def _fetch_substances(
        self,
        query: str | None,
        limit: int | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch substances from PubChem.

        Args:
            query: Search query
            limit: Max records

        Yields:
            Substance records
        """
        fetched = 0

        if query:
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

        else:
            raise ValueError("Query is required for substance search")

    async def _fetch_assays(
        self,
        query: str | None,
        limit: int | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch assays from PubChem.

        Args:
            query: Search query (assay ID or target)
            limit: Max records

        Yields:
            Assay records
        """
        fetched = 0

        if query:
            await self.rate_limiter.acquire()

            # PubChem assay search via PUG REST API
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

        else:
            raise ValueError("Query is required for assay search")

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
        loop = asyncio.get_event_loop()
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
                # Check circuit breaker state
                cb_state = self.circuit_breaker.get_state()
                failure_count = self.circuit_breaker.get_failure_count()

                if cb_state.value == "CLOSED" and failure_count == 0:
                    return HealthStatus.HEALTHY
                elif failure_count <= 2:
                    return HealthStatus.DEGRADED
                else:
                    return HealthStatus.UNHEALTHY
            else:
                return HealthStatus.DEGRADED

        except Exception:
            return HealthStatus.UNHEALTHY

    async def close(self) -> None:
        """Close thread pool."""
        self.thread_pool.shutdown(wait=True)

    def __repr__(self) -> str:
        """String representation."""
        return f"PubChemClient(rate={self.rate_limiter.rate})"
