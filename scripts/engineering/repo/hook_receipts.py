"""State-bound local check receipts; never runtime admission or CI acceptance.

No environment values, source contents or child output are persisted. Local
hashes detect stale evidence, not a malicious user able to forge local files.
"""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import re
import subprocess
import stat
import sys
import time
from typing import Any
import uuid

LIMIT = 8 * 1024 * 1024
RECEIPT_LIMIT = 128 * 1024
KIND = "bioetl.local_check_receipt.v1"


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _git(root: Path, *args: str, index_file: str | None = None) -> bytes:
    from scripts.engineering.repo.check_no_partial_tree import _isolated_git_env

    env = _isolated_git_env(index_file=index_file)
    result = subprocess.run(
        ["git", "-c", "core.fsmonitor=false", *args],
        cwd=root,
        env=env,
        capture_output=True,
        check=True,
        timeout=10,
    )
    if len(result.stdout) > LIMIT:
        raise ValueError("state evidence exceeds limit")
    return result.stdout


def _file_digest(path: Path, *, limit: int = 16 * 1024 * 1024) -> str:
    before = path.stat()
    hashed = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while block := stream.read(64 * 1024):
            size += len(block)
            if size > limit:
                raise ValueError("measured input exceeds limit")
            hashed.update(block)
    after = path.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise ValueError("input changed while measuring")
    return hashed.hexdigest()


def _distribution_paths() -> list[str]:
    """Deduplicate proven physical aliases, retaining distinct installations."""
    paths = []
    seen: set[tuple[int, int] | str] = set()
    for entry in sys.path:
        path = Path(entry).resolve()
        try:
            info = path.stat()
            identity: tuple[int, int] | str = (
                (info.st_dev, info.st_ino) if info.st_ino else str(path)
            )
        except OSError:
            identity = str(path)
        if identity not in seen:
            seen.add(identity)
            paths.append(str(path))
    return paths


def environment_identity(env: Mapping[str, str] | None = None) -> str:
    """Require exact compatibility; persist a digest, never environment values."""
    # Enumerate equivalent editable-install search roots once, not set(name,
    # version): different metadata installations must remain distinguishable.
    packages = sorted(
        (item.metadata["Name"], item.version)
        for item in importlib.metadata.distributions(path=_distribution_paths())
    )
    return digest(
        {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": sys.version,
            "executable": str(Path(sys.executable).resolve()),
            "executable_sha256": _file_digest(
                Path(sys.executable).resolve(), limit=64 * 1024 * 1024
            ),
            "prefix": sys.prefix,
            "packages": packages,
            "environment_digest": digest(dict(os.environ if env is None else env)),
        }
    )


def _index_material(
    root: Path, view: str | None, *, reject_hidden: bool
) -> dict[str, bytes]:
    from scripts.engineering.repo.check_no_partial_tree import _reject_intent_to_add

    index = _git(root, "ls-files", "--sparse", "--stage", "-z", index_file=view)
    if any(
        row
        and (
            row.startswith((b"040000 ", b"160000 "))
            or row.split(b"\t", 1)[0].rsplit(b" ", 1)[-1] != b"0"
        )
        for row in index.split(b"\0")
    ):
        raise ValueError("gitlink, unmerged or sparse index is not qualified")
    _reject_intent_to_add(root, index_file=view)
    marked = _git(root, "ls-files", "-v", "-z", index_file=view)
    if reject_hidden and any(
        row and (row[:1].islower() or row.startswith(b"S "))
        for row in marked.split(b"\0")
    ):
        raise ValueError("hidden index entries are not qualified")
    return {"index": index, "flags": marked}


def _reject_gitlink_revisions(root: Path, *revisions: str) -> None:
    """A parent commit id does not attest files inside an unqualified submodule."""
    for revision in dict.fromkeys(revisions):
        rows = _git(root, "ls-tree", "-r", "-z", revision).split(b"\0")
        if any(row.startswith(b"160000 ") for row in rows):
            raise ValueError("gitlink revision is not qualified")


def _dotenv_material(root: Path) -> dict[str, str]:
    values = {}
    for path in sorted(root.glob(".env*")):
        if not path.is_file() or path.is_symlink():
            raise ValueError("unqualified dotenv input")
        values[path.name] = _file_digest(path)
    return values


def protected_state(root: Path, base: str = "origin/main") -> dict[str, str]:
    """Cheap semantic index/HEAD/base/env bookend for callbacks; no cache reuse."""
    from scripts.engineering.repo.check_no_partial_tree import (
        _index_views,
        _shallow_boundaries,
        check_checkout_state,
        validate_revision_token,
    )

    base = validate_revision_token(base)
    _reject_gitlink_revisions(root, "HEAD", base)
    indexes = [
        _index_material(root, view, reject_hidden=False) for view in _index_views(root)
    ]
    if check_checkout_state(root):
        raise ValueError("checkout state is not qualified")
    return {
        "head_sha": _git(root, "rev-parse", "--verify", "HEAD^{commit}")
        .strip()
        .decode("ascii"),
        "base_sha": _git(root, "rev-parse", "--verify", base + "^{commit}")
        .strip()
        .decode("ascii"),
        "history_sha256": digest(sorted(_shallow_boundaries(root))),
        "index_sha256": digest(
            [
                {key: hashlib.sha256(value).hexdigest() for key, value in item.items()}
                for item in indexes
            ]
        ),
        "dotenv_sha256": digest(_dotenv_material(root)),
    }


def _path_state(
    root: Path, views: list[str | None], base: str
) -> tuple[dict[str, str], dict[str, str]]:
    names: set[str] = set()
    for view in views:
        for args in [
            (
                "diff",
                base,
                "HEAD",
                "--no-ext-diff",
                "--no-textconv",
                "--no-renames",
                "--name-only",
                "-z",
            ),
            (
                "diff-files",
                "--no-ext-diff",
                "--no-textconv",
                "--no-renames",
                "--name-only",
                "-z",
            ),
            (
                "diff",
                "--cached",
                "HEAD",
                "--no-ext-diff",
                "--no-textconv",
                "--no-renames",
                "--name-only",
                "-z",
            ),
            ("ls-files", "--others", "--exclude-standard", "-z"),
        ]:
            names.update(
                part.decode("utf-8")
                for part in _git(root, *args, index_file=view).split(b"\0")
                if part
            )
    from scripts.engineering.repo.budget_guard import worktree_policy_paths

    names.update(worktree_policy_paths(root, base))
    measured = {}
    for relative in sorted(names):
        target = root / relative
        if not target.resolve().is_relative_to(root) or target.is_symlink():
            raise ValueError("unqualified changed input path")
        if target.is_dir():
            raise ValueError("unqualified directory source input")
        measured[relative] = (
            digest(
                {
                    "content_sha256": _file_digest(target),
                    "mode": stat.S_IMODE(target.stat().st_mode),
                }
            )
            if target.is_file()
            else "MISSING"
        )
    checkers = {
        path.name: _file_digest(path)
        for path in sorted(Path(__file__).parent.glob("*.py"))
    }
    return measured, checkers


def snapshot(
    root: Path, *, env: Mapping[str, str] | None = None, base: str = "origin/main"
) -> dict[str, Any]:
    """Measure both indexes and source bytes with stable material/ref bookends."""
    from scripts.engineering.repo.check_no_partial_tree import _index_views

    root = root.resolve()
    before = protected_state(root, base)
    views = _index_views(root)
    for view in views:
        _index_material(root, view, reject_hidden=True)
    measured, checkers = _path_state(root, views, before["base_sha"])
    environment = environment_identity(env)
    if before != protected_state(root, base) or (measured, checkers) != _path_state(
        root, views, before["base_sha"]
    ):
        raise ValueError("state changed while measuring")
    identity = {
        **before,
        "source_sha256": digest(measured),
        "checker_sha256": digest(checkers),
        "worktree": str(root),
        "git_dir": _git(root, "rev-parse", "--path-format=absolute", "--git-dir")
        .strip()
        .decode("utf-8"),
        "environment_sha256": environment,
    }
    identity["identity_sha256"] = digest(identity)
    return identity


def receipt_directory(root: Path) -> Path:
    common = Path(
        _git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
        .strip()
        .decode()
    ).resolve()
    directory = common / "bioetl-check-receipts"
    if directory.is_symlink() or directory.resolve().parent != common:
        raise ValueError("receipt directory escaped metadata")
    return directory


def write_receipt(
    root: Path, state: dict[str, Any], checks: list[dict[str, Any]]
) -> Path:
    """One immutable file per invocation; parallel agents never overwrite it."""
    directory = receipt_directory(root)
    directory.mkdir(exist_ok=True)
    payload = {
        "kind": KIND,
        "runtime_admission": False,
        "ci_acceptance": False,
        "state": state,
        "checks": checks,
        "created_at_unix": time.time(),
    }
    payload["payload_sha256"] = digest(payload)
    encoded = json.dumps(payload, sort_keys=True).encode()
    if len(encoded) > RECEIPT_LIMIT:
        raise ValueError("receipt exceeds limit")
    target = directory / (uuid.uuid4().hex + ".json")
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    return target


def _read_owned_bytes(owned: Path, directory: Path) -> bytes:
    before = owned.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError("receipt must be a regular file")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(owned, flags)
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        after = owned.lstat()
        expected = (before.st_dev, before.st_ino)
        if (
            (opened.st_dev, opened.st_ino) != expected
            or (after.st_dev, after.st_ino) != expected
            or not stat.S_ISREG(after.st_mode)
            or directory.resolve() != directory
        ):
            raise ValueError("receipt changed while opening")
        return stream.read(RECEIPT_LIMIT + 1)


def _read_receipt(root: Path, target: Path) -> dict[str, Any]:
    directory = receipt_directory(root)
    if (
        target.is_symlink()
        or target.resolve().parent != directory
        or not re.fullmatch(r"[a-f0-9]{32}\.json", target.name)
    ):
        raise ValueError("unowned receipt path")
    # Rebuild a canonical UUID slot under trusted metadata, never open the CLI path.
    owned = directory / (uuid.UUID(hex=target.stem).hex + ".json")
    encoded = _read_owned_bytes(owned, directory)
    if len(encoded) > RECEIPT_LIMIT:
        raise ValueError("receipt exceeds limit")
    payload = json.loads(encoded)
    if not isinstance(payload, dict):
        raise ValueError("unknown receipt shape")
    signature = payload.pop("payload_sha256")
    if signature != digest(payload) or payload["kind"] != KIND:
        raise ValueError("receipt corrupt or unknown")
    if (
        payload["runtime_admission"] is not False
        or payload["ci_acceptance"] is not False
    ):
        raise ValueError("local evidence cannot grant admission")
    return payload


def _check_verdict(payload: dict[str, Any], expected: list[str], reuse: bool) -> str:
    checks = payload["checks"]
    if not isinstance(checks, list) or [row["id"] for row in checks] != expected:
        raise ValueError("required check set mismatch")
    if not checks or any(
        row["status"] != "PASS"
        or type(row["returncode"]) is not int
        or row["returncode"] != 0
        for row in checks
    ):
        return "required_checks_not_passed"
    created = payload["created_at_unix"]
    if (
        isinstance(created, bool)
        or not isinstance(created, (int, float))
        or not math.isfinite(created)
        or created > time.time()
    ):
        raise ValueError("invalid observation time")
    if reuse and (
        time.time() - created > 60
        or any(row.get("cacheable") is not True for row in checks)
    ):
        return "check_requires_fresh_execution"
    return "same_local_state_only"


def validate_receipt(
    root: Path,
    target: Path,
    current: dict[str, Any],
    expected_checks: list[str],
    *,
    for_reuse: bool = False,
) -> dict[str, str]:
    """SKIP, ERROR, FAIL, stale state and malformed evidence never become PASS."""
    try:
        payload = _read_receipt(root, target)
        if payload["state"] != current:
            return {
                "status": "ERROR",
                "reason": "state_or_checker_or_environment_changed",
            }
        reason = _check_verdict(payload, expected_checks, for_reuse)
        return {
            "status": "PASS" if reason == "same_local_state_only" else "ERROR",
            "reason": reason,
        }
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        RecursionError,
        OverflowError,
        subprocess.SubprocessError,
    ):
        return {"status": "ERROR", "reason": "receipt_unavailable_or_invalid"}
