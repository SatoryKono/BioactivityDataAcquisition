"""Application-level debug export collection for per-run audit packs."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from bioetl.domain.ports import DebugExportPort
from bioetl.domain.types import DebugExportPack, DebugExportResult, RunID

if TYPE_CHECKING:
    from .debug_export_collector import DebugExportCollector

from .debug_export_collector import DebugExportCollector
from .debug_export_helpers import _utc_now
from .debug_export_pack_assembly import build_debug_export_pack
from .debug_export_service_recording_mixin import DebugExportServiceRecordingMixin

__all__ = [
    "DebugExportConfig",
    "DebugExportPack",
    "DebugExportResult",
    "DebugExportService",
    "DebugExportWriterProtocol",
]


@dataclass(frozen=True, slots=True)
class DebugExportConfig:
    """Runtime configuration for debug audit-pack export."""

    enabled: bool = False
    formats: tuple[str, ...] = ("csv", "xlsx")
    output_dir: str = "artifacts/debug_exports"
    include_bom: bool = False
    max_rows_per_sheet: int = 1_048_576
    workflow_id: str = "standalone"


def create_debug_export_collector(
    *,
    run_id: str,
    pipeline_id: str,
    provider_id: str,
    workflow_id: str,
    manifest_id: str | None,
) -> DebugExportCollector:
    """Factory function to create DebugExportCollector."""
    return DebugExportCollector(
        run_id=run_id,
        pipeline_id=pipeline_id,
        provider_id=provider_id,
        workflow_id=workflow_id,
        manifest_id=manifest_id,
    )


class DebugExportCollectorBuilderProtocol(Protocol):
    """Factory contract for constructing the collector dependency."""

    def __call__(
        self,
        *,
        run_id: str,
        pipeline_id: str,
        provider_id: str,
        workflow_id: str,
        manifest_id: str | None,
    ) -> DebugExportCollector:
        """Build one collector for the current run context."""
        ...


DebugExportWriterProtocol = DebugExportPort


class DebugExportService(DebugExportServiceRecordingMixin):
    """Collect per-run audit rows before persistence through an adapter."""

    def __init__(
        self,
        *,
        config: DebugExportConfig,
        run_id: RunID | UUID,
        pipeline_id: str,
        provider_id: str,
        manifest_id: str | None = None,
        writer: DebugExportWriterProtocol | None = None,
        collector_factory: DebugExportCollectorBuilderProtocol = create_debug_export_collector,
        created_at_factory: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._config = config
        self._run_id = str(run_id)
        self._pipeline_id = pipeline_id
        self._provider_id = provider_id
        self._writer = writer
        self._created_at_factory = created_at_factory
        self._collector = collector_factory(
            run_id=self._run_id,
            pipeline_id=self._pipeline_id,
            provider_id=self._provider_id,
            workflow_id=config.workflow_id,
            manifest_id=manifest_id,
        )
        self._debug_root: str | None = None

    @property
    def enabled(self) -> bool:
        return bool(self._config.enabled)

    @property
    def workflow_id(self) -> str:
        return self._config.workflow_id

    @property
    def output_dir(self) -> str:
        return self._config.output_dir

    def attach_manifest_id(self, manifest_id: str | None) -> None:
        self._collector.attach_manifest_id(manifest_id)

    def set_debug_root(self, path: str | Path) -> None:
        self._debug_root = str(path)

    def build_pack(self, *, status: str = "complete") -> DebugExportPack:
        """Build the in-memory audit pack from collected rows."""
        return build_debug_export_pack(
            collector=self._collector,
            run_id=self._run_id,
            pipeline_id=self._pipeline_id,
            provider_id=self._provider_id,
            workflow_id=self.workflow_id,
            output_root=self._debug_root or self.output_dir,
            formats=self._config.formats,
            include_bom=self._config.include_bom,
            max_rows_per_sheet=self._config.max_rows_per_sheet,
            created_at_factory=self._created_at_factory,
            status=status,
        )

    async def persist(self, *, status: str = "complete") -> DebugExportResult:
        """Persist the collected audit pack through the adapter."""
        if not self.enabled or self._writer is None:
            raise RuntimeError(
                "Debug export is not enabled or writer is not configured"
            )
        result = self._writer.write_pack(pack=self.build_pack(status=status))
        if isinstance(result, DebugExportResult):
            return result
        return await result

    def finalize(
        self,
        *,
        status: str,
        manifest_id: str | None,
    ) -> DebugExportResult | Awaitable[DebugExportResult] | None:
        """Persist the collected pack once the run reaches its terminal state."""
        if not self.enabled or self._writer is None:
            return None
        self.attach_manifest_id(manifest_id)
        return self._writer.write_pack(pack=self.build_pack(status=status))
