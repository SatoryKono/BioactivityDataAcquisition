"""Integration-style tests for ChemblDataClientHTTPImpl wiring."""

from unittest.mock import MagicMock

import pytest
from bioetl.infrastructure.clients.chembl.impl.http_client import (
    ChemblDataClientHTTPImpl,
)
from bioetl.infrastructure.clients.chembl.request_builder import (
    ChemblRequestBuilder,
)
from bioetl.infrastructure.clients.chembl.response_parser import (
    ChemblResponseParser,
)
from bioetl.infrastructure.clients.base.contracts import RateLimiterABC
from bioetl.infrastructure.clients.middleware import HttpClientMiddleware


@pytest.fixture
def mock_components():
    return {
        "request_builder": MagicMock(spec=ChemblRequestBuilder),
        "response_parser": MagicMock(spec=ChemblResponseParser),
        "rate_limiter": MagicMock(spec=RateLimiterABC),
        "http_middleware": MagicMock(spec=HttpClientMiddleware),
    }


@pytest.fixture
def client(mock_components):
    client = ChemblDataClientHTTPImpl(
        request_builder=mock_components["request_builder"],
        response_parser=mock_components["response_parser"],
        rate_limiter=mock_components["rate_limiter"],
        http_middleware=mock_components["http_middleware"],
    )
    yield client


def test_request_activity(client, mock_components):
    # Arrange
    mock_builder = mock_components["request_builder"]
    mock_builder.for_endpoint.return_value = mock_builder
    mock_builder.build.return_value = "http://chembl/activity"

    mock_response = MagicMock()
    mock_response.json.return_value = {"data": "test"}
    mock_components["http_middleware"].request.return_value = mock_response

    # Configure response parser to return the data pass-through or processed
    mock_components["response_parser"].parse.return_value = {"data": "test"}

    # Act
    result = client.request_activity(molecule_chembl_id="CHEMBL123")

    # Assert
    mock_builder.for_endpoint.assert_called_with("activity")
    mock_builder.build.assert_called_with({"molecule_chembl_id": "CHEMBL123"})
    mock_components["http_middleware"].request.assert_called_with(
        "GET", "http://chembl/activity"
    )
    assert result == {"data": "test"}


def test_rate_limiter_usage(client, mock_components):
    # Arrange
    mock_limiter = mock_components["rate_limiter"]
    mock_components["http_middleware"].request.return_value = MagicMock(
        json=lambda: {},
        raise_for_status=lambda: None
    )

    # Act
    # iter_pages uses the rate limiter
    list(client.iter_pages("http://test"))

    # Assert
    mock_limiter.wait_if_needed.assert_called()
    mock_limiter.acquire.assert_called()
