"""Canonical serialization and atomic writes."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path

from .constants import SHA256_PATTERN


def sha256_file(path: Path) -> str:
    """Return the lowercase SHA-256 hex digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
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
    temporary = destination.with_name(f".{destination.name}.tmp")
    try:
        temporary.write_bytes(payload)
        temporary.replace(destination)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise


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
