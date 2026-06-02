"""Collector for debug export audit rows."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from datetime import datetime

from bioetl.domain.types import BatchID, BronzeRecord, ErrorType, GoldRecord

from .debug_export_helpers import (
    _base_row,
    _extract_rejection_details_mapping,
    _extract_rejection_diagnostics,
    _extract_rule_id,
    _infer_failed_field,
    _infer_reason_code,
    _jsonable_payload,
    _lineage_sort_key,
    _normalize_optional_text,
    _normalize_text,
    _payload_hash,
    _primary_key,
    _record_payload,
    _source_record_id,
)


def build_dq_summary_rows(
    *,
    run_id: str,
    workflow_id: str,
    pipeline_id: str,
    silver_rejected_rows: Sequence[dict[str, object]],
    silver_quarantine_rows: Sequence[dict[str, object]],
    gold_rejected_rows: Sequence[dict[str, object]],
) -> tuple[dict[str, object], ...]:
    """Build deterministic DQ summary rows from collected exclusion tables."""
    counter = Counter()
    for rows in (
        silver_rejected_rows,
        silver_quarantine_rows,
        gold_rejected_rows,
    ):
        for row in rows:
            stage = row.get("stage", "")
            status = row.get("status", "")
            reason_code = row.get("reason_code", "")
            action = row.get("action", "")
            counter[(stage, status, reason_code, action)] += 1
    return tuple(
        {
            "run_id": run_id,
            "workflow_id": workflow_id,
            "pipeline_id": pipeline_id,
            "stage": stage,
            "status": status,
            "reason_code": reason_code,
            "action": action,
            "record_count": count,
        }
        for (stage, status, reason_code, action), count in sorted(counter.items())
    )


def get_sorted_lineage_rows(
    rows: Sequence[dict[str, object]],
) -> tuple[dict[str, object], ...]:
    """Return lineage rows sorted by stable fragment/edge/node identity."""
    return tuple(sorted(rows, key=_lineage_sort_key))


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
            dict(source_metadata)
            if isinstance(source_metadata, dict)
            else (
                source_metadata.model_dump()
                if hasattr(source_metadata, "model_dump")
                else (
                    source_metadata.__dict__
                    if hasattr(source_metadata, "__dict__")
                    else {}
                )
            )
        )
        for offset, raw_record in enumerate(records):
            raw_payload = _record_payload(raw_record)
            row = _base_row(
                run_id=self._run_id,
                workflow_id=self._workflow_id,
                pipeline_id=self._pipeline_id,
                provider_id=self._provider_id,
                stage="bronze",
                record_index=start_index + offset,
                raw_record=raw_payload,
                normalized_record=raw_payload,
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
        gold_excluded_by_contract: bool = False,
        gold_filter_details: object | None = None,
        created_at: datetime,
    ) -> None:
        raw_payload = _record_payload(raw_record)
        silver_payload = _record_payload(silver_record)
        self._silver_full_rows.append(
            _base_row(
                run_id=self._run_id,
                workflow_id=self._workflow_id,
                pipeline_id=self._pipeline_id,
                provider_id=self._provider_id,
                stage="silver",
                record_index=record_index,
                raw_record=raw_payload,
                normalized_record=silver_payload,
                status="included",
                action="include",
                created_at=created_at,
            )
        )
        if gold_record is not None:
            gold_payload = _record_payload(gold_record)
            self._gold_record_index_by_hash[
                _payload_hash(provider_id=self._provider_id, record=gold_payload)
            ] = record_index
            self._gold_full_rows.append(
                _base_row(
                    run_id=self._run_id,
                    workflow_id=self._workflow_id,
                    pipeline_id=self._pipeline_id,
                    provider_id=self._provider_id,
                    stage="gold",
                    record_index=record_index,
                    raw_record=raw_payload,
                    normalized_record=gold_payload,
                    status="included",
                    action="include",
                    created_at=created_at,
                )
            )
        elif gold_excluded_by_contract:
            detail_mapping = _extract_rejection_details_mapping(gold_filter_details)
            failed_field, failed_value, expected_constraint = (
                _extract_rejection_diagnostics(
                    record=silver_payload,
                    details=gold_filter_details,
                    message="Gold semantic filter excluded the record.",
                )
            )
            self._gold_rejected_rows.append(
                _base_row(
                    run_id=self._run_id,
                    workflow_id=self._workflow_id,
                    pipeline_id=self._pipeline_id,
                    provider_id=self._provider_id,
                    stage="gold",
                    record_index=record_index,
                    raw_record=raw_payload,
                    normalized_record=silver_payload,
                    status="rejected",
                    action="filter",
                    created_at=created_at,
                    reason_code="SEMANTIC_FILTER_EXCLUDED",
                    reason_message=(
                        (_normalize_text(detail_mapping.get("message")) or "")
                        if detail_mapping is not None
                        else ""
                    )
                    or "Gold semantic filter excluded the record.",
                    rule_id=(
                        _normalize_text(detail_mapping.get("rule_type"))
                        or _normalize_text(detail_mapping.get("reason_code"))
                        if detail_mapping is not None
                        else ""
                    ),
                    rule_layer="gold",
                    failed_field=failed_field,
                    failed_value=failed_value,
                    expected_constraint=expected_constraint,
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
        raw_payload = _record_payload(raw_record)
        failed_field = _infer_failed_field(raw_payload, details)
        target_rows = (
            self._silver_quarantine_rows
            if policy == "quarantine"
            else self._silver_rejected_rows
        )
        target_rows.append(
            _base_row(
                run_id=self._run_id,
                workflow_id=self._workflow_id,
                pipeline_id=self._pipeline_id,
                provider_id=self._provider_id,
                stage="silver",
                record_index=record_index,
                raw_record=raw_payload,
                normalized_record=raw_payload,
                status="quarantined" if policy == "quarantine" else "rejected",
                action=policy or reason_code,
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
            normalized = _record_payload(record)
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

    def record_gold_validation_failure(
        self,
        *,
        records: Sequence[GoldRecord],
        errors: object,
        created_at: datetime,
    ) -> None:
        error_text = str(errors)
        for record in records:
            normalized = _record_payload(record)
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
                    action="fail",
                    created_at=created_at,
                    reason_code="GOLD_CONTRACT_VIOLATION",
                    reason_message=error_text,
                    rule_id=_extract_rule_id(error_text),
                    rule_layer="gold",
                    failed_field=_infer_failed_field(normalized, error_text),
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
                "primary_key": _primary_key(raw_record),
                "payload_hash": _payload_hash(
                    provider_id=self._provider_id, record=raw_record
                ),
                "source_record_id": _source_record_id(raw_record),
                "created_at": created_at.isoformat(),
            }
        )
