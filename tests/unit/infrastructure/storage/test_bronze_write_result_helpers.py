"""Unit tests for BronzeWriteResult infrastructure helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest

from bioetl.domain.types import BatchID
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.infrastructure.storage.bronze_write_result_helpers import (
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


def test_is_bronze_write_result_persisted_reports_file_state() -> None:
    file_path = Path("/virtual/batch_abc.jsonl.zst")
    result = _make_result(file_path)

    with patch("pathlib.Path.exists", return_value=False) as exists:
        assert not is_bronze_write_result_persisted(result)
        exists.assert_called_once()

    with patch("pathlib.Path.exists", return_value=True) as exists:
        assert is_bronze_write_result_persisted(result)
        exists.assert_called_once()
