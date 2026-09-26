"""Edge contracts for provider registration support resolution."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.composition.providers._registration_contracts import (
    _create_adapter_for_provider,
    _resolve_provider_registry_candidate,
)

pytestmark = pytest.mark.unit


def test_create_adapter_for_provider_delegates_all_runtime_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The lazy adapter seam forwards registry and provider-specific arguments."""
    expected = MagicMock(name="adapter")
    create = MagicMock(return_value=expected)
    monkeypatch.setattr(
        "bioetl.composition.factories.datasource.data_source_factory.DataSourceFactory.create",
        create,
    )
    client = MagicMock(name="client")
    logger = MagicMock(name="logger")
    settings = MagicMock(name="settings")
    registry = MagicMock(name="registry")

    result = _create_adapter_for_provider(
        "chembl",
        http_client=client,
        logger=logger,
        settings=settings,
        provider_registry=registry,
        entity="activity",
    )

    assert result is expected
    create.assert_called_once_with(
        "chembl",
        http_client=client,
        logger=logger,
        settings=settings,
        provider_registry=registry,
        entity="activity",
    )


def test_incomplete_registry_candidate_is_rejected() -> None:
    """Partial registry lookalikes cannot cross the composition boundary."""
    incomplete = MagicMock(spec=["get_http_config", "create_data_source"])

    assert _resolve_provider_registry_candidate(incomplete) is None
