from unittest.mock import Mock, patch

import pytest

from bioetl.application.container import PipelineContainer
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.provider_registry import ProviderRegistryABC
from bioetl.domain.providers import ProviderDefinition


@pytest.fixture
def mock_config():
    config = Mock(spec=PipelineConfig)
    config.provider = "dummy"
    config.entity_name = "test_entity"
    config.input_mode = "api"
    config.pipeline = {}
    config.hashing = Mock()
    config.hashing.business_key_fields = ["id"]
    return config


@pytest.fixture
def mock_registry():
    registry = Mock(spec=ProviderRegistryABC)
    definition = Mock(spec=ProviderDefinition)
    definition.config_type = Mock
    definition.components = Mock()
    registry.get_provider.return_value = definition
    return registry


@pytest.fixture
def container(mock_config, mock_registry):
    return PipelineContainer(
        config=mock_config, provider_registry=mock_registry, loader=Mock()
    )


def test_container_initialization(container):
    assert container is not None


def test_get_record_source_delegates_to_factory(container, mock_registry):
    with patch("bioetl.application.container.RecordSourceFactory") as MockFactory:
        factory_instance = MockFactory.return_value
        factory_instance.create_record_source.return_value = "mock_source"

        source = container.get_record_source("mock_extraction_service")

        assert source == "mock_source"
        MockFactory.assert_called_once()
        factory_instance.create_record_source.assert_called_once()


def test_get_hooks_delegates_to_factory(container):
    with patch("bioetl.application.container.PipelineHookFactory") as MockFactory:
        factory_instance = MockFactory.return_value
        factory_instance.create_hooks.return_value = ["hook1", "hook2"]

        hooks = container.get_hooks()

        assert hooks == ["hook1", "hook2"]
        MockFactory.assert_called_once()
        factory_instance.create_hooks.assert_called_once()


def test_get_normalization_service_delegates_to_factory(container):
    with patch("bioetl.application.container.ProviderServiceFactory") as MockFactory:
        factory_instance = MockFactory.return_value
        factory_instance.create_normalization_service.return_value = "mock_norm_service"

        service = container.get_normalization_service()

        assert service == "mock_norm_service"
        MockFactory.assert_called_once()
        factory_instance.create_normalization_service.assert_called_once()


def test_get_extraction_service_delegates_to_factory(container):
    with patch("bioetl.application.container.ProviderServiceFactory") as MockFactory:
        factory_instance = MockFactory.return_value
        factory_instance.create_extraction_service.return_value = "mock_ext_service"

        service = container.get_extraction_service()

        assert service == "mock_ext_service"
        MockFactory.assert_called_once()
        factory_instance.create_extraction_service.assert_called_once()
