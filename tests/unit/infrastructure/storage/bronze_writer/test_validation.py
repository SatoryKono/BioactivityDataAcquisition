"""Validation and bootstrap invariants for BronzeWriter."""

from __future__ import annotations

import pytest

from tests.unit.infrastructure.storage.bronze_writer.support import (  # noqa: F401
    TestBronzeWriterInit,
    TestBronzeWriterJsonValidation,
    TestBronzeWriterNameValidation,
    TestBronzeWriterUTCValidation,
    batch_id,
    ingestion_ts,
    noop_logger,
    noop_metrics,
    run_id,
    run_type,
    sample_records,
)

pytestmark = pytest.mark.unit
