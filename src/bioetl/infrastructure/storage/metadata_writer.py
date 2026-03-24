"""Atomic sidecar metadata writer for Bronze, Silver, and Gold layers."""

from __future__ import annotations

from bioetl.infrastructure.storage.metadata.writer_operations import METADATA_FILENAME

from .metadata_writer_impl import MetadataWriter

__all__ = ["METADATA_FILENAME", "MetadataWriter"]
