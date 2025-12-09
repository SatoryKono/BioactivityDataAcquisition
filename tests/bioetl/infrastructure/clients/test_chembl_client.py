from unittest.mock import MagicMock

import pytest

from bioetl.domain.clients.base.contracts import ApiClientABC, RateLimiterABC
from bioetl.infrastructure.clients.chembl.impl.chembl_http_client_impl import (
    ChemblHttpClientImpl,
)
from bioetl.infrastructure.clients.chembl.request_builder import (
    ChemblRequestBuilderImpl,
)
from bioetl.infrastructure.clients.chembl.response_parser import (
    ChemblResponseParserImpl,
)


@pytest.fixture
def mock_components():
    request_builder = MagicMock(spec=ChemblRequestBuilderImpl)
    request_builder.for_endpoint = MagicMock(return_value=request_builder)
    return {
        "request_builder": request_builder,
        "response_parser": MagicMock(spec=ChemblResponseParserImpl),
        "rate_limiter": MagicMock(spec=RateLimiterABC),
        "http_client": MagicMock(spec=ApiClientABC),
    }


@pytest.fixture
def client(mock_components):
    client = ChemblHttpClientImpl(
        request_builder=mock_components["request_builder"],
        response_parser=mock_components["response_parser"],
        rate_limiter=mock_components["rate_limiter"],
        client=mock_components["http_client"],
    )
    yield client


def test_fetch_activity_with_http_client(client, mock_components):
    # Arrange
    mock_builder = mock_components["request_builder"]
    mock_builder.for_endpoint.return_value = mock_builder
    mock_builder.build.return_value = "http://chembl/activity"

    mock_response = MagicMock()
    mock_response.json.return_value = {"data": "test"}
    mock_components["http_client"].request.return_value = mock_response

    mock_components["response_parser"].parse_response.return_value = {"data": "test"}

    # Act
    result = client.fetch("activity", molecule_chembl_id="CHEMBL123")

    # Assert
    mock_builder.for_endpoint.assert_called_with("activity")
    mock_builder.build.assert_called_with({"molecule_chembl_id": "CHEMBL123"})
    mock_components["http_client"].request.assert_called_with(
        "GET", "http://chembl/activity"
    )
    assert result == {"data": "test"}


def test_rate_limiter_usage(client, mock_components):
    # Arrange
    mock_limiter = mock_components["rate_limiter"]
    mock_components["http_client"].request.return_value = MagicMock(
        json=lambda: {}, raise_for_status=lambda: None
    )

    # Act
    list(client.iter_pages("http://test"))

    # Assert
    mock_limiter.wait_if_needed.assert_called()
    mock_limiter.acquire.assert_called()
