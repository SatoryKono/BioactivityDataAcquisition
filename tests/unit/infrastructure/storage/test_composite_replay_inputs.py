"""Immutable parent inputs retain Arrow types and never use live fallback."""

import asyncio
import json
from datetime import datetime, UTC
from hashlib import sha256
from unittest.mock import AsyncMock

import pyarrow as pa
import numpy as np
import pytest

from bioetl.infrastructure.storage.composite_replay_inputs import (
    CompositeInputCapture,
    CompositeReplayInputReader,
)


@pytest.fixture
def table():
    return pa.table(
        {
            "assay_id": pa.array(["A", "B", "C"]),
            "cell_id": pa.array([None, "CELL", None], type=pa.string()),
            "values": pa.array([[1, 2], [], None], type=pa.list_(pa.int64())),
            "created": pa.array(
                [datetime(2026, 10, 3, tzinfo=UTC)] * 3,
                type=pa.timestamp("us", tz="UTC"),
            ),
        }
    )


@pytest.mark.asyncio
async def test_captures_first_full_read_and_replays_after_source_removed(
    tmp_path, table
):
    live = AsyncMock()
    live.read_table.return_value = table
    capture = CompositeInputCapture(tmp_path / "snapshot", live)
    projected = await capture.read_table("chembl.assay", columns=["assay_id"], limit=1)
    assert projected.equals(table.select(["assay_id"]).slice(0, 1))
    live.read_table.side_effect = AssertionError("Live read after snapshot")
    assert (await capture.read_table("chembl.assay")).equals(table)
    assert await capture.get_schema("chembl.assay") == table.schema
    assert await capture.get_row_count("chembl.assay") == 3
    assert await capture.table_exists("chembl.assay")
    digest = capture.seal(required_tables=frozenset({"chembl.assay"}))
    reader = CompositeReplayInputReader(tmp_path / "snapshot", envelope_sha256=digest)
    assert (await reader.read_table("chembl.assay")).equals(table)
    assert (await reader.read_table("chembl.assay", ["cell_id"], 2)).equals(
        table.select(["cell_id"]).slice(0, 2)
    )
    assert await reader.get_schema("chembl.assay") == table.schema
    assert await reader.get_row_count("chembl.assay") == 3
    assert await reader.table_exists("chembl.assay")
    assert not await reader.table_exists("chembl.tissue")
    with pytest.raises(ValueError, match="not_captured"):
        await reader.read_table("chembl.tissue")
    await reader.aclose()
    await capture.aclose()
    live.read_table.assert_awaited_once_with("chembl.assay")
    live.aclose.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_required_input_prevents_publication(tmp_path, table):
    capture = CompositeInputCapture(
        tmp_path / "snapshot", AsyncMock(read_table=AsyncMock(return_value=table))
    )
    await capture.read_table("chembl.assay")
    with pytest.raises(ValueError, match="required_input_missing"):
        capture.seal(required_tables=frozenset({"chembl.assay", "chembl.cell_line"}))
    assert not (tmp_path / "snapshot").exists()


@pytest.mark.asyncio
async def test_capture_cannot_overwrite_or_extend_sealed_evidence(tmp_path, table):
    root = tmp_path / "snapshot"
    live = AsyncMock(read_table=AsyncMock(return_value=table))
    capture = CompositeInputCapture(root, live)
    await capture.read_table("seed")
    capture.seal(required_tables=frozenset({"seed"}))
    before = {path.name: path.read_bytes() for path in root.iterdir()}
    with pytest.raises(ValueError, match="already_sealed"):
        capture.seal(required_tables=frozenset({"seed"}))
    with pytest.raises(ValueError, match="already_sealed"):
        await capture.read_table("seed")
    replacement = CompositeInputCapture(root, live)
    await replacement.read_table("seed")
    with pytest.raises(FileExistsError):
        replacement.seal(required_tables=frozenset({"seed"}))
    assert before == {path.name: path.read_bytes() for path in root.iterdir()}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "damage",
    ["envelope", "missing", "changed", "escape", "duplicate", "required", "version"],
)
async def test_replay_rejects_incomplete_or_corrupted_inputs(tmp_path, table, damage):
    root = tmp_path / "snapshot"
    capture = CompositeInputCapture(
        root, AsyncMock(read_table=AsyncMock(return_value=table))
    )
    await capture.read_table("seed")
    digest = capture.seal(required_tables=frozenset({"seed"}))
    envelope = root / "inputs.json"
    payload = json.loads(envelope.read_bytes())
    blob = root / payload["inputs"][0]["file"]
    if damage == "envelope":
        envelope.write_bytes(b"tampered")
    elif damage == "missing":
        blob.unlink()
    elif damage == "changed":
        blob.write_bytes(b"tampered")
    else:
        if damage == "escape":
            payload["inputs"][0]["file"] = "../foreign.arrow"
        elif damage == "duplicate":
            payload["inputs"].append(payload["inputs"][0])
        elif damage == "required":
            payload["required_tables"].append("uncaptured")
        else:
            payload["version"] = "unknown"
        content = json.dumps(payload).encode()
        envelope.write_bytes(content)
        digest = sha256(content).hexdigest()
    with pytest.raises((ValueError, FileNotFoundError)):
        CompositeReplayInputReader(root, envelope_sha256=digest)


@pytest.mark.asyncio
async def test_non_arrow_payload_cannot_be_sealed(tmp_path):
    capture = CompositeInputCapture(
        tmp_path / "snapshot", AsyncMock(read_table=AsyncMock(return_value=[]))
    )
    with pytest.raises(TypeError, match="arrow_table"):
        await capture.read_table("seed")
    with pytest.raises(ValueError, match="required_input_missing"):
        capture.seal(required_tables=frozenset())


@pytest.mark.asyncio
async def test_parallel_reads_freeze_one_version_and_block_premature_seal(
    tmp_path, table
):
    entered, release = asyncio.Event(), asyncio.Event()

    async def read(_name):
        entered.set()
        await release.wait()
        return table

    live = AsyncMock(read_table=AsyncMock(side_effect=read))
    capture = CompositeInputCapture(tmp_path / "snapshot", live)
    first = asyncio.create_task(capture.read_table("seed"))
    await entered.wait()
    second = asyncio.create_task(capture.read_table("seed"))
    with pytest.raises(ValueError, match="read_in_progress"):
        capture.seal(required_tables=frozenset({"seed"}))
    release.set()
    results = await asyncio.gather(first, second)
    assert all(result.equals(table) for result in results)
    live.read_table.assert_awaited_once()
    capture.seal(required_tables=frozenset({"seed"}))


@pytest.mark.asyncio
async def test_cancelled_read_does_not_publish_or_poison_capture(tmp_path, table):
    entered = asyncio.Event()

    async def read(_name):
        entered.set()
        await asyncio.Event().wait()

    live = AsyncMock(read_table=AsyncMock(side_effect=read))
    capture = CompositeInputCapture(tmp_path / "snapshot", live)
    task = asyncio.create_task(capture.read_table("seed"))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    with pytest.raises(ValueError, match="required_input_missing"):
        capture.seal(required_tables=frozenset({"seed"}))
    live.read_table.side_effect = None
    live.read_table.return_value = table
    await capture.read_table("seed")
    capture.seal(required_tables=frozenset({"seed"}))


@pytest.mark.asyncio
async def test_source_buffer_mutation_cannot_change_captured_values(tmp_path):
    values = np.array([1, 2, 3], dtype=np.int64)
    table = pa.table({"value": pa.array(values)})
    capture = CompositeInputCapture(
        tmp_path / "snapshot", AsyncMock(read_table=AsyncMock(return_value=table))
    )
    captured = await capture.read_table("seed")
    values[0] = 999
    assert table.column("value")[0].as_py() == 999
    assert captured.column("value")[0].as_py() == 1
    digest = capture.seal(required_tables=frozenset({"seed"}))
    reader = CompositeReplayInputReader(tmp_path / "snapshot", envelope_sha256=digest)
    assert (await reader.read_table("seed")).column("value")[0].as_py() == 1
