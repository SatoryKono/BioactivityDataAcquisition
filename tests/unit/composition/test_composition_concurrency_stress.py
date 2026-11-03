"""Stress concurrent access to composition registries and lazy default init."""

from __future__ import annotations

import threading
from typing import Any
from unittest.mock import MagicMock

import pytest

import bioetl.composition._service_registry as _service_registry
import bioetl.composition.providers._default_registry as _def_reg
from bioetl.composition.providers._models import ProviderConfig
from bioetl.composition.providers.provider_registry import ProviderRegistry

_THREAD_COUNT_SINGLETON = 50
_THREAD_COUNT_REGISTRY = 20
_THREAD_COUNT_SERVICE = 50


@pytest.mark.unit
def test_get_default_provider_registry_concurrency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Concurrent first-access must return one shared default registry instance.

    ``monkeypatch`` restores the prior singleton so provider registrations on the
    real default registry are not discarded after the test.
    """
    monkeypatch.setattr(_def_reg, "_default_provider_registry", None)

    instances: list[Any] = []
    lock = threading.Lock()
    barrier = threading.Barrier(_THREAD_COUNT_SINGLETON)

    def worker() -> None:
        barrier.wait()
        reg = _def_reg.get_default_provider_registry()
        with lock:
            instances.append(reg)

    threads = [threading.Thread(target=worker) for _ in range(_THREAD_COUNT_SINGLETON)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(instances) == _THREAD_COUNT_SINGLETON
    first = instances[0]
    assert all(inst is first for inst in instances), (
        "get_default_provider_registry must return one shared singleton under "
        f"concurrent first access; got {len({id(inst) for inst in instances})} "
        "distinct instances"
    )
    assert _def_reg.get_default_provider_registry() is first


class MockAdapter:
    def __init__(self, **kwargs: object) -> None:
        pass


@pytest.mark.unit
def test_provider_registry_create_adapter_concurrency() -> None:
    """Concurrent create_adapter after registration must not raise."""
    registry = ProviderRegistry()
    config = ProviderConfig(adapter_class=MockAdapter)
    registry.register("test_provider", config)

    results: list[object] = []
    exceptions: list[Exception] = []
    lock = threading.Lock()
    barrier = threading.Barrier(_THREAD_COUNT_REGISTRY)

    def worker() -> None:
        try:
            barrier.wait()
            adapter = registry.create_adapter(
                "test_provider",
                http_client=MagicMock(),
                logger=MagicMock(),
                settings=MagicMock(),
            )
            with lock:
                results.append(adapter)
        except Exception as exc:
            with lock:
                exceptions.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(_THREAD_COUNT_REGISTRY)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not exceptions, f"Exceptions occurred: {exceptions}"
    assert len(results) == _THREAD_COUNT_REGISTRY


@pytest.mark.unit
def test_provider_registry_create_data_source_concurrency() -> None:
    """Concurrent create_data_source after registration must not raise."""
    registry = ProviderRegistry()
    config = ProviderConfig(adapter_class=MockAdapter, data_source_creator=MagicMock())
    registry.register("test_provider", config)

    results: list[object] = []
    exceptions: list[Exception] = []
    lock = threading.Lock()
    barrier = threading.Barrier(_THREAD_COUNT_REGISTRY)

    def worker() -> None:
        try:
            barrier.wait()
            data_source = registry.create_data_source(
                "test_provider",
                settings=MagicMock(),
                pipeline_config=MagicMock(),
                logger=MagicMock(),
            )
            with lock:
                results.append(data_source)
        except Exception as exc:
            with lock:
                exceptions.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(_THREAD_COUNT_REGISTRY)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not exceptions, f"Exceptions occurred: {exceptions}"
    assert len(results) == _THREAD_COUNT_REGISTRY


class DummyProtocol:
    pass


@pytest.mark.unit
def test_service_registry_concurrency(monkeypatch: pytest.MonkeyPatch) -> None:
    """Concurrent assignment into an isolated ``_REGISTRY`` must not raise.

    Intent: every worker completes a write then a read without exceptions.
    This does **not** prove factory write/read consistency under overwrite —
    many threads replace the same ``DummyProtocol`` key; the collected values
    only show that each worker observed *some* callable after its write.
    """
    isolated: dict[type[Any], object] = {}
    monkeypatch.setattr(_service_registry, "_REGISTRY", isolated)

    results: list[int] = []
    lock = threading.Lock()
    barrier = threading.Barrier(_THREAD_COUNT_SERVICE)

    def worker(idx: int) -> None:
        barrier.wait()
        _service_registry._REGISTRY[DummyProtocol] = lambda: idx
        factory = _service_registry._REGISTRY[DummyProtocol]
        assert callable(factory)
        with lock:
            results.append(factory())

    threads = [
        threading.Thread(target=worker, args=(i,)) for i in range(_THREAD_COUNT_SERVICE)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(results) == _THREAD_COUNT_SERVICE
    # Mutations stay on the monkeypatched map; process-global _REGISTRY is restored
    # by monkeypatch teardown (DummyProtocol must not leak across tests).
    assert _service_registry._REGISTRY is isolated
    assert DummyProtocol in isolated
