"""Integration tests for PipelineContainer DI container.

Tests verify that the container properly assembles pipeline dependencies,
enforces required dependencies, and correctly implements lazy initialization.
"""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from bioetl.application.container import PipelineContainer
from bioetl.application.contracts import PipelineContainerABC
from bioetl.domain.configs import (
    ChemblSourceConfig,
    DataFlowConfig,
    DataSinkConfig,
    DataSourceConfig,
    PipelineConfig,
    PipelineIdentityConfig,
    ProviderHttpConfig,
)
from bioetl.domain.observability import LoggingPortABC
from bioetl.domain.pipelines.contracts import ErrorPolicyABC, LoaderABC, PipelineHookABC
from bioetl.domain.provider_registry import ProviderRegistryABC
from bioetl.domain.providers import (
    ProviderComponents,
    ProviderDefinition,
    ProviderId,
)
from bioetl.domain.transform.contracts import HashServiceABC
from bioetl.domain.validation.service import ValidationService

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def minimal_identity() -> PipelineIdentityConfig:
    """Minimal valid identity config for chembl provider."""
    return PipelineIdentityConfig(
        pipeline_id="test.activity",
        provider="chembl",
        entity="activity",
        primary_key=["activity_id"],
    )


@pytest.fixture
def minimal_data_flow() -> DataFlowConfig:
    """Minimal valid data flow config."""
    return DataFlowConfig(
        source=DataSourceConfig(
            input_mode="auto_detect",
            batch_size=100,
        ),
        sink=DataSinkConfig(
            output_path="./data/output",
            dry_run=False,
        ),
    )


@pytest.fixture
def minimal_config(
    minimal_identity: PipelineIdentityConfig,
    minimal_data_flow: DataFlowConfig,
) -> PipelineConfig:
    """Minimal valid config for chembl provider."""
    provider_http = ProviderHttpConfig(base_url="https://www.ebi.ac.uk/chembl/api/data")
    provider_config = ChemblSourceConfig(provider="chembl", http=provider_http)

    return PipelineConfig(
        identity=minimal_identity,
        data_flow=minimal_data_flow,
        provider_config=provider_config,
    )


@pytest.fixture
def mock_loader() -> LoaderABC:
    """Mock loader satisfying LoaderABC."""
    return create_autospec(LoaderABC, instance=True)


@pytest.fixture
def mock_provider_registry() -> ProviderRegistryABC:
    """Mock provider registry with chembl provider."""
    registry = create_autospec(ProviderRegistryABC, instance=True)

    # Configure registry to return a valid definition for "chembl"
    components = create_autospec(ProviderComponents, instance=True)

    definition = ProviderDefinition(
        id=ProviderId.CHEMBL,
        config_type=ChemblSourceConfig,
        components=components,
    )

    registry.get_provider.return_value = definition

    return registry


@pytest.fixture
def mock_hash_service() -> HashServiceABC:
    """Mock hash service satisfying HashServiceABC."""
    return create_autospec(HashServiceABC, instance=True)


@pytest.fixture
def container_with_defaults(
    minimal_config: PipelineConfig,
    mock_loader: LoaderABC,
    mock_provider_registry: ProviderRegistryABC,
    mock_hash_service: HashServiceABC,
) -> PipelineContainer:
    """Container with minimal required dependencies and defaults."""
    return PipelineContainer(
        minimal_config,
        loader=mock_loader,
        provider_registry=mock_provider_registry,
        hash_service=mock_hash_service,
    )


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.integration
class TestContainerRequiredDependencies:
    """Tests for required dependency validation."""

    def test_container_requires_loader(
        self,
        minimal_config: PipelineConfig,
        mock_provider_registry: ProviderRegistryABC,
    ) -> None:
        """Container raises ValueError when loader=None."""
        with pytest.raises(ValueError, match="Loader must be provided"):
            PipelineContainer(
                minimal_config,
                loader=None,
                provider_registry=mock_provider_registry,
            )

    def test_container_requires_provider_registry_or_provider(
        self,
        minimal_config: PipelineConfig,
        mock_loader: LoaderABC,
    ) -> None:
        """Container raises ValueError when neither registry nor provider is given."""
        with pytest.raises(
            ValueError,
            match="Provider registry must be supplied",
        ):
            PipelineContainer(
                minimal_config,
                loader=mock_loader,
                provider_registry=None,
                provider_registry_provider=None,
            )


@pytest.mark.integration
class TestContainerCoreServices:
    """Tests for core service getters."""

    def test_get_logger_returns_logging_port(
        self, container_with_defaults: PipelineContainer
    ) -> None:
        """get_logger returns object with LoggingPortABC interface.

        Note: The default noop logger is duck-typed (SimpleNamespace),
        so we check for required interface methods.
        """
        logger = container_with_defaults.get_logger()

        # Check duck-typing: logger has required methods
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "debug")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "apply_bind")
        assert callable(logger.info)
        assert callable(logger.apply_bind)

    def test_get_validation_service_returns_configured(
        self, container_with_defaults: PipelineContainer
    ) -> None:
        """get_validation_service returns ValidationService instance."""
        validation_service = container_with_defaults.get_validation_service()

        assert isinstance(validation_service, ValidationService)

    def test_get_loader_returns_injected_loader(
        self,
        minimal_config: PipelineConfig,
        mock_loader: LoaderABC,
        mock_provider_registry: ProviderRegistryABC,
    ) -> None:
        """get_loader returns the same loader that was injected."""
        container = PipelineContainer(
            minimal_config,
            loader=mock_loader,
            provider_registry=mock_provider_registry,
        )

        result = container.get_loader()

        assert result is mock_loader


@pytest.mark.integration
class TestContainerTransformComponents:
    """Tests for transform component getters."""

    def test_get_hash_service_returns_hash_service_abc(
        self, container_with_defaults: PipelineContainer
    ) -> None:
        """get_hash_service returns HashServiceABC implementation."""
        hash_service = container_with_defaults.get_hash_service()

        assert isinstance(hash_service, HashServiceABC)

    def test_get_hash_service_returns_same_instance(
        self, container_with_defaults: PipelineContainer
    ) -> None:
        """get_hash_service returns same instance on repeated calls (cached)."""
        first_call = container_with_defaults.get_hash_service()
        second_call = container_with_defaults.get_hash_service()

        assert first_call is second_call

    def test_get_hash_service_raises_when_not_configured(
        self,
        minimal_config: PipelineConfig,
        mock_loader: LoaderABC,
        mock_provider_registry: ProviderRegistryABC,
    ) -> None:
        """get_hash_service raises RuntimeError when not injected."""
        container = PipelineContainer(
            minimal_config,
            loader=mock_loader,
            provider_registry=mock_provider_registry,
            # hash_service not provided
        )

        with pytest.raises(RuntimeError, match="Hash service is not configured"):
            container.get_hash_service()


@pytest.mark.integration
class TestContainerRuntimeComponents:
    """Tests for runtime component getters."""

    def test_get_hooks_returns_list(
        self, container_with_defaults: PipelineContainer
    ) -> None:
        """get_hooks returns a list of PipelineHookABC implementations."""
        hooks = container_with_defaults.get_hooks()

        assert isinstance(hooks, list)
        for hook in hooks:
            assert isinstance(hook, PipelineHookABC)

    def test_get_error_policy_returns_policy(
        self, container_with_defaults: PipelineContainer
    ) -> None:
        """get_error_policy returns ErrorPolicyABC implementation."""
        error_policy = container_with_defaults.get_error_policy()

        assert isinstance(error_policy, ErrorPolicyABC)


@pytest.mark.integration
class TestContainerDependencyInjection:
    """Tests for custom dependency injection."""

    def test_container_uses_injected_dependencies(
        self,
        minimal_config: PipelineConfig,
        mock_loader: LoaderABC,
        mock_provider_registry: ProviderRegistryABC,
    ) -> None:
        """Container uses injected logger instead of creating default."""
        custom_logger = create_autospec(LoggingPortABC, instance=True)

        container = PipelineContainer(
            minimal_config,
            loader=mock_loader,
            provider_registry=mock_provider_registry,
            logger=custom_logger,
        )

        result = container.get_logger()

        assert result is custom_logger

    def test_container_uses_injected_hash_service(
        self,
        minimal_config: PipelineConfig,
        mock_loader: LoaderABC,
        mock_provider_registry: ProviderRegistryABC,
    ) -> None:
        """Container uses injected hash_service instead of factory-created."""
        custom_hash_service = create_autospec(HashServiceABC, instance=True)

        container = PipelineContainer(
            minimal_config,
            loader=mock_loader,
            provider_registry=mock_provider_registry,
            hash_service=custom_hash_service,
        )

        result = container.get_hash_service()

        assert result is custom_hash_service

    def test_container_uses_injected_hooks(
        self,
        minimal_config: PipelineConfig,
        mock_loader: LoaderABC,
        mock_provider_registry: ProviderRegistryABC,
    ) -> None:
        """Container uses injected hooks list instead of default."""
        custom_hook = create_autospec(PipelineHookABC, instance=True)
        custom_hooks = [custom_hook]

        container = PipelineContainer(
            minimal_config,
            loader=mock_loader,
            provider_registry=mock_provider_registry,
            hooks=custom_hooks,
        )

        result = container.get_hooks()

        assert len(result) == 1
        assert result[0] is custom_hook

    def test_container_uses_injected_error_policy(
        self,
        minimal_config: PipelineConfig,
        mock_loader: LoaderABC,
        mock_provider_registry: ProviderRegistryABC,
    ) -> None:
        """Container uses injected error_policy instead of default."""
        custom_policy = create_autospec(ErrorPolicyABC, instance=True)

        container = PipelineContainer(
            minimal_config,
            loader=mock_loader,
            provider_registry=mock_provider_registry,
            error_policy=custom_policy,
        )

        result = container.get_error_policy()

        assert result is custom_policy


@pytest.mark.integration
class TestContainerLazyInitialization:
    """Tests for lazy initialization behavior."""

    def test_container_lazy_initialization_transform_factory(
        self,
        minimal_config: PipelineConfig,
        mock_loader: LoaderABC,
        mock_provider_registry: ProviderRegistryABC,
        mock_hash_service: HashServiceABC,
    ) -> None:
        """Transform factory is created lazily on first access."""
        container = PipelineContainer(
            minimal_config,
            loader=mock_loader,
            provider_registry=mock_provider_registry,
            hash_service=mock_hash_service,
        )

        # Internal transform factory should be None before access
        assert container._transform_factory is None

        # First access triggers creation
        _ = container.get_hash_service()

        # Now factory should be initialized
        assert container._transform_factory is not None

    def test_container_lazy_initialization_service_factory(
        self,
        minimal_config: PipelineConfig,
        mock_loader: LoaderABC,
        mock_provider_registry: ProviderRegistryABC,
    ) -> None:
        """Service factory is created lazily on first access."""
        container = PipelineContainer(
            minimal_config,
            loader=mock_loader,
            provider_registry=mock_provider_registry,
        )

        # Internal service factory should be None before access
        assert container._service_factory is None

        # First access triggers creation via get_normalization_service
        _ = container.get_normalization_service()

        # Now factory should be initialized
        assert container._service_factory is not None


@pytest.mark.integration
class TestContainerContractCompliance:
    """Tests for PipelineContainerABC contract compliance."""

    def test_container_implements_contract(
        self, container_with_defaults: PipelineContainer
    ) -> None:
        """PipelineContainer implements PipelineContainerABC."""
        assert isinstance(container_with_defaults, PipelineContainerABC)

    def test_container_config_property_returns_config(
        self, container_with_defaults: PipelineContainer, minimal_config: PipelineConfig
    ) -> None:
        """Container.config property returns the injected config."""
        assert container_with_defaults.config is minimal_config


@pytest.mark.integration
class TestContainerProviderRegistryResolution:
    """Tests for provider registry resolution."""

    def test_container_accepts_provider_registry_callable(
        self,
        minimal_config: PipelineConfig,
        mock_loader: LoaderABC,
        mock_provider_registry: ProviderRegistryABC,
    ) -> None:
        """Container accepts provider_registry_provider callable instead of instance."""
        provider_called = False

        def registry_provider() -> ProviderRegistryABC:
            nonlocal provider_called
            provider_called = True
            return mock_provider_registry

        container = PipelineContainer(
            minimal_config,
            loader=mock_loader,
            provider_registry_provider=registry_provider,
        )

        # Provider not called yet (lazy)
        assert not provider_called

        # Container created successfully with callable
        assert container is not None
