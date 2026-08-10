"""Integrity regressions for the local checkpoint envelope."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bioetl.domain.serialization import serialize_to_json
from bioetl.domain.types import RunID
from bioetl.infrastructure.checkpoint._local_checkpoint_integrity import (
    compute_checkpoint_payload_sha256,
)
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpointAdapter
from tests.helpers.deterministic_ids import deterministic_run_uuid_from_callsite

pytestmark = pytest.mark.unit


def _run_id() -> RunID:
    return deterministic_run_uuid_from_callsite("local-checkpoint-integrity")


def _checkpoint_path(base_path: Path, pipeline: str = "pipeline") -> Path:
    return base_path / f"{pipeline}.json"


@pytest.mark.asyncio
async def test_save_persists_digest_and_load_reports_valid_checksum(
    tmp_path: Path,
) -> None:
    adapter = LocalCheckpointAdapter(tmp_path)
    await adapter.save("pipeline", _run_id(), {"offset": 4})

    raw = json.loads(_checkpoint_path(tmp_path).read_text(encoding="utf-8"))
    assert raw["payload_sha256"] == compute_checkpoint_payload_sha256(raw)

    loaded = await adapter.load("pipeline")
    assert loaded is not None
    assert loaded[1]["checkpoint_checksum_valid"] is True


@pytest.mark.asyncio
async def test_load_recomputes_checksum_after_mutable_payload_tampering(
    tmp_path: Path,
) -> None:
    adapter = LocalCheckpointAdapter(tmp_path)
    await adapter.save("pipeline", _run_id(), {"offset": 4})
    path = _checkpoint_path(tmp_path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["metadata"]["offset"] = 999
    path.write_text(json.dumps(raw), encoding="utf-8")

    loaded = await adapter.load("pipeline")
    assert loaded is not None
    assert loaded[1]["checkpoint_checksum_valid"] is False


@pytest.mark.asyncio
async def test_save_strips_forged_caller_checksum_verdict(tmp_path: Path) -> None:
    adapter = LocalCheckpointAdapter(tmp_path)
    await adapter.save(
        "pipeline",
        _run_id(),
        {"checkpoint_checksum_valid": False, "offset": 4},
    )

    raw = json.loads(_checkpoint_path(tmp_path).read_text(encoding="utf-8"))
    assert "checkpoint_checksum_valid" not in raw["metadata"]
    loaded = await adapter.load("pipeline")
    assert loaded is not None
    assert loaded[1]["checkpoint_checksum_valid"] is True


@pytest.mark.asyncio
async def test_history_load_recomputes_checksum_after_tampering(tmp_path: Path) -> None:
    adapter = LocalCheckpointAdapter(tmp_path)
    run_id = _run_id()
    await adapter.save("pipeline", run_id, {"manifest_id": "manifest-1"})
    history_dir = tmp_path / ".history" / "by_pipeline" / "pipeline" / str(run_id)
    history_path = next(history_dir.glob("*.json"))
    raw = json.loads(history_path.read_text(encoding="utf-8"))
    raw["pipeline"] = "other-pipeline"
    history_path.write_text(json.dumps(raw), encoding="utf-8")

    loaded = await adapter.load_for_run("pipeline", run_id)
    assert loaded is not None
    assert loaded[1]["checkpoint_checksum_valid"] is False


@pytest.mark.asyncio
async def test_legacy_digestless_checkpoint_removes_forged_verdict(
    tmp_path: Path,
) -> None:
    run_id = _run_id()
    _checkpoint_path(tmp_path).write_text(
        serialize_to_json(
            {
                "pipeline": "pipeline",
                "run_id": str(run_id),
                "metadata": {"checkpoint_checksum_valid": True, "offset": 4},
                "version": "2.0",
            }
        ),
        encoding="utf-8",
    )

    loaded = await LocalCheckpointAdapter(tmp_path).load("pipeline")
    assert loaded is not None
    assert "checkpoint_checksum_valid" not in loaded[1]


@pytest.mark.asyncio
async def test_malformed_persisted_digest_reports_invalid(tmp_path: Path) -> None:
    adapter = LocalCheckpointAdapter(tmp_path)
    await adapter.save("pipeline", _run_id(), {"offset": 4})
    path = _checkpoint_path(tmp_path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["payload_sha256"] = True
    path.write_text(json.dumps(raw), encoding="utf-8")

    loaded = await adapter.load("pipeline")
    assert loaded is not None
    assert loaded[1]["checkpoint_checksum_valid"] is False


@pytest.mark.asyncio
async def test_non_object_metadata_is_rejected_before_schema_coercion(
    tmp_path: Path,
) -> None:
    _checkpoint_path(tmp_path).write_text(
        serialize_to_json(
            {
                "pipeline": "pipeline",
                "run_id": str(_run_id()),
                "metadata": ["wrong-shape"],
                "version": "2.0",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="metadata must be a dictionary"):
        await LocalCheckpointAdapter(tmp_path).load("pipeline")
