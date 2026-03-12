"""Unit tests for CrossRef adapter factory."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.composition.factories.datasource.crossref import create_crossref_adapter


@pytest.mark.unit
def test_create_crossref_adapter_with_mailto_kwarg() -> None:
    """create_crossref_adapter uses mailto from kwargs."""
    http_client = MagicMock()
    logger = MagicMock()
    adapter = create_crossref_adapter(
        http_client=http_client,
        logger=logger,
        settings=None,
        mailto="test@example.com",
    )
    assert adapter is not None


@pytest.mark.unit
def test_create_crossref_adapter_with_settings_email() -> None:
    """create_crossref_adapter falls back to settings.default_email."""
    http_client = MagicMock()
    logger = MagicMock()
    settings = SimpleNamespace(default_email="settings@example.com")
    adapter = create_crossref_adapter(
        http_client=http_client,
        logger=logger,
        settings=settings,  # type: ignore[arg-type]
    )
    assert adapter is not None


@pytest.mark.unit
def test_create_crossref_adapter_no_mailto_raises() -> None:
    """create_crossref_adapter raises ValueError when mailto unresolvable."""
    with pytest.raises(ValueError, match="mailto"):
        create_crossref_adapter(
            http_client=MagicMock(),
            logger=MagicMock(),
            settings=None,
        )


@pytest.mark.unit
def test_create_crossref_adapter_no_http_client_raises() -> None:
    """create_crossref_adapter raises ValueError when http_client is None."""
    with pytest.raises(ValueError, match="http_client"):
        create_crossref_adapter(
            http_client=None,
            logger=MagicMock(),
            settings=None,
            mailto="test@example.com",
        )


@pytest.mark.unit
def test_create_crossref_adapter_no_logger_raises() -> None:
    """create_crossref_adapter raises ValueError when logger is None."""
    with pytest.raises(ValueError, match="logger"):
        create_crossref_adapter(
            http_client=MagicMock(),
            logger=None,
            settings=None,
            mailto="test@example.com",
        )


@pytest.mark.unit
def test_create_crossref_adapter_with_optional_kwargs() -> None:
    """create_crossref_adapter forwards optional kwargs."""
    http_client = MagicMock()
    logger = MagicMock()
    adapter = create_crossref_adapter(
        http_client=http_client,
        logger=logger,
        settings=None,
        mailto="test@example.com",
        batch_size=100,
        metrics=MagicMock(),
        error_handler=MagicMock(),
    )
    assert adapter is not None
