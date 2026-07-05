"""Coordinator for metadata request building, finalization, and atomic writes."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.infrastructure.storage.metadata.writer_operations import (
    _MetadataWriteRequest,
    _prepare_metadata_write_operation,
)

from .metadata_writer_helpers import (
    _execute_prepared_metadata_write_operation,
    _load_existing_metadata_model,
    _record_artifact_publication,
    _resolve_existing_metadata_path,
)

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import (
        BronzeMetadata,
        GoldMetadata,
        SilverMetadata,
    )
    from bioetl.domain.ports import LoggerPort, MetricsPort

__all__ = ["_MetadataWriterOperations"]


class _MetadataWriterOperations:
    """Coordinator for metadata request building, finalization, and atomic writes."""

    def __init__(
        self,
        *,
        logger: LoggerPort,
        metrics: MetricsPort | None,
        retry_policy: object,
        artifact_recorder_provider: Callable[
            [],
            object | None,
        ],
    ) -> None:
        self._logger = logger
        self._metrics = metrics
        self._retry_policy = retry_policy
        self._artifact_recorder_provider = artifact_recorder_provider

    def build_metadata_write_request(
        self,
        *,
        base_path: str | Path,
        metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
        layer: str,
        table_name: str | None = None,
        flat_structure: bool = False,
        provider: str | None = None,
        entity: str | None = None,
    ) -> _MetadataWriteRequest:
        """Build a normalized metadata sidecar request for the canonical write path."""
        return _MetadataWriteRequest(
            base_path=base_path,
            metadata=metadata,
            layer=layer,
            table_name=table_name,
            flat_structure=flat_structure,
            provider=provider,
            entity=entity,
        )

    async def finalize_existing_layer_metadata(
        self,
        *,
        base_path: str | Path,
        layer: str,
        apply_finalization: Callable[[SilverMetadata | GoldMetadata], None],
        table_name: str | None = None,
        flat_structure: bool = False,
        provider: str | None = None,
        entity: str | None = None,
    ) -> str | None:
        """Load, patch, and atomically rewrite an existing Silver/Gold sidecar."""
        metadata_path = _resolve_existing_metadata_path(
            base_path=base_path,
            layer=layer,
            table_name=table_name,
            flat_structure=flat_structure,
            provider=provider,
            entity=entity,
        )
        existing_metadata = _load_existing_metadata_model(
            metadata_path,
            layer=layer,
        )
        if existing_metadata is None:
            return None

        apply_finalization(existing_metadata)
        return await self.write_metadata(
            self.build_metadata_write_request(
                base_path=base_path,
                metadata=existing_metadata,
                layer=layer,
                table_name=table_name,
                flat_structure=flat_structure,
                provider=provider,
                entity=entity,
            )
        )

    async def write_layer_metadata(
        self,
        *,
        base_path: str | Path,
        metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
        layer: str,
        table_name: str | None = None,
        flat_structure: bool = False,
        provider: str | None = None,
        entity: str | None = None,
    ) -> str:
        """Build and execute one normalized metadata write request."""
        metadata_path = await self.write_metadata(
            self.build_metadata_write_request(
                base_path=base_path,
                metadata=metadata,
                layer=layer,
                table_name=table_name,
                flat_structure=flat_structure,
                provider=provider,
                entity=entity,
            )
        )
        _record_artifact_publication(
            recorder=self._artifact_recorder_provider(),
            metrics=self._metrics,
            layer=layer,
            base_path=base_path,
            metadata_path=metadata_path,
            metadata=metadata,
        )
        return metadata_path

    async def write_metadata(self, request: _MetadataWriteRequest) -> str:
        """Write sidecar metadata for Bronze/Silver/Gold layers and return file path."""
        operation = _prepare_metadata_write_operation(request)
        return await _execute_prepared_metadata_write_operation(
            logger=self._logger,
            metrics=self._metrics,
            retry_policy=self._retry_policy,
            operation=operation,
            metadata=request.metadata,
        )
