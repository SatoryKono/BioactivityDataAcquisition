from unittest.mock import Mock

import pytest
import requests

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
from bioetl.infrastructure.errors import (
    ApiParseError,
    ApiTimeoutError,
    ApiUnexpectedStatusError,
)


@pytest.fixture(name="mock_request_builder")
def fixture_request_builder():
    """Mock ChemblRequestBuilderImpl."""
    builder = Mock(spec=ChemblRequestBuilderImpl)
    builder.build_for_endpoint.return_value = builder
    builder.build_request.return_value = "http://test-url"
    return builder


@pytest.fixture(name="mock_response_parser")
def fixture_response_parser():
    """Mock ChemblResponseParserImpl."""
    return Mock(spec=ChemblResponseParserImpl)


@pytest.fixture(name="mock_rate_limiter")
def fixture_rate_limiter():
    """Mock RateLimiterABC."""
    return Mock(spec=RateLimiterABC)


@pytest.fixture(name="client")
def fixture_client(
    mock_request_builder,
    mock_response_parser,
    mock_rate_limiter,
    mock_http_client,
):
    """Create ChemblHttpClientImpl instance with mocks."""
    client = ChemblHttpClientImpl(
        request_builder=mock_request_builder,
        response_parser=mock_response_parser,
        rate_limiter=mock_rate_limiter,
        client=mock_http_client,
    )
    return client


@pytest.fixture(name="mock_http_client")
def fixture_http_client():
    """Mock ApiClientABC."""
    http_client = Mock(spec=ApiClientABC)
    http_client.request = Mock()
    return http_client


def test_metadata(client, mock_request_builder):
    """Test metadata request."""
    # Setup
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "UP"}
    client.http.request.return_value = mock_response

    # Execute
    result = client.metadata()

    # Verify
    mock_request_builder.build_for_endpoint.assert_called_with("status")
    client.http.request.assert_called_with("GET", "http://test-url")
    assert result == {"status": "UP"}


def test_fetch_activity(client, mock_request_builder):
    """Test fetch delegates to request_builder and execute."""
    # Setup
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"activities": []}
    client.http.request.return_value = mock_response

    # Execute
    result = client.fetch("activity", molecule_chembl_id="CHEMBL1")

    # Verify
    mock_request_builder.build_for_endpoint.assert_called_with("activity")
    mock_request_builder.build_request.assert_called_with(
        {"molecule_chembl_id": "CHEMBL1"}
    )
    assert result == {"activities": []}


def test_execute_request_json_error(client):
    """Test JSON parse error is mapped to ApiParseError."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("bad json")
    client.http.request.return_value = mock_response

    with pytest.raises(ApiParseError) as err:
        client.fetch("activity")

    assert err.value.provider == "chembl"
    assert err.value.endpoint == "http://test-url"
    assert err.value.status_code == 200


def test_rate_limiter_called(client):
    """Test rate limiter is called during iteration."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    client.http.request.return_value = mock_response

    gen = client.iter_pages("http://test")
    next(gen)

    client.rate_limiter.wait_if_needed.assert_called()
    client.rate_limiter.acquire.assert_called()


def test_iter_pages_fetches_all_pages(client):
    """iter_pages should continue requesting while next link exists."""
    first_response = Mock()
    first_response.status_code = 200
    first_response.json.return_value = {
        "page_meta": {
            "next": "/page2",
            "limit": 20,
            "offset": 0,
            "total_count": 40,
        },
        "results": [1],
    }
    second_response = Mock()
    second_response.status_code = 200
    second_response.json.return_value = {
        "page_meta": {
            "next": None,
            "limit": 20,
            "offset": 20,
            "total_count": 40,
        },
        "results": [2],
    }
    client.http.request.side_effect = [first_response, second_response]

    pages = list(client.iter_pages("https://example.org/page1"))

    assert pages == [
        first_response.json.return_value,
        second_response.json.return_value,
    ]
    assert client.http.request.call_count == 2
    client.http.request.assert_any_call("GET", "https://example.org/page1")
    client.http.request.assert_any_call("GET", "https://example.org/page2")
    assert client.rate_limiter.wait_if_needed.call_count == 2
    assert client.rate_limiter.acquire.call_count == 2


def test_iter_pages_without_next_stops_after_first(client):
    """iter_pages yields single page when pagination metadata lacks next link."""
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "page_meta": {"next": None, "limit": 20, "offset": 0, "total_count": 20},
        "results": [1],
    }
    client.http.request.return_value = response

    pages = list(client.iter_pages("https://example.org/page1"))

    assert pages == [response.json.return_value]
    client.http.request.assert_called_once_with("GET", "https://example.org/page1")


def test_execute_request_wraps_timeout(client):
    client.http.request.side_effect = requests.Timeout("timeout")

    with pytest.raises(ApiTimeoutError) as err:
        client.fetch("activity")

    assert err.value.provider == "chembl"
    assert err.value.endpoint == "http://test-url"


def test_execute_request_unexpected_status(client):
    response = Mock()
    response.status_code = 503
    response.json.return_value = {}
    client.http.request.return_value = response

    with pytest.raises(ApiUnexpectedStatusError) as err:
        client.fetch("activity")

    assert err.value.status_code == 503
    assert err.value.endpoint == "http://test-url"
