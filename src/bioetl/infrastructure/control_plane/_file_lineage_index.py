"""Private index helpers for file-backed lineage fragment persistence."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from bioetl.domain.lineage import LineageGraphFragment


class LineageIndexCorruptionError(ValueError):
    """Raised when a lineage index JSONL file is truncated or malformed."""


def stable_key_filename(key: str) -> str:
    """Return a filesystem-safe filename stem for one semantic key."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def build_stored_fragment_id(fragment: LineageGraphFragment) -> str:
    """Return one occurrence-scoped stored fragment identity."""
    anchors = [fragment.fragment_id]
    if fragment.run_id is not None:
        anchors.append(fragment.run_id)
    if fragment.manifest_id is not None:
        anchors.append(fragment.manifest_id)
    if len(anchors) == 1:
        return fragment.fragment_id
    digest = hashlib.sha256("|".join(anchors).encode("utf-8")).hexdigest()[:12]
    return f"{fragment.fragment_id}:occurrence:{digest}"


def load_fragment_ids(index_path: Path, *, key: str) -> list[str]:
    """Load fragment identifiers from one JSONL index file."""
    if not index_path.exists():
        return []
    raw_text = index_path.read_text(encoding="utf-8")
    if not raw_text.strip():
        return []
    if not raw_text.endswith(("\n", "\r")):
        raise LineageIndexCorruptionError(
            f"Lineage index '{index_path}' is corrupted: truncated tail line"
        )
    fragment_ids: dict[str, None] = {}
    for line_number, line in enumerate(raw_text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as error:
            raise LineageIndexCorruptionError(
                f"Lineage index '{index_path}' is corrupted at line "
                f"{line_number}: {error.msg}"
            ) from error
        if not isinstance(payload, dict):
            raise LineageIndexCorruptionError(
                f"Lineage index '{index_path}' is corrupted at line "
                f"{line_number}: payload must be a JSON object"
            )
        if str(payload.get("key")) != key:
            raise LineageIndexCorruptionError(
                f"Lineage index '{index_path}' is corrupted at line "
                f"{line_number}: unexpected key"
            )
        fragment_id = payload.get("fragment_id")
        if fragment_id is None or not str(fragment_id).strip():
            raise LineageIndexCorruptionError(
                f"Lineage index '{index_path}' is corrupted at line "
                f"{line_number}: missing fragment_id"
            )
        fragment_ids[str(fragment_id)] = None
    return list(fragment_ids)


def truncate_index_to_offset(
    path: Path,
    *,
    offset: int,
    os_module: Any = os,  # Any: Dependency injection for testability (default: real os module)
    flush_file_descriptor: Callable[[int], None],
) -> None:
    """Best-effort rollback of one lineage index file to a known-good offset."""
    if not path.exists():
        return
    file_descriptor = os_module.open(path, os_module.O_RDWR)
    try:
        os_module.ftruncate(file_descriptor, offset)
        flush_file_descriptor(file_descriptor)
    finally:
        os_module.close(file_descriptor)


def append_jsonl_payload(
    path: Path,
    payload: bytes,
    *,
    open_flags: int,
    os_module: Any = os,  # Any: Dependency injection for testability (default: real os module)
    flush_file_descriptor: Callable[[int], None],
) -> int:
    """Append one full JSONL payload with rollback on partial writes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor = os_module.open(path, open_flags, 0o666)
    bytes_written = 0
    checkpoint_size = 0
    try:
        checkpoint_size = os_module.fstat(file_descriptor).st_size
        while bytes_written < len(payload):
            written = os_module.write(file_descriptor, payload[bytes_written:])
            if written <= 0:
                raise OSError("Lineage index append produced an empty write")
            bytes_written += written
        flush_file_descriptor(file_descriptor)
        return checkpoint_size
    except OSError:
        if bytes_written > 0:
            try:
                os_module.ftruncate(file_descriptor, checkpoint_size)
                flush_file_descriptor(file_descriptor)
            except OSError:
                pass
        raise
    finally:
        os_module.close(file_descriptor)
