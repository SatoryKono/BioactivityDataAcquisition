"""Compatibility tests for canonical composition module names."""

from __future__ import annotations


def test_pipeline_assembler_reexports_generic_pipeline_factory() -> None:
    """Canonical pipeline_assembler path should expose the legacy factory symbols."""
    from bioetl.composition.factories.pipeline.assembler import GenericPipelineFactory
    from bioetl.composition.factories.pipeline.pipeline_assembler import (
        GenericPipelineFactory as CanonicalGenericPipelineFactory,
    )

    assert CanonicalGenericPipelineFactory is GenericPipelineFactory


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


def test_dq_services_factory_reexports_legacy_factory() -> None:
    """Canonical dq_services_factory path should expose the legacy DQ factory."""
    from bioetl.composition.factories.dq.dq_services_factory import (
        DQServicesFactory as CanonicalDQServicesFactory,
    )
    from bioetl.composition.factories.dq.factory import DQServicesFactory

    assert CanonicalDQServicesFactory is DQServicesFactory


def test_pipeline_runner_service_bootstrap_reexports_legacy_entrypoint() -> None:
    """Canonical bootstrap module should expose the legacy runner entrypoint."""
    from bioetl.composition.bootstrap.runtime.pipeline_runner_service_bootstrap import (
        bootstrap_pipeline_runner_service as canonical_bootstrap,
    )
    from bioetl.composition.bootstrap.runtime.runner import (
        bootstrap_pipeline_runner_service,
    )

    assert canonical_bootstrap is bootstrap_pipeline_runner_service
