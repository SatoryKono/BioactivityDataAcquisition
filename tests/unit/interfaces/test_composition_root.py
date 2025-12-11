"""Unit tests for CompositionRoot."""

from __future__ import annotations

from unittest.mock import Mock

from bioetl.domain.observability import LoggingPortABC, MetricsPortABC
from bioetl.interfaces.composition_root import (
    CompositionRoot,
    ObservabilityStack,
    get_composition_root,
    reset_composition_root,
)
from bioetl.interfaces.factories import (
    InfrastructureFactoryABC,
    ObservabilityFactoryABC,
)


class MockLogger(LoggingPortABC):
    """Mock logger for testing."""

    def debug(self, msg: str, **kwargs) -> None:
        pass

    def info(self, msg: str, **kwargs) -> None:
        pass

    def warning(self, msg: str, **kwargs) -> None:
        pass

    def error(self, msg: str, **kwargs) -> None:
        pass

    def critical(self, msg: str, **kwargs) -> None:
        pass

    def exception(self, msg: str, **kwargs) -> None:
        pass

    def apply_bind(self, **kwargs) -> "LoggingPortABC":
        return self


class MockMetrics(MetricsPortABC):
    """Mock metrics for testing."""

    def inc_counter(self, name: str, labels: dict[str, str]) -> None:
        pass

    def observe_histogram(
        self, name: str, value: float, labels: dict[str, str]
    ) -> None:
        pass

    def update_stage_duration(
        self,
        *,
        pipeline: str,
        provider: str,
        entity: str,
        stage: str,
        outcome: str,
        duration_sec: float,
    ) -> None:
        pass

    def update_stage_total(
        self,
        *,
        pipeline: str,
        provider: str,
        entity: str,
        stage: str,
        outcome: str,
    ) -> None:
        pass


class TestCompositionRootInit:
    """Test CompositionRoot initialization."""

    def test_init_with_defaults(self) -> None:
        """Verify CompositionRoot initializes with defaults."""
        root = CompositionRoot()

        assert root is not None

    def test_init_with_custom_observability_factory(self) -> None:
        """Verify CompositionRoot uses custom observability factory."""
        mock_factory = Mock(spec=ObservabilityFactoryABC)
        mock_factory.create_logger.return_value = MockLogger()
        mock_factory.create_metrics.return_value = MockMetrics()

        root = CompositionRoot(observability_factory=mock_factory)

        logger = root.get_logger()
        metrics = root.get_metrics()

        mock_factory.create_logger.assert_called_once()
        mock_factory.create_metrics.assert_called_once()
        assert isinstance(logger, MockLogger)
        assert isinstance(metrics, MockMetrics)

    def test_init_with_custom_infrastructure_factory(self) -> None:
        """Verify CompositionRoot uses custom infrastructure factory."""
        mock_factory = Mock(spec=InfrastructureFactoryABC)

        root = CompositionRoot(infrastructure_factory=mock_factory)

        assert root is not None


class TestCompositionRootObservability:
    """Test CompositionRoot observability methods."""

    def test_get_observability_stack(self) -> None:
        """Verify get_observability_stack returns correct stack."""
        mock_factory = Mock(spec=ObservabilityFactoryABC)
        mock_factory.create_logger.return_value = MockLogger()
        mock_factory.create_metrics.return_value = MockMetrics()

        root = CompositionRoot(observability_factory=mock_factory)
        stack = root.get_observability_stack()

        assert isinstance(stack, ObservabilityStack)
        assert isinstance(stack.logger, MockLogger)
        assert isinstance(stack.metrics, MockMetrics)


class TestCompositionRootProviderRegistry:
    """Test CompositionRoot provider registry methods."""

    def test_get_provider_registry_creates_registry(self) -> None:
        """Verify get_provider_registry creates registry."""
        root = CompositionRoot()

        registry = root.get_provider_registry()

        assert registry is not None

    def test_get_provider_registry_caches_result(self) -> None:
        """Verify get_provider_registry caches result."""
        root = CompositionRoot()

        registry1 = root.get_provider_registry()
        registry2 = root.get_provider_registry()

        assert registry1 is registry2


class TestCompositionRootSchemaContractProvider:
    """Test CompositionRoot schema contract provider methods."""

    def test_get_schema_contract_provider_creates_provider(self) -> None:
        """Verify get_schema_contract_provider creates provider."""
        root = CompositionRoot()

        provider = root.get_schema_contract_provider()

        assert provider is not None

    def test_get_schema_contract_provider_caches_result(self) -> None:
        """Verify get_schema_contract_provider caches result."""
        root = CompositionRoot()

        provider1 = root.get_schema_contract_provider()
        provider2 = root.get_schema_contract_provider()

        assert provider1 is provider2

    def test_get_schema_contract_provider_uses_explicit_provider(self) -> None:
        """Verify get_schema_contract_provider uses explicit provider."""
        from bioetl.domain.ports.schema import SchemaContractProviderABC

        mock_provider = Mock(spec=SchemaContractProviderABC)

        root = CompositionRoot(schema_contract_provider=mock_provider)
        provider = root.get_schema_contract_provider()

        assert provider is mock_provider


class TestCompositionRootSingleton:
    """Test CompositionRoot singleton functions."""

    def test_get_composition_root_returns_singleton(self) -> None:
        """Verify get_composition_root returns singleton."""
        reset_composition_root()

        root1 = get_composition_root()
        root2 = get_composition_root()

        assert root1 is root2

    def test_reset_composition_root_clears_singleton(self) -> None:
        """Verify reset_composition_root clears singleton."""
        reset_composition_root()
        root1 = get_composition_root()

        reset_composition_root()
        root2 = get_composition_root()

        assert root1 is not root2


class TestCompositionRootHttpInfrastructure:
    """Test CompositionRoot HTTP infrastructure methods."""

    def test_create_http_session(self) -> None:
        """Verify create_http_session creates session."""
        import requests

        root = CompositionRoot()

        session = root.create_http_session()

        assert isinstance(session, requests.Session)

    def test_create_http_session_uses_custom_factory(self) -> None:
        """Verify create_http_session uses custom factory."""

        class MockSession:
            pass

        root = CompositionRoot(http_session_factory=MockSession)

        session = root.create_http_session()

        assert isinstance(session, MockSession)
