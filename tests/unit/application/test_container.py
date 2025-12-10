"""Unit tests for SimplePipelineContainer."""

from __future__ import annotations

import pytest

from bioetl.application.mappers.chembl.record_mapper import ChemblRecordMapper
from bioetl.application.mappers.contracts import RecordMapperABC
from bioetl.application.services.schema_bootstrap import SchemaBootstrapService
from bioetl.application.services.schema_contract_provider import (
    SchemaContractProviderImpl,
)
from bioetl.domain.ports.parsing import ResponseParserPortABC
from bioetl.domain.ports.schema import SchemaContractProviderABC
from bioetl.infrastructure.clients.chembl.response_parser import (
    ChemblGenericResponseParser,
)
from bioetl.infrastructure.config.loader import (
    clear_schema_contract_provider,
    get_schema_contract_provider,
)
from bioetl.interfaces.simple_container import SimplePipelineContainer


@pytest.fixture()
def container() -> SimplePipelineContainer:
    """Create a fresh container for each test."""
    container = SimplePipelineContainer()
    yield container
    # Cleanup after test
    container.reset()


class TestBootstrapSequence:
    """Test bootstrap initialization sequence."""

    def test_bootstrap_initializes_schema_bootstrap_service(
        self, container: SimplePipelineContainer
    ) -> None:
        """Bootstrap should initialize SchemaBootstrapService."""
        assert container._schema_bootstrap is None

        container.bootstrap()

        assert container._schema_bootstrap is not None
        assert isinstance(container._schema_bootstrap, SchemaBootstrapService)

    def test_bootstrap_initializes_schema_contract_provider(
        self, container: SimplePipelineContainer
    ) -> None:
        """Bootstrap should initialize SchemaContractProvider."""
        assert container._schema_contract_provider is None

        container.bootstrap()

        assert container._schema_contract_provider is not None
        assert isinstance(
            container._schema_contract_provider, SchemaContractProviderImpl
        )

    def test_bootstrap_injects_into_infrastructure(
        self, container: SimplePipelineContainer
    ) -> None:
        """Bootstrap should inject schema contract provider into infrastructure."""
        clear_schema_contract_provider()
        assert get_schema_contract_provider() is None

        container.bootstrap()

        provider = get_schema_contract_provider()
        assert provider is not None
        assert provider is container._schema_contract_provider

    def test_bootstrap_is_idempotent(self, container: SimplePipelineContainer) -> None:
        """Calling bootstrap multiple times should not reinitialize."""
        container.bootstrap()
        first_bootstrap = container._schema_bootstrap
        first_provider = container._schema_contract_provider

        container.bootstrap()

        assert container._schema_bootstrap is first_bootstrap
        assert container._schema_contract_provider is first_provider

    def test_is_bootstrapped_flag(self, container: SimplePipelineContainer) -> None:
        """is_bootstrapped should reflect bootstrap state."""
        assert not container.is_bootstrapped

        container.bootstrap()

        assert container.is_bootstrapped


class TestLazyInitialization:
    """Test lazy initialization of components."""

    def test_record_mapper_lazy_init(self, container: SimplePipelineContainer) -> None:
        """record_mapper property should lazily create mapper."""
        assert container._record_mapper is None

        mapper = container.record_mapper

        assert mapper is not None
        assert isinstance(mapper, ChemblRecordMapper)
        assert container._record_mapper is mapper

    def test_record_mapper_returns_same_instance(
        self, container: SimplePipelineContainer
    ) -> None:
        """Multiple accesses should return same mapper instance."""
        first = container.record_mapper
        second = container.record_mapper

        assert first is second

    def test_response_parser_lazy_init(
        self, container: SimplePipelineContainer
    ) -> None:
        """response_parser property should lazily create parser."""
        assert container._response_parser is None

        parser = container.response_parser

        assert parser is not None
        assert isinstance(parser, ChemblGenericResponseParser)
        assert container._response_parser is parser

    def test_response_parser_returns_same_instance(
        self, container: SimplePipelineContainer
    ) -> None:
        """Multiple accesses should return same parser instance."""
        first = container.response_parser
        second = container.response_parser

        assert first is second

    def test_lazy_init_does_not_require_bootstrap(
        self, container: SimplePipelineContainer
    ) -> None:
        """record_mapper and response_parser should work without bootstrap."""
        assert not container.is_bootstrapped

        mapper = container.record_mapper
        parser = container.response_parser

        assert mapper is not None
        assert parser is not None
        assert not container.is_bootstrapped


class TestErrorWhenNotBootstrapped:
    """Test errors when accessing bootstrap-dependent components."""

    def test_schema_contract_provider_raises_without_bootstrap(
        self, container: SimplePipelineContainer
    ) -> None:
        """Accessing schema_contract_provider should raise if not bootstrapped."""
        with pytest.raises(RuntimeError, match="Container not bootstrapped"):
            _ = container.schema_contract_provider

    def test_schema_bootstrap_raises_without_bootstrap(
        self, container: SimplePipelineContainer
    ) -> None:
        """Accessing schema_bootstrap should raise if not bootstrapped."""
        with pytest.raises(RuntimeError, match="Container not bootstrapped"):
            _ = container.schema_bootstrap

    def test_schema_contract_provider_works_after_bootstrap(
        self, container: SimplePipelineContainer
    ) -> None:
        """schema_contract_provider should work after bootstrap."""
        container.bootstrap()

        provider = container.schema_contract_provider

        assert provider is not None
        assert isinstance(provider, SchemaContractProviderABC)

    def test_schema_bootstrap_works_after_bootstrap(
        self, container: SimplePipelineContainer
    ) -> None:
        """schema_bootstrap should work after bootstrap."""
        container.bootstrap()

        service = container.schema_bootstrap

        assert service is not None
        assert isinstance(service, SchemaBootstrapService)


class TestContainerReset:
    """Test container reset functionality."""

    def test_reset_clears_all_components(
        self, container: SimplePipelineContainer
    ) -> None:
        """Reset should clear all cached components."""
        container.bootstrap()
        _ = container.record_mapper
        _ = container.response_parser

        container.reset()

        assert container._schema_bootstrap is None
        assert container._schema_contract_provider is None
        assert container._record_mapper is None
        assert container._response_parser is None
        assert not container.is_bootstrapped

    def test_reset_clears_infrastructure_provider(
        self, container: SimplePipelineContainer
    ) -> None:
        """Reset should clear the global infrastructure provider."""
        container.bootstrap()
        assert get_schema_contract_provider() is not None

        container.reset()

        assert get_schema_contract_provider() is None

    def test_can_bootstrap_after_reset(
        self, container: SimplePipelineContainer
    ) -> None:
        """Container should be usable after reset."""
        container.bootstrap()
        container.reset()

        container.bootstrap()

        assert container.is_bootstrapped
        assert container._schema_contract_provider is not None


class TestContractTypes:
    """Test that components conform to contracts."""

    def test_record_mapper_implements_contract(
        self, container: SimplePipelineContainer
    ) -> None:
        """record_mapper should implement RecordMapperABC."""
        mapper = container.record_mapper

        assert isinstance(mapper, RecordMapperABC)
        assert hasattr(mapper, "map_records")
        assert hasattr(mapper, "get_supported_entities")

    def test_response_parser_implements_contract(
        self, container: SimplePipelineContainer
    ) -> None:
        """response_parser should implement ResponseParserPortABC."""
        parser = container.response_parser

        assert isinstance(parser, ResponseParserPortABC)
        assert hasattr(parser, "parse_to_records")
        assert hasattr(parser, "extract_pagination")

    def test_schema_contract_provider_implements_contract(
        self, container: SimplePipelineContainer
    ) -> None:
        """schema_contract_provider should implement SchemaContractProviderABC."""
        container.bootstrap()
        provider = container.schema_contract_provider

        assert isinstance(provider, SchemaContractProviderABC)
        assert hasattr(provider, "get_contract")
        assert hasattr(provider, "get_input_schema_name")
        assert hasattr(provider, "get_output_schema_name")
