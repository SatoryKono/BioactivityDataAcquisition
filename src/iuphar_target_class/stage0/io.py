"""Canonical serialization and atomic writes."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import tempfile
from pathlib import Path

from .constants import SHA256_PATTERN


def _open_confined_hash_input(path: Path, root: Path, flags: int) -> int:
    """Pin the root and validate the final descriptor before any byte is read."""
    if os.open not in os.supports_dir_fd or not hasattr(os, "O_DIRECTORY"):
        raise OSError("confined hashing requires directory descriptor support")
    resolved_root = root.resolve()
    absolute_path = path.absolute()
    if ".." in absolute_path.parts or not absolute_path.is_relative_to(resolved_root):
        raise ValueError(f"path outside allowed root: {path}")
    relative_path = absolute_path.relative_to(resolved_root)
    root_identity = resolved_root.stat()
    flags |= getattr(os, "O_NOFOLLOW", 0)
    root_fd = os.open(
        resolved_root, os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        pinned_identity = os.fstat(root_fd)
        if (pinned_identity.st_dev, pinned_identity.st_ino) != (
            root_identity.st_dev,
            root_identity.st_ino,
        ):
            raise ValueError("allowed root changed before opening")
        fd = os.open(relative_path, flags, dir_fd=root_fd)
        try:
            opened = Path(f"/proc/self/fd/{fd}").readlink()
            opened_root = Path(f"/proc/self/fd/{root_fd}").readlink()
            if not opened.is_absolute() or not opened.is_relative_to(opened_root):
                raise ValueError(f"opened file outside allowed root: {path}")
        except OSError as error:
            os.close(fd)
            raise OSError(
                "confined hashing requires a final file descriptor path"
            ) from error
        except ValueError:
            os.close(fd)
            raise
        return fd
    finally:
        os.close(root_fd)


def _checked_hash_input(path: Path) -> Path:
    """Accept an explicitly selected file, rejecting traversal and sibling links.

    Acceptance and migration callers may select files outside CWD. Their selected
    parent is the default boundary; stage zero supplies its repository root.
    """
    absolute_path = path.absolute()
    if ".." in absolute_path.parts:
        raise ValueError(f"path traversal is not allowed: {path}")
    allowed_root = absolute_path.parent.resolve()
    resolved = absolute_path.resolve()
    if not resolved.is_relative_to(allowed_root):
        raise ValueError(f"path outside selected parent: {path}")
    return resolved


def sha256_file(path: Path, *, root: Path | None = None) -> str:
    """Hash a selected file, using descriptor confinement for an explicit root.

    Confined hashing requires Linux procfs. Other platforms fail closed rather
    than validating a pathname and reopening it. Without root, callers retain
    their explicit external-file selection; traversal and sibling links fail.
    """
    digest = hashlib.sha256()
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    fd = (
        _open_confined_hash_input(path, root, flags)
        if root is not None
        else os.open(_checked_hash_input(path), flags)
    )
    with os.fdopen(fd, "rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    """Return the lowercase SHA-256 hex digest of bytes."""
    return hashlib.sha256(payload).hexdigest()


def canonical_json_bytes(payload: object) -> bytes:
    """Serialize JSON with sorted keys, UTF-8, and a single trailing newline."""
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    return (text + "\n").encode("utf-8")


def atomic_write_bytes(path: Path, payload: bytes, *, root: Path) -> None:
    """Write ``payload`` via a sibling temp file, then ``Path.replace``.

    ``path`` must resolve inside ``root``. The check rejects traversal before
    any byte is written.
    """
    root_resolved = root.resolve()
    destination = path.resolve()
    if not destination.is_relative_to(root_resolved):
        message = "path escapes root"
        raise ValueError(message)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        # Exclusive creation preserves any existing sibling and prevents a
        # predictable temporary symlink from redirecting the write.
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
        temporary.replace(destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def canonical_csv_bytes(columns: tuple[str, ...], rows: list[dict[str, str]]) -> bytes:
    """Serialize a table with a fixed header, ``\\n`` endings, and no index."""
    buffer = io.StringIO(newline="\n")
    writer = csv.DictWriter(
        buffer,
        fieldnames=list(columns),
        lineterminator="\n",
        extrasaction="raise",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({column: row[column] for column in columns})
    return buffer.getvalue().encode("utf-8")


def blank(value: str | None) -> str:
    """CSV representation of a missing string."""
    return "" if value is None else value


def blank_int(value: int | None) -> str:
    """CSV representation of a missing integer."""
    return "" if value is None else str(value)


def csv_bool(value: bool) -> str:
    """Stable boolean tokens."""
    return "true" if value else "false"


def optional_sha256(value: object) -> str | None:
    """Accept only a real SHA-256 hex digest."""
    if value is None:
        return None
    if not isinstance(value, str):
        message = "sha256 must be a string or null"
        raise TypeError(message)
    if not value:
        return None
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        message = f"sha256 does not match {SHA256_PATTERN}: {value}"
        raise ValueError(message)
    return value
