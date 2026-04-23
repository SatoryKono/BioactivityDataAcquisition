"""Tracing, logging, and metrics invariants for BronzeWriter."""

from __future__ import annotations

import pytest

from testing_support.bronze_writer import (  # noqa: F401
    TestBronzeWriterLoggerInjection,
    TestBronzeWriterMetrics,
    TestBronzeWriterTracing,
    batch_id,
    ingestion_ts,
    noop_logger,
    noop_metrics,
    run_id,
    run_type,
    sample_records,
)

pytestmark = pytest.mark.unit
