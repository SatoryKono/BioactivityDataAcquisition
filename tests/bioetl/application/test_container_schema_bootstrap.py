"""Tests for schema bootstrap integration in PipelineContainer.

These tests verify that PipelineContainer correctly uses SchemaBootstrapService
instead of directly calling register_schemas, per ADR-0006 architecture guidelines.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from bioetl.application.container import PipelineContainer
from bioetl.application.services.schema_bootstrap import (
    SchemaBootstrapService,
)
from bioetl.domain.configs import (
    DataFlowConfig,
    DataSinkConfig,
    DataSourceConfig,
    DummyProviderConfig,
    PipelineConfig,
    PipelineIdentityConfig,
    ProviderHttpConfig,
)
from bioetl.domain.providers import (
    ProviderComponents,
    ProviderDefinition,
    ProviderId,
)
from bioetl.infrastructure.provider_registry import InMemoryProviderRegistry

if TYPE_CHECKING:
    from bioetl.domain.validation import SchemaProviderABC


class DummyComponents(ProviderComponents):
    """Minimal components for testing."""

    def create_client(self, config: DummyProviderConfig) -> dict[str, str]:
        return {"provider": config.provider}

    def create_extraction_service(
        self,
        config: DummyProviderConfig,
        *,
        client: dict[str, str] | None = None,
    ) -> tuple[str, str]:
        resolved_client = client or self.create_client(config)
        return resolved_client["provider"], str(config.http.base_url)


@pytest.fixture()
def provider_registry() -> InMemoryProviderRegistry:
    """Create a provider registry with dummy provider registered."""
    registry = InMemoryProviderRegistry()
    definition = ProviderDefinition(
        id=ProviderId.DUMMY,
        config_type=DummyProviderConfig,
        components=DummyComponents(),
        description="Dummy provider for schema bootstrap tests",
    )
    registry.register_provider(definition)
    return registry


@pytest.fixture()
def pipeline_config() -> PipelineConfig:
    """Create a minimal pipeline config for testing using new decomposed format."""
    return PipelineConfig(
        identity=PipelineIdentityConfig(
            pipeline_id="dummy.entity",
            provider="dummy",
            entity="entity",
        ),
        data_flow=DataFlowConfig(
            source=DataSourceConfig(
                input_mode="auto_detect",
                batch_size=10,
            ),
            sink=DataSinkConfig(
                output_path="/tmp/out",
            ),
        ),
        provider_config=DummyProviderConfig(
            provider="dummy",
            http=ProviderHttpConfig(base_url="http://example.com"),
        ),
    )


class TestContainerDoesNotCallRegisterSchemasDirectly:
    """Verify that container uses SchemaBootstrapService instead of register_schemas."""

    def test_container_init_does_not_call_register_schemas(
        self,
        pipeline_config: PipelineConfig,
        provider_registry: InMemoryProviderRegistry,
    ) -> None:
        """Container initialization should NOT call register_schemas directly.

        Per ADR-0006, schema registration should happen via SchemaBootstrapService,
        not through direct domain function calls.
        """
        loader = MagicMock()

        with patch(
            "bioetl.application.container.create_schema_bootstrap_service"
        ) as mock_create_service:
            mock_service = MagicMock(spec=SchemaBootstrapService)
            mock_create_service.return_value = mock_service

            # Patch register_schemas to detect if it's called directly
            with patch("bioetl.domain.schemas.register_schemas") as mock_register:
                _container = PipelineContainer(
                    pipeline_config,
                    loader=loader,
                    provider_registry=provider_registry,
                )

                # register_schemas should NOT be called during container init
                mock_register.assert_not_called()

                # SchemaBootstrapService factory should have been called instead
                mock_create_service.assert_called_once()

    def test_schema_registration_is_lazy_via_service(
        self,
        pipeline_config: PipelineConfig,
        provider_registry: InMemoryProviderRegistry,
    ) -> None:
        """Schema registration should happen lazily when validation service is requested."""
        loader = MagicMock()
        mock_service = MagicMock(spec=SchemaBootstrapService)
        mock_schema_provider = MagicMock()
        mock_service.ensure_registered.return_value = mock_schema_provider

        container = PipelineContainer(
            pipeline_config,
            loader=loader,
            provider_registry=provider_registry,
            schema_bootstrap_service=mock_service,
        )

        # ensure_registered should NOT be called during init
        mock_service.ensure_registered.assert_not_called()

        # Only when we request validation service
        _validation_service = container.get_validation_service()

        # Now ensure_registered should have been called
        mock_service.ensure_registered.assert_called_once()

    def test_custom_schema_bootstrap_service_is_used(
        self,
        pipeline_config: PipelineConfig,
        provider_registry: InMemoryProviderRegistry,
    ) -> None:
        """Container should use injected schema_bootstrap_service if provided."""
        loader = MagicMock()
        custom_service = MagicMock(spec=SchemaBootstrapService)
        mock_schema_provider = MagicMock()
        custom_service.ensure_registered.return_value = mock_schema_provider

        container = PipelineContainer(
            pipeline_config,
            loader=loader,
            provider_registry=provider_registry,
            schema_bootstrap_service=custom_service,
        )

        _validation_service = container.get_validation_service()

        # Our custom service should have been used
        custom_service.ensure_registered.assert_called_once()


class TestSchemaBootstrapServiceIntegration:
    """Integration tests for SchemaBootstrapService with PipelineContainer."""

    def test_schema_provider_parameter_passed_to_bootstrap_service(
        self,
        pipeline_config: PipelineConfig,
        provider_registry: InMemoryProviderRegistry,
    ) -> None:
        """When schema_provider is passed, it should be used by bootstrap service."""
        loader = MagicMock()
        custom_schema_provider: SchemaProviderABC = MagicMock()

        with patch(
            "bioetl.application.container.create_schema_bootstrap_service"
        ) as mock_create:
            mock_service = MagicMock(spec=SchemaBootstrapService)
            mock_create.return_value = mock_service

            _container = PipelineContainer(
                pipeline_config,
                loader=loader,
                provider_registry=provider_registry,
                schema_provider=custom_schema_provider,
            )

            # Verify schema_provider was passed to factory
            mock_create.assert_called_once_with(schema_provider=custom_schema_provider)

    def test_backward_compatibility_without_explicit_service(
        self,
        pipeline_config: PipelineConfig,
        provider_registry: InMemoryProviderRegistry,
    ) -> None:
        """Container should work without explicit schema_bootstrap_service parameter.

        This ensures backward compatibility with existing code.
        """
        loader = MagicMock()

        # Create container without schema_bootstrap_service
        container = PipelineContainer(
            pipeline_config,
            loader=loader,
            provider_registry=provider_registry,
        )

        # Should be able to get validation service without errors
        validation_service = container.get_validation_service()
        assert validation_service is not None

    def test_multiple_validation_service_calls_use_same_registration(
        self,
        pipeline_config: PipelineConfig,
        provider_registry: InMemoryProviderRegistry,
    ) -> None:
        """Multiple calls to get_validation_service use same registered schemas."""
        loader = MagicMock()
        mock_service = MagicMock(spec=SchemaBootstrapService)
        mock_schema_provider = MagicMock()
        mock_service.ensure_registered.return_value = mock_schema_provider

        container = PipelineContainer(
            pipeline_config,
            loader=loader,
            provider_registry=provider_registry,
            schema_bootstrap_service=mock_service,
        )

        # Call multiple times
        _service1 = container.get_validation_service()
        _service2 = container.get_validation_service()
        _service3 = container.get_validation_service()

        # ensure_registered is idempotent, so multiple calls are fine
        # but they should all use the same service
        assert mock_service.ensure_registered.call_count == 3
