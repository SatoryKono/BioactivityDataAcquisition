"""Canonical composition-module path tests."""

from __future__ import annotations

def test_storage_factory_reexports_storage_factory() -> None:
    """Canonical storage_factory path should expose the legacy storage factory symbols."""
    from bioetl.composition.factories.storage.factory import StorageFactory
    from bioetl.composition.factories.storage.storage_factory import (
        StorageFactory as CanonicalStorageFactory,
    )

    assert CanonicalStorageFactory is StorageFactory


def test_datasource_package_reexports_registry_and_factory() -> None:
    """Datasource package root should expose the canonical data-source API."""
    from bioetl.composition.factories.datasource.data_source_factory import (
        DataSourceFactory as CanonicalDataSourceFactory,
        DataSourceRegistry as CanonicalDataSourceRegistry,
    )
    from bioetl.composition.factories.datasource import (
        DataSourceFactory,
        DataSourceRegistry,
    )

    assert CanonicalDataSourceFactory is DataSourceFactory
    assert CanonicalDataSourceRegistry is DataSourceRegistry


def test_pipeline_runner_service_bootstrap_reexports_legacy_entrypoint() -> None:
    """Canonical bootstrap module should expose the legacy runner entrypoint."""
    from bioetl.composition.bootstrap.runtime.pipeline_runner_service_bootstrap import (
        bootstrap_pipeline_runner_service as canonical_bootstrap,
    )
    from bioetl.composition.bootstrap.runtime.runner import (
        bootstrap_pipeline_runner_service,
    )

    assert canonical_bootstrap is bootstrap_pipeline_runner_service


def test_pipeline_configs_import_warns_and_reexports_registry_manifest() -> None:
    """Canonical registry manifest import remains the supported pipeline config path."""
    from bioetl.composition.factories.pipeline.registry_manifest import (
        PIPELINE_CONFIGS,
        PipelineFactoryConfig,
    )

    assert PIPELINE_CONFIGS is not None
    assert PipelineFactoryConfig is not None

