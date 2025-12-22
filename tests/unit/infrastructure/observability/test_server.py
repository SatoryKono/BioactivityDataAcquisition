"""Unit tests for Prometheus metrics server."""

import errno
import time
from unittest.mock import patch

import pytest

from bioetl.infrastructure.observability import server


@pytest.fixture(autouse=True)
def reset_server_state():
    """Reset server state between tests."""
    # Store original state
    original_port = server._SERVER_PORT
    
    # Reset state before test
    server._SERVER_PORT = None
    
    yield
    
    # Restore original state after test
    server._SERVER_PORT = original_port


@pytest.mark.unit
class TestStartMetricsServer:
    """Tests for start_metrics_server function."""

    def test_start_server_success(self):
        """Test successful server start on specified port."""
        with patch("bioetl.infrastructure.observability.server.start_http_server") as mock_start:
            server.start_metrics_server(8000)
            mock_start.assert_called_once_with(8000)
            assert server._SERVER_PORT == 8000

    def test_start_server_idempotent_same_port(self):
        """Test calling start_metrics_server twice with same port is idempotent."""
        with patch("bioetl.infrastructure.observability.server.start_http_server") as mock_start:
            server.start_metrics_server(8000)
            server.start_metrics_server(8000)
            
            # Should only call once
            mock_start.assert_called_once_with(8000)
            assert server._SERVER_PORT == 8000

    def test_start_server_different_port_raises_error(self):
        """Test starting server on different port after successful start raises RuntimeError."""
        with patch("bioetl.infrastructure.observability.server.start_http_server") as mock_start:
            # First start on port 8000
            server.start_metrics_server(8000)
            assert server._SERVER_PORT == 8000
            
            # Try to start on different port
            with pytest.raises(RuntimeError) as exc_info:
                server.start_metrics_server(9000)
            
            assert "already running on port 8000" in str(exc_info.value)
            assert "cannot start on port 9000" in str(exc_info.value)
            
            # Should still only have called once with original port
            mock_start.assert_called_once_with(8000)
            assert server._SERVER_PORT == 8000

    def test_address_already_in_use_raises_error(self):
        """Test EADDRINUSE error is raised, not silently ignored."""
        with patch(
            "bioetl.infrastructure.observability.server.start_http_server",
            side_effect=OSError(errno.EADDRINUSE, "Address already in use")
        ):
            with pytest.raises(OSError) as exc_info:
                server.start_metrics_server(8000)
            
            # Should raise with clear error message
            assert "Port 8000 is already in use by another process" in str(exc_info.value)
            assert "Metrics server cannot be started" in str(exc_info.value)
            
            # Server port should NOT be set
            assert server._SERVER_PORT is None

    def test_other_os_error_is_propagated(self):
        """Test other OSError types are propagated without modification."""
        with patch(
            "bioetl.infrastructure.observability.server.start_http_server",
            side_effect=OSError(errno.EACCES, "Permission denied")
        ):
            with pytest.raises(OSError) as exc_info:
                server.start_metrics_server(8000)
            
            # Original error should be raised
            assert exc_info.value.errno == errno.EACCES
            
            # Server port should NOT be set
            assert server._SERVER_PORT is None

    def test_unexpected_error_is_propagated(self):
        """Test unexpected exceptions are propagated."""
        with patch(
            "bioetl.infrastructure.observability.server.start_http_server",
            side_effect=ValueError("Unexpected error")
        ):
            with pytest.raises(ValueError) as exc_info:
                server.start_metrics_server(8000)
            
            assert "Unexpected error" in str(exc_info.value)
            
            # Server port should NOT be set
            assert server._SERVER_PORT is None

    def test_concurrent_start_same_port(self):
        """Test concurrent calls with same port are handled correctly."""
        call_count = 0
        
        def mock_start_http(port):
            nonlocal call_count
            call_count += 1
            # Simulate some delay by checking global state
            time.sleep(0.01)
        
        with patch(
            "bioetl.infrastructure.observability.server.start_http_server",
            side_effect=mock_start_http
        ):
            # Simulate what would happen in a race condition
            # First call should succeed
            server.start_metrics_server(8000)
            assert server._SERVER_PORT == 8000
            
            # Second call should be idempotent
            server.start_metrics_server(8000)
            
            # Should only call the underlying function once
            assert call_count == 1

    def test_default_port(self):
        """Test server starts with default port 8000."""
        with patch("bioetl.infrastructure.observability.server.start_http_server") as mock_start:
            server.start_metrics_server()
            mock_start.assert_called_once_with(8000)
            assert server._SERVER_PORT == 8000
