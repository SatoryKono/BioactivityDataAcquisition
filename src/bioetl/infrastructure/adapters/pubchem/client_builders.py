"""Factory helpers for PubChem adapter defaults."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from pydantic import BaseModel

from bioetl.domain.entities.pubchem import PubchemMoleculeRecord
from bioetl.infrastructure.adapters.common.adapter_defaults import (
    create_default_request_collector,
)
from bioetl.infrastructure.adapters.pubchem.entity_mapper import PubChemEntityMapper

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
    from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter
    from bioetl.infrastructure.adapters.pubchem.fetch_strategies import (
        PubChemFetchStrategies,
    )

PUBCHEM_DTO_MODELS: dict[str, type[BaseModel]] = {
    "compound": PubchemMoleculeRecord,
}


def _create_default_pubchem_entity_mapper() -> PubChemEntityMapper:
    """Create default entity mapper for non-DI call sites."""
    return PubChemEntityMapper()


def _create_default_pubchem_request_collector() -> APIRequestCollector:
    """Create default request collector for non-DI call sites."""
    return create_default_request_collector()


def _create_default_pubchem_fetch_strategies(
    *,
    logger: LoggerPort,
    rate_limiter: TokenBucketRateLimiter,
    circuit_breaker: CircuitBreakerGuard,
    mapper: PubChemEntityMapper,
    run_in_executor: Callable[..., Awaitable[object]],
    provider_name: str,
    request_collector: APIRequestCollector,
) -> PubChemFetchStrategies:
    """Create default fetch strategies for non-DI call sites.

    Args:
        logger: Logger port for structured logging.
        rate_limiter: Token bucket rate limiter for API throttling.
        circuit_breaker: Circuit breaker for fault tolerance.
        mapper: Entity mapper for converting API responses to domain records.
        run_in_executor: Callable to run synchronous pubchempy calls in a thread pool.
        provider_name: Provider identifier used in metrics labels.
        request_collector: Collector for tracking API request metadata.

    Returns:
        Configured PubChemFetchStrategies instance.
    """
    from bioetl.infrastructure.adapters.pubchem.fetch_strategies import (
        PubChemFetchStrategies,
    )

    return PubChemFetchStrategies(
        mapper=mapper,
        transport={
            "logger": logger,
            "rate_limiter": rate_limiter,
            "circuit_breaker": circuit_breaker,
            "run_in_executor": run_in_executor,
        },
        provider_name=provider_name,
        request_collector=request_collector,
    )


__all__ = [
    "PUBCHEM_DTO_MODELS",
    "_create_default_pubchem_entity_mapper",
    "_create_default_pubchem_fetch_strategies",
    "_create_default_pubchem_request_collector",
]
