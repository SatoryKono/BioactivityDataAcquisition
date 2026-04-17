"""Unit tests for AdapterMetricsRecorder."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder


@pytest.mark.unit
class TestAdapterMetrics:
    """Tests for AdapterMetricsRecorder."""

    def test_measure_request_records_histogram(self):
        """Test that measure_request records histogram metric."""
        mock_metrics = MagicMock()
        adapter_metrics = AdapterMetricsRecorder(
            metrics=mock_metrics, provider="chembl"
        )

        with adapter_metrics.measure_request("/activity"):
            assert True

        # Verify histogram was observed
        mock_metrics.observe_histogram.assert_called_once()
        call_args = mock_metrics.observe_histogram.call_args
        assert call_args[0][0] == "bioetl_adapter_request_duration_seconds"
        assert call_args[0][1] > 0  # Duration should be positive
        assert call_args[0][2] == {"provider": "chembl", "endpoint": "/activity"}

    def test_measure_request_records_counter_success(self):
        """Test that measure_request records success counter."""
        mock_metrics = MagicMock()
        adapter_metrics = AdapterMetricsRecorder(
            metrics=mock_metrics, provider="uniprot"
        )

        with adapter_metrics.measure_request("/protein"):
            assert True

        # Verify counter was incremented with success status
        mock_metrics.increment_counter.assert_called_once()
        call_args = mock_metrics.increment_counter.call_args
        assert call_args[0][0] == "bioetl_adapter_requests_total"
        assert call_args[0][1] == 1
        assert call_args[0][2] == {
            "provider": "uniprot",
            "endpoint": "/protein",
            "status": "success",
        }

    def test_measure_request_records_counter_error(self):
        """Test that measure_request records error counter on exception."""
        mock_metrics = MagicMock()
        adapter_metrics = AdapterMetricsRecorder(
            metrics=mock_metrics, provider="pubmed"
        )

        with pytest.raises(ValueError):
            with adapter_metrics.measure_request("/esearch"):
                raise ValueError("Test error")

        # Verify counter was incremented with error status
        mock_metrics.increment_counter.assert_called_once()
        call_args = mock_metrics.increment_counter.call_args
        assert call_args[0][0] == "bioetl_adapter_requests_total"
        assert call_args[0][2]["status"] == "error"

    def test_measure_request_propagates_exception(self):
        """Test that exceptions are properly propagated."""
        mock_metrics = MagicMock()
        adapter_metrics = AdapterMetricsRecorder(
            metrics=mock_metrics, provider="chembl"
        )

        with pytest.raises(RuntimeError, match="Connection failed"):
            with adapter_metrics.measure_request("/compound"):
                raise RuntimeError("Connection failed")

    def test_measure_request_with_noop_metrics(self):
        """Test that NoOpMetrics works correctly."""
        noop_metrics = NoOpMetrics()
        adapter_metrics = AdapterMetricsRecorder(
            metrics=noop_metrics, provider="chembl"
        )
        executed = False

        # Should not raise any exceptions
        with adapter_metrics.measure_request("/activity"):
            executed = True

        assert executed is True

    def test_measure_request_without_metrics_is_best_effort(self):
        """Missing metrics port should not break adapter request flow."""
        adapter_metrics = AdapterMetricsRecorder(metrics=None, provider="chembl")
        executed = False

        with adapter_metrics.measure_request("/activity"):
            executed = True

        assert executed is True

    def test_record_batch_size(self):
        """Test that record_batch_size records histogram metric."""
        mock_metrics = MagicMock()
        adapter_metrics = AdapterMetricsRecorder(
            metrics=mock_metrics, provider="chembl"
        )

        adapter_metrics.record_batch_size("/activity", 500)

        mock_metrics.observe_histogram.assert_called_once_with(
            "bioetl_adapter_batch_size",
            500.0,
            {"provider": "chembl", "endpoint": "/activity"},
        )

    def test_different_endpoints_have_correct_labels(self):
        """Test that different endpoints get correct labels."""
        mock_metrics = MagicMock()
        adapter_metrics = AdapterMetricsRecorder(
            metrics=mock_metrics, provider="uniprot"
        )
        search_measured = False

        with adapter_metrics.measure_request("/uniprotkb/search"):
            search_measured = True
        stream_measured = False

        with adapter_metrics.measure_request("/uniprotkb/stream"):
            stream_measured = True

        # Verify two different endpoints were recorded
        assert search_measured is True
        assert stream_measured is True
        assert mock_metrics.observe_histogram.call_count == 2
        calls = mock_metrics.observe_histogram.call_args_list
        assert calls[0][0][2]["endpoint"] == "/uniprotkb/search"
        assert calls[1][0][2]["endpoint"] == "/uniprotkb/stream"

    def test_provider_label_preserved(self):
        """Test that provider label is correctly set."""
        mock_metrics = MagicMock()

        chembl_metrics = AdapterMetricsRecorder(metrics=mock_metrics, provider="chembl")
        chembl_measured = False
        with chembl_metrics.measure_request("/activity"):
            chembl_measured = True

        uniprot_metrics = AdapterMetricsRecorder(
            metrics=mock_metrics, provider="uniprot"
        )
        uniprot_measured = False
        with uniprot_metrics.measure_request("/protein"):
            uniprot_measured = True

        assert chembl_measured is True
        assert uniprot_measured is True
        calls = mock_metrics.observe_histogram.call_args_list
        assert calls[0][0][2]["provider"] == "chembl"
        assert calls[1][0][2]["provider"] == "uniprot"

    def test_measure_request_updates_p95_gauge(self):
        """Rolling request p95 should be updated after request completion."""
        mock_metrics = MagicMock()
        adapter_metrics = AdapterMetricsRecorder(
            metrics=mock_metrics, provider="chembl"
        )
        executed = False

        with adapter_metrics.measure_request("/activity"):
            executed = True

        assert executed is True
        mock_metrics.set_gauge.assert_called_once()
        call_args = mock_metrics.set_gauge.call_args
        assert call_args[0][0] == "bioetl_adapter_request_p95_seconds"
        assert call_args[0][2] == {"provider": "chembl", "endpoint": "/activity"}
        assert call_args[0][1] >= 0.0

    def test_measure_request_normalizes_dynamic_endpoint_segments(self):
        """Dynamic path segments must collapse to bounded placeholders."""
        mock_metrics = MagicMock()
        adapter_metrics = AdapterMetricsRecorder(
            metrics=mock_metrics, provider="crossref"
        )
        executed = False

        with adapter_metrics.measure_request("/works/123456789"):
            executed = True

        assert executed is True
        histogram_call = mock_metrics.observe_histogram.call_args
        assert histogram_call[0][2] == {
            "provider": "crossref",
            "endpoint": "/works/{id}",
        }

    def test_record_fallback_outcome_records_counters_and_hit_rate(self):
        """Fallback attempts/hits and hit-rate should be emitted consistently."""
        mock_metrics = MagicMock()
        adapter_metrics = AdapterMetricsRecorder(
            metrics=mock_metrics, provider="pubmed"
        )

        adapter_metrics.record_fallback_outcome(
            "fetch_filtered_with_fallback",
            candidates=4,
            hits=3,
        )

        assert mock_metrics.increment_counter.call_count == 2
        attempt_call = mock_metrics.increment_counter.call_args_list[0]
        hit_call = mock_metrics.increment_counter.call_args_list[1]
        assert attempt_call[0][0] == "bioetl_adapter_fallback_attempts_total"
        assert attempt_call[0][1] == 4
        assert hit_call[0][0] == "bioetl_adapter_fallback_hits_total"
        assert hit_call[0][1] == 3
        mock_metrics.set_gauge.assert_called_once_with(
            "bioetl_adapter_fallback_hit_rate",
            0.75,
            {"provider": "pubmed", "operation": "fetch_filtered_with_fallback"},
        )
