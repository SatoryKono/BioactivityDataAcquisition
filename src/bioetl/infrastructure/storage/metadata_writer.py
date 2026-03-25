"""Facade for metadata sidecar writing.

This module preserves historical patch-points used by unit tests and older
callers while delegating the real implementation to split helper/impl modules.
"""

from __future__ import annotations

from bioetl.infrastructure.storage.metadata.writer_operations import (
    METADATA_FILENAME,
    _MetadataWriteRequest,
    _prepare_metadata_write_operation,
)

from . import metadata_writer_helpers as _helpers
from .metadata_writer_impl import MetadataWriter as _BaseMetadataWriter

_get_metadata_filename = _helpers._get_metadata_filename
atomic_write_text = _helpers.atomic_write_text


async def _execute_prepared_metadata_write_operation(
    **kwargs: object,
) -> str:
    """Delegate through the facade-local patch seam for atomic writes."""
    original_atomic_write_text = _helpers.atomic_write_text
    _helpers.atomic_write_text = atomic_write_text
    try:
        return await _helpers._execute_prepared_metadata_write_operation(**kwargs)
    finally:
        _helpers.atomic_write_text = original_atomic_write_text


class MetadataWriter(_BaseMetadataWriter):
    """Facade subclass that preserves legacy monkeypatch seams."""

    async def _write_metadata(self, request: _MetadataWriteRequest) -> str:
        operation = _prepare_metadata_write_operation(request)
        return await _execute_prepared_metadata_write_operation(
            logger=self._logger,
            metrics=self._metrics,
            retry_policy=self._atomic_replace_retry_policy,
            operation=operation,
            metadata=request.metadata,
        )


__all__ = [
    "METADATA_FILENAME",
    "MetadataWriter",
    "_execute_prepared_metadata_write_operation",
    "_get_metadata_filename",
    "atomic_write_text",
]
