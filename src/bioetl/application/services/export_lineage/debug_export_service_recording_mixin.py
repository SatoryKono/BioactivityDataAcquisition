# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Record-method delegation for DebugExportService."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime
from typing import TYPE_CHECKING, Any, cast

from bioetl.domain.types import BatchID, BronzeRecord, ErrorType, GoldRecord

from .debug_export_helpers import _jsonable_payload

if TYPE_CHECKING:
    from .debug_export_collector import DebugExportCollector


class DebugExportServiceRecordingMixin:
    """Delegate enabled debug-export recording calls to the collector."""

    _collector: DebugExportCollector = cast(Any, None)  # Any: host attr default (PD3)
    _created_at_factory: Callable[[], datetime] = cast(
        Any, None
    )  # Any: host attr default (PD3)

    @property
    def enabled(self) -> bool:
        """Return whether debug-export recording is enabled."""
        raise NotImplementedError

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
            created_at=self._created_at_factory(),
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
        gold_filter_details: object | None = None,
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
            gold_filter_details=gold_filter_details,
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
            details_payload=details,
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
        details_payload: object | None = None,
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
            details_payload=details_payload,
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


__all__ = ["DebugExportServiceRecordingMixin"]
