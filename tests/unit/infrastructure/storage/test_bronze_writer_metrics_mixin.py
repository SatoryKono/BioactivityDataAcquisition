"""Unit tests for BronzeWriterMetricsMixin."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.infrastructure.storage.bronze.metrics_mixin import (
    BronzeWriterMetricsMixin,
)


class _Host(BronzeWriterMetricsMixin):
    """Minimal host that wires the mixin for isolated testing."""

    def __init__(self) -> None:
        self.logger = MagicMock()
        self._metrics = MagicMock()


@pytest.mark.unit
class TestBronzeWriterMetricsMixin:
    """Tests for Bronze write metrics emission."""

    def test_emit_bronze_write_metrics_observes_histogram(self) -> None:
        """Should call observe_histogram with duration and labels."""
        host = _Host()
        host._emit_bronze_write_metrics(
            duration=1.234,
            provider="chembl",
            entity="activity",
            record_count=100,
            compressed_size=2048,
            uncompressed_size=4096,
            relative_path="chembl/activity/2025-01-15/data.jsonl.zst",
            batch_id=BatchID("b-1"),
            run_id=RunID("r-1"),
            run_type=RunType.INCREMENTAL,
        )
        host._metrics.observe_histogram.assert_called_once_with(
            "bioetl_bronze_write_duration_seconds",
            1.234,
            {"provider": "chembl", "entity": "activity"},
        )

    def test_emit_bronze_write_metrics_increments_records_counter(self) -> None:
        """Should increment bioetl_bronze_records_written_total counter."""
        host = _Host()
        host._emit_bronze_write_metrics(
            duration=0.5,
            provider="pubmed",
            entity="publication",
            record_count=200,
            compressed_size=3000,
            uncompressed_size=6000,
            relative_path="pubmed/publication/2025-01-15/data.jsonl.zst",
            batch_id=BatchID("b-2"),
            run_id=RunID("r-2"),
            run_type=RunType.BACKFILL,
        )
        calls = host._metrics.increment_counter.call_args_list
        assert calls[0].args == (
            "bioetl_bronze_records_written_total",
            200,
            {"provider": "pubmed", "entity": "publication"},
        )

    def test_emit_bronze_write_metrics_increments_bytes_counter(self) -> None:
        """Should increment bioetl_bronze_bytes_written_total with compressed size."""
        host = _Host()
        host._emit_bronze_write_metrics(
            duration=0.5,
            provider="chembl",
            entity="compound",
            record_count=50,
            compressed_size=1500,
            uncompressed_size=3000,
            relative_path="chembl/compound/2025-01-15/data.jsonl.zst",
            batch_id=BatchID("b-3"),
            run_id=RunID("r-3"),
            run_type=RunType.REBUILD,
        )
        calls = host._metrics.increment_counter.call_args_list
        assert calls[1].args == (
            "bioetl_bronze_bytes_written_total",
            1500,
            {"provider": "chembl", "entity": "compound"},
        )

    def test_emit_bronze_write_metrics_logs_info(self) -> None:
        """Should log bronze_write_complete with structured fields."""
        host = _Host()
        host._emit_bronze_write_metrics(
            duration=2.567,
            provider="chembl",
            entity="activity",
            record_count=10,
            compressed_size=512,
            uncompressed_size=1024,
            relative_path="chembl/activity/2025-01-15/data.jsonl.zst",
            batch_id=BatchID("b-4"),
            run_id=RunID("r-4"),
            run_type=RunType.INCREMENTAL,
        )
        host.logger.info.assert_called_once()
        call_args = host.logger.info.call_args
        assert call_args.args[0] == "bronze_write_complete"
        assert call_args.kwargs["duration_seconds"] == pytest.approx(2.567)
