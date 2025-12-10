from unittest.mock import patch

from bioetl.infrastructure.observability.server import start_metrics_server_once


@patch("bioetl.infrastructure.observability.server.start_http_server")
def test_metrics_server_once(mock_start_http_server):
    # Reset singleton state if possible, but assuming isolation or just testing logic
    # Note: start_metrics_server_once uses a global variable or closure state.
    # If it's a module level variable, we might need to reset it.

    # First call - disabled
    assert (
        start_metrics_server_once(enabled=False, port=9100, address="127.0.0.1")
        is False
    )
    mock_start_http_server.assert_not_called()

    # Second call - enabled (should start)
    # Warning: if previous tests ran, this might return False if state wasn't reset.
    # We should probably reset the state manually if we can access it.
    import bioetl.infrastructure.observability.server as server_mod

    server_mod._METRICS_SERVER_STARTED = False

    started = start_metrics_server_once(enabled=True, port=9101, address="127.0.0.1")
    assert started is True
    mock_start_http_server.assert_called_once()

    # Third call - enabled again (should not start)
    started_again = start_metrics_server_once(
        enabled=True, port=9101, address="127.0.0.1"
    )
    assert started_again is False
    # Count should remain 1
    mock_start_http_server.assert_called_once()
