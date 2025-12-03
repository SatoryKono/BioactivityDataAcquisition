"""
Tests for ChemblDataClientHTTPImpl.
"""
# pylint: disable=redefined-outer-name
from unittest.mock import Mock, patch

import pytest
import requests

from bioetl.infrastructure.clients.base.contracts import (
    RateLimiterABC,
    RetryPolicyABC,
)
from bioetl.infrastructure.clients.chembl.impl.http_client import (
    ChemblDataClientHTTPImpl,
)
from bioetl.infrastructure.clients.chembl.request_builder import (
    ChemblRequestBuilder,
)
from bioetl.infrastructure.clients.chembl.response_parser import (
    ChemblResponseParser,
)


@pytest.fixture(name="mock_request_builder")
def fixture_request_builder():
    """Mock ChemblRequestBuilder."""
    builder = Mock(spec=ChemblRequestBuilder)
    builder.for_endpoint.return_value = builder
    builder.build.return_value = "http://test-url"
    return builder


@pytest.fixture(name="mock_response_parser")
def fixture_response_parser():
    """Mock ChemblResponseParser."""
    return Mock(spec=ChemblResponseParser)


@pytest.fixture(name="mock_rate_limiter")
def fixture_rate_limiter():
    """Mock RateLimiterABC."""
    return Mock(spec=RateLimiterABC)


@pytest.fixture(name="mock_retry_policy")
def fixture_retry_policy():
    """Mock RetryPolicyABC."""
    policy = Mock(spec=RetryPolicyABC)
    policy.should_retry.return_value = False
    return policy


@pytest.fixture(name="client")
def fixture_client(
    mock_request_builder,
    mock_response_parser,
    mock_rate_limiter,
    mock_retry_policy
):
    """Create ChemblDataClientHTTPImpl instance with mocks."""
    with patch("requests.Session") as mock_session_cls:
        mock_session = mock_session_cls.return_value
        client = ChemblDataClientHTTPImpl(
            request_builder=mock_request_builder,
            response_parser=mock_response_parser,
            rate_limiter=mock_rate_limiter,
            retry_policy=mock_retry_policy
        )
        client.session = mock_session
        return client


def test_metadata(client, mock_request_builder):
    """Test metadata request."""
    # Setup
    mock_response = Mock()
    mock_response.json.return_value = {"status": "UP"}
    client.session.get.return_value = mock_response

    # Execute
    result = client.metadata()

    # Verify
    mock_request_builder.for_endpoint.assert_called_with("status")
    client.session.get.assert_called()
    assert result == {"status": "UP"}


def test_request_activity(client, mock_request_builder):
    """Test request_activity delegates to request_builder and execute."""
    # Setup
    mock_response = Mock()
    mock_response.json.return_value = {"activities": []}
    client.session.get.return_value = mock_response

    # Execute
    result = client.request_activity(molecule_chembl_id="CHEMBL1")

    # Verify
    mock_request_builder.for_endpoint.assert_called_with("activity")
    mock_request_builder.build.assert_called_with(
        {"molecule_chembl_id": "CHEMBL1"}
    )
    assert result == {"activities": []}


def test_request_retry_logic_success_after_fail(client, mock_retry_policy):
    """Test retry logic retries on failure and succeeds."""
    # Setup
    mock_retry_policy.should_retry.side_effect = [True, False]
    mock_retry_policy.get_delay.return_value = 0

    fail_resp = Mock()
    fail_resp.raise_for_status.side_effect = requests.RequestException("Fail")

    success_resp = Mock()
    success_resp.json.return_value = {"data": "ok"}
    success_resp.raise_for_status.return_value = None

    client.session.get.side_effect = [
        requests.RequestException("Fail"),
        success_resp
    ]

    # Execute
    result = client.request_activity()

    # Verify
    assert client.session.get.call_count == 2
    assert result == {"data": "ok"}


def test_request_retry_logic_gives_up(client, mock_retry_policy):
    """Test retry logic gives up after policy returns False."""
    # Setup
    mock_retry_policy.should_retry.return_value = False

    client.session.get.side_effect = requests.RequestException("Fail")

    # Execute
    with pytest.raises(requests.RequestException):
        client.request_activity()

    # Verify
    assert client.session.get.call_count == 1


def test_rate_limiter_called(client):
    """Test rate limiter is called during iteration."""
    # This tests iter_pages which uses rate limiter
    # iter_pages yields results from execute_request

    client.session.get.return_value.json.return_value = {}

    # We need to mock execute_request logic inside iter_pages
    # or ensure it works
    # In current impl, iter_pages calls execute_request

    gen = client.iter_pages("http://test")
    next(gen)

    client.rate_limiter.wait_if_needed.assert_called()
    client.rate_limiter.acquire.assert_called()
