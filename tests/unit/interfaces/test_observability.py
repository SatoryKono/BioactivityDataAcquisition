"""Unit tests for Observability Interface."""

import errno
from unittest.mock import patch

import pytest

from bioetl.infrastructure.observability import server
from bioetl.interfaces.observability import start_metrics_server


@pytest.fixture(autouse=True)
def reset_server_state():
    """Reset server state between tests."""
    original_port = server._SERVER_PORT
    server._SERVER_PORT = None
    yield
    server._SERVER_PORT = original_port


@pytest.mark.unit
def test_start_metrics_server_success():
    """Test start_metrics_server calls the underlying server starter."""
    with patch(
        "bioetl.infrastructure.observability.server.start_http_server"
    ) as mock_start:
        start_metrics_server(8000)
        mock_start.assert_called_once_with(8000)


@pytest.mark.unit
def test_start_metrics_server_address_in_use():
    """Test start_metrics_server raises OSError when port is in use."""
    os_error = OSError("Address already in use")
    os_error.errno = errno.EADDRINUSE
    
    with patch(
        "bioetl.infrastructure.observability.server.start_http_server",
        side_effect=os_error,
    ):
        with pytest.raises(OSError) as exc_info:
            start_metrics_server(9090)
        
        # Should include helpful error message
        assert "Port 9090 is already in use by another process" in str(exc_info.value)


@pytest.mark.unit
def test_start_metrics_server_other_failure():
    """Test start_metrics_server propagates other OSErrors."""
    os_error = OSError("Permission denied")
    os_error.errno = errno.EACCES
    
    with patch(
        "bioetl.infrastructure.observability.server.start_http_server",
        side_effect=os_error,
    ):
        with pytest.raises(OSError):
            start_metrics_server(9090)
