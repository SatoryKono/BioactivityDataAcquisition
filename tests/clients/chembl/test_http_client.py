"""
Tests for the ChemblDataClientHTTPImpl.
"""
from unittest.mock import MagicMock, Mock, patch

import pytest

from bioetl.infrastructure.clients.base.contracts import RateLimiterABC, RetryPolicyABC
from bioetl.infrastructure.clients.chembl.impl.http_client import ChemblDataClientHTTPImpl
from bioetl.infrastructure.clients.chembl.request_builder import ChemblRequestBuilder
from bioetl.infrastructure.clients.chembl.response_parser import ChemblResponseParser


@pytest.fixture
def mock_request_builder_fixture():
    """Fixture for request builder."""
    rb = MagicMock(spec=ChemblRequestBuilder)
    rb.for_endpoint.return_value = rb
    rb.build.return_value = "http://test.url"
    return rb


@pytest.fixture
def mock_response_parser_fixture():
    """Fixture for response parser."""
    return MagicMock(spec=ChemblResponseParser)


@pytest.fixture
def mock_rate_limiter_fixture():
    """Fixture for rate limiter."""
    return MagicMock(spec=RateLimiterABC)


@pytest.fixture
def mock_retry_policy_fixture():
    """Fixture for retry policy."""
    rp = MagicMock(spec=RetryPolicyABC)
    rp.should_retry.return_value = False
    return rp


@pytest.fixture
def client(
    mock_request_builder_fixture,
    mock_response_parser_fixture,
    mock_rate_limiter_fixture,
    mock_retry_policy_fixture
):
    """Fixture for HTTP client."""
    return ChemblDataClientHTTPImpl(
        request_builder=mock_request_builder_fixture,
        response_parser=mock_response_parser_fixture,
        rate_limiter=mock_rate_limiter_fixture,
        retry_policy=mock_retry_policy_fixture
    )


def test_request_activity(client, mock_request_builder_fixture):
    """Test requesting activity data."""
    with patch("requests.Session") as mock_session_cls:
        mock_session = mock_session_cls.return_value
        mock_response = Mock()
        mock_response.json.return_value = {"data": 1}
        mock_session.get.return_value = mock_response

        # Re-init client to use mocked session or just patch existing
        client.session = mock_session

        result = client.request_activity(arg1="val")

        assert result == {"data": 1}
        mock_request_builder_fixture.for_endpoint.assert_called_with(
            "activity"
        )
        mock_request_builder_fixture.build.assert_called_with({"arg1": "val"})
        mock_session.get.assert_called_with("http://test.url")


def test_execute_request_retry(client, mock_retry_policy_fixture):
    """Test request retry logic."""
    mock_retry_policy_fixture.should_retry.side_effect = [True, False]
    mock_retry_policy_fixture.get_delay.return_value = 0.01

    with patch("requests.Session") as mock_session_cls:
        mock_session = mock_session_cls.return_value

        # First call raises exception, second call succeeds
        mock_response_success = Mock()
        mock_response_success.json.return_value = {"success": True}

        mock_session.get.side_effect = [
            Exception("Fail"),
            mock_response_success
        ]
        client.session = mock_session

        url = "http://test.url"
        # pylint: disable=protected-access
        result = client._execute_request(url)

        assert result == {"success": True}
        assert mock_session.get.call_count == 2
        assert mock_retry_policy_fixture.should_retry.call_count >= 1


def test_metadata(client, mock_request_builder_fixture):
    """Test metadata retrieval."""
    with patch("requests.Session") as mock_session_cls:
        mock_session = mock_session_cls.return_value
        mock_session.get.return_value.json.return_value = {"version": "1.0"}
        client.session = mock_session

        result = client.metadata()

        assert result == {"version": "1.0"}
        mock_request_builder_fixture.for_endpoint.assert_called_with("status")


def test_close(client):
    """Test closing the client session."""
    mock_session = Mock()
    client.session = mock_session
    client.close()
    mock_session.close.assert_called_once()


def test_request_methods(client, mock_request_builder_fixture):
    """Test various request methods."""
    mock_session = Mock()
    mock_session.get.return_value.json.return_value = {}
    client.session = mock_session

    client.request_assay()
    mock_request_builder_fixture.for_endpoint.assert_called_with("assay")

    client.request_target()
    mock_request_builder_fixture.for_endpoint.assert_called_with("target")

    client.request_document()
    mock_request_builder_fixture.for_endpoint.assert_called_with("document")

    client.request_molecule()
    mock_request_builder_fixture.for_endpoint.assert_called_with("molecule")


def test_iter_pages(client, mock_rate_limiter_fixture):
    """Test pagination iteration."""
    mock_session = Mock()
    client.session = mock_session

    # Response 1 with next_marker
    mock_response = Mock()
    mock_response.json.return_value = {
        "page_meta": {"next": None},
        "activities": []
    }
    mock_session.get.return_value = mock_response

    pages = list(client.iter_pages("http://url"))

    assert len(pages) == 1
    mock_rate_limiter_fixture.acquire.assert_called()
