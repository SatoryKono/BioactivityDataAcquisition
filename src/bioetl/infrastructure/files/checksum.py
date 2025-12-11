"""Checksum helpers for deterministic file hashing."""

import hashlib
from pathlib import Path

from bioetl.infrastructure.settings.files import DEFAULT_FILE_SETTINGS


def compute_file_sha256(path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(
            lambda: f.read(DEFAULT_FILE_SETTINGS.checksum_chunk_size), b""
        ):
            sha256.update(chunk)
    return sha256.hexdigest()


def compute_files_sha256(paths: list[Path]) -> dict[str, str]:
    """Compute SHA256 hashes for multiple files.

    Missing files are skipped.
    """
    checksums: dict[str, str] = {}
    for path in paths:
        if not path.exists():
            continue
        checksums[path.name] = compute_file_sha256(path)
    return checksums
