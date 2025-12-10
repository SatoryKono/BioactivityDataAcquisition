"""Checksum calculator component implementation."""

from __future__ import annotations

import hashlib
from pathlib import Path

from bioetl.domain.ports.output import ChecksumCalculatorPort
from bioetl.infrastructure.constants import CHECKSUM_CHUNK_SIZE


class ChecksumCalculator(ChecksumCalculatorPort):
    """SHA256 checksum calculator for file integrity verification.

    This component handles all checksum-related operations
    without knowledge of file formats or pipeline context.
    """

    def __init__(self, *, chunk_size: int | None = None) -> None:
        """Initialize calculator.

        Args:
            chunk_size: Size of chunks for reading large files.
                        Defaults to CHECKSUM_CHUNK_SIZE constant.
        """
        self._chunk_size = chunk_size or CHECKSUM_CHUNK_SIZE

    def compute_checksum(self, path: Path) -> str:
        """Compute SHA256 checksum for a single file.

        Args:
            path: Path to the file.

        Returns:
            Hex-encoded SHA256 hash string.

        Raises:
            FileNotFoundError: If file does not exist.
        """
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(self._chunk_size), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def compute_checksums(self, paths: list[Path]) -> dict[str, str]:
        """Compute SHA256 checksums for multiple files.

        Missing files are silently skipped.

        Args:
            paths: List of file paths.

        Returns:
            Dict mapping filename (not full path) to checksum.
        """
        checksums: dict[str, str] = {}
        for path in paths:
            if not path.exists():
                continue
            checksums[path.name] = self.compute_checksum(path)
        return checksums


__all__ = ["ChecksumCalculator"]
