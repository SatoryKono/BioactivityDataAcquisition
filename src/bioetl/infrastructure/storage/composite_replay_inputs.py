"""Immutable Arrow inputs for an offline composite merge.

The reader never falls back to Delta or a provider when an input is absent.
The caller must bind the envelope digest to the parent evidence before use.
"""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import override

import orjson
import pyarrow as pa

from bioetl.domain.ports import DeltaReaderPort


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _table_bytes(table: pa.Table) -> bytes:
    sink = pa.BufferOutputStream()
    with pa.ipc.new_file(sink, table.schema) as writer:
        writer.write_table(table)
    return bytes(sink.getvalue())


def _publish(path: Path, payload: bytes) -> None:
    """Create once; never replace historical evidence, even with identical bytes."""
    with path.open("xb") as stream:
        stream.write(payload)


class CompositeInputCapture:
    """Capture the exact full tables returned to the merge, before preprocessing."""

    def __init__(self, root: Path, reader: DeltaReaderPort) -> None:
        self._root = root
        self._reader = reader
        self._tables: dict[str, pa.Table] = {}
        self._sealed = False
        self._read_lock = asyncio.Lock()

    async def read_table(
        self,
        table_path: str,
        columns: list[str] | None = None,
        limit: int | None = None,
    ) -> object:
        """Freeze the first full read and serve repeated reads from that snapshot."""
        async with self._read_lock:
            if self._sealed:
                raise ValueError("composite_capture_already_sealed")
            if table_path not in self._tables:
                table = await self._reader.read_table(table_path)
                if not isinstance(table, pa.Table):
                    raise TypeError("composite_input_must_be_arrow_table")
                # Arrow may reference a mutable NumPy/source buffer. Own the
                # bytes now, rather than allowing later writes to alter history.
                frozen = _table_bytes(table)
                self._tables[table_path] = pa.ipc.open_file(
                    pa.BufferReader(frozen)
                ).read_all()
        table = self._tables[table_path]
        if columns is not None:
            table = table.select(columns)
        return table if limit is None else table.slice(0, limit)

    async def get_schema(self, table_path: str) -> object:
        """Return the captured schema."""
        table = await self.read_table(table_path)
        assert isinstance(table, pa.Table)
        return table.schema

    async def get_row_count(self, table_path: str) -> int:
        """Return the captured row count."""
        table = await self.read_table(table_path)
        assert isinstance(table, pa.Table)
        return int(table.num_rows)

    async def table_exists(self, table_path: str) -> bool:
        """Delegate only during capture; existence alone never captures an input."""
        return table_path in self._tables or await self._reader.table_exists(table_path)

    async def aclose(self) -> None:
        """The execution owner retains ownership of the underlying reader."""

    def seal(self, *, required_tables: frozenset[str]) -> str:
        """Publish all inputs then their digest-bound inventory, returning its hash.

        ``required_tables`` comes from the execution contract, not from observed
        reads. A swallowed input error therefore cannot certify completeness.
        A failed publication leaves an unsealed directory that cannot be replayed.
        """
        if self._sealed:
            raise ValueError("composite_capture_already_sealed")
        if self._read_lock.locked():
            raise ValueError("composite_capture_read_in_progress")
        if not required_tables or not required_tables.issubset(self._tables):
            raise ValueError("composite_required_input_missing")
        self._root.mkdir(parents=True, exist_ok=False)
        entries: list[dict[str, str]] = []
        for name, table in sorted(self._tables.items()):
            payload = _table_bytes(table)
            digest = _digest(payload)
            filename = f"{len(entries):04d}-{digest}.arrow"
            _publish(self._root / filename, payload)
            entries.append({"table": name, "file": filename, "sha256": digest})
        envelope = orjson.dumps(
            {
                "version": "composite-inputs-v1",
                "required_tables": sorted(required_tables),
                "inputs": entries,
            },
            option=orjson.OPT_SORT_KEYS,
        )
        _publish(self._root / "inputs.json", envelope)
        self._sealed = True
        return _digest(envelope)


class CompositeReplayInputReader(DeltaReaderPort):
    """Read verified inputs with no live reader or datasource dependency."""

    def __init__(self, root: Path, *, envelope_sha256: str) -> None:
        self._tables: dict[str, pa.Table] = {}
        envelope = (root / "inputs.json").read_bytes()
        if _digest(envelope) != envelope_sha256:
            raise ValueError("composite_input_envelope_digest_mismatch")
        payload = orjson.loads(envelope)
        if payload.get("version") != "composite-inputs-v1":
            raise ValueError("composite_input_envelope_version_invalid")
        for item in payload["inputs"]:
            name, filename = item["table"], item["file"]
            candidate = (root / filename).resolve()
            if (
                not isinstance(name, str)
                or not name
                or name in self._tables
                or Path(filename).name != filename
                or not candidate.is_relative_to(root.resolve())
            ):
                raise ValueError("composite_input_reference_invalid")
            content = candidate.read_bytes()
            if _digest(content) != item["sha256"]:
                raise ValueError("composite_input_digest_mismatch")
            self._tables[name] = pa.ipc.open_file(pa.BufferReader(content)).read_all()
        required = payload["required_tables"]
        if not required or not set(required).issubset(self._tables):
            raise ValueError("composite_required_input_missing")

    @override
    async def read_table(
        self,
        table_path: str,
        columns: list[str] | None = None,
        limit: int | None = None,
    ) -> object:
        """Read the verified in-memory snapshot; missing tables fail closed."""
        if table_path not in self._tables:
            raise ValueError("composite_replay_input_not_captured")
        table = self._tables[table_path]
        if columns is not None:
            table = table.select(columns)
        return table if limit is None else table.slice(0, limit)

    async def get_schema(self, table_path: str) -> object:
        """Return the verified schema."""
        table = await self.read_table(table_path)
        assert isinstance(table, pa.Table)
        return table.schema

    async def get_row_count(self, table_path: str) -> int:
        """Return the verified row count."""
        table = await self.read_table(table_path)
        assert isinstance(table, pa.Table)
        return int(table.num_rows)

    @override
    async def table_exists(self, table_path: str) -> bool:
        """Check only the sealed inventory."""
        return table_path in self._tables

    async def aclose(self) -> None:
        """No live resources are owned by the offline reader."""
