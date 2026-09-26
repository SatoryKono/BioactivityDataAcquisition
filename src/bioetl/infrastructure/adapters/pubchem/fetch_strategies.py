"""Thin PubChem fetch facade; heavy query/search/flow logic lives in helpers."""

from __future__ import annotations

__all__ = ["PubChemFetchStrategies"]

from typing import TYPE_CHECKING, cast

from bioetl.infrastructure.adapters.common.error_bundles import (
    build_common_network_error_bundle,
)
from bioetl.infrastructure.adapters.pubchem._fetch_strategy_identifiers import (
    _PubChemIdentifierFetchMixin,
)
from bioetl.infrastructure.adapters.pubchem._fetch_strategy_search import (
    _PubChemSearchFetchMixin,
)
from bioetl.infrastructure.adapters.pubchem._fetch_strategy_transport import (
    resolve_transport_bag,
)
from bioetl.infrastructure.adapters.pubchem.constants import PUBCHEM_API_BASE
from bioetl.infrastructure.adapters.pubchem.fetch_flow import PubChemFetchFlow
from bioetl.infrastructure.adapters.pubchem.response_mapper import (
    PubChemResponseMapper,
    normalize_pubchem_results,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
    from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter
    from bioetl.infrastructure.adapters.pubchem.entity_mapper import PubChemEntityMapper


class PubChemFetchStrategies(
    _PubChemIdentifierFetchMixin,
    _PubChemSearchFetchMixin,
):
    """Helper class for PubChem fetch operations."""

    FETCH_STRATEGY_ERRORS = build_common_network_error_bundle(
        KeyError,
    )

    def __init__(
        self,
        mapper: PubChemEntityMapper,
        transport: dict[str, object] | None = None,
        provider_name: str = "pubchem",
        request_collector: APIRequestCollector | None = None,
        response_mapper: PubChemResponseMapper | None = None,
        fetch_flow: PubChemFetchFlow | None = None,
        **legacy: object,
    ) -> None:
        """Initialize fetch strategies.

        Prefer ``transport`` with keys logger/rate_limiter/circuit_breaker/
        run_in_executor. Transitional/unit callers may pass them as kwargs.
        """
        resolved = resolve_transport_bag(transport, legacy)
        self._logger = cast("LoggerPort", resolved["logger"])
        self._rate_limiter = cast("TokenBucketRateLimiter", resolved["rate_limiter"])
        self._circuit_breaker = cast("CircuitBreakerGuard", resolved["circuit_breaker"])
        self._run_in_executor = cast(
            "Callable[..., Any]",  # Any: executor forwards arbitrary callable results.
            resolved["run_in_executor"],
        )
        self._mapper = mapper
        self._provider_name = provider_name
        self._request_collector = request_collector
        self._response_mapper = response_mapper or PubChemResponseMapper(mapper)
        self._fetch_flow = fetch_flow or PubChemFetchFlow(
            rate_limiter=self._rate_limiter,
            circuit_breaker=self._circuit_breaker,
            run_in_executor=self._run_in_executor,
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
