# This module tests the observability interface.
# The observability module starts a metrics server internally by setting `_SERVER_STARTED` to `True`.
# Below are the test functions to ensure server initialization behaviour.

from unittest import mock
import pytest
from bioetl.interfaces import observability
from bioetl.infrastructure.observability import server as infra_server

# Mock `_SERVER_STARTED` to isolate state among test cases.
@pytest.fixture(autouse=True)
def reset_server_started():
    """Reset the `_SERVER_STARTED` before each test."""
    infra_server._SERVER_STARTED = False  # Ensure isolation
    yield
    infra_server._SERVER_STARTED = False  # Cleanup

def test_start_metrics_server_success():
    """Verify metrics_server starts successfully"""
    # The interface function calls the infrastructure function.
    # We want to mock the infrastructure function to verify it's called.
    with mock.patch("bioetl.interfaces.observability._start_server") as mock_start:
        observability.start_metrics_server()
        mock_start.assert_called_once()

def test_start_metrics_server_failure():
    """Simulate server failure and verify """
    with mock.patch("bioetl.interfaces.observability._start_server", side_effect=Exception("Failed")):
        with pytest.raises(Exception, match="Failed"):
            observability.start_metrics_server()
