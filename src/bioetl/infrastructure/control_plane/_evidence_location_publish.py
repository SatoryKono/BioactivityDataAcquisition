"""Exclusive create-if-absent publication for evidence-location records."""

from __future__ import annotations

import contextlib
import errno
import os
import tempfile
from pathlib import Path

from bioetl.infrastructure.control_plane._durability import (
    flush_control_plane_file_descriptor,
)

__all__ = [
    "publish_bytes_if_absent",
    "read_existing_bytes",
]


def read_existing_bytes(path: Path) -> bytes | None:
    """Return file bytes or ``None`` when the path is absent."""
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None
    except IsADirectoryError as exc:
        raise ValueError(f"evidence location path is a directory: {path}") from exc


def _publish_new_file_exclusive(source: Path, target: Path) -> None:
    """Hard-link ``source`` to ``target`` without overwriting an existing file."""
    try:
        os.link(os.fspath(source), os.fspath(target))
    except OSError as exc:
        if exc.errno == errno.EEXIST and not isinstance(exc, FileExistsError):
            raise FileExistsError(*exc.args) from exc
        raise
    with contextlib.suppress(OSError):
        source.unlink()


def publish_bytes_if_absent(target: Path, data: bytes) -> bool:
    """Atomically create ``target`` when missing.

    Returns:
        ``True`` when this caller created the file; ``False`` when it already
        existed (caller must compare bytes / decide conflict).

    Never overwrites an existing file, including under competing writers.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path_str = tempfile.mkstemp(
        suffix=".tmp",
        prefix="." + target.stem + "_",
        dir=target.parent,
    )
    temp_path = Path(temp_path_str)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            flush_control_plane_file_descriptor(handle.fileno())
        try:
            _publish_new_file_exclusive(temp_path, target)
        except FileExistsError:
            return False
        return True
    finally:
        with contextlib.suppress(OSError):
            if temp_path.exists():
                temp_path.unlink()
