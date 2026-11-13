"""Private, source-bound metadata for explicit local closeout commands.

Hashes are local observations, not signatures or authenticated CI transport.
No bundle contents, environment values or subprocess output are stored here.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any, BinaryIO
import uuid

from memory import proof
from scripts.engineering.repo import hook_receipts

LIMIT = 8 * 1024 * 1024
SOURCE_ROOT = Path(__file__).resolve().parents[3]
REQUEST_KIND = "bioetl.closeout.command.request.v1"
RESULT_KIND = "bioetl.closeout.command.result.v1"
RUNTIMES = {"codex", "junie", "devin"}
CLAIMS = {"tested", "reviewed", "done", "ready_to_merge"}


def result(outcome: str, reason: str, event: str | None) -> dict[str, Any]:
    """A local command never authenticates CI or admits an agent lifecycle."""
    codes = {
        "STOP": proof.OUTCOME_EXIT_CODES["STOP"],
        "DEGRADED": proof.OUTCOME_EXIT_CODES["DEGRADED"],
        "ERROR": 2,
        "USER_STOP": 130,
    }
    return {
        "kind": RESULT_KIND,
        "outcome": outcome,
        "exit_code": codes[outcome],
        "reason": reason,
        "event_id": event,
        "claim_qualified": False,
        "runtime_admission": False,
        "ci_acceptance": False,
        "native_event_observed": False,
    }


def event_identity(value: str | None) -> str:
    """Only canonical UUID slots can name command events."""
    if value is None:
        return uuid.uuid4().hex
    parsed = uuid.UUID(value)
    if value != parsed.hex:
        raise ValueError("noncanonical event identity")
    return parsed.hex


def directory(root: Path, event: str, *, reserve: bool = False) -> Path:
    """Reserve one exclusive event, preserving all earlier and foreign state."""
    event = event_identity(event)
    common = hook_receipts.receipt_directory(root).parent
    base = common / "bioetl-closeout-commands"
    if base.is_symlink() or base.resolve() != base:
        raise ValueError("unqualified command directory")
    base.mkdir(exist_ok=True)
    target = base / event
    if reserve:
        target.mkdir(mode=0o700)
    if target.is_symlink() or target.resolve() != target or not target.is_dir():
        raise ValueError("unqualified command event")
    return target


def write_once(target: Path, name: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Write one immutable owned metadata slot; never replace a prior result."""
    if name not in {"request.json", "result.json", "worker.lock"}:
        raise ValueError("unknown metadata slot")
    if target.resolve() != target:
        raise ValueError("metadata directory changed")
    record = {**payload, "payload_sha256": hook_receipts.digest(payload)}
    encoded = json.dumps(record, sort_keys=True).encode()
    if len(encoded) > hook_receipts.RECEIPT_LIMIT:
        raise ValueError("metadata exceeds limit")
    descriptor = os.open(target / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    return record


def read(target: Path, name: str) -> dict[str, Any]:
    """Read only bounded regular files below an owned event directory."""
    if name not in {"request.json", "result.json"}:
        raise ValueError("unknown metadata slot")
    raw = hook_receipts._read_owned_bytes(target / name, target)
    if len(raw) > hook_receipts.RECEIPT_LIMIT:
        raise ValueError("metadata exceeds limit")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("invalid metadata")
    content = {key: item for key, item in value.items() if key != "payload_sha256"}
    if value.get("payload_sha256") != hook_receipts.digest(content):
        raise ValueError("invalid metadata digest")
    return value


@contextmanager
def bundle_stream(root: Path, path: Path) -> Iterator[BinaryIO]:
    """Open a confined regular bundle without copying its contents to metadata."""
    candidate = path if path.is_absolute() else root / path
    resolved = candidate.resolve(strict=True)
    if candidate.is_symlink() or not resolved.is_relative_to(root):
        raise ValueError("unqualified bundle path")
    before = resolved.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError("bundle must be a regular file")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(resolved, flags)
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise ValueError("bundle changed while opening")
        yield stream


def bundle_bytes(stream: BinaryIO) -> bytes:
    """Measure stable bounded input; the caller never logs or persists bytes."""
    before = os.fstat(stream.fileno())
    if not stat.S_ISREG(before.st_mode) or before.st_size > LIMIT:
        raise ValueError("unqualified bundle input")
    stream.seek(0)
    raw = stream.read(LIMIT + 1)
    after = os.fstat(stream.fileno())
    if len(raw) > LIMIT or (before.st_size, before.st_mtime_ns) != (
        after.st_size,
        after.st_mtime_ns,
    ):
        raise ValueError("bundle changed while reading")
    stream.seek(0)
    return raw


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def branch(root: Path) -> str:
    return (
        hook_receipts._git(root, "branch", "--show-current").strip().decode()
        or "detached"
    )


def scope_matches(
    bundle: Any, root: Path, *, task_hash: str, runtime: str, claim: str
) -> bool:
    """Reject a known foreign scope before costly state measurement or execution."""
    if not isinstance(bundle, dict):
        return False
    task = bundle.get("task_id")
    return (
        isinstance(task, str)
        and sha256(task.encode()) == task_hash
        and bundle.get("runtime") == runtime
        and bundle.get("claim") == claim
        and isinstance(bundle.get("repository"), dict)
        and bundle["repository"].get("branch") == branch(root)
    )


def capture(root: Path, env: Mapping[str, str]) -> dict[str, Any]:
    """Bind indexes, history, branch, checker/dependency bytes and environment.

    Root dotenv hashes are observations of that root only, not a filesystem
    sandbox or prevention of arbitrary writes elsewhere. Filter preflight does
    not isolate a hostile concurrent Git-configuration writer.
    """
    expected = SOURCE_ROOT / "src/memory/proof.py"
    if Path(proof.__file__).resolve() != expected:
        raise ValueError("foreign proof core")
    proof._reject_gitlinks(root, timeout=10)
    proof._reject_active_git_filters(root, timeout=10)
    from scripts.engineering.repo.check_no_partial_tree import _index_views

    indexes = [
        hook_receipts._index_material(root, view, reject_hidden=True)
        for view in _index_views(root)
    ]
    if any(index != indexes[0] for index in indexes[1:]):
        raise ValueError("alternate index is not represented by the canonical bundle")
    dependencies = (
        "src/memory/proof.py",
        "src/memory/fs_confine.py",
        "configs/quality/proof_or_stop_policy.yaml",
        "configs/quality/proof_or_stop_bundle.schema.json",
    )
    before = {
        name: hook_receipts._file_digest(SOURCE_ROOT / name) for name in dependencies
    }
    result = {
        "snapshot": hook_receipts.snapshot(root, env=env),
        "branch_sha256": hook_receipts.digest(branch(root)),
        "dependencies_sha256": hook_receipts.digest(before),
    }
    if before != {
        name: hook_receipts._file_digest(SOURCE_ROOT / name) for name in dependencies
    }:
        raise ValueError("dependencies changed while measuring")
    return result
