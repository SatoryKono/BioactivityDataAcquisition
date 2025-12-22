# This module tests the observability interface.
# The observability module starts a metrics server internally by setting `_SERVER_STARTED` to `True`.
# Below are the test functions to ensure server initialization behaviour.

from unittest import mock
import pytest
from src.interfaces import observability

# Mock `_SERVER_STARTED` to isolate state among test cases.
@pytest.fixture(autouse=True)
def reset_server_started():
    """Reset the `_SERVER_STARTED` before each test."""
    observability._SERVER_STARTED = False  # Ensure isolation
    yield
    observability._SERVER_STARTED = False  # Cleanup

def test_start_metrics_server_success():
    """Verify metrics_server starts successfully"""
    with mock.patch("src.interfaces.observability.start_server") as mock_start:
        observability.start_metrics_server()
        mock_start.assert_called_once()

def test_start_metrics_server_failure():
    """Simulate server failure and verify """
    with mock.patch("src.interfaces.observability.start_server", side_effect=Exception("Failed")):
        with pytest.raises(Exception, match="Failed"):
            observability.start_metrics_server()