"""Collector for debug export audit rows."""

from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

from bioetl.domain.types import BatchID, BronzeRecord, ErrorType, GoldRecord, RunID

if TYPE_CHECKING:
    pass

from .debug_export_helpers import (
    _extract_rule_id,
    _infer_failed_field,
    _infer_reason_code,
    _jsonable_payload,
    _lineage_sort_key,
    _normalize_optional_text,
    _normalize_text,
    _payload_hash,
    _primary_key,
    _row_sort_key,
    _safe_payload,
    _source_record_id,
    _base_row,
)


class DebugExportCollector:
    """Collect and store audit rows for debug export."""

    def __init__(
        self,
        *,
        run_id: str,
        pipeline_id: str,
        provider_id: str,
        workflow_id: str,
        manifest_id: str | None = None,
    ) -> None:
        self._run_id = run_id
        self._pipeline_id = pipeline_id
        self._provider_id = provider_id
        self._workflow_id = workflow_id
        self._manifest_id = manifest_id
        self._bronze_rows: list[dict[str, object]] = []
        self._silver_full_rows: list[dict[str, object]] = []
        self._silver_rejected_rows: list[dict[str, object]] = []
        self._silver_quarantine_rows: list[dict[str, object]] = []
        self._gold_full_rows: list[dict[str, object]] = []
        self._gold_rejected_rows: list[dict[str, object]] = []
        self._lineage_rows: list[dict[str, object]] = []
        self._gold_record_index_by_hash: dict[str, int] = {}

    @property
    def bronze_rows(self) -> list[dict[str, object]]:
        return self._bronze_rows

    @property
    def silver_full_rows(self) -> list[dict[str, object]]:
        return self._silver_full_rows

    @property
    def silver_rejected_rows(self) -> list[dict[str, object]]:
        return self._silver_rejected_rows

    @property
    def silver_quarantine_rows(self) -> list[dict[str, object]]:
        return self._silver_quarantine_rows

    @property
    def gold_full_rows(self) -> list[dict[str, object]]:
        return self._gold_full_rows

    @property
    def gold_rejected_rows(self) -> list[dict[str, object]]:
        return self._gold_rejected_rows

    @property
    def lineage_rows(self) -> list[dict[str, object]]:
        return self._lineage_rows

    def attach_manifest_id(self, manifest_id: str | None) -> None:
        self._manifest_id = manifest_id

    def record_bronze_batch(
        self,
        *,
        records: Sequence[BronzeRecord],
        batch_id: BatchID,
        start_index: int,
        source_metadata: object | None = None,
    ) -> None:
        source_attrs = (
            source_metadata.model_dump()
            if hasattr(source_metadata, "model_dump")
            else (
                source_metadata.__dict__ if hasattr(source_metadata, "__dict__") else {}
            )
        )
        for offset, raw_record in enumerate(records):
            row = _base_row(
                run_id=self._run_id,
                workflow_id=self._workflow_id,
                pipeline_id=self._pipeline_id,
                provider_id=self._provider_id,
                stage="bronze",
                record_index=start_index + offset,
                raw_record=raw_record.model_dump(),
                normalized_record=raw_record.model_dump(),
                status="included",
                action="extract",
                created_at=datetime.now(),
            )
            row["batch_id"] = str(batch_id)
            row["source_metadata"] = _jsonable_payload(source_attrs)
            self._bronze_rows.append(row)

    def record_transform_success(
        self,
        *,
        raw_record: BronzeRecord,
        record_index: int,
        silver_record: BronzeRecord,
        gold_record: BronzeRecord | None = None,
        created_at: datetime,
    ) -> None:
        self._silver_full_rows.append(
            _base_row(
                run_id=self._run_id,
                workflow_id=self._workflow_id,
                pipeline_id=self._pipeline_id,
                provider_id=self._provider_id,
                stage="silver",
                record_index=record_index,
                raw_record=raw_record.model_dump(),
                normalized_record=silver_record.model_dump(),
                status="included",
                action="include",
                created_at=created_at,
            )
        )
        if gold_record is not None:
            self._gold_record_index_by_hash[
                _payload_hash(provider_id=self._provider_id, record=gold_record)
            ] = record_index
            self._gold_full_rows.append(
                _base_row(
                    run_id=self._run_id,
                    workflow_id=self._workflow_id,
                    pipeline_id=self._pipeline_id,
                    provider_id=self._provider_id,
                    stage="gold",
                    record_index=record_index,
                    raw_record=raw_record.model_dump(),
                    normalized_record=gold_record.model_dump(),
                    status="included",
                    action="include",
                    created_at=created_at,
                )
            )

    def record_transform_failure(
        self,
        *,
        raw_record: BronzeRecord,
        record_index: int,
        error_type: ErrorType | None = None,
        details: str = "",
        policy: str | None = None,
        created_at: datetime,
    ) -> None:
        reason_code = _infer_reason_code(
            error_type=error_type, details=details, policy=policy
        )
        reason_message = details or f"{error_type.value if error_type else 'Unknown'}"
        rule_id = _extract_rule_id(details)
        rule_layer = "silver"
        failed_field = _infer_failed_field(raw_record.model_dump(), details)
        self._silver_rejected_rows.append(
            _base_row(
                run_id=self._run_id,
                workflow_id=self._workflow_id,
                pipeline_id=self._pipeline_id,
                provider_id=self._provider_id,
                stage="silver",
                record_index=record_index,
                raw_record=raw_record.model_dump(),
                normalized_record=raw_record.model_dump(),
                status="rejected",
                action=reason_code,
                created_at=created_at,
                reason_code=reason_code,
                reason_message=reason_message,
                rule_id=rule_id,
                rule_layer=rule_layer,
                failed_field=failed_field,
            )
        )

    def record_gold_filter(
        self,
        *,
        records: Sequence[GoldRecord],
        reason_code: str,
        reason_message: str = "",
        created_at: datetime,
    ) -> None:
        for record in records:
            normalized = record.model_dump()
            existing = _normalize_optional_text(normalized.get("_debug_record_index"))
            try:
                record_index = int(existing) if existing else None
            except ValueError:
                record_index = None
            self._gold_rejected_rows.append(
                _base_row(
                    run_id=self._run_id,
                    workflow_id=self._workflow_id,
                    pipeline_id=self._pipeline_id,
                    provider_id=self._provider_id,
                    stage="gold",
                    record_index=record_index,
                    raw_record=normalized,
                    normalized_record=normalized,
                    status="rejected",
                    action=reason_code,
                    created_at=created_at,
                    reason_code=reason_code,
                    reason_message=reason_message,
                    rule_id="",
                    rule_layer="gold",
                    failed_field="",
                )
            )

    def record_lineage(
        self,
        *,
        fragment_id: str,
        edge_type: str,
        node_id: str,
        raw_record: BronzeRecord,
        created_at: datetime,
    ) -> None:
        self._lineage_rows.append(
            {
                "run_id": self._run_id,
                "workflow_id": self._workflow_id,
                "pipeline_id": self._pipeline_id,
                "provider_id": self._provider_id,
                "fragment_id": fragment_id,
                "edge_type": edge_type,
                "node_id": node_id,
                "primary_key": _primary_key(raw_record.model_dump()),
                "payload_hash": _payload_hash(
                    provider_id=self._provider_id, record=raw_record
                ),
                "created_at": created_at.isoformat(),
            }
        )

    def build_dq_summary_rows(self) -> list[dict[str, object]]:
        from collections import Counter

        counter = Counter()
        for row in self._silver_rejected_rows:
            stage = row.get("stage", "")
            status = row.get("status", "")
            reason_code = row.get("reason_code", "")
            action = row.get("action", "")
            counter[(stage, status, reason_code, action)] += 1
        return tuple(
            {
                "run_id": self._run_id,
                "workflow_id": self._workflow_id,
                "pipeline_id": self._pipeline_id,
                "stage": stage,
                "status": status,
                "reason_code": reason_code,
                "action": action,
                "record_count": count,
            }
            for (stage, status, reason_code, action), count in sorted(counter.items())
        )

    def get_sorted_lineage_rows(self) -> tuple[dict[str, object], ...]:
        return tuple(sorted(self._lineage_rows, key=_lineage_sort_key))
