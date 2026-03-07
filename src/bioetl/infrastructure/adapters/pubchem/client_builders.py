"""Factory helpers for PubChem adapter defaults."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from pydantic import BaseModel

from bioetl.domain.entities.pubchem import PubchemMoleculeRecord
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.pubchem.entity_mapper import PubChemEntityMapper

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
    from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
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
    return APIRequestCollector()


def _create_default_pubchem_fetch_strategies(
    *,
    logger: LoggerPort,
    rate_limiter: TokenBucket,
    circuit_breaker: CircuitBreaker,
    mapper: PubChemEntityMapper,
    run_in_executor: Callable[..., Awaitable[object]],
    provider_name: str,
    request_collector: APIRequestCollector,
) -> PubChemFetchStrategies:
    """Create default fetch strategies for non-DI call sites."""
    from bioetl.infrastructure.adapters.pubchem.fetch_strategies import (
        PubChemFetchStrategies,
    )

    return PubChemFetchStrategies(
        logger=logger,
        rate_limiter=rate_limiter,
        circuit_breaker=circuit_breaker,
        mapper=mapper,
        run_in_executor=run_in_executor,
        provider_name=provider_name,
        request_collector=request_collector,
    )


__all__ = [
    "PUBCHEM_DTO_MODELS",
    "_create_default_pubchem_entity_mapper",
    "_create_default_pubchem_fetch_strategies",
    "_create_default_pubchem_request_collector",
]
