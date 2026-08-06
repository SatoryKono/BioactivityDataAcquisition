"""PubChem adapter factory for composition-layer wiring only."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import cast

from bioetl.composition.factories.datasource.adapter_helpers import (
    AdapterHelpersFactory,
)
from bioetl.domain.ports import ErrorHandlerPort, LoggerPort, MetricsPort
from bioetl.infrastructure.adapters.common import SyncAdapterDependencyContext
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter
from bioetl.infrastructure.adapters.pubchem import PubChemAdapter
from bioetl.infrastructure.adapters.pubchem.entity_mapper import PubChemEntityMapper
from bioetl.infrastructure.adapters.pubchem.fetch_strategies import (
    PubChemFetchStrategies,
)
from bioetl.infrastructure.config.source_config_loader import load_source_config

__all__ = ["PubChemRuntimeDependencies", "create_pubchem_adapter"]


@dataclass(frozen=True, slots=True)
class PubChemRuntimeDependencies:
    """Composition-owned runtime collaborators for the PubChem adapter."""

    error_handler: ErrorHandlerPort
    request_collector: APIRequestCollector
    entity_mapper: PubChemEntityMapper
    fetch_strategies: PubChemFetchStrategies
    dependency_context: SyncAdapterDependencyContext | None = None


def _resolve_rate_limit(provider: str) -> tuple[float, int]:
    """Resolve provider rate-limit config with stable defaults."""
    try:
        source_config = load_source_config(provider)
    except ValueError:
        return 5.0, 10
    return (
        source_config.rate_limit.requests_per_second,
        source_config.rate_limit.burst,
    )


def _resolve_circuit_breaker(provider: str) -> tuple[int, int]:
    """Resolve provider circuit-breaker config with stable defaults."""
    try:
        source_config = load_source_config(provider)
    except ValueError:
        return 5, 300
    return (
        source_config.circuit_breaker.failure_threshold,
        source_config.circuit_breaker.recovery_timeout,
    )


def _create_executor_runner(
    thread_pool: ThreadPoolExecutor,
) -> Callable[..., Awaitable[object]]:
    """Create an async executor bridge bound to one injected thread pool."""

    async def run_in_executor(
        func: Callable[..., object],
        *args: object,
    ) -> object:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(thread_pool, func, *args)

    return run_in_executor


def _build_runtime_dependencies(
    *,
    logger: LoggerPort,
    metrics: MetricsPort | None,
    rate_limiter: TokenBucketRateLimiter,
    circuit_breaker: CircuitBreakerGuard,
    thread_pool: ThreadPoolExecutor,
    error_handler: ErrorHandlerPort | None,
    request_collector: APIRequestCollector | None,
    entity_mapper: PubChemEntityMapper | None,
    fetch_strategies: PubChemFetchStrategies | None,
) -> PubChemRuntimeDependencies:
    """Build PubChem runtime collaborators at the composition edge."""
    dependency_context: SyncAdapterDependencyContext | None = None
    if error_handler is None or request_collector is None:
        helper_services = AdapterHelpersFactory.create_sync_helpers(
            provider="pubchem",
            logger=logger,
            metrics=metrics,
        )
        error_handler = error_handler or helper_services.error_handler
        request_collector = request_collector or helper_services.request_collector
        dependency_context = SyncAdapterDependencyContext(
            metrics=helper_services.metrics,
            error_handler=error_handler,
            request_collector=request_collector,
        )

    mapper = entity_mapper or PubChemEntityMapper()
    strategies = fetch_strategies or PubChemFetchStrategies(
        mapper=mapper,
        transport={
            "logger": logger,
            "rate_limiter": rate_limiter,
            "circuit_breaker": circuit_breaker,
            "run_in_executor": _create_executor_runner(thread_pool),
        },
        provider_name=PubChemAdapter.provider_name,
        request_collector=request_collector,
    )
    return PubChemRuntimeDependencies(
        error_handler=error_handler,
        request_collector=request_collector,
        entity_mapper=mapper,
        fetch_strategies=strategies,
        dependency_context=dependency_context,
    )


def create_pubchem_adapter(
    http_client: object | None = None,
    logger: LoggerPort | None = None,
    settings: object | None = None,
    **kwargs: object,
) -> PubChemAdapter:
    """Create PubChem adapter with composition-owned runtime assembly."""
    if logger is None:
        raise ValueError("PubChem adapter requires logger")

    del http_client, settings
    default_rate, default_capacity = _resolve_rate_limit("pubchem")
    default_cb_threshold, default_cb_timeout = _resolve_circuit_breaker("pubchem")
    rate = cast(float, kwargs.pop("rate", default_rate))
    capacity = cast(int, kwargs.pop("capacity", default_capacity))
    cb_threshold = cast(
        int,
        kwargs.pop("circuit_breaker_threshold", default_cb_threshold),
    )
    cb_timeout = cast(
        int,
        kwargs.pop("circuit_breaker_timeout", default_cb_timeout),
    )
    max_workers = cast(int, kwargs.pop("max_workers", 4))
    strict_error_handling = cast(bool, kwargs.pop("strict_error_handling", False))
    metrics = cast("MetricsPort | None", kwargs.pop("metrics", None))
    error_handler = cast("ErrorHandlerPort | None", kwargs.pop("error_handler", None))
    request_collector = cast(
        "APIRequestCollector | None",
        kwargs.pop("request_collector", None),
    )
    entity_mapper = cast(
        "PubChemEntityMapper | None", kwargs.pop("entity_mapper", None)
    )
    fetch_strategies = cast(
        "PubChemFetchStrategies | None",
        kwargs.pop("fetch_strategies", None),
    )

    rate_limiter = TokenBucketRateLimiter(
        rate=rate,
        capacity=capacity,
        provider="pubchem",
    )
    circuit_breaker = CircuitBreakerGuard(
        provider="pubchem",
        failure_threshold=cb_threshold,
        recovery_timeout=cb_timeout,
        metrics=metrics,
    )
    thread_pool = ThreadPoolExecutor(max_workers=max_workers)
    try:
        runtime_dependencies = _build_runtime_dependencies(
            logger=logger,
            metrics=metrics,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            thread_pool=thread_pool,
            error_handler=error_handler,
            request_collector=request_collector,
            entity_mapper=entity_mapper,
            fetch_strategies=fetch_strategies,
        )
        return PubChemAdapter(
            logger=logger,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            thread_pool=thread_pool,
            owns_thread_pool=True,
            strict_error_handling=strict_error_handling,
            dependency_context=runtime_dependencies.dependency_context,
            error_handler=runtime_dependencies.error_handler,
            request_collector=runtime_dependencies.request_collector,
            entity_mapper=runtime_dependencies.entity_mapper,
            fetch_strategies=runtime_dependencies.fetch_strategies,
        )
    except Exception:
        # Composition owns the pool until the adapter is successfully constructed.
        thread_pool.shutdown(wait=False, cancel_futures=True)
        raise
