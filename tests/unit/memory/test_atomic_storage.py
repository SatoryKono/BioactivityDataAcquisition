"""Tests for atomic and conflict-aware memory storage."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from memory.storage import (
    StorageConflictError,
    append_jsonl,
    atomic_write_json,
    atomic_write_text,
    content_digest,
    exclusive_lock,
)

pytestmark = pytest.mark.unit


def test_atomic_write_text_replaces_complete_content(tmp_path: Path) -> None:
    target = tmp_path / "memory.txt"

    digest = atomic_write_text(target, "complete\n")

    assert target.read_text(encoding="utf-8") == "complete\n"
    assert digest == content_digest(b"complete\n")
    assert not list(tmp_path.glob("*.tmp"))
    assert not list(tmp_path.glob("*.lock"))


def test_atomic_write_rejects_stale_expected_digest(tmp_path: Path) -> None:
    target = tmp_path / "memory.json"
    original_digest = atomic_write_json(target, {"version": 1})
    atomic_write_json(target, {"version": 2}, expected_digest=original_digest)

    with pytest.raises(StorageConflictError, match="stale expected digest"):
        atomic_write_json(target, {"version": 3}, expected_digest=original_digest)

    assert json.loads(target.read_text(encoding="utf-8")) == {"version": 2}


def test_append_jsonl_preserves_order_and_canonical_encoding(tmp_path: Path) -> None:
    target = tmp_path / "events.jsonl"

    append_jsonl(target, {"sequence": 1, "actor": "a"})
    digest = append_jsonl(target, {"actor": "b", "sequence": 2})

    lines = target.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["sequence"] for line in lines] == [1, 2]
    assert lines[1] == '{"actor":"b","sequence":2}'
    assert digest == content_digest(target.read_bytes())


def test_exclusive_lock_times_out_on_conflict(tmp_path: Path) -> None:
    target = tmp_path / "events.jsonl"

    with exclusive_lock(target):
        with pytest.raises(StorageConflictError, match="timed out acquiring lock"):
            with exclusive_lock(target, timeout_seconds=0, poll_seconds=0):
                pytest.fail("conflicting lock must not be acquired")


def test_exclusive_lock_recovers_dead_owner(tmp_path: Path) -> None:
    target = tmp_path / "events.jsonl"
    lock_path = tmp_path / ".events.jsonl.lock"
    lock_path.write_text(
        json.dumps({"pid": 999_999_999, "process_start": "1", "schema_version": 1}),
        encoding="utf-8",
    )

    with exclusive_lock(target, timeout_seconds=0):
        assert lock_path.exists()

    assert not lock_path.exists()


def test_exclusive_lock_recovers_missing_pid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "events.jsonl"
    lock_path = tmp_path / ".events.jsonl.lock"
    lock_path.write_text(
        json.dumps({"pid": 999_999_999, "process_start": "1", "schema_version": 1}),
        encoding="utf-8",
    )
    monkeypatch.setattr("memory.storage.psutil.pid_exists", lambda _pid: False)

    with exclusive_lock(target, timeout_seconds=0):
        assert lock_path.exists()

    assert not lock_path.exists()


def test_exclusive_lock_recovers_stale_malformed_metadata(tmp_path: Path) -> None:
    target = tmp_path / "events.jsonl"
    lock_path = tmp_path / ".events.jsonl.lock"
    lock_path.write_text("not-json", encoding="utf-8")
    old = time.time() - 60
    os.utime(lock_path, (old, old))

    with exclusive_lock(
        target,
        timeout_seconds=0,
        stale_after_seconds=30,
    ):
        assert lock_path.exists()

    assert not lock_path.exists()


def test_exclusive_lock_does_not_steal_recent_malformed_lock(tmp_path: Path) -> None:
    target = tmp_path / "events.jsonl"
    lock_path = tmp_path / ".events.jsonl.lock"
    lock_path.write_text("not-json", encoding="utf-8")

    with pytest.raises(StorageConflictError, match="timed out acquiring lock"):
        with exclusive_lock(
            target,
            timeout_seconds=0,
            poll_seconds=0,
            stale_after_seconds=30,
        ):
            pytest.fail("recent malformed lock must not be stolen")
