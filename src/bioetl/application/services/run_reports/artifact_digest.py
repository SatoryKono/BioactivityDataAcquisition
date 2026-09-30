"""Canonical artifact digest helpers for run-report JSON and layer files."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

_DIGEST_KEYS = ("sha256", "digest", "content_hash")
_HASH_READ_CHUNK_SIZE = 256 * 1024

__all__ = [
    "canonical_report_sha256",
    "file_sha256",
]


def canonical_report_sha256(payload: Mapping[str, object]) -> str:
    """Hash JSON with artifact digest fields blanked so the digest can live in-file."""
    encoded = json.dumps(
        _blank_artifact_digests(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    """Return the sha256 hex digest of one existing file."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(_HASH_READ_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _blank_artifact_digests(payload: Mapping[str, object]) -> object:
    cloned: object = json.loads(
        json.dumps(payload, ensure_ascii=False, allow_nan=False)
    )
    if not isinstance(cloned, dict):
        return cloned
    cloned.pop("selected_run_snapshot", None)
    artifacts = cloned.get("artifacts")
    if isinstance(artifacts, list):
        for item in artifacts:
            if isinstance(item, dict):
                for key in _DIGEST_KEYS:
                    item.pop(key, None)
    return cloned
