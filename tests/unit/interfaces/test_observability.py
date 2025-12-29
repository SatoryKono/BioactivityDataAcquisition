from __future__ import annotations

from unittest import mock

import pytest

from bioetl.infrastructure.observability import server as obs_server
from bioetl.interfaces import observability

# This module tests the observability interface.
# The observability module starts a metrics server internally by setting `_SERVER_STARTED` to `True`.
# Below are the test functions to ensure server initialization behaviour.


# Mock `_SERVER_STARTED` to isolate state among test cases.
@pytest.fixture(autouse=True)
def reset_server_started():
    """Reset the `_SERVER_STARTED` before each test."""
    obs_server._SERVER_STARTED = False  # Ensure isolation
    yield
    obs_server._SERVER_STARTED = False  # Cleanup


def test_start_metrics_server_success():
    """Verify metrics_server starts successfully"""
    with mock.patch(
        "bioetl.infrastructure.observability.server.start_http_server"
    ) as mock_start:
        observability.start_metrics_server()
        mock_start.assert_called_once()


def test_start_metrics_server_failure():
    """Simulate server failure and verify graceful handling.

    The server is designed to catch exceptions and return False (fail_fast=False by default)
    rather than raising exceptions, to allow pipelines to continue without metrics.
    """
    with mock.patch(
        "bioetl.infrastructure.observability.server.start_http_server",
        side_effect=Exception("Failed"),
    ):
        # Server catches exceptions and returns False for graceful degradation
        result = obs_server.start_metrics_server(port=8000, fail_fast=False)
        assert result is False


def test_interface_passes_config_params():
    """Verify interface layer passes all config params to server."""
    # Patch at the module level where it's imported as _start_server
    with mock.patch("bioetl.interfaces.observability._start_server") as mock_server:
        mock_server.return_value = True
        result = observability.start_metrics_server(
            port=9090,
            fail_fast=True,
            retry_count=5,
            retry_delay=2.0,
        )

        mock_server.assert_called_once_with(
            port=9090,
            fail_fast=True,
            retry_count=5,
            retry_delay=2.0,
        )
        assert result is True


def test_interface_exposes_metrics_server_error():
    """Verify MetricsServerError is exported from interface."""
    assert observability.MetricsServerError is obs_server.MetricsServerError
