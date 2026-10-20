"""PubChem SDK executor timeout (#12008)."""

from __future__ import annotations

import inspect
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

import pubchempy as pcp
import pytest

from bioetl.composition.factories.datasource import pubchem as pubchem_factory
from bioetl.composition.factories.datasource.pubchem import _create_executor_runner
from bioetl.infrastructure.adapters.pubchem.fetch_flow import ExecutorTimeoutState
from bioetl.domain.resilience import RetryConfig
from bioetl.infrastructure.adapters.common.adapter_defaults import (
    create_default_error_handler,
)
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter
from bioetl.infrastructure.adapters.pubchem import PubChemAdapter
from bioetl.infrastructure.adapters.pubchem.entity_mapper import PubChemEntityMapper
from bioetl.infrastructure.adapters.pubchem.fetch_flow import PubChemFetchFlow
from bioetl.infrastructure.adapters.pubchem.fetch_strategies import (
    PubChemFetchStrategies,
)

pytestmark = pytest.mark.unit


def test_factory_does_not_set_process_socket_timeout() -> None:
    source = inspect.getsource(pubchem_factory)
    assert "setdefaulttimeout" not in source


async def test_executor_runner_cancels_wait_for_stalled_call() -> None:
    started = threading.Event()
    release = threading.Event()

    def hang() -> str:
        started.set()
        release.wait(timeout=2.0)
        return "late"

    pool = ThreadPoolExecutor(max_workers=1)
    runner = _create_executor_runner(pool, timeout_sec=0.05)
    started_at = time.monotonic()
    try:
        with pytest.raises(TimeoutError):
            await runner(hang)
        assert started.is_set()
        assert time.monotonic() - started_at < 0.5
    finally:
        release.set()
        pool.shutdown(wait=True, cancel_futures=False)


async def test_timeout_is_not_replayed_and_trips_circuit_breaker() -> None:
    calls: list[str] = []

    async def stall(*_args: object) -> object:
        calls.append("sdk")
        raise TimeoutError("pubchem sdk stalled")

    breaker = CircuitBreakerGuard(provider="pubchem", failure_threshold=2)
    recorded: list[int] = []
    flow = PubChemFetchFlow(
        rate_limiter=MagicMock(acquire=MagicMock()),
        circuit_breaker=breaker,
        run_in_executor=stall,
        record_request=lambda *_args, status_code=200, **_kwargs: recorded.append(
            status_code
        ),
        normalize_results=lambda raw: raw if isinstance(raw, list) else [],
        retry_config=RetryConfig(max_attempts=3),
    )
    flow.rate_limiter.acquire = _async_none()

    with pytest.raises(TimeoutError):
        await flow.execute(
            endpoint="/compound/cid/962",
            pubchem_callable=lambda: None,
            pubchem_args=(),
        )

    assert calls == ["sdk"]
    assert recorded == [0]
    assert breaker.get_failure_count() == 1


def _adapter(
    pool: ThreadPoolExecutor,
    *,
    owns_thread_pool: bool = False,
    executor_timeout_sec: float | None = None,
    executor_timeout_state: ExecutorTimeoutState | None = None,
) -> PubChemAdapter:
    logger = MagicMock()
    breaker = CircuitBreakerGuard(provider="pubchem", failure_threshold=2)
    limiter = TokenBucketRateLimiter(rate=100.0, capacity=100)
    collector = APIRequestCollector()
    mapper = PubChemEntityMapper()
    return PubChemAdapter(
        logger=logger,
        rate_limiter=limiter,
        circuit_breaker=breaker,
        thread_pool=pool,
        owns_thread_pool=owns_thread_pool,
        error_handler=create_default_error_handler(logger=logger, metrics=None),
        request_collector=collector,
        entity_mapper=mapper,
        fetch_strategies=PubChemFetchStrategies(
            logger=logger,
            rate_limiter=limiter,
            circuit_breaker=breaker,
            mapper=mapper,
            run_in_executor=_async_none(),
            provider_name="pubchem",
            request_collector=collector,
        ),
        executor_timeout_sec=executor_timeout_sec,
        executor_timeout_state=executor_timeout_state,
    )


async def test_health_probe_times_out_stalled_sdk_call() -> None:
    started = threading.Event()
    release = threading.Event()

    def hang(*_args: object) -> list[object]:
        started.set()
        release.wait(timeout=2.0)
        return ["water"]

    pool = ThreadPoolExecutor(max_workers=1)
    logger = MagicMock()
    breaker = CircuitBreakerGuard(provider="pubchem", failure_threshold=2)
    limiter = TokenBucketRateLimiter(rate=100.0, capacity=100)
    collector = APIRequestCollector()
    mapper = PubChemEntityMapper()
    adapter = PubChemAdapter(
        logger=logger,
        rate_limiter=limiter,
        circuit_breaker=breaker,
        thread_pool=pool,
        error_handler=create_default_error_handler(logger=logger, metrics=None),
        request_collector=collector,
        entity_mapper=mapper,
        fetch_strategies=PubChemFetchStrategies(
            logger=logger,
            rate_limiter=limiter,
            circuit_breaker=breaker,
            mapper=mapper,
            run_in_executor=_async_none(),
            provider_name="pubchem",
            request_collector=collector,
        ),
        executor_timeout_sec=0.05,
    )
    original = pcp.get_compounds
    pcp.get_compounds = hang
    started_at = time.monotonic()
    try:
        with pytest.raises(TimeoutError):
            await adapter._probe_health()
        assert started.is_set()
        assert time.monotonic() - started_at < 0.5
        assert breaker.get_failure_count() == 1
    finally:
        pcp.get_compounds = original
        release.set()
        pool.shutdown(wait=True, cancel_futures=False)


async def test_close_after_timeout_does_not_wait_for_worker() -> None:
    started = threading.Event()
    release = threading.Event()

    def hang(*_args: object) -> list[object]:
        started.set()
        release.wait(timeout=2.0)
        return ["water"]

    pool = ThreadPoolExecutor(max_workers=1)
    adapter = _adapter(pool, owns_thread_pool=True, executor_timeout_sec=0.05)
    original = pcp.get_compounds
    pcp.get_compounds = hang
    try:
        with pytest.raises(TimeoutError):
            await adapter._probe_health()
        assert started.is_set()
        started_close = time.monotonic()
        await adapter.close()
        assert time.monotonic() - started_close < 0.3
        assert pool._shutdown is True
    finally:
        pcp.get_compounds = original
        release.set()
        pool.shutdown(wait=True, cancel_futures=False)


async def test_close_without_timeout_waits_for_owned_pool() -> None:
    pool = ThreadPoolExecutor(max_workers=1)
    adapter = _adapter(pool, owns_thread_pool=True)
    try:
        with patch.object(pool, "shutdown", wraps=pool.shutdown) as mock_shutdown:
            await adapter.close()
        mock_shutdown.assert_called_once_with(wait=True)
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


async def test_shared_runner_timeout_makes_adapter_close_skip_wait() -> None:
    started = threading.Event()
    release = threading.Event()

    def hang() -> str:
        started.set()
        release.wait(timeout=2.0)
        return "late"

    pool = ThreadPoolExecutor(max_workers=1)
    state = ExecutorTimeoutState()
    adapter = _adapter(pool, owns_thread_pool=True, executor_timeout_state=state)
    runner = _create_executor_runner(pool, 0.05, state)
    try:
        with pytest.raises(TimeoutError):
            await runner(hang)
        assert state.timed_out is True
        started_close = time.monotonic()
        await adapter.close()
        assert time.monotonic() - started_close < 0.3
    finally:
        release.set()
        pool.shutdown(wait=False, cancel_futures=True)


def _async_none():
    async def _run(*_args: object, **_kwargs: object) -> None:
        return None

    return _run
