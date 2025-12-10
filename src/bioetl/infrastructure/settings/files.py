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

# Legacy compatibility constants (deprecated, use FileSettings instance instead)
MAX_FILE_RETRIES: Final[int] = DEFAULT_FILE_SETTINGS.max_retries
RETRY_DELAY_SEC: Final[float] = DEFAULT_FILE_SETTINGS.retry_delay_sec
CHECKSUM_CHUNK_SIZE: Final[int] = DEFAULT_FILE_SETTINGS.checksum_chunk_size


__all__ = [
    "FileSettings",
    "DEFAULT_FILE_SETTINGS",
    # Legacy compatibility
    "MAX_FILE_RETRIES",
    "RETRY_DELAY_SEC",
    "CHECKSUM_CHUNK_SIZE",
]
