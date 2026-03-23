"""Final metadata write orchestration extracted from PostrunService."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

from bioetl.application.core.postrun._metadata_writes import (
    build_final_metadata_write_coroutines,
    get_run_statistics,
)

if TYPE_CHECKING:
    from bioetl.application.core.postrun.metadata_version_resolver import (
        PostrunMetadataVersionResolver,
    )
    from bioetl.application.services.dq_report_service import DQReportResult
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import (
        ExecutorMetricsPort,
        MetadataCoordinatorPort,
        MetadataWriterPort,
        StorageMaintenancePort,
    )


class PostrunMetadataWriteService:
    """Handles final metadata writes for Silver and Gold outputs."""

    def __init__(
        self,
        *,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        context: PipelineContext,
        storage: StorageMaintenancePort,
        metadata_coordinator: MetadataCoordinatorPort | None,
        metadata_writer: MetadataWriterPort | None,
        metadata_version_resolver: PostrunMetadataVersionResolver,
    ) -> None:
        self._config = config
        self._runtime = runtime
        self._context = context
        self._storage = storage
        self._metadata_coordinator = metadata_coordinator
        self._metadata_writer = metadata_writer
        self._metadata_version_resolver = metadata_version_resolver

    async def write_final_metadata_if_available(
        self,
        executor: ExecutorMetricsPort,
        dq_reports: DQReportResult | None,
    ) -> None:
        """Write final metadata when the required collaborators are configured."""
        if not self._has_metadata_targets():
            return
        write_coroutines = self._build_write_coroutines(
            executor=executor,
            dq_reports=dq_reports,
        )
        if write_coroutines:
            await asyncio.gather(*write_coroutines)

    def _has_metadata_targets(self) -> bool:
        """Return whether the metadata pipeline has the required writers configured."""
        return (
            self._metadata_coordinator is not None and self._metadata_writer is not None
        )

    def _build_write_coroutines(
        self,
        *,
        executor: ExecutorMetricsPort,
        dq_reports: DQReportResult | None,
    ) -> list[Awaitable[object]]:
        """Build final metadata write coroutines for the current postrun flow."""
        return build_final_metadata_write_coroutines(
            metadata_coordinator=self._metadata_coordinator,
            metadata_writer=self._metadata_writer,
            storage=self._storage,
            config=self._config,
            runtime=self._runtime,
            context=self._context,
            stats=get_run_statistics(executor),
            dq_reports=dq_reports,
            completed_at=datetime.now(UTC),
            resolve_delta_version=self._resolve_delta_version,
        )

    def _resolve_delta_version(
        self,
        table_path: str,
        layer: Literal["silver", "gold"],
    ) -> int | None:
        """Resolve the latest Delta version through the injected resolver."""
        return self._metadata_version_resolver.resolve_delta_version(
            table_path,
            layer=layer,
        )


__all__ = ["PostrunMetadataWriteService"]
