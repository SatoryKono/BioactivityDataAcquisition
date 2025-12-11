"""File operation settings: buffer sizes, retry configuration, temp paths.

This module consolidates all file-related constants that were previously
defined in infrastructure/constants.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class FileSettings:
    """File operation configuration.

    Contains settings for atomic file operations, checksum calculations,
    and retry behavior for file system operations.
    """

    max_retries: int = 3
    """Maximum number of retry attempts for file operations (e.g., atomic replace)."""

    retry_delay_sec: float = 0.5
    """Base delay between file operation retries in seconds."""

    checksum_chunk_size: int = 8192
    """Buffer size in bytes for reading files during checksum calculation."""

    temp_suffix: str = ".tmp"
    """Suffix for temporary files during atomic write operations."""


# Default instance for convenient access
DEFAULT_FILE_SETTINGS: Final[FileSettings] = FileSettings()


__all__ = [
    "FileSettings",
    "DEFAULT_FILE_SETTINGS",
]
