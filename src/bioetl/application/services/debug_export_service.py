"""Application-level debug export collection for per-run audit packs."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from inspect import isawaitable
from pathlib import Path
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from bioetl.domain.types import (
    BatchID,
    BronzeRecord,
    DebugExportPack,
    DebugExportResult,
    ErrorType,
    GoldRecord,
    RunID,
)

if TYPE_CHECKING:
    from .debug_export_collector import DebugExportCollector

from .debug_export_collector import (
    DebugExportCollector,
    build_dq_summary_rows,
    get_sorted_lineage_rows,
)
from .debug_export_helpers import _jsonable_payload, _utc_now
from .debug_reason_dictionary import DEBUG_REASON_DICTIONARY

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


@dataclass(frozen=True, slots=True)
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


@dataclass(frozen=True, slots=True)
class DebugExportWriterProtocol(Protocol):
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
        gold_excluded_by_contract: bool = False,
        created_at: datetime | None = None,
    ) -> None:
        if not self.enabled:
            return
        self._collector.record_transform_success(
            raw_record=raw_record,
            record_index=record_index,
            silver_record=silver_record,
            gold_record=gold_record,
            gold_excluded_by_contract=gold_excluded_by_contract,
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

    def record_filtered_out(
        self,
        *,
        raw_record: BronzeRecord,
        record_index: int,
        reason: str,
        details: object | None,
        policy: str | None,
        created_at: datetime | None = None,
    ) -> None:
        if not self.enabled:
            return
        reason_message = (
            reason if details is None else f"{reason}: {_jsonable_payload(details)}"
        )
        self._collector.record_transform_failure(
            raw_record=raw_record,
            record_index=record_index,
            details=reason_message,
            policy=policy,
            created_at=created_at or self._created_at_factory(),
        )

    def record_data_quality_failure(
        self,
        *,
        raw_record: BronzeRecord,
        record_index: int,
        error_type: ErrorType | None,
        error_details: str,
        policy: str | None,
        created_at: datetime | None = None,
    ) -> None:
        if not self.enabled:
            return
        self._collector.record_transform_failure(
            raw_record=raw_record,
            record_index=record_index,
            error_type=error_type,
            details=error_details,
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

    def record_gold_validation_failure(
        self,
        *,
        records: Sequence[GoldRecord],
        errors: object,
        created_at: datetime | None = None,
    ) -> None:
        if not self.enabled:
            return
        self._collector.record_gold_validation_failure(
            records=records,
            errors=errors,
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

    def build_pack(self, *, status: str = "complete") -> DebugExportPack:
        """Build the in-memory audit pack from collected rows."""
        tables = {
            "bronze_index": tuple(self._collector._bronze_rows),
            "silver_full": tuple(self._collector._silver_full_rows),
            "silver_rejected": tuple(self._collector._silver_rejected_rows),
            "silver_quarantine": tuple(self._collector._silver_quarantine_rows),
            "gold_full": tuple(self._collector._gold_full_rows),
            "gold_rejected": tuple(self._collector._gold_rejected_rows),
            "dq_summary": build_dq_summary_rows(
                run_id=self._run_id,
                workflow_id=self.workflow_id,
                pipeline_id=self._pipeline_id,
                silver_rejected_rows=self._collector._silver_rejected_rows,
                silver_quarantine_rows=self._collector._silver_quarantine_rows,
                gold_rejected_rows=self._collector._gold_rejected_rows,
            ),
            "lineage": get_sorted_lineage_rows(self._collector._lineage_rows),
            "reason_dictionary": DEBUG_REASON_DICTIONARY,
        }
        return DebugExportPack(
            run_id=self._run_id,
            pipeline_id=self._pipeline_id,
            provider_id=self._provider_id,
            workflow_id=self.workflow_id,
            manifest_id=self._collector._manifest_id,
            status=status,
            output_root=self._debug_root or self.output_dir,
            formats=self._config.formats,
            include_bom=self._config.include_bom,
            max_rows_per_sheet=self._config.max_rows_per_sheet,
            created_at=self._created_at_factory(),
            tables=tables,
            reason_dictionary=DEBUG_REASON_DICTIONARY,
        )

    async def persist(self, *, status: str = "complete") -> DebugExportResult:
        """Persist the collected audit pack through the adapter."""
        if not self.enabled or self._writer is None:
            raise RuntimeError(
                "Debug export is not enabled or writer is not configured"
            )
        result = self._writer.write_pack(pack=self.build_pack(status=status))
        if isawaitable(result):
            return await result
        return result

    def finalize(
        self,
        *,
        status: str,
        manifest_id: str | None,
    ) -> DebugExportResult | None:
        """Persist the collected pack once the run reaches its terminal state."""
        if not self.enabled or self._writer is None:
            return None
        self.attach_manifest_id(manifest_id)
        return self._writer.write_pack(pack=self.build_pack(status=status))
