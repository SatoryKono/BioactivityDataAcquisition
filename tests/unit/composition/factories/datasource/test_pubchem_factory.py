"""Tests for the PubChem composition factory."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.factories.datasource.pubchem import create_pubchem_adapter
from bioetl.infrastructure.adapters.common import SyncAdapterDependencyContext


@pytest.mark.unit
class TestCreatePubChemAdapter:
    """Verify composition-owned PubChem assembly."""

    def test_requires_logger(self) -> None:
        with pytest.raises(ValueError, match="requires logger"):
            create_pubchem_adapter(logger=None)

    @patch("bioetl.composition.factories.datasource.pubchem.ThreadPoolExecutor")
    @patch("bioetl.composition.factories.datasource.pubchem.PubChemAdapter")
    @patch("bioetl.composition.factories.datasource.pubchem.PubChemFetchStrategies")
    @patch("bioetl.composition.factories.datasource.pubchem.PubChemEntityMapper")
    @patch(
        "bioetl.composition.factories.datasource.pubchem."
        "AdapterHelpersFactory.create_sync_helpers"
    )
    def test_builds_runtime_dependencies_in_composition(
        self,
        mock_create_sync_helpers: MagicMock,
        mock_entity_mapper_cls: MagicMock,
        mock_fetch_strategies_cls: MagicMock,
        mock_pubchem_adapter_cls: MagicMock,
        mock_thread_pool_cls: MagicMock,
    ) -> None:
        helper_bundle = MagicMock()
        helper_bundle.metrics = MagicMock(name="metrics")
        helper_bundle.error_handler = MagicMock(name="error_handler")
        helper_bundle.request_collector = MagicMock(name="request_collector")
        mock_create_sync_helpers.return_value = helper_bundle

        mapper = MagicMock(name="entity_mapper")
        mock_entity_mapper_cls.return_value = mapper
        strategies = MagicMock(name="fetch_strategies")
        mock_fetch_strategies_cls.return_value = strategies
        thread_pool = MagicMock(name="thread_pool")
        mock_thread_pool_cls.return_value = thread_pool
        adapter = MagicMock(name="adapter")
        mock_pubchem_adapter_cls.return_value = adapter

        logger = MagicMock()
        metrics = MagicMock()

        result = create_pubchem_adapter(logger=logger, metrics=metrics)

        mock_create_sync_helpers.assert_called_once_with(
            provider="pubchem",
            logger=logger,
            metrics=metrics,
        )
        mock_entity_mapper_cls.assert_called_once_with()
        mock_fetch_strategies_cls.assert_called_once()
        strategies_kwargs = mock_fetch_strategies_cls.call_args.kwargs
        assert strategies_kwargs["mapper"] is mapper
        assert strategies_kwargs["request_collector"] is helper_bundle.request_collector
        assert callable(strategies_kwargs["run_in_executor"])

        adapter_kwargs = mock_pubchem_adapter_cls.call_args.kwargs
        assert adapter_kwargs["thread_pool"] is thread_pool
        assert isinstance(
            adapter_kwargs["dependency_context"],
            SyncAdapterDependencyContext,
        )
        assert adapter_kwargs["dependency_context"].metrics is helper_bundle.metrics
        assert (
            adapter_kwargs["dependency_context"].error_handler
            is helper_bundle.error_handler
        )
        assert (
            adapter_kwargs["dependency_context"].request_collector
            is helper_bundle.request_collector
        )
        assert adapter_kwargs["error_handler"] is helper_bundle.error_handler
        assert adapter_kwargs["request_collector"] is helper_bundle.request_collector
        assert adapter_kwargs["entity_mapper"] is mapper
        assert adapter_kwargs["fetch_strategies"] is strategies
        assert result is adapter

    @patch("bioetl.composition.factories.datasource.pubchem.ThreadPoolExecutor")
    @patch("bioetl.composition.factories.datasource.pubchem.PubChemAdapter")
    @patch("bioetl.composition.factories.datasource.pubchem.PubChemFetchStrategies")
    @patch("bioetl.composition.factories.datasource.pubchem.PubChemEntityMapper")
    @patch(
        "bioetl.composition.factories.datasource.pubchem."
        "AdapterHelpersFactory.create_sync_helpers"
    )
    def test_preserves_explicit_runtime_overrides(
        self,
        mock_create_sync_helpers: MagicMock,
        mock_entity_mapper_cls: MagicMock,
        mock_fetch_strategies_cls: MagicMock,
        mock_pubchem_adapter_cls: MagicMock,
        mock_thread_pool_cls: MagicMock,
    ) -> None:
        explicit_error_handler = MagicMock(name="explicit_error_handler")
        explicit_request_collector = MagicMock(name="explicit_request_collector")
        explicit_entity_mapper = MagicMock(name="explicit_entity_mapper")
        explicit_fetch_strategies = MagicMock(name="explicit_fetch_strategies")
        mock_thread_pool_cls.return_value = MagicMock(name="thread_pool")

        create_pubchem_adapter(
            logger=MagicMock(),
            error_handler=explicit_error_handler,
            request_collector=explicit_request_collector,
            entity_mapper=explicit_entity_mapper,
            fetch_strategies=explicit_fetch_strategies,
        )

        mock_create_sync_helpers.assert_not_called()
        mock_entity_mapper_cls.assert_not_called()
        mock_fetch_strategies_cls.assert_not_called()
        adapter_kwargs = mock_pubchem_adapter_cls.call_args.kwargs
        assert adapter_kwargs["dependency_context"] is None
        assert adapter_kwargs["error_handler"] is explicit_error_handler
        assert adapter_kwargs["request_collector"] is explicit_request_collector
        assert adapter_kwargs["entity_mapper"] is explicit_entity_mapper
        assert adapter_kwargs["fetch_strategies"] is explicit_fetch_strategies
