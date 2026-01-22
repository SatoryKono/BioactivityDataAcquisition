from __future__ import annotations

from unittest import mock

import pytest

from bioetl.composition._bootstrap import observability as composition_observability
from bioetl.infrastructure import observability as infra_observability
from bioetl.infrastructure.observability import server as obs_server
from bioetl.interfaces import observability

# This module tests the observability interface.
# The observability module re-exports metrics server components from infrastructure layer
# (not from composition._bootstrap) to respect layer boundaries.


# Mock `_SERVER_STARTED` to isolate state among test cases.
@pytest.fixture(autouse=True)
def reset_server_started():
    """Reset the `_SERVER_STARTED` before each test."""
    obs_server._SERVER_STARTED = False  # Ensure isolation
    yield
    obs_server._SERVER_STARTED = False  # Cleanup


def test_start_metrics_server_success():
    """Verify metrics_server starts successfully via interface."""
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


def test_interface_re_exports_from_infrastructure():
    """Verify interface re-exports start_metrics_server from infrastructure layer.

    interfaces/observability.py imports from infrastructure.observability
    (not composition._bootstrap) to respect layer boundaries.
    """
    # The function should be the same object since it's a re-export
    assert observability.start_metrics_server is infra_observability.start_metrics_server
    # Composition layer also imports from infrastructure, so all should be the same
    assert (
        observability.start_metrics_server
        is composition_observability.start_metrics_server
    )


def test_interface_exposes_metrics_server_error():
    """Verify MetricsServerError is exported from interface via infrastructure."""
    # Interface imports directly from infrastructure
    assert observability.MetricsServerError is infra_observability.MetricsServerError
    # All layers should reference the same exception class from infrastructure
    assert observability.MetricsServerError is obs_server.MetricsServerError
    assert (
        observability.MetricsServerError is composition_observability.MetricsServerError
    )
