import pytest
from unittest.mock import MagicMock, patch
from bioetl.infrastructure.clients.chembl.impl.http_client import ChemblDataClientHTTPImpl
from bioetl.infrastructure.clients.chembl.request_builder import ChemblRequestBuilder
from bioetl.infrastructure.clients.chembl.response_parser import ChemblResponseParser
from bioetl.infrastructure.clients.base.contracts import RateLimiterABC, RetryPolicyABC


@pytest.fixture
def mock_components():
    return {
        "request_builder": MagicMock(spec=ChemblRequestBuilder),
        "response_parser": MagicMock(spec=ChemblResponseParser),
        "rate_limiter": MagicMock(spec=RateLimiterABC),
        "retry_policy": MagicMock(spec=RetryPolicyABC),
    }


@pytest.fixture
def client(mock_components):
    with patch(
        "bioetl.infrastructure.clients.chembl.impl.http_client.requests.Session"
    ) as mock_session_cls:
        mock_session = mock_session_cls.return_value
        client = ChemblDataClientHTTPImpl(
            request_builder=mock_components["request_builder"],
            response_parser=mock_components["response_parser"],
            rate_limiter=mock_components["rate_limiter"],
            retry_policy=mock_components["retry_policy"]
        )
        client.session = mock_session  # Ensure we use the mock
        yield client


def test_request_activity(client, mock_components):
    # Arrange
    mock_builder = mock_components["request_builder"]
    mock_builder.for_endpoint.return_value = mock_builder
    mock_builder.build.return_value = "http://chembl/activity"
    
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": "test"}
    client.session.get.return_value = mock_response
    
    # Act
    result = client.request_activity(molecule_chembl_id="CHEMBL123")
    
    # Assert
    mock_builder.for_endpoint.assert_called_with("activity")
    mock_builder.build.assert_called_with({"molecule_chembl_id": "CHEMBL123"})
    client.session.get.assert_called_with("http://chembl/activity")
    assert result == {"data": "test"}


def test_retry_logic_success_after_retry(client, mock_components):
    # Arrange
    mock_policy = mock_components["retry_policy"]
    mock_policy.should_retry.side_effect = [True, False]  # Retry once
    mock_policy.get_delay.return_value = 0.01
    
    client.session.get.side_effect = [
        Exception("Network Error"),
        MagicMock(
            json=lambda: {"success": True},
            raise_for_status=lambda: None
        )
    ]
    
    # Act
    result = client._execute_request("http://test")
    
    # Assert
    assert client.session.get.call_count == 2
    assert result == {"success": True}


def test_rate_limiter_usage(client, mock_components):
    # Arrange
    mock_limiter = mock_components["rate_limiter"]
    client.session.get.return_value = MagicMock(
        json=lambda: {},
        raise_for_status=lambda: None
    )
    
    # Act
    # iter_pages uses the rate limiter
    list(client.iter_pages("http://test"))
    
    # Assert
    mock_limiter.wait_if_needed.assert_called()
    mock_limiter.acquire.assert_called()
