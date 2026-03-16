"""PubChem API client adapter.

Implements DataSourcePort for PubChem compound retrieval.

Requirements:
- Uses pubchempy library (legacy sync)
- Rate limit: 5 req/sec (TokenBucketRateLimiter)
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

from bioetl.domain.exceptions import BioETLError, CircuitBreakerOpenError, NetworkError
from bioetl.domain.types import HealthStatus, JsonDict
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.filterable_mixin import FilterableStubMixin
from bioetl.infrastructure.adapters.pubchem.client_builders import (
    _create_default_pubchem_entity_mapper,
    _create_default_pubchem_fetch_strategies,
    _create_default_pubchem_request_collector,
)
from bioetl.infrastructure.adapters.pubchem.client_model_mixin import (
    PubChemAdapterModelMixin,
)
from bioetl.infrastructure.adapters.pubchem.entity_mapper import PubChemEntityMapper
from bioetl.infrastructure.adapters.sync_base import BaseSyncAdapter

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import ErrorHandlerPort, LoggerPort
    from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
    from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter
    from bioetl.infrastructure.adapters.pubchem.fetch_strategies import (
        PubChemFetchStrategies,
    )

PUBCHEM_HEALTH_ERRORS = (
    BioETLError,
    NetworkError,
    OSError,
    ValueError,
    TypeError,
    RuntimeError,
    Exception,
)


class PubChemAdapter(PubChemAdapterModelMixin, FilterableStubMixin, BaseSyncAdapter):
    """PubChem API adapter implementing DataSourcePort.

    Provides access to chemical compound data from PubChem database.
    Uses pubchempy library which is synchronous, so runs in ThreadPoolExecutor.

    All dependencies are injected via constructor (Composition Root pattern).

    Uses FilterableStubMixin for:
    - fetch_multi_filtered: Not supported by PubChem API
    - fetch_filtered_with_fallback: Delegates to fetch_filtered (CIDs are stable)

    Example:
        >>> # Dependencies created in Composition Root
        >>> rate_limiter = TokenBucketRateLimiter(rate=5.0, capacity=10)
        >>> circuit_breaker = CircuitBreakerGuard(provider="pubchem")
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
        rate_limiter: TokenBucketRateLimiter,
        circuit_breaker: CircuitBreakerGuard,
        thread_pool: ThreadPoolExecutor,
        strict_error_handling: bool = False,
        *,
        error_handler: ErrorHandlerPort | None = None,
        owns_thread_pool: bool = False,
        request_collector: APIRequestCollector | None = None,
        entity_mapper: PubChemEntityMapper | None = None,
        fetch_strategies: PubChemFetchStrategies | None = None,
    ) -> None:
        """Initialize PubChem client.

        All infrastructure components are injected from Composition Root.

        Args:
            logger: LoggerPort instance for structured logging.
            rate_limiter: Pre-configured token bucket rate limiter.
            circuit_breaker: Pre-configured circuit breaker.
            thread_pool: Pre-configured thread pool executor.
            strict_error_handling: Whether to raise exceptions or log warnings.
            error_handler: Pre-built error handler (optional, injected by
                    AdapterHelpersFactory). Falls back to inline ErrorService.
            owns_thread_pool: Whether this adapter owns the injected thread pool
                and should shut it down on close.
            request_collector: Pre-built request collector (optional, injected by
                    AdapterHelpersFactory). Falls back to inline APIRequestCollector.
            entity_mapper: Pre-built entity mapper (optional).
            fetch_strategies: Pre-built fetch strategies (optional).

        """
        super().__init__(
            logger=logger,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            thread_pool=thread_pool,
            strict_error_handling=strict_error_handling,
            error_handler=error_handler,
            owns_thread_pool=owns_thread_pool,
        )
        self._mapper = (
            entity_mapper
            if entity_mapper is not None
            else _create_default_pubchem_entity_mapper()
        )
        self._request_collector = (
            request_collector
            if request_collector is not None
            else _create_default_pubchem_request_collector()
        )
        self._strategies = (
            fetch_strategies
            if fetch_strategies is not None
            else _create_default_pubchem_fetch_strategies(
                logger=logger,
                rate_limiter=rate_limiter,
                circuit_breaker=circuit_breaker,
                mapper=self._mapper,
                run_in_executor=self._run_in_executor,
                provider_name=self.provider_name,
                request_collector=self._request_collector,
            )
        )

    async def _fetch_compound(
        self, query: str | None, limit: int | None
    ) -> AsyncIterator[JsonDict]:  # Any: untyped API JSON record
        """Fetch compounds by query.

        Args:
            query: Compound name or search string; required, raises ValueError if None.
            limit: Optional maximum number of compounds to yield.

        Yields:
            Raw compound records from the PubChem API.

        Raises:
            ValueError: If query is None or empty.
        """
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

    async def _probe_health(self) -> HealthStatus:
        """Perform PubChem health probe using lightweight water query (CID 962).

        Returns:
            HealthStatus reflecting the current PubChem API availability via circuit breaker state.
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
        """Get the PubChem health check endpoint.

        Returns:
            Endpoint path string used for PubChem health probe requests.
        """
        return "/rest/pug/compound/cid/962/property/MolecularFormula/JSON"
