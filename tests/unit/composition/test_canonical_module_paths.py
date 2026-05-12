"""Canonical composition-module path tests."""

from __future__ import annotations


def test_storage_factory_reexports_storage_factory() -> None:
    """Canonical storage_factory path should expose the legacy storage factory symbols."""
    from bioetl.composition.factories.storage.factory import StorageFactory
    from bioetl.composition.factories.storage.storage_factory import (
        StorageFactory as CanonicalStorageFactory,
    )

    assert CanonicalStorageFactory is StorageFactory


def test_datasource_package_reexports_factory_and_creator_helper() -> None:
    """Datasource package root should expose only the canonical datasource seams."""
    from bioetl.composition.factories.datasource.data_source_factory import (
        DataSourceFactory as CanonicalDataSourceFactory,
        get_data_source_creator as canonical_get_data_source_creator,
    )
    from bioetl.composition.factories.datasource import (
        DataSourceFactory,
        get_data_source_creator,
    )

    assert CanonicalDataSourceFactory is DataSourceFactory
    assert canonical_get_data_source_creator is get_data_source_creator


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


def test_registry_api_reexports_canonical_registry_symbols() -> None:
    """Canonical registry API should expose the package-root registry types."""
    from bioetl.composition.registry_api import (
        PipelineDefinition as CanonicalPipelineDefinition,
        PipelineRegistry as CanonicalPipelineRegistry,
        create_registry as canonical_create_registry,
        get_default_registry as canonical_get_default_registry,
    )
    from bioetl.composition.factories.pipeline.registry import (
        PipelineDefinition,
        PipelineRegistry,
        create_registry,
    )
    from bioetl.composition.registry_default import get_default_registry

    assert CanonicalPipelineDefinition is PipelineDefinition
    assert CanonicalPipelineRegistry is PipelineRegistry
    assert canonical_create_registry is create_registry
    assert canonical_get_default_registry is get_default_registry


def test_registry_api_surface_stays_narrow() -> None:
    """Registry API should stay limited to the sanctioned registry seam."""
    import bioetl.composition.registry_api as registry_api

    assert set(registry_api.__all__) == {
        "PipelineDefinition",
        "PipelineRegistry",
        "create_registry",
        "get_default_registry",
        "register_all_pipelines",
    }


def test_registry_api_reexports_pipeline_registration() -> None:
    """Registry API should expose the canonical pipeline registration seam."""
    from bioetl.composition.registry_api import register_all_pipelines
    from bioetl.composition.factories.pipeline.registry import (
        register_all_pipelines as canonical_register_all_pipelines,
    )

    assert register_all_pipelines is canonical_register_all_pipelines


def test_execution_api_reexports_pipeline_runner_service() -> None:
    """Execution API should expose the canonical pipeline runner service seam."""
    from bioetl.composition.execution_api import (
        get_pipeline_runner_service as canonical_get_pipeline_runner_service,
    )
    from bioetl.composition.services_api import get_pipeline_runner_service

    assert canonical_get_pipeline_runner_service is get_pipeline_runner_service


def test_control_plane_api_reexports_canonical_control_plane_services() -> None:
    """Control-plane API should expose canonical admin and inspection seams."""
    from bioetl.composition.control_plane_api import (
        get_adr_service as canonical_get_adr_service,
        get_checkpoint_runtime_service as canonical_get_checkpoint_runtime_service,
        get_config_service as canonical_get_config_service,
    )
    from bioetl.composition.resources_api import get_checkpoint_runtime_service
    from bioetl.composition.services_api import get_adr_service, get_config_service

    assert canonical_get_adr_service is get_adr_service
    assert canonical_get_checkpoint_runtime_service is get_checkpoint_runtime_service
    assert canonical_get_config_service is get_config_service


def test_health_api_reexports_canonical_health_services() -> None:
    """Health API should expose the canonical health and quarantine seams."""
    from bioetl.composition.bootstrap.cli.health import (
        HealthServerDependencies as CanonicalHealthServerDependencies,
    )
    from bioetl.composition.health_api import (
        HealthServerDependencies,
        get_health_service as canonical_get_health_service,
        get_quarantine_runtime_service as canonical_get_quarantine_runtime_service,
        get_quarantine_service as canonical_get_quarantine_service,
    )
    from bioetl.composition.resources_api import get_quarantine_runtime_service
    from bioetl.composition.services_api import (
        get_health_service,
        get_quarantine_service,
    )

    assert HealthServerDependencies is CanonicalHealthServerDependencies
    assert canonical_get_health_service is get_health_service
    assert canonical_get_quarantine_runtime_service is get_quarantine_runtime_service
    assert canonical_get_quarantine_service is get_quarantine_service


def test_maintenance_api_reexports_canonical_maintenance_services() -> None:
    """Maintenance API should expose the canonical maintenance service seams."""
    from bioetl.composition.maintenance_api import (
        get_lifecycle_service as canonical_get_lifecycle_service,
        get_bronze_cleanup_service as canonical_get_bronze_cleanup_service,
        preview_cleanup as canonical_preview_cleanup,
        get_vacuum_service as canonical_get_vacuum_service,
    )
    from bioetl.composition.resources_api import (
        get_lifecycle_service,
        preview_cleanup,
    )
    from bioetl.composition.services_api import (
        get_bronze_cleanup_service,
        get_vacuum_service,
    )

    assert canonical_get_lifecycle_service is get_lifecycle_service
    assert canonical_get_bronze_cleanup_service is get_bronze_cleanup_service
    assert canonical_preview_cleanup is preview_cleanup
    assert canonical_get_vacuum_service is get_vacuum_service
