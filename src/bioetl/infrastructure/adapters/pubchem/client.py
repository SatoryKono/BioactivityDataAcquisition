"""PubChem API client adapter.

Implements RULES.md Appendix A - PubChem specifications.

Requirements:
- Uses pubchempy library (legacy sync)
- Rate limit: 5 req/sec (TokenBucket)
- Health: lightweight query
- Entities: compounds, substances, assays, bioassays

DTO Support:
- fetch_as_models(): Returns typed DTO models (PubChemCompoundRecord)
- fetch(): Returns raw dicts (backward compatible)

Documentation: https://pubchemdocs.ncbi.nlm.nih.gov/pug-rest
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

import pubchempy as pcp
from pydantic import BaseModel

from bioetl.domain.entities.pubchem import PubChemCompoundRecord
from bioetl.domain.exceptions import CircuitBreakerOpenError
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.sync_base import BaseSyncAdapter

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
    from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket


# Mapping from entity_type to DTO model class
PUBCHEM_DTO_MODELS: dict[str, type[BaseModel]] = {
    "compound": PubChemCompoundRecord,
}


class PubChemAdapter(BaseSyncAdapter):
    """PubChem API adapter implementing DataSourcePort.

    Provides access to chemical compound data from PubChem database.
    Uses pubchempy library which is synchronous, so runs in ThreadPoolExecutor.

    All dependencies are injected via constructor (Composition Root pattern).

    Example:
        >>> # Dependencies created in Composition Root
        >>> rate_limiter = TokenBucket(rate=5.0, capacity=10)
        >>> circuit_breaker = CircuitBreaker(provider="pubchem")
        >>> thread_pool = ThreadPoolExecutor(max_workers=4)
        >>> adapter = PubChemAdapter(
        ...     logger=logger,
        ...     rate_limiter=rate_limiter,
        ...     circuit_breaker=circuit_breaker,
        ...     thread_pool=thread_pool,
        ... )
        >>> compounds = [c async for c in adapter.fetch("compound", query="aspirin", limit=10)]
        >>> [c['cid'] for c in compounds]  # List of compound IDs
        [2244, 2245, 2246]

    """

    provider_name: str = "pubchem"

    def __init__(
        self,
        logger: LoggerPort,
        rate_limiter: TokenBucket,
        circuit_breaker: CircuitBreaker,
        thread_pool: ThreadPoolExecutor,
        strict_error_handling: bool = False,
    ) -> None:
        """Initialize PubChem client.

        All infrastructure components are injected from Composition Root.

        Args:
            logger: LoggerPort instance for structured logging.
            rate_limiter: Pre-configured token bucket rate limiter.
            circuit_breaker: Pre-configured circuit breaker.
            thread_pool: Pre-configured thread pool executor.
            strict_error_handling: Whether to raise exceptions or log warnings.

        """
        super().__init__(
            logger=logger,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            thread_pool=thread_pool,
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

        strategy = self._fetch_strategies.get(entity_type)
        if not strategy:
            raise ValueError(
                f"Unsupported entity type: {entity_type}. "
                f"Supported: {', '.join(self._fetch_strategies.keys())}"
            )

        # Pass arguments as keyword to avoid signature mismatch
        async for record in strategy(query=query, limit=limit):  # type: ignore[operator]
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

        Uses connectivity_smiles/smiles (replaces deprecated canonical/isomeric_smiles).
        """
        return {
            "cid": compound.cid,
            "molecular_formula": compound.molecular_formula,
            "molecular_weight": compound.molecular_weight,
            # Use connectivity_smiles (replaces deprecated canonical_smiles)
            "canonical_smiles": compound.connectivity_smiles,
            # Use smiles (replaces deprecated isomeric_smiles)
            "isomeric_smiles": compound.smiles,
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
        """Convert pubchempy Substance to dictionary."""
        return {
            "sid": substance.sid,
            "source_name": substance.source_name,
            "source_id": substance.source_id,
            "cids": substance.standardized_cids,
            "synonyms": substance.synonyms,
        }

    def _assay_to_dict(self, assay: dict[str, Any]) -> dict[str, Any]:
        """Convert assay data to standardized dictionary."""
        return {
            "aid": assay.get("aid"),
            "name": assay.get("name"),
            "description": assay.get("description"),
            "protocol": assay.get("protocol"),
            "target": assay.get("target"),
        }

    async def fetch_as_models(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        *,
        validate: bool = True,
    ) -> AsyncIterator[BaseModel]:
        """Fetch records from PubChem as typed DTO models.

        Returns Pydantic DTO models instead of raw dicts for type safety.
        Uses domain DTOs with extra='forbid' to detect API changes.

        Args:
            entity_type: Type of entity (compound, substance, assay)
            limit: Maximum number of records to fetch
            query: Search query string
            filter_ids: Unused for PubChem
            filter_field: Unused for PubChem
            validate: If True, validate with model_validate (strict).
                     If False, use model_construct (skip validation, faster).

        Yields:
            Typed DTO models (PubChemCompoundRecord for compound)

        Raises:
            ValueError: If entity_type is not supported for DTO conversion

        Example:
            >>> async for compound in adapter.fetch_as_models("compound", query="aspirin"):
            ...     print(compound.cid, compound.canonical_smiles)

        """
        model_class = PUBCHEM_DTO_MODELS.get(entity_type)
        if model_class is None:
            raise ValueError(
                f"No DTO model for entity_type '{entity_type}'. "
                f"Supported: {', '.join(PUBCHEM_DTO_MODELS.keys())}"
            )

        async for record in self.fetch(
            entity_type=entity_type,
            limit=limit,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
        ):
            # Convert CID to string for DTO (domain DTOs use str for IDs)
            if "cid" in record and record["cid"] is not None:
                record["cid"] = str(record["cid"])

            if validate:
                yield model_class.model_validate(record)
            else:
                yield model_class.model_construct(**record)

    async def _probe_health(self) -> HealthStatus:
        """Perform PubChem health probe using lightweight water query (CID 962)."""
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
                return self._fallback_health_status()

            self.logger.warning(
                "health_check_degraded",
                provider=self.provider_name,
                reason="empty_response",
            )
            return HealthStatus.DEGRADED

        except CircuitBreakerOpenError:
            # Circuit breaker open - return UNHEALTHY directly
            self.logger.warning(
                "health_check_circuit_open",
                provider=self.provider_name,
            )
            return HealthStatus.UNHEALTHY

        except Exception as e:
            error_type = self._error_handler.get_error_type(e)
            self.logger.warning(
                "health_check_failed",
                provider=self.provider_name,
                error_type=error_type.value,
                error=str(e),
            )
            raise  # Let base class handle via _fallback_health_status()

    def _get_health_endpoint(self) -> str:
        """Get the PubChem health check endpoint."""
        return "/rest/pug/compound/cid/962/property/MolecularFormula/JSON"

    def __repr__(self) -> str:
        """Return string representation."""
        return f"PubChemAdapter(rate={self.rate_limiter.rate})"
