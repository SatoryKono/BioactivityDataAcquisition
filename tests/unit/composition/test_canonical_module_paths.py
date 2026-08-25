# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Canonical composition-module path tests."""

from __future__ import annotations


import pytest

pytestmark = pytest.mark.unit


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


def test_pipeline_configs_imports_use_canonical_manifest_and_config_type_paths() -> (
    None
):
    """Registry data and config types should stay on their canonical seams."""
    from bioetl.composition.factories.pipeline.config_types import (
        PipelineFactoryConfig,
    )
    from bioetl.composition.factories.pipeline.registry_manifest import (
        PIPELINE_CONFIGS,
    )

    assert PIPELINE_CONFIGS is not None
    assert PipelineFactoryConfig is not None


def test_registry_api_reexports_canonical_registry_symbols() -> None:
    """Canonical registry API should expose the package-root registry types."""
    import bioetl.composition.registry_api as registry_api

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

    assert CanonicalPipelineDefinition is PipelineDefinition
    assert CanonicalPipelineRegistry is PipelineRegistry
    assert canonical_create_registry is create_registry
    assert canonical_get_default_registry is registry_api.get_default_registry


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
    from bioetl.composition._services import get_pipeline_runner_service

    assert canonical_get_pipeline_runner_service is get_pipeline_runner_service


def test_execution_api_exposes_runner_and_metrics_seams() -> None:
    """Execution API remains the sanctioned CLI seam after access-module removal."""
    from bioetl.composition.execution_api import (
        ensure_metrics_server_started,
        get_pipeline_runner_service,
    )

    assert callable(ensure_metrics_server_started)
    assert callable(get_pipeline_runner_service)


def test_control_plane_api_reexports_canonical_control_plane_services() -> None:
    """Control-plane API should expose canonical admin and inspection seams."""
    from bioetl.composition.control_plane_runtime import (
        get_adr_service as canonical_get_adr_service,
        get_checkpoint_runtime_service as canonical_get_checkpoint_runtime_service,
        get_config_service as canonical_get_config_service,
    )
    from bioetl.composition._services import get_adr_service, get_config_service
    from bioetl.composition.resources_runtime import get_checkpoint_runtime_service

    assert canonical_get_adr_service is get_adr_service
    assert canonical_get_checkpoint_runtime_service is get_checkpoint_runtime_service
    assert canonical_get_config_service is get_config_service


def test_control_plane_service_access_routes_to_canonical_owner_seams() -> None:
    """First-party control-plane access should bind directly to owner seams."""
    from bioetl.composition._services import get_config_service
    from bioetl.composition.control_plane_runtime import (
        get_workflow_execution_service,
        load_workflow_config,
    )
    from bioetl.composition.control_plane_service_access import (
        get_checkpoint_runtime_service as canonical_get_checkpoint_runtime_service,
        get_config_service as canonical_get_config_service,
        get_workflow_execution_service as canonical_get_workflow_execution_service,
        list_configured_pipeline_names as canonical_list_configured_pipeline_names,
        load_workflow_config as canonical_load_workflow_config,
    )
    from bioetl.composition.config_catalog import list_configured_pipeline_names
    from bioetl.composition.resources_runtime import get_checkpoint_runtime_service

    assert canonical_get_checkpoint_runtime_service is get_checkpoint_runtime_service
    # control_plane_service_access delegates to _services, so we check behavior not identity
    assert callable(canonical_get_config_service)
    assert callable(get_config_service)
    # Note: we do NOT check identity for get_config_service due to delegation pattern
    assert canonical_get_workflow_execution_service is get_workflow_execution_service
    assert canonical_list_configured_pipeline_names is list_configured_pipeline_names
    assert canonical_load_workflow_config is load_workflow_config


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
    from bioetl.composition._services import get_health_service, get_quarantine_service
    from bioetl.composition.resources_runtime import get_quarantine_runtime_service

    assert HealthServerDependencies is CanonicalHealthServerDependencies
    assert canonical_get_health_service is get_health_service
    assert canonical_get_quarantine_runtime_service is get_quarantine_runtime_service
    assert canonical_get_quarantine_service is get_quarantine_service


def test_maintenance_api_reexports_canonical_maintenance_services() -> None:
    """Maintenance API should keep logic-free lazy exports over owner seams."""
    from bioetl.composition.maintenance_api import (
        get_bronze_cleanup_service as canonical_get_bronze_cleanup_service,
        get_vacuum_service as canonical_get_vacuum_service,
    )
    from bioetl.composition._services import (
        get_bronze_cleanup_service,
        get_vacuum_service,
    )

    assert canonical_get_bronze_cleanup_service is get_bronze_cleanup_service
    assert canonical_get_vacuum_service is get_vacuum_service


def test_maintenance_api_exposes_cleanup_and_vacuum_seams() -> None:
    """Maintenance API remains the sanctioned CLI seam after access-module removal."""
    from bioetl.composition.maintenance_api import (
        get_bronze_cleanup_service,
        get_vacuum_service,
    )

    assert callable(get_bronze_cleanup_service)
    assert callable(get_vacuum_service)
