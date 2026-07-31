"""Atomic, conflict-aware filesystem primitives for repository memory."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class StorageConflictError(RuntimeError):
    """Raised when an optimistic write or lock acquisition conflicts."""


def _process_start_token(pid: int) -> str | None:
    """Return the Linux process start token when available."""
    stat_path = Path("/proc") / str(pid) / "stat"
    try:
        fields = stat_path.read_text(encoding="utf-8").split()
    except (OSError, UnicodeError):
        return None
    return fields[21] if len(fields) > 21 else None


def _lock_owner_is_alive(payload: dict[str, Any]) -> bool:
    """Return whether lock metadata still identifies the same live process."""
    pid = payload.get("pid")
    if not isinstance(pid, int) or pid < 1:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError as exc:
        # Windows reports a missing PID as ERROR_INVALID_PARAMETER instead of
        # ProcessLookupError. Unknown probe failures remain fail-closed.
        return getattr(exc, "winerror", None) != 87
    expected_start = payload.get("process_start")
    actual_start = _process_start_token(pid)
    if isinstance(expected_start, str) and actual_start is not None:
        return expected_start == actual_start
    return True


def _recover_orphaned_lock(lock_path: Path, *, stale_after_seconds: float) -> bool:
    """Remove a lock only when its owner is dead or malformed metadata is stale."""
    try:
        raw = lock_path.read_text(encoding="utf-8")
        payload = json.loads(raw)
        stat = lock_path.stat()
    except FileNotFoundError:
        return True
    except (OSError, UnicodeError, json.JSONDecodeError):
        try:
            age_seconds = max(time.time() - lock_path.stat().st_mtime, 0.0)
        except FileNotFoundError:
            return True
        if age_seconds < stale_after_seconds:
            return False
        lock_path.unlink(missing_ok=True)
        return True
    if isinstance(payload, dict) and _lock_owner_is_alive(payload):
        return False
    # The path cannot be replaced while it exists because contenders use O_EXCL.
    # Concurrent recoverers may both unlink, but only one can acquire afterward.
    if stat.st_ino == lock_path.stat().st_ino:
        lock_path.unlink(missing_ok=True)
    return True


def content_digest(data: bytes) -> str:
    """Return the stable SHA-256 digest used for optimistic writes."""
    return hashlib.sha256(data).hexdigest()


@contextmanager
def exclusive_lock(
    target: Path,
    *,
    timeout_seconds: float = 5.0,
    poll_seconds: float = 0.01,
    stale_after_seconds: float = 300.0,
) -> Iterator[None]:
    """Acquire a portable sidecar lock using exclusive file creation."""
    target.parent.mkdir(parents=True, exist_ok=True)
    lock_path = target.with_name(f".{target.name}.lock")
    deadline = time.monotonic() + timeout_seconds
    lock_fd: int | None = None
    while lock_fd is None:
        try:
            lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            if _recover_orphaned_lock(
                lock_path, stale_after_seconds=stale_after_seconds
            ):
                continue
            if time.monotonic() >= deadline:
                raise StorageConflictError(
                    f"timed out acquiring lock: {target}"
                ) from exc
            time.sleep(poll_seconds)
    try:
        payload = {
            "pid": os.getpid(),
            "process_start": _process_start_token(os.getpid()),
            "schema_version": 1,
        }
        os.write(
            lock_fd,
            (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8"),
        )
        os.fsync(lock_fd)
        yield
    finally:
        os.close(lock_fd)
        lock_path.unlink(missing_ok=True)


def atomic_write_bytes(
    target: Path,
    data: bytes,
    *,
    expected_digest: str | None = None,
) -> str:
    """Atomically replace target and optionally enforce optimistic concurrency."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with exclusive_lock(target):
        if expected_digest is not None:
            current = target.read_bytes() if target.exists() else b""
            if content_digest(current) != expected_digest:
                raise StorageConflictError(f"stale expected digest for: {target}")
        temp_path: Path | None = None
        try:
            fd, raw_temp_path = tempfile.mkstemp(
                dir=target.parent,
                prefix=f".{target.name}.",
                suffix=".tmp",
            )
            temp_path = Path(raw_temp_path)
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, target)  # noqa: PTH105 - atomic replace is required
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
    return content_digest(data)


def atomic_write_text(
    target: Path,
    text: str,
    *,
    expected_digest: str | None = None,
) -> str:
    """Atomically write UTF-8 text."""
    return atomic_write_bytes(
        target,
        text.encode("utf-8"),
        expected_digest=expected_digest,
    )


def atomic_write_json(
    target: Path,
    payload: Any,
    *,
    expected_digest: str | None = None,
) -> str:
    """Atomically write deterministic JSON."""
    rendered = (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return atomic_write_text(target, rendered, expected_digest=expected_digest)


def append_jsonl(
    target: Path,
    payload: Any,
    *,
    reject_if: Callable[[dict[str, Any]], bool] | None = None,
    conflict_message: str = "JSONL record already exists",
) -> str:
    """Append one deterministic JSONL event through an atomic replacement."""
    target.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
    with exclusive_lock(target):
        existing = target.read_bytes() if target.exists() else b""
        if reject_if is not None:
            for raw_line in existing.decode("utf-8").splitlines():
                if not raw_line.strip():
                    continue
                row = json.loads(raw_line)
                if not isinstance(row, dict):
                    raise ValueError(f"JSONL record must be an object: {target}")
                if reject_if(row):
                    raise StorageConflictError(conflict_message)
        updated = existing + line.encode("utf-8") + b"\n"
        temp_path: Path | None = None
        try:
            fd, raw_temp_path = tempfile.mkstemp(
                dir=target.parent,
                prefix=f".{target.name}.",
                suffix=".tmp",
            )
            temp_path = Path(raw_temp_path)
            with os.fdopen(fd, "wb") as handle:
                handle.write(updated)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, target)  # noqa: PTH105 - atomic replace is required
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
    return content_digest(updated)
