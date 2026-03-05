"""PubChem API client adapter.

Implements RULES.md Appendix A - PubChem specifications.

Requirements:
- Uses pubchempy library (legacy sync)
- Rate limit: 5 req/sec (TokenBucket)
- Health: lightweight query
- Entities: compounds, substances, assays, bioassays

Fetch modes:
- SMILES filtering: Primary mode - fetch compounds by SMILES list from CSV
- CID filtering: Optional - fetch compounds by CID list
- Query search: Legacy - search by compound name

DTO Support:
- fetch_as_models(): Returns typed DTO models (PubchemMoleculeRecord)
- fetch(): Returns raw dicts (backward compatible)

Documentation: https://pubchemdocs.ncbi.nlm.nih.gov/pug-rest
"""

from __future__ import annotations

__all__ = ["PUBCHEM_HEALTH_ERRORS", "PubChemAdapter"]


from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

import pubchempy as pcp
from pydantic import BaseModel

from bioetl.domain.entities.pubchem import PubchemMoleculeRecord
from bioetl.domain.exceptions import BioETLError, CircuitBreakerOpenError, NetworkError
from bioetl.domain.types import HealthStatus, JsonDict
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.filterable_mixin import FilterableStubMixin
from bioetl.infrastructure.adapters.pubchem.constants import PUBCHEM_API_BASE
from bioetl.infrastructure.adapters.pubchem.entity_mapper import PubChemEntityMapper
from bioetl.infrastructure.adapters.sync_base import BaseSyncAdapter

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.models.metadata import SourceMetadata
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
    from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket


# Mapping from entity_type to DTO model class
PUBCHEM_DTO_MODELS: dict[str, type[BaseModel]] = {
    "compound": PubchemMoleculeRecord,
}

PUBCHEM_HEALTH_ERRORS = (
    BioETLError,
    NetworkError,
    OSError,
    ValueError,
    TypeError,
    RuntimeError,
    Exception,
)


class PubChemAdapter(FilterableStubMixin, BaseSyncAdapter):
    """PubChem API adapter implementing DataSourcePort.

    Provides access to chemical compound data from PubChem database.
    Uses pubchempy library which is synchronous, so runs in ThreadPoolExecutor.

    All dependencies are injected via constructor (Composition Root pattern).

    Uses FilterableStubMixin for:
    - fetch_multi_filtered: Not supported by PubChem API
    - fetch_filtered_with_fallback: Delegates to fetch_filtered (CIDs are stable)

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
        >>> # Each compound dict contains a 'cid' key with the PubChem compound ID
        >>> len(compounds)
        10

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
        self._mapper = PubChemEntityMapper()
        self._request_collector = APIRequestCollector()
        from bioetl.infrastructure.adapters.pubchem.fetch_strategies import (
            PubChemFetchStrategies,
        )

        self._strategies = PubChemFetchStrategies(
            logger=logger,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            mapper=self._mapper,
            run_in_executor=self._run_in_executor,
            provider_name=self.provider_name,
            request_collector=self._request_collector,
        )

    async def _fetch_compound(
        self, query: str | None, limit: int | None
    ) -> AsyncIterator[JsonDict]:  # Any: untyped API JSON record
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
    ) -> AsyncIterator[JsonDict]:  # Any: untyped API JSON record
        """Fetch records from PubChem. Supports SMILES/CID filtering and name search.

        Args:
            entity_type: Entity type identifier.
            limit: Maximum number of records to process.
            query: Search query string.
            filter_ids: List of identifiers to filter by.
            filter_field: Field name to apply filter on.
            offset: Offset.

        Returns:
            Async iterator yielding fetched records.
        """
        if filter_ids and filter_field:
            async for record in self.fetch_filtered(
                entity_type, filter_ids, filter_field, limit
            ):
                yield record
            return

        fetch_methods: dict[
            str,
            Callable[[], AsyncIterator[JsonDict]],  # Any: untyped API JSON record
        ] = {  # Any: untyped API JSON record
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
    ) -> AsyncIterator[JsonDict]:  # Any: untyped API JSON record
        """Fetch PubChem records by filter ID list. Implements FilterableDataSourcePort.

        Args:
            entity_type: Entity type identifier.
            filter_ids: List of identifiers to filter by.
            filter_field: Field name to apply filter on.
            limit: Maximum number of records to process.

        Returns:
            Async iterator yielding fetched records.
        """
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

    # fetch_multi_filtered and fetch_filtered_with_fallback are provided
    # by FilterableStubMixin (see class inheritance)

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
            Typed DTO models (PubchemMoleculeRecord for compound)

        Raises:
            ValueError: If entity_type is not supported for DTO conversion

        Example:
            >>> async for compound in adapter.fetch_as_models("compound", query="aspirin"):
            ...     logger.debug("compound_fetched", cid=compound.cid, smiles=compound.canonical_smiles)

        Returns:
            Async iterator yielding fetched records.
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

        except PUBCHEM_HEALTH_ERRORS as e:
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

    def get_source_metadata(self, api_version: str | None = None) -> SourceMetadata:
        """Get accumulated API request metadata for Bronze layer enrichment.

        Returns SourceMetadata with all recorded API requests and aggregated
        statistics (total_requests, avg_duration, total_bytes).

        The collector is cleared after calling this method to prepare for
        the next batch.

        Note:
            Since pubchempy doesn't expose raw HTTP response objects,
            metadata is based on estimated values (e.g., response sizes).

        Args:
            api_version: Optional API version to include in metadata.

        Returns:
            SourceMetadata with api_requests, total_requests, avg_request_duration_ms,
            and total_response_bytes populated from collected requests.

        """
        metadata = self._request_collector.to_source_metadata(
            source_type="api",
            url=PUBCHEM_API_BASE,
            api_version=api_version,
        )
        self._request_collector.clear()
        return metadata

    def clear_request_collector(self) -> None:
        """Clear the API request collector without generating metadata.

        Use this to reset the collector when metadata is not needed,
        for example during health checks or error recovery.
        """
        self._request_collector.clear()

    @property
    def request_count(self) -> int:
        """Get the number of recorded API requests since last clear."""
        return self._request_collector.request_count
