"""ARCH-CR2-01: bronze async paths offload blocking I/O via asyncio.to_thread."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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
