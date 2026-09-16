"""Tests for PubChem default dependency builders."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bioetl.infrastructure.adapters.pubchem import client_builders

pytestmark = pytest.mark.unit


def test_default_mapper_and_collector_builders_delegate_to_canonical_types() -> None:
    mapper = object()
    collector = object()
    with (
        patch.object(client_builders, "PubChemEntityMapper", return_value=mapper) as mapper_cls,
        patch.object(
            client_builders,
            "create_default_request_collector",
            return_value=collector,
        ) as collector_factory,
    ):
        assert client_builders._create_default_pubchem_entity_mapper() is mapper
        assert client_builders._create_default_pubchem_request_collector() is collector
    mapper_cls.assert_called_once_with()
    collector_factory.assert_called_once_with()


def test_default_fetch_strategy_builder_preserves_transport_dependencies() -> None:
    strategy = object()
    strategy_cls = MagicMock(return_value=strategy)
    logger = object()
    rate_limiter = object()
    circuit_breaker = object()
    mapper = object()
    run_in_executor = MagicMock()
    collector = object()

    with patch(
        "bioetl.infrastructure.adapters.pubchem.fetch_strategies.PubChemFetchStrategies",
        strategy_cls,
    ):
        assert (
            client_builders._create_default_pubchem_fetch_strategies(
                logger=logger,
                rate_limiter=rate_limiter,
                circuit_breaker=circuit_breaker,
                mapper=mapper,
                run_in_executor=run_in_executor,
                provider_name="pubchem",
                request_collector=collector,
            )
            is strategy
        )

    assert strategy_cls.call_args.kwargs == {
        "mapper": mapper,
        "transport": {
            "logger": logger,
            "rate_limiter": rate_limiter,
            "circuit_breaker": circuit_breaker,
            "run_in_executor": run_in_executor,
        },
        "provider_name": "pubchem",
        "request_collector": collector,
    }
