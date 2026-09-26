"""Bronze zstd stream settings stay memory-safe (publication OOM regression)."""

from __future__ import annotations

from pathlib import Path

import pytest
import zstandard as zstd

from bioetl.infrastructure.storage.bronze.io_mixin import BronzeWriterIOMixin
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter


pytestmark = pytest.mark.unit


class _ThreadProbeMixin(BronzeWriterIOMixin):
    COMPRESSION_LEVEL = 3
    COMPRESSION_THREADS = -1
    COMPRESSION_CHUNK_SIZE = 64


def test_negative_thread_count_is_clamped_to_single_thread() -> None:
    mixin = _ThreadProbeMixin()

    assert mixin._effective_compression_threads() == 0


def test_stream_compressor_does_not_pledge_unknown_content_size() -> None:
    mixin = _ThreadProbeMixin()

    compressor = mixin._build_stream_compressor()

    assert compressor is not None
    params = getattr(compressor, "compression_params", None)
    if params is not None:
        write_size = getattr(params, "write_content_size", None)
        if write_size is not None:
            assert write_size is False
    assert mixin._effective_compression_threads() == 0


def test_writer_default_threads_are_single_thread() -> None:
    assert BronzeWriter.COMPRESSION_THREADS == 0


def test_negative_thread_setting_still_writes_valid_zstd(tmp_path: Path) -> None:
    mixin = _ThreadProbeMixin()
    target = tmp_path / "batch.jsonl.zst"
    payload = [b'{"id": 1}\n', b'{"id": 2}\n']

    count, size = mixin._write_atomic_stream(iter(payload), target)

    assert count == 2
    assert size == sum(len(item) for item in payload)
    with zstd.ZstdDecompressor().stream_reader(target.open("rb")) as reader:
        decompressed = reader.read()
    assert decompressed == b"".join(payload)
