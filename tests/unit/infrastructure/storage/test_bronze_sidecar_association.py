"""Sidecar association cases for an existing Bronze batch retry."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import orjson
import pytest
from bioetl.infrastructure.storage.bronze.pipeline_helpers import BronzeWritePrepared
from bioetl.infrastructure.storage.bronze.write_execution import _bronze_sidecar_bytes

pytestmark = pytest.mark.unit

_METADATA = {"batch_id": "batch-1", "entity": "activity", "provider": "chembl"}
_RECORD = b'{"id":1}\n'


def _prepared(tmp_path: Path) -> BronzeWritePrepared:
    payload = tmp_path / "batch.jsonl.zst"
    payload.write_bytes(b"compressed-payload")
    return BronzeWritePrepared(
        records_iter=iter(()),
        record_list=[_RECORD],
        date_str="2024-01-01",
        relative_path="chembl/activity/batch.jsonl.zst",
        metadata=dict(_METADATA),
        full_path=payload,
        meta_path=payload.with_suffix(".zst.meta.json"),
    )


def _canonical(payload: dict[str, object]) -> bytes:
    return orjson.dumps(payload, option=orjson.OPT_SORT_KEYS)


def _association(
    prepared: BronzeWritePrepared, copy_sha256: str | None
) -> dict[str, object]:
    payload_digest = hashlib.sha256(prepared.full_path.read_bytes()).hexdigest()
    return {
        **prepared.metadata,
        "cleanup_association": {
            "schema": 1,
            "payload_sha256": payload_digest,
            "copy_sha256": copy_sha256,
        },
    }


def test_missing_association_keeps_legacy_and_replaces_foreign_sidecar(
    tmp_path: Path,
) -> None:
    prepared = _prepared(tmp_path)
    legacy = _canonical(dict(prepared.metadata))
    prepared.meta_path.write_bytes(legacy)
    assert _bronze_sidecar_bytes(prepared, save_json=True) == legacy

    foreign = _canonical({**prepared.metadata, "extra": "foreign"})
    prepared.meta_path.write_bytes(foreign)
    refreshed = _bronze_sidecar_bytes(prepared, save_json=True)
    assert refreshed != foreign
    body = json.loads(refreshed)
    assert (
        body["cleanup_association"]["copy_sha256"]
        == hashlib.sha256(_RECORD).hexdigest()
    )


def test_null_copy_digest_stays_null_when_retry_requests_json(tmp_path: Path) -> None:
    prepared = _prepared(tmp_path)
    stored = _canonical(_association(prepared, None))
    prepared.meta_path.write_bytes(stored)
    assert _bronze_sidecar_bytes(prepared, save_json=False) == stored
    kept = _bronze_sidecar_bytes(prepared, save_json=True)
    assert kept == stored
    assert json.loads(kept)["cleanup_association"]["copy_sha256"] is None


def test_matching_copy_digest_keeps_existing_sidecar(tmp_path: Path) -> None:
    prepared = _prepared(tmp_path)
    digest = hashlib.sha256(_RECORD).hexdigest()
    stored = _canonical(_association(prepared, digest))
    prepared.meta_path.write_bytes(stored)
    assert _bronze_sidecar_bytes(prepared, save_json=True) == stored


def test_different_copy_digest_proposes_the_current_record_digest(
    tmp_path: Path,
) -> None:
    prepared = _prepared(tmp_path)
    stored = _canonical(_association(prepared, "ab" * 32))
    prepared.meta_path.write_bytes(stored)
    proposed = _bronze_sidecar_bytes(prepared, save_json=True)
    assert proposed != stored
    assert (
        json.loads(proposed)["cleanup_association"]["copy_sha256"]
        == hashlib.sha256(_RECORD).hexdigest()
    )
