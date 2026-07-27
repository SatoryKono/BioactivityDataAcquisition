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

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, cast

import pubchempy as pcp

from bioetl.domain.exceptions import BioETLError, CircuitBreakerOpenError, NetworkError
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.filterable_mixin import FilterableStubMixin
from bioetl.infrastructure.adapters.pubchem._client_fetch_surface import (
    _PubChemClientFetchMixin,
)
from bioetl.infrastructure.adapters.pubchem.client_model_mixin import (
    PubChemAdapterModelMixin,
)
from bioetl.infrastructure.adapters.pubchem.entity_mapper import PubChemEntityMapper
from bioetl.infrastructure.adapters.sync_base import BaseSyncAdapter

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.common.dependency_context import (
        SyncAdapterDependencyContext,
    )
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


class PubChemAdapter(
    _PubChemClientFetchMixin,
    PubChemAdapterModelMixin,
    FilterableStubMixin,
    BaseSyncAdapter,
):
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
        ...     error_handler=error_handler,
        ...     request_collector=request_collector,
        ...     entity_mapper=entity_mapper,
        ...     fetch_strategies=fetch_strategies,
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
        dependency_context: SyncAdapterDependencyContext | None = None,
        owns_thread_pool: bool = False,
        entity_mapper: PubChemEntityMapper,
        **legacy_runtime: object,
    ) -> None:
        """Initialize PubChem client.

        Optional error_handler/request_collector/fetch_strategies may be passed
        via ``**legacy_runtime`` without growing the S107 parameter budget.
        """
        fetch_strategies = legacy_runtime.pop("fetch_strategies", None)
        error_handler = legacy_runtime.pop("error_handler", None)
        request_collector = legacy_runtime.pop("request_collector", None)
        if legacy_runtime:
            unexpected = ", ".join(sorted(str(k) for k in legacy_runtime))
            raise TypeError(
                f"PubChemAdapter() got unexpected keyword argument(s): {unexpected}"
            )
        if fetch_strategies is None:
            raise ValueError("PubChemAdapter requires fetch_strategies")
        if error_handler is None:
            raise ValueError("PubChemAdapter requires error_handler")
        super().__init__(
            logger=logger,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            thread_pool=thread_pool,
            strict_error_handling=strict_error_handling,
            dependency_context=dependency_context,
            error_handler=error_handler,  # type: ignore[arg-type]
            owns_thread_pool=owns_thread_pool,
        )
        self._mapper = entity_mapper
        request_collector_port = (
            dependency_context.request_collector
            if dependency_context is not None
            else request_collector
        )
        if request_collector_port is None:
            raise ValueError("PubChemAdapter requires request_collector")
        self._request_collector = cast("APIRequestCollector", request_collector_port)
        self._strategies = cast("PubChemFetchStrategies", fetch_strategies)

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
