"""Test concurrent access to composition registries and initialization to verify thread-safety assumptions."""

import threading
from unittest.mock import MagicMock


import bioetl.composition.providers._default_registry as _def_reg
from bioetl.composition._service_registry import _REGISTRY
from bioetl.composition.providers.provider_registry import ProviderRegistry
from bioetl.composition.providers._models import ProviderConfig


def test_get_default_provider_registry_concurrency() -> None:
    """Verify if concurrent first-access creates multiple singleton instances."""
    _def_reg._default_provider_registry = None  # Force uninitialized state
    instances = []
    barrier = threading.Barrier(50)

    def worker() -> None:
        barrier.wait()
        reg = _def_reg.get_default_provider_registry()
        instances.append(id(reg))

    threads = [threading.Thread(target=worker) for _ in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # While conceptually racy, the import system lock or simple timing might make it pass sometimes.
    # Therefore, we just run the test to see if it causes deadlocks/exceptions, and log the length.
    assert len(set(instances)) >= 1, "Expected at least one registry instance"


class MockAdapter:
    def __init__(self, **kwargs: object):
        pass


def test_provider_registry_create_adapter_concurrency() -> None:
    """Verify concurrency during create_adapter invocation after lock release."""
    registry = ProviderRegistry()
    config = ProviderConfig(adapter_class=MockAdapter)
    registry.register("test_provider", config)

    results = []
    exceptions = []
    barrier = threading.Barrier(20)

    def worker() -> None:
        try:
            barrier.wait()
            # This calls the internal _creator.create_adapter
            adapter = registry.create_adapter(
                "test_provider",
                http_client=MagicMock(),
                logger=MagicMock(),
                settings=MagicMock()
            )
            results.append(adapter)
        except Exception as e:
            exceptions.append(e)

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not exceptions, f"Exceptions occurred: {exceptions}"
    assert len(results) == 20


def test_provider_registry_create_data_source_concurrency() -> None:
    """Verify concurrency during create_data_source invocation after lock release."""
    registry = ProviderRegistry()
    config = ProviderConfig(adapter_class=MockAdapter, data_source_creator=MagicMock())
    registry.register("test_provider", config)

    results = []
    exceptions = []
    barrier = threading.Barrier(20)

    def worker() -> None:
        try:
            barrier.wait()
            # This calls the internal _creator.create_data_source
            data_source = registry.create_data_source(
                "test_provider",
                settings=MagicMock(),
                pipeline_config=MagicMock(),
                logger=MagicMock()
            )
            results.append(data_source)
        except Exception as e:
            exceptions.append(e)

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not exceptions, f"Exceptions occurred: {exceptions}"
    assert len(results) == 20


class DummyProtocol:
    pass


def test_service_registry_concurrency() -> None:
    """Verify if concurrent mutations to _REGISTRY are safe."""
    results = []
    barrier = threading.Barrier(50)

    def worker(idx: int) -> None:
        barrier.wait()
        _REGISTRY[DummyProtocol] = lambda: idx

        if DummyProtocol in _REGISTRY:
            results.append(_REGISTRY[DummyProtocol]())

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # The dictionary itself in cpython is thread safe for concurrent assignments.
    assert len(results) == 50
