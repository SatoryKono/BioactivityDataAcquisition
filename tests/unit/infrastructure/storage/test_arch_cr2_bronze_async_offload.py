"""ARCH-CR2-01: bronze async paths offload blocking I/O via asyncio.to_thread."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import orjson
import pytest
import zstandard as zstd

from bioetl.infrastructure.storage.bronze.read_cleanup_mixin import (
    BronzeWriterReadCleanupMixin,
)


class _Host(BronzeWriterReadCleanupMixin):
    def __init__(self, base: Path) -> None:
        self.base_path = base
        self._flat_structure = False
        self._logger = MagicMock()
        self._metrics = MagicMock()


@pytest.mark.asyncio
async def test_read_bronze_uses_to_thread(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = orjson.dumps({"a": 1}) + b"\n"
    compressed = zstd.ZstdCompressor().compress(payload)
    rel = "chembl/activity/2026-07-01/batch_test.jsonl.zst"
    full = tmp_path / rel
    full.parent.mkdir(parents=True)
    full.write_bytes(compressed)

    host = _Host(tmp_path)
    calls: list[object] = []

    async def _tracking_to_thread(fn, /, *args, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(fn)
        return fn(*args, **kwargs)

    monkeypatch.setattr(
        "bioetl.infrastructure.storage.bronze.read_cleanup_mixin.asyncio.to_thread",
        _tracking_to_thread,
    )

    rows = [row async for row in host.read_bronze(rel)]
    assert rows == [{"a": 1}]
    assert calls, "read_bronze must offload decompress/read via to_thread"


@pytest.mark.asyncio
@pytest.mark.parametrize("separator", ["\u0085", "\u2028", "\u2029"])
@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
async def test_read_bronze_preserves_unicode_separators(
    tmp_path: Path, separator: str, newline: bytes
) -> None:
    records = [{"title": f"First{separator}second"}, {"title": "Next record"}]
    payload = newline.join(orjson.dumps(record) for record in records) + newline
    path = tmp_path / "batch_unicode.jsonl.zst"
    path.write_bytes(zstd.ZstdCompressor().compress(payload))

    rows = [row async for row in _Host(tmp_path).read_bronze(path.name)]

    assert rows == records


@pytest.mark.asyncio
async def test_read_bronze_missing_file_raises(tmp_path: Path) -> None:
    """Failure path: missing bronze artifact must not yield silent empty success."""
    host = _Host(tmp_path)
    with pytest.raises(FileNotFoundError):
        _ = [row async for row in host.read_bronze("missing/path.jsonl.zst")]


@pytest.mark.asyncio
async def test_read_bronze_corrupt_payload_raises(tmp_path: Path) -> None:
    rel = "chembl/activity/2026-07-01/batch_bad.jsonl.zst"
    full = tmp_path / rel
    full.parent.mkdir(parents=True)
    full.write_bytes(b"not-zstd-payload")
    host = _Host(tmp_path)
    with pytest.raises(Exception):
        _ = [row async for row in host.read_bronze(rel)]
