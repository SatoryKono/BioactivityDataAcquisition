"""Atomic write and sidecar invariants for BronzeWriter."""

from __future__ import annotations

import pytest

from tests.testing_support.bronze_writer import (  # noqa: F401
    TestBronzeWriterAtomicWrite,
    TestBronzeWriterAudit,
    TestBronzeWriterMetadataDeterminism,
    batch_id,
    ingestion_ts,
    noop_logger,
    noop_metrics,
    run_id,
    run_type,
    sample_records,
)

pytestmark = pytest.mark.unit
