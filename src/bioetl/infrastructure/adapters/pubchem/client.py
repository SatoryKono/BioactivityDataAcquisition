"""PubChem API client adapter.

Implements RULES.md Appendix A - PubChem specifications.

Requirements:
- Uses pubchempy library (legacy sync)
- Rate limit: 5 req/sec (TokenBucket)
- Health: lightweight query
- Entities: compounds, substances, assays, bioassays

Documentation: https://pubchemdocs.ncbi.nlm.nih.gov/pug-rest
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pubchempy as pcp

from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.http.health import (
    assess_health_from_circuit_breaker,
)
from bioetl.infrastructure.adapters.sync_base import BaseSyncAdapter


class PubChemClient(BaseSyncAdapter):
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
        logger: LoggerPort,
        rate: float = 5.0,  # 5 req/sec per RULES.md
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 300,
        max_workers: int = 4,
        strict_error_handling: bool = False,
    ) -> None:
        """Initialize PubChem client.

        Args:
            logger: LoggerPort instance for structured logging.
            rate: Requests per second (default: 5.0 per RULES.md).
            circuit_breaker_threshold: Failures before opening circuit.
            circuit_breaker_timeout: Recovery timeout in seconds.
            max_workers: Thread pool size.
            strict_error_handling: Whether to raise exceptions or log warnings.

        """
        super().__init__(
            rate=rate,
            logger=logger,
            circuit_breaker_threshold=circuit_breaker_threshold,
            circuit_breaker_timeout=circuit_breaker_timeout,
            max_workers=max_workers,
            strict_error_handling=strict_error_handling,
        )

        self._fetch_strategies = {
            "compound": self._fetch_compounds,
            "substance": self._fetch_substances,
            "assay": self._fetch_assays,
        }

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records from PubChem."""
        # Note: filter_ids and filter_field are ignored for PubChem -
        # filtering should be done via query parameter
        _ = filter_ids, filter_field  # Mark as intentionally unused
        # Apply rate limiting
        await self.rate_limiter.acquire()

        strategy = self._fetch_strategies.get(entity_type)
        if not strategy:
            raise ValueError(
                f"Unsupported entity type: {entity_type}. "
                f"Supported: {', '.join(self._fetch_strategies.keys())}"
            )

        # Pass arguments as keyword to avoid signature mismatch
        async for record in strategy(query=query, limit=limit):
            yield record

    async def _fetch_compounds(
        self,
        query: str | None,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch compounds from PubChem."""
        if not query:
            raise ValueError("Query is required for compound fetch")

        async for record in self._fetch_by_query(query, limit):
            yield record

    async def _fetch_by_query(
        self, query: str, limit: int | None
    ) -> AsyncIterator[dict[str, Any]]:
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
        limit: int | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch substances from PubChem."""
        if not query:
            raise ValueError("Query is required for substance search")

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
        limit: int | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch assays from PubChem."""
        if not query:
            raise ValueError("Query is required for assay search")

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

    def __repr__(self) -> str:
        """Return string representation."""
        return f"PubChemClient(rate={self.rate_limiter.rate})"
