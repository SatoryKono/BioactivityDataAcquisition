"""Smoke tests for factory class availability.

Ensures key factory classes are importable and expose expected
public construction methods.
"""

from __future__ import annotations

import pytest


@pytest.mark.smoke
class TestFactoryClassAvailability:
    """Key factory classes must be importable and structurally correct."""

    def test_pipeline_registry_importable(self) -> None:
        from bioetl.composition.factories.pipeline.registry import (
            register_all_pipelines,
        )

        assert callable(register_all_pipelines)

    def test_storage_factory_importable(self) -> None:
        from bioetl.composition.factories.storage.factory import StorageFactory

        assert hasattr(StorageFactory, "__init__")

    def test_storage_factory_alt_importable(self) -> None:
        from bioetl.composition.factories.storage.storage_factory import (
            StorageFactory,
        )

        assert hasattr(StorageFactory, "__init__")

    def test_services_factory_importable(self) -> None:
        from bioetl.composition.factories.services.factory import (
            BaseServicesFactory,
        )

        assert hasattr(BaseServicesFactory, "__init__")

    def test_services_bundle_importable(self) -> None:
        from bioetl.composition.factories.services.bundle import (
            ServiceBundleDependencies,
        )

        assert hasattr(ServiceBundleDependencies, "__init__")

    def test_http_client_factory_importable(self) -> None:
        from bioetl.composition.factories.datasource.http_client import (
            HttpClientFactory,
        )

        assert hasattr(HttpClientFactory, "__init__")

    def test_dq_factory_importable(self) -> None:
        from bioetl.composition.factories.dq.factory import DQServicesFactory

        assert hasattr(DQServicesFactory, "__init__")

    def test_transformer_factory_importable(self) -> None:
        from bioetl.composition.factories.transformer_factory import (
            register_all_transformers,
        )

        assert callable(register_all_transformers)
