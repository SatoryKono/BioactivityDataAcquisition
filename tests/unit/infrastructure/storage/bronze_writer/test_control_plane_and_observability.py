"""Tracing, logging, and metrics invariants for BronzeWriter."""

from __future__ import annotations

import pytest

from tests.unit.infrastructure.storage.bronze_writer.support import (  # noqa: F401
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
