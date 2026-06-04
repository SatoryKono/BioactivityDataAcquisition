"""Facade for metadata sidecar writing.

This module preserves historical patch-points used by unit tests and older
callers while delegating the real implementation to split helper/impl modules.
"""

from __future__ import annotations

from typing import Any, cast

from bioetl.infrastructure.storage.metadata.writer_operations import (
    METADATA_FILENAME,
    _MetadataWriteRequest,
    _prepare_metadata_write_operation,
    _PreparedMetadataWriteOperation,
)
from bioetl.infrastructure.storage.metadata_writer_operations_impl import (
    _MetadataWriterOperations as _BaseMetadataWriterOperations,
)

from . import metadata_writer_helpers as _helpers
from .metadata_writer_impl import (
    MetadataWriter as _BaseMetadataWriter,
)

_get_metadata_filename = _helpers._get_metadata_filename
atomic_write_text = _helpers.atomic_write_text


async def _execute_prepared_metadata_write_operation(
    *,
    logger: object,
    metrics: object | None,
    retry_policy: object,
    operation: _PreparedMetadataWriteOperation,
    metadata: object,
) -> str:
    """Delegate through the facade-local patch seam for atomic writes."""
    original_atomic_write_text = _helpers.atomic_write_text
    _helpers.atomic_write_text = atomic_write_text
    try:
        return await _helpers._execute_prepared_metadata_write_operation(
            logger=cast("Any", logger),  # Any: facade preserves legacy patch seam.
            metrics=cast("Any", metrics),  # Any: optional metrics backend is dynamic.
            retry_policy=cast(
                "Any",  # Any: helper owns the concrete retry-policy implementation.
                retry_policy,
            ),  # Any: retry-policy concrete type stays in helper implementation.
            operation=operation,
            metadata=cast(
                "Any",  # Any: facade spans Bronze/Silver/Gold metadata models.
                metadata,
            ),  # Any: facade accepts multiple metadata model variants.
        )
    finally:
        _helpers.atomic_write_text = original_atomic_write_text


class _FacadeMetadataWriterOperations(_BaseMetadataWriterOperations):
    """Operations shim that preserves the historical facade patch seam."""

    async def write_metadata(self, request: _MetadataWriteRequest) -> str:
        operation = _prepare_metadata_write_operation(request)
        return await _execute_prepared_metadata_write_operation(
            logger=self._logger,
            metrics=self._metrics,
            retry_policy=self._retry_policy,
            operation=operation,
            metadata=request.metadata,
        )


class MetadataWriter(_BaseMetadataWriter):
    """Facade subclass that preserves legacy monkeypatch seams."""

    def __init__(
        self,
        logger: object,
        *,
        atomic_replace_retry_policy: object | None = None,
        metrics: object | None = None,
    ) -> None:
        super().__init__(
            logger=cast("Any", logger),  # Any: facade preserves legacy patch seam
            atomic_replace_retry_policy=cast(
                "Any",  # Any: helper owns concrete retry-policy implementation
                atomic_replace_retry_policy,
            ),  # Any: helper owns concrete retry-policy implementation
            metrics=cast("Any", metrics),  # Any: optional metrics backend is dynamic
        )
        self._operations = _FacadeMetadataWriterOperations(
            logger=cast("Any", self._logger),  # Any: facade preserves legacy patch seam
            metrics=cast(
                "Any",  # Any: optional metrics backend is dynamic
                self._metrics,
            ),  # Any: optional metrics backend is dynamic
            retry_policy=cast(
                "Any",  # Any: helper owns concrete retry-policy implementation
                self._atomic_replace_retry_policy,
            ),  # Any: helper owns concrete retry-policy implementation
            artifact_recorder_provider=lambda: self._artifact_recorder,
        )

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
