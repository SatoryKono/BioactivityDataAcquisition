"""Application-level debug export collection for per-run audit packs."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol
from uuid import UUID

from bioetl.domain.types import BatchID, BronzeRecord, ErrorType, GoldRecord, RunID

from .debug_export_collector import DebugExportCollector
from .debug_export_helpers import _utc_now
from .debug_reason_dictionary import DEBUG_REASON_DICTIONARY

__all__ = [
    "DebugExportConfig",
    "DebugExportPack",
    "DebugExportResult",
    "DebugExportService",
    "DebugExportWriterPort",
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


@dataclass(frozen=True, slots=True)
class DebugExportPack:
    """Deterministic in-memory representation of one debug export run pack."""

    run_id: str
    pipeline_id: str
    provider_id: str
    workflow_id: str
    manifest_id: str | None
    status: str
    output_root: str
    formats: tuple[str, ...]
    include_bom: bool
    max_rows_per_sheet: int
    created_at: datetime
    tables: dict[str, tuple[dict[str, object], ...]]
    reason_dictionary: tuple[dict[str, str], ...]


@dataclass(frozen=True, slots=True)
class DebugExportResult:
    """Persisted debug export artifact metadata."""

    root_path: str
    manifest_path: str
    debug_export_hash: str
    file_paths: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DebugExportWriterPort(Protocol):
    """Infrastructure writer contract for persisted debug export packs."""

    def write_pack(
        self,
        *,
        pack: DebugExportPack,
    ) -> DebugExportResult:
        """Persist the provided audit pack and return artifact metadata."""
        ...


class DebugExportService:
    """Collect per-run audit rows before persistence through an adapter."""

    def __init__(
        self,
        *,
        config: DebugExportConfig,
        run_id: RunID | UUID,
        pipeline_id: str,
        provider_id: str,
        manifest_id: str | None = None,
        writer: DebugExportWriterPort | None = None,
        created_at_factory: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._config = config
        self._run_id = str(run_id)
        self._pipeline_id = pipeline_id
        self._provider_id = provider_id
        self._writer = writer
        self._created_at_factory = created_at_factory
        self._collector = DebugExportCollector(
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

    def record_bronze_batch(
        self,
        *,
        records: Sequence[BronzeRecord],
        batch_id: BatchID,
        start_index: int,
        source_metadata: object | None = None,
    ) -> None:
        if not self.enabled:
            return
        self._collector.record_bronze_batch(
            records=records,
            batch_id=batch_id,
            start_index=start_index,
            source_metadata=source_metadata,
        )

    def record_transform_success(
        self,
        *,
        raw_record: BronzeRecord,
        record_index: int,
        silver_record: BronzeRecord,
        gold_record: BronzeRecord | None = None,
        created_at: datetime | None = None,
    ) -> None:
        if not self.enabled:
            return
        self._collector.record_transform_success(
            raw_record=raw_record,
            record_index=record_index,
            silver_record=silver_record,
            gold_record=gold_record,
            created_at=created_at or self._created_at_factory(),
        )

    def record_transform_failure(
        self,
        *,
        raw_record: BronzeRecord,
        record_index: int,
        error_type: ErrorType | None = None,
        details: str = "",
        policy: str | None = None,
        created_at: datetime | None = None,
    ) -> None:
        if not self.enabled:
            return
        self._collector.record_transform_failure(
            raw_record=raw_record,
            record_index=record_index,
            error_type=error_type,
            details=details,
            policy=policy,
            created_at=created_at or self._created_at_factory(),
        )

    def record_gold_filter(
        self,
        *,
        records: Sequence[GoldRecord],
        reason_code: str,
        reason_message: str = "",
        created_at: datetime | None = None,
    ) -> None:
        if not self.enabled:
            return
        self._collector.record_gold_filter(
            records=records,
            reason_code=reason_code,
            reason_message=reason_message,
            created_at=created_at or self._created_at_factory(),
        )

    def record_lineage(
        self,
        *,
        fragment_id: str,
        edge_type: str,
        node_id: str,
        raw_record: BronzeRecord,
        created_at: datetime | None = None,
    ) -> None:
        if not self.enabled:
            return
        self._collector.record_lineage(
            fragment_id=fragment_id,
            edge_type=edge_type,
            node_id=node_id,
            raw_record=raw_record,
            created_at=created_at or self._created_at_factory(),
        )

    def build_pack(self) -> DebugExportPack:
        """Build the in-memory audit pack from collected rows."""
        tables = {
            "bronze": tuple(self._collector.bronze_rows),
            "silver_full": tuple(self._collector.silver_full_rows),
            "silver_rejected": tuple(self._collector.silver_rejected_rows),
            "silver_quarantine": tuple(self._collector.silver_quarantine_rows),
            "gold_full": tuple(self._collector.gold_full_rows),
            "gold_rejected": tuple(self._collector.gold_rejected_rows),
            "dq_summary": self._collector.build_dq_summary_rows(),
            "lineage": self._collector.get_sorted_lineage_rows(),
            "reason_dictionary": DEBUG_REASON_DICTIONARY,
        }
        return DebugExportPack(
            run_id=self._run_id,
            pipeline_id=self._pipeline_id,
            provider_id=self._provider_id,
            workflow_id=self.workflow_id,
            manifest_id=self._collector._manifest_id,
            status="complete",
            output_root=self.output_dir,
            formats=self._config.formats,
            include_bom=self._config.include_bom,
            max_rows_per_sheet=self._config.max_rows_per_sheet,
            created_at=self._created_at_factory(),
            tables=tables,
            reason_dictionary=DEBUG_REASON_DICTIONARY,
        )

    async def persist(self) -> DebugExportResult:
        """Persist the collected audit pack through the adapter."""
        if not self.enabled or self._writer is None:
            raise RuntimeError(
                "Debug export is not enabled or writer is not configured"
            )
        pack = self.build_pack()
        return await self._writer.write_pack(pack=pack)
