"""Atomic sidecar metadata writer for Bronze, Silver, and Gold layers.

This module re-exports from split modules for backward compatibility.
"""

from __future__ import annotations

# Re-export from split modules
from bioetl.infrastructure.storage.metadata.writer_operations import (
    METADATA_FILENAME,
)
from bioetl.infrastructure.storage.metadata_writer_public import MetadataWriter

__all__ = ["METADATA_FILENAME", "MetadataWriter"]
