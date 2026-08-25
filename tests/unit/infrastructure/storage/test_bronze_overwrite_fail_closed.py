# pyright: reportArgumentType=false
"""Unit tests for Bronze same-batch overwrite fail-closed behavior (#9632)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.storage.bronze.io_mixin import (
    BronzeWriterIOMixin,
    write_bytes_if_absent_or_same,
)


class _Mixin(BronzeWriterIOMixin):
    COMPRESSION_LEVEL = 3
    COMPRESSION_THREADS = 1
    COMPRESSION_CHUNK_SIZE = 65536

    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path
        self._flat_structure = True
        self.logger = MagicMock()
        self._logger = self.logger
        self._metrics = MagicMock()
        self._resolve_bronze_path = lambda provider, entity, date_str, filename: filename


@pytest.mark.unit
def test_bronze_same_payload_is_idempotent(tmp_path: Path) -> None:
    mixin = _Mixin(tmp_path)
    target = tmp_path / "batch.jsonl.zst"
    records = [b"{\"id\": 1}\n", b"{\"id\": 2}\n"]
    mixin._write_atomic_stream(iter(records), target)
    first = target.read_bytes()
    mixin._write_atomic_stream(iter(records), target)
    assert target.read_bytes() == first


@pytest.mark.unit
def test_bronze_different_payload_raises_file_exists(tmp_path: Path) -> None:
    mixin = _Mixin(tmp_path)
    target = tmp_path / "batch.jsonl.zst"
    mixin._write_atomic_stream(iter([b"{\"id\": 1}\n"]), target)
    with pytest.raises(FileExistsError, match="already exists with different payload"):
        mixin._write_atomic_stream(iter([b"{\"id\": 2}\n"]), target)


@pytest.mark.unit
def test_sidecar_same_bytes_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "batch.meta.json"
    payload = b"{\"k\": 1}"
    write_bytes_if_absent_or_same(path, payload, mismatch_message="mismatch")
    write_bytes_if_absent_or_same(path, payload, mismatch_message="mismatch")
    assert path.read_bytes() == payload


@pytest.mark.unit
def test_sidecar_different_bytes_raises(tmp_path: Path) -> None:
    path = tmp_path / "batch.meta.json"
    write_bytes_if_absent_or_same(path, b"{\"k\": 1}", mismatch_message="sidecar mismatch")
    with pytest.raises(FileExistsError, match="sidecar mismatch"):
        write_bytes_if_absent_or_same(path, b"{\"k\": 2}", mismatch_message="sidecar mismatch")

