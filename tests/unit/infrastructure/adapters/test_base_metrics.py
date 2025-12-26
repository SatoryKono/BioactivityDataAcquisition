"""Unit tests for AdapterMetrics."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics


@pytest.mark.unit
class TestAdapterMetrics:
    """Tests for AdapterMetrics."""

    def test_measure_request_records_histogram(self):
        """Test that measure_request records histogram metric."""
        mock_metrics = MagicMock()
        adapter_metrics = AdapterMetrics(metrics=mock_metrics, provider="chembl")

        with adapter_metrics.measure_request("/activity"):
            pass  # Simulate successful request

        # Verify histogram was observed
        mock_metrics.observe_histogram.assert_called_once()
        call_args = mock_metrics.observe_histogram.call_args
        assert call_args[0][0] == "adapter_request_duration_seconds"
        assert call_args[0][1] > 0  # Duration should be positive
        assert call_args[0][2] == {"provider": "chembl", "endpoint": "/activity"}

    def test_measure_request_records_counter_success(self):
        """Test that measure_request records success counter."""
        mock_metrics = MagicMock()
        adapter_metrics = AdapterMetrics(metrics=mock_metrics, provider="uniprot")

        with adapter_metrics.measure_request("/protein"):
            pass

        # Verify counter was incremented with success status
        mock_metrics.increment_counter.assert_called_once()
        call_args = mock_metrics.increment_counter.call_args
        assert call_args[0][0] == "adapter_requests_total"
        assert call_args[0][1] == 1
        assert call_args[0][2] == {
            "provider": "uniprot",
            "endpoint": "/protein",
            "status": "success",
        }

    def test_measure_request_records_counter_error(self):
        """Test that measure_request records error counter on exception."""
        mock_metrics = MagicMock()
        adapter_metrics = AdapterMetrics(metrics=mock_metrics, provider="pubmed")

        with pytest.raises(ValueError):
            with adapter_metrics.measure_request("/esearch"):
                raise ValueError("Test error")

        # Verify counter was incremented with error status
        mock_metrics.increment_counter.assert_called_once()
        call_args = mock_metrics.increment_counter.call_args
        assert call_args[0][0] == "adapter_requests_total"
        assert call_args[0][2]["status"] == "error"

    def test_measure_request_propagates_exception(self):
        """Test that exceptions are properly propagated."""
        mock_metrics = MagicMock()
        adapter_metrics = AdapterMetrics(metrics=mock_metrics, provider="chembl")

        with pytest.raises(RuntimeError, match="Connection failed"):
            with adapter_metrics.measure_request("/compound"):
                raise RuntimeError("Connection failed")

    def test_measure_request_with_noop_metrics(self):
        """Test that NoOpMetrics works correctly."""
        noop_metrics = NoOpMetrics()
        adapter_metrics = AdapterMetrics(metrics=noop_metrics, provider="chembl")

        # Should not raise any exceptions
        with adapter_metrics.measure_request("/activity"):
            pass

    def test_record_batch_size(self):
        """Test that record_batch_size records histogram metric."""
        mock_metrics = MagicMock()
        adapter_metrics = AdapterMetrics(metrics=mock_metrics, provider="chembl")

        adapter_metrics.record_batch_size("/activity", 500)

        mock_metrics.observe_histogram.assert_called_once_with(
            "adapter_batch_size",
            500.0,
            {"provider": "chembl", "endpoint": "/activity"},
        )

    def test_different_endpoints_have_correct_labels(self):
        """Test that different endpoints get correct labels."""
        mock_metrics = MagicMock()
        adapter_metrics = AdapterMetrics(metrics=mock_metrics, provider="uniprot")

        with adapter_metrics.measure_request("/uniprotkb/search"):
            pass

        with adapter_metrics.measure_request("/uniprotkb/stream"):
            pass

        # Verify two different endpoints were recorded
        assert mock_metrics.observe_histogram.call_count == 2
        calls = mock_metrics.observe_histogram.call_args_list
        assert calls[0][0][2]["endpoint"] == "/uniprotkb/search"
        assert calls[1][0][2]["endpoint"] == "/uniprotkb/stream"

    def test_provider_label_preserved(self):
        """Test that provider label is correctly set."""
        mock_metrics = MagicMock()

        chembl_metrics = AdapterMetrics(metrics=mock_metrics, provider="chembl")
        with chembl_metrics.measure_request("/activity"):
            pass

        uniprot_metrics = AdapterMetrics(metrics=mock_metrics, provider="uniprot")
        with uniprot_metrics.measure_request("/protein"):
            pass

        calls = mock_metrics.observe_histogram.call_args_list
        assert calls[0][0][2]["provider"] == "chembl"
        assert calls[1][0][2]["provider"] == "uniprot"
