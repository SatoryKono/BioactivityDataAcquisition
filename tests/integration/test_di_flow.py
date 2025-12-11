"""Integration tests for dependency injection flow.

These tests verify the complete dependency injection graph from
CompositionRoot to Pipeline creation without global state.
"""

from __future__ import annotations

import pytest

from bioetl.domain.observability import LoggingPortABC, MetricsPortABC
from bioetl.domain.schemas.pipeline_contracts import PipelineSchemaModel
from bioetl.interfaces.composition_root import CompositionRoot
from bioetl.interfaces.factories import ObservabilityFactoryABC


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

    def increment(self, name: str, value: int = 1, **tags) -> None:
        pass

    def gauge(self, name: str, value: float, **tags) -> None:
        pass

    def timing(self, name: str, value: float, **tags) -> None:
        pass

    def histogram(self, name: str, value: float, **tags) -> None:
        pass


class TestObservabilityFactory(ObservabilityFactoryABC):
    """Test factory providing mock observability components."""

    def __init__(self) -> None:
        self._logger = MockLogger()
        self._metrics = MockMetrics()

    def create_logger(self) -> LoggingPortABC:
        return self._logger

    def create_metrics(self) -> MetricsPortABC:
        return self._metrics


class TestDIFlow:
    """Test dependency injection flow integration."""

    def test_composition_root_creates_schema_contract_provider(self) -> None:
        """Verify CompositionRoot creates schema contract provider."""
        root = CompositionRoot(
            observability_factory=TestObservabilityFactory()
        )

        provider = root.get_schema_contract_provider()

        assert provider is not None
        # Provider should be cached
        assert root.get_schema_contract_provider() is provider

    def test_composition_root_creates_schema_contract_loader(self) -> None:
        """Verify CompositionRoot creates schema contract loader."""
        root = CompositionRoot(
            observability_factory=TestObservabilityFactory()
        )

        loader = root.create_schema_contract_loader()

        assert loader is not None
        # Loader should be able to get config
        # (requires actual infrastructure to be bootstrapped)

    def test_composition_root_observability_from_factory(self) -> None:
        """Verify CompositionRoot uses observability factory."""
        factory = TestObservabilityFactory()
        root = CompositionRoot(observability_factory=factory)

        logger = root.get_logger()
        metrics = root.get_metrics()

        assert isinstance(logger, MockLogger)
        assert isinstance(metrics, MockMetrics)

    def test_composition_root_provides_provider_registry(self) -> None:
        """Verify CompositionRoot provides provider registry."""
        root = CompositionRoot(
            observability_factory=TestObservabilityFactory()
        )

        registry = root.get_provider_registry()

        assert registry is not None
        # Registry should be cached
        assert root.get_provider_registry() is registry

    def test_no_global_state_in_loader_module(self) -> None:
        """Verify loader module has no global state."""
        from bioetl.infrastructure.config import loader

        # These should not exist in __all__
        assert "set_schema_contract_provider" not in loader.__all__
        assert "get_schema_contract_provider" not in loader.__all__
        assert "_set_provider_internal" not in loader.__all__
        assert "_clear_provider_internal" not in loader.__all__


class TestSchemaContractInjection:
    """Test schema contract injection into pipeline components."""

    def test_get_pipeline_contract_returns_model(self) -> None:
        """Verify get_pipeline_contract returns PipelineSchemaModel."""
        from bioetl.domain.schemas.pipeline_contracts import get_pipeline_contract

        contract = get_pipeline_contract("chembl.activity")

        assert isinstance(contract, PipelineSchemaModel)
        assert contract.pipeline_code == "chembl.activity"

    def test_get_pipeline_contract_uses_default_for_unknown(self) -> None:
        """Verify get_pipeline_contract creates default for unknown pipeline."""
        from bioetl.domain.schemas.pipeline_contracts import get_pipeline_contract

        contract = get_pipeline_contract(
            "unknown.pipeline",
            default_entity="my_entity"
        )

        assert isinstance(contract, PipelineSchemaModel)
        assert contract.pipeline_code == "unknown.pipeline"
        assert contract.schema_out == "my_entity"


class TestLegacyAdapters:
    """Test legacy adapter for backward compatibility."""

    def test_create_composition_root_with_legacy_emits_warning(self) -> None:
        """Verify legacy adapter emits deprecation warning."""
        from bioetl.interfaces.legacy_adapters import (
            create_composition_root_with_legacy,
        )

        with pytest.warns(DeprecationWarning, match="logger/metrics parameters"):
            root = create_composition_root_with_legacy(
                logger=MockLogger(),
                metrics=MockMetrics(),
            )

        assert root is not None
        assert isinstance(root.get_logger(), MockLogger)
        assert isinstance(root.get_metrics(), MockMetrics)

    def test_create_composition_root_with_legacy_no_warning_without_legacy_params(
        self,
    ) -> None:
        """Verify legacy adapter doesn't warn when not using legacy params."""
        import warnings

        from bioetl.interfaces.legacy_adapters import (
            create_composition_root_with_legacy,
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            root = create_composition_root_with_legacy(
                observability_factory=TestObservabilityFactory()
            )

        # Should not emit deprecation warning
        deprecation_warnings = [
            x for x in w if issubclass(x.category, DeprecationWarning)
        ]
        assert len(deprecation_warnings) == 0
        assert root is not None
