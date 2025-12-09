from unittest.mock import Mock

from unittest.mock import Mock

import pytest
import requests

from bioetl.domain.configs import ClientConfig
from bioetl.domain.observability import LoggingPortABC, MetricsPortABC
from bioetl.infrastructure.clients.base.impl.unified_api_client_impl import (
    UnifiedAPIClientImpl,
)
from bioetl.infrastructure.errors import ApiClientError, ApiTimeoutError


def test_request_call_wraps_timeout_error() -> None:
    base_client = Mock()
    base_client.request.side_effect = requests.Timeout("timeout")
    logger = Mock(spec=LoggingPortABC)
    metrics = Mock(spec=MetricsPortABC)
    client = UnifiedAPIClientImpl(
        provider="chembl",
        config=ClientConfig(),
        base_client=base_client,
        logger=logger,
        metrics=metrics,
    )

    with pytest.raises(ApiTimeoutError) as err:
        client.request("GET", "https://example.org")

    assert err.value.provider == "chembl"
    assert err.value.endpoint == "https://example.org"
    logger.error.assert_called_once()
    metrics.inc_counter.assert_any_call(
        "client_request_errors",
        {"provider": "chembl", "endpoint": "https://example.org", "status": "timeout"},
    )


def test_request_call_wraps_request_exception() -> None:
    base_client = Mock()
    base_client.request.side_effect = requests.RequestException("boom")
    metrics = Mock(spec=MetricsPortABC)
    client = UnifiedAPIClientImpl(
        provider="chembl",
        config=ClientConfig(),
        base_client=base_client,
        metrics=metrics,
    )

    with pytest.raises(ApiClientError) as err:
        client.request("POST", "https://example.org", data={})

    assert err.value.provider == "chembl"
    assert err.value.endpoint == "https://example.org"
    metrics.inc_counter.assert_any_call(
        "client_request_errors",
        {"provider": "chembl", "endpoint": "https://example.org", "status": "ApiClientError"},
    )


def test_request_records_metrics_on_success() -> None:
    base_client = Mock()
    response = Mock()
    response.status_code = 200
    base_client.request.return_value = response
    metrics = Mock(spec=MetricsPortABC)
    client = UnifiedAPIClientImpl(
        provider="chembl", config=ClientConfig(), base_client=base_client, metrics=metrics
    )

    result = client.request("GET", "https://example.org")

    assert result is response
    metrics.inc_counter.assert_any_call(
        "client_request_total",
        {"provider": "chembl", "endpoint": "https://example.org", "status": "200"},
    )
    metrics.observe_histogram.assert_called_once()
