"""Unit tests for BronzeWriteResult infrastructure helpers."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from bioetl.domain.types import BatchID
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.infrastructure.storage.bronze_write_result_helpers import (
    bronze_write_result_exists,
    is_bronze_write_result_persisted,
)

pytestmark = pytest.mark.unit


def _make_result(path: Path) -> BronzeWriteResult:
    return BronzeWriteResult(
        batch_id=BatchID(uuid4()),
        relative_path="chembl/activity/2024-01-15/batch_abc.jsonl.zst",
        absolute_path=str(path),
        record_count=1,
        compressed_size=10,
        uncompressed_size=20,
        checksum_blake2="abc123",
    )


def test_is_bronze_write_result_persisted_reports_file_state(tmp_path: Path) -> None:
    file_path = tmp_path / "batch_abc.jsonl.zst"
    result = _make_result(file_path)

    assert not is_bronze_write_result_persisted(result)

    file_path.write_bytes(b"payload")
    assert is_bronze_write_result_persisted(result)


def test_bronze_write_result_exists_warns_and_delegates(tmp_path: Path) -> None:
    file_path = tmp_path / "batch_abc.jsonl.zst"
    file_path.write_bytes(b"payload")
    result = _make_result(file_path)

    with pytest.deprecated_call(match="deprecated"):
        assert bronze_write_result_exists(result)
