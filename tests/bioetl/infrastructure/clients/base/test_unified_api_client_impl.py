from unittest.mock import Mock

import pytest
import requests

from bioetl.domain.configs import ClientConfig
from bioetl.domain.observability import LoggingPortABC
from bioetl.infrastructure.clients.base.impl.unified_api_client_impl import (
    UnifiedAPIClientImpl,
)
from bioetl.infrastructure.errors import ApiClientError, ApiTimeoutError


def test_request_call_wraps_timeout_error() -> None:
    base_client = Mock()
    base_client.request.side_effect = requests.Timeout("timeout")
    logger = Mock(spec=LoggingPortABC)
    client = UnifiedAPIClientImpl(
        provider="chembl", config=ClientConfig(), base_client=base_client, logger=logger
    )

    with pytest.raises(ApiTimeoutError) as err:
        client.request("GET", "https://example.org")

    assert err.value.provider == "chembl"
    assert err.value.endpoint == "https://example.org"
    logger.error.assert_called_once()


def test_request_call_wraps_request_exception() -> None:
    base_client = Mock()
    base_client.request.side_effect = requests.RequestException("boom")
    client = UnifiedAPIClientImpl(
        provider="chembl", config=ClientConfig(), base_client=base_client
    )

    with pytest.raises(ApiClientError) as err:
        client.request("POST", "https://example.org", data={})

    assert err.value.provider == "chembl"
    assert err.value.endpoint == "https://example.org"
