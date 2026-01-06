"""Tests for composition/factories/transformer_factory.py.

These tests verify the transformer factory for DI-based transformer creation.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from bioetl.composition.factories.transformer_factory import (
    _TRANSFORMER_REGISTRY,
    create_transformer,
    get_transformer_class,
    register_all_transformers,
    register_transformer,
)


@pytest.fixture(autouse=True)
def clean_registry() -> None:
    """Clean the registry before and after each test."""
    _TRANSFORMER_REGISTRY.clear()
    yield
    _TRANSFORMER_REGISTRY.clear()


class MockTransformer:
    """Mock transformer for testing."""

    def __init__(
        self,
        provider: str,
        entity_type: str | None = None,
        tracer: Any = None,
        metrics: Any = None,
        gold_filters: Any = None,
        identity_service: Any = None,
        pii_hasher: Any = None,
    ):
        self.provider = provider
        self.entity_type = entity_type
        self.tracer = tracer
        self.metrics = metrics
        self.gold_filters = gold_filters
        self.identity_service = identity_service
        self.pii_hasher = pii_hasher


class TestRegisterTransformer:
    """Tests for register_transformer function."""

    def test_register_transformer(self) -> None:
        """register_transformer adds to registry."""
        register_transformer("test_provider", "test_entity", MockTransformer)

        assert ("test_provider", "test_entity") in _TRANSFORMER_REGISTRY
        assert (
            _TRANSFORMER_REGISTRY[("test_provider", "test_entity")] is MockTransformer
        )

    def test_register_multiple_transformers(self) -> None:
        """Multiple transformers can be registered."""
        register_transformer("provider1", "entity1", MockTransformer)
        register_transformer("provider2", "entity2", MockTransformer)

        assert len(_TRANSFORMER_REGISTRY) == 2

    def test_register_overwrites_existing(self) -> None:
        """Registering same key overwrites existing."""

        class AnotherMockTransformer:
            pass

        register_transformer("provider", "entity", MockTransformer)
        register_transformer("provider", "entity", AnotherMockTransformer)

        assert _TRANSFORMER_REGISTRY[("provider", "entity")] is AnotherMockTransformer


class TestGetTransformerClass:
    """Tests for get_transformer_class function."""

    def test_get_registered_transformer(self) -> None:
        """get_transformer_class returns registered class."""
        register_transformer("chembl", "activity", MockTransformer)

        result = get_transformer_class("chembl", "activity")

        assert result is MockTransformer

    def test_get_unregistered_returns_none(self) -> None:
        """get_transformer_class returns None for unregistered."""
        result = get_transformer_class("nonexistent", "entity")

        assert result is None


class TestCreateTransformer:
    """Tests for create_transformer function."""

    def test_create_transformer_basic(self) -> None:
        """create_transformer creates instance."""
        register_transformer("chembl", "activity", MockTransformer)

        transformer = create_transformer("chembl", "activity")

        assert isinstance(transformer, MockTransformer)
        assert transformer.provider == "chembl"

    def test_create_transformer_with_tracer(self) -> None:
        """create_transformer passes tracer."""
        mock_tracer = MagicMock()
        register_transformer("chembl", "activity", MockTransformer)

        transformer = create_transformer("chembl", "activity", tracer=mock_tracer)

        assert transformer.tracer is mock_tracer

    def test_create_transformer_with_metrics(self) -> None:
        """create_transformer passes metrics."""
        mock_metrics = MagicMock()
        register_transformer("chembl", "activity", MockTransformer)

        transformer = create_transformer("chembl", "activity", metrics=mock_metrics)

        assert transformer.metrics is mock_metrics

    def test_create_transformer_with_both_observability(self) -> None:
        """create_transformer passes both tracer and metrics."""
        mock_tracer = MagicMock()
        mock_metrics = MagicMock()
        register_transformer("chembl", "activity", MockTransformer)

        transformer = create_transformer(
            "chembl",
            "activity",
            tracer=mock_tracer,
            metrics=mock_metrics,
        )

        assert transformer.tracer is mock_tracer
        assert transformer.metrics is mock_metrics

    def test_create_transformer_passes_entity_type(self) -> None:
        """create_transformer passes entity_type to transformer."""
        register_transformer("chembl", "activity", MockTransformer)

        transformer = create_transformer("chembl", "activity")

        assert transformer.entity_type == "activity"

    def test_create_transformer_with_gold_filters(self) -> None:
        """create_transformer passes gold_filters."""
        mock_gold_filters = MagicMock()
        register_transformer("chembl", "activity", MockTransformer)

        transformer = create_transformer(
            "chembl", "activity", gold_filters=mock_gold_filters
        )

        assert transformer.gold_filters is mock_gold_filters

    def test_create_transformer_with_identity_service(self) -> None:
        """create_transformer passes identity_service."""
        mock_identity_service = MagicMock()
        register_transformer("chembl", "activity", MockTransformer)

        transformer = create_transformer(
            "chembl", "activity", identity_service=mock_identity_service
        )

        assert transformer.identity_service is mock_identity_service

    def test_create_transformer_with_pii_hasher(self) -> None:
        """create_transformer passes pii_hasher."""
        mock_pii_hasher = MagicMock()
        register_transformer("chembl", "activity", MockTransformer)

        transformer = create_transformer(
            "chembl", "activity", pii_hasher=mock_pii_hasher
        )

        assert transformer.pii_hasher is mock_pii_hasher

    def test_create_transformer_with_all_parameters(self) -> None:
        """create_transformer passes all parameters correctly."""
        mock_tracer = MagicMock()
        mock_metrics = MagicMock()
        mock_gold_filters = MagicMock()
        mock_identity_service = MagicMock()
        mock_pii_hasher = MagicMock()
        register_transformer("pubchem", "compound", MockTransformer)

        transformer = create_transformer(
            "pubchem",
            "compound",
            tracer=mock_tracer,
            metrics=mock_metrics,
            gold_filters=mock_gold_filters,
            identity_service=mock_identity_service,
            pii_hasher=mock_pii_hasher,
        )

        assert transformer.provider == "pubchem"
        assert transformer.entity_type == "compound"
        assert transformer.tracer is mock_tracer
        assert transformer.metrics is mock_metrics
        assert transformer.gold_filters is mock_gold_filters
        assert transformer.identity_service is mock_identity_service
        assert transformer.pii_hasher is mock_pii_hasher

    def test_create_transformer_unregistered_raises(self) -> None:
        """create_transformer raises KeyError for unregistered."""
        with pytest.raises(KeyError) as exc_info:
            create_transformer("nonexistent", "entity")

        assert "No transformer registered" in str(exc_info.value)
        assert "nonexistent" in str(exc_info.value)
        assert "entity" in str(exc_info.value)

    def test_create_transformer_error_lists_available(self) -> None:
        """KeyError includes list of available transformers."""
        register_transformer("chembl", "activity", MockTransformer)

        with pytest.raises(KeyError) as exc_info:
            create_transformer("pubchem", "compound")

        error_msg = str(exc_info.value)
        assert "Available:" in error_msg
        assert "chembl" in error_msg or "activity" in error_msg


class TestRegisterAllTransformers:
    """Tests for register_all_transformers function."""

    def test_register_all_populates_registry(self) -> None:
        """register_all_transformers populates the registry."""
        register_all_transformers()

        # Check ChEMBL transformers
        assert ("chembl", "activity") in _TRANSFORMER_REGISTRY
        assert ("chembl", "assay") in _TRANSFORMER_REGISTRY
        assert ("chembl", "molecule") in _TRANSFORMER_REGISTRY
        assert ("chembl", "target") in _TRANSFORMER_REGISTRY
        assert ("chembl", "document") in _TRANSFORMER_REGISTRY
        assert ("chembl", "target_component") in _TRANSFORMER_REGISTRY

        # Check PubChem transformers
        assert ("pubchem", "compound") in _TRANSFORMER_REGISTRY

        # Check UniProt transformers
        assert ("uniprot", "protein") in _TRANSFORMER_REGISTRY

        # Check PubMed transformers
        assert ("pubmed", "publications") in _TRANSFORMER_REGISTRY

    def test_register_all_is_idempotent(self) -> None:
        """register_all_transformers can be called multiple times."""
        register_all_transformers()
        count_first = len(_TRANSFORMER_REGISTRY)

        register_all_transformers()
        count_second = len(_TRANSFORMER_REGISTRY)

        assert count_first == count_second

    def test_registered_transformers_are_classes(self) -> None:
        """Registered items are classes."""
        register_all_transformers()

        for key, value in _TRANSFORMER_REGISTRY.items():
            assert isinstance(value, type), f"{key} is not a class"

    def test_create_transformer_after_register_all(self) -> None:
        """Transformers can be created after register_all."""
        register_all_transformers()

        # Should not raise
        transformer = create_transformer("chembl", "activity")
        assert transformer is not None

    def test_all_providers_registered(self) -> None:
        """All expected providers are registered."""
        register_all_transformers()

        providers = {key[0] for key in _TRANSFORMER_REGISTRY.keys()}
        expected_providers = {
            "chembl",
            "crossref",
            "openalex",
            "pubchem",
            "pubmed",
            "semanticscholar",
            "uniprot",
        }

        assert providers == expected_providers


class TestModuleExports:
    """Tests for module __all__ exports."""

    def test_all_exports(self) -> None:
        """All expected functions are exported."""
        from bioetl.composition.factories import transformer_factory

        expected = [
            "create_transformer",
            "get_transformer_class",
            "register_all_transformers",
            "register_transformer",
        ]
        for name in expected:
            assert name in transformer_factory.__all__
            assert hasattr(transformer_factory, name)
