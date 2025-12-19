"""Unit tests for Observability Interface."""

from unittest.mock import MagicMock, patch

import pytest

from bioetl.interfaces.observability import start_metrics_server


@pytest.mark.unit
def test_start_metrics_server_success():
    """Test start_metrics_server calls the underlying server starter."""
    # We now mock the internal import or the function it calls
    with patch("bioetl.interfaces.observability._start_server") as mock_start:
        start_metrics_server(8000)
        mock_start.assert_called_once_with(8000)


@pytest.mark.unit
def test_start_metrics_server_failure():
    """Test start_metrics_server raises OSError on failure."""
    with patch(
        "bioetl.interfaces.observability._start_server", side_effect=OSError("In use")
    ):
        with pytest.raises(OSError):
            start_metrics_server(9090)
