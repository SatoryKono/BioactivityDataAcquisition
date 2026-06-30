"""Focused tests for the services factory package lazy facade."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unit


def test_services_package_lazy_exports_submodules_and_pipeline_creation() -> None:
    """Submodule and pipeline-creation exports resolve without eager package cycles."""
    import bioetl.composition.factories.services as services
    from bioetl.composition.factories.pipeline import creation_support

    assert services.factory.__name__ == "bioetl.composition.factories.services.factory"
    assert services.bundle.__name__ == "bioetl.composition.factories.services.bundle"
    assert services._PipelineCreationInputs is creation_support._PipelineCreationInputs
    assert services._ServiceBundleDeps is creation_support._ServiceBundleDeps
    assert (
        services._create_pipeline_with_services_impl
        is creation_support._create_pipeline_with_services_impl
    )


def test_services_package_lazy_exports_factory_and_observability_helpers() -> None:
    """Factory and observability API branches remain explicit package exports."""
    import bioetl.composition.factories.services as services
    from bioetl.composition.factories.services import factory, observability_api

    assert services.BaseServicesFactory is factory.BaseServicesFactory
    assert services.ServicesBuilder is factory.ServicesBuilder
    assert (
        services.create_data_normalization_service
        is factory.create_data_normalization_service
    )
    assert services.create_shared_metrics is observability_api.create_shared_metrics
    assert (
        services._create_cached_bronze_data_source
        is observability_api._create_cached_bronze_data_source
    )
    assert services._create_data_source is observability_api._create_data_source


def test_services_package_unknown_export_raises_attribute_error() -> None:
    """Unknown names must fail fast instead of becoming implicit compat seams."""
    import bioetl.composition.factories.services as services

    missing_name = "not_a_services_export"
    with pytest.raises(AttributeError, match=missing_name):
        getattr(services, missing_name)
