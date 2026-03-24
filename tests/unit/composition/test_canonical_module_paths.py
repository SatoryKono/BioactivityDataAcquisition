"""Compatibility tests for canonical composition module names."""

from __future__ import annotations

import importlib
import sys

import pytest


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


@pytest.mark.unit
def test_services_creation_api_import_warns_and_points_to_pipeline_creation_api() -> (
    None
):
    """Deprecated services creation_api shim should warn toward the pipeline seam."""
    sys.modules.pop("bioetl.composition.factories.services.creation_api", None)

    with pytest.warns(
        DeprecationWarning,
        match="bioetl\\.composition\\.factories\\.pipeline\\.creation_api",
    ):
        importlib.import_module("bioetl.composition.factories.services.creation_api")


def test_services_creation_api_reexports_pipeline_creation_symbols() -> None:
    """Services creation API should stay as a deprecated alias over pipeline creation_api."""
    from bioetl.composition.factories.pipeline.creation_api import (
        _PipelineCreationInputs as CanonicalPipelineCreationInputs,
        _create_pipeline_with_services_impl as canonical_create_pipeline,
    )
    from bioetl.composition.factories.services.creation_api import (
        _PipelineCreationInputs,
        _create_pipeline_with_services_impl,
    )

    assert _PipelineCreationInputs is CanonicalPipelineCreationInputs
    assert _create_pipeline_with_services_impl is canonical_create_pipeline


@pytest.mark.unit
def test_pipeline_config_resolution_import_warns_and_reexports_canonical_helpers() -> (
    None
):
    """Deprecated config_resolution shim should warn and preserve canonical symbols."""
    sys.modules.pop(
        "bioetl.composition.factories.pipeline.config_resolution",
        None,
    )

    with pytest.warns(
        DeprecationWarning,
        match="bioetl\\.infrastructure\\.config\\.pipeline_config_api",
    ):
        compat_module = importlib.import_module(
            "bioetl.composition.factories.pipeline.config_resolution"
        )

    from bioetl.infrastructure.config.converters import yaml_config_to_domain
    from bioetl.infrastructure.config.domain_config_resolver import (
        DomainConfigResolver,
        resolve_domain_pipeline_config,
    )
    from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config

    assert compat_module.DomainConfigResolver is DomainConfigResolver
    assert (
        compat_module.resolve_domain_pipeline_config is resolve_domain_pipeline_config
    )
    assert compat_module.load_pipeline_config is load_pipeline_config
    assert compat_module.yaml_config_to_domain is yaml_config_to_domain


@pytest.mark.unit
def test_pipeline_configs_import_warns_and_reexports_registry_manifest() -> None:
    """Deprecated pipeline.configs shim should warn and preserve registry symbols."""
    sys.modules.pop("bioetl.composition.factories.pipeline.configs", None)

    with pytest.warns(
        DeprecationWarning,
        match="bioetl\\.composition\\.factories\\.pipeline\\.registry_manifest",
    ):
        compat_module = importlib.import_module(
            "bioetl.composition.factories.pipeline.configs"
        )

    from bioetl.composition.factories.pipeline.registry_manifest import (
        PIPELINE_CONFIGS as canonical_pipeline_configs,
        PipelineFactoryConfig as CanonicalPipelineFactoryConfig,
    )

    assert compat_module.PIPELINE_CONFIGS is canonical_pipeline_configs
    assert compat_module.PipelineFactoryConfig is CanonicalPipelineFactoryConfig


def test_pipeline_configs_module_reexports_registry_manifest() -> None:
    """Legacy pipeline configs module should stay as a compatibility shim."""
    from bioetl.composition.factories.pipeline.configs import (
        PIPELINE_CONFIGS,
        PipelineFactoryConfig,
    )
    from bioetl.composition.factories.pipeline.registry_manifest import (
        PIPELINE_CONFIGS as canonical_pipeline_configs,
        PipelineFactoryConfig as CanonicalPipelineFactoryConfig,
    )

    assert PIPELINE_CONFIGS is canonical_pipeline_configs
    assert PipelineFactoryConfig is CanonicalPipelineFactoryConfig


def test_pipeline_creation_api_reexports_creation_wiring_symbols() -> None:
    """Pipeline creation API should stay as a direct compatibility shim."""
    from bioetl.composition.factories.pipeline._creation_wiring import (
        _PipelineCreationInputs as CanonicalPipelineCreationInputs,
        _create_pipeline_with_services_impl as canonical_create_pipeline,
    )
    from bioetl.composition.factories.pipeline.creation_api import (
        _PipelineCreationInputs,
        _create_pipeline_with_services_impl,
    )

    assert _PipelineCreationInputs is CanonicalPipelineCreationInputs
    assert _create_pipeline_with_services_impl is canonical_create_pipeline
