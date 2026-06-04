"""Gold validation and lineage row recording for debug export collectors."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from bioetl.domain.types import BronzeRecord, GoldRecord

from .debug_export_collector_helpers import (
    build_gold_rejected_row,
    build_lineage_row,
    resolve_debug_record_index,
)
from .debug_export_helpers import (
    _extract_rule_id,
    _infer_failed_field,
    _record_payload,
)


class DebugExportGoldRowsMixin:
    """Record Gold rejection and lineage rows into collector-owned tables."""

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
            record_index = resolve_debug_record_index(normalized)
            self._gold_rejected_rows.append(
                build_gold_rejected_row(
                    run_id=self._run_id,
                    workflow_id=self._workflow_id,
                    pipeline_id=self._pipeline_id,
                    provider_id=self._provider_id,
                    record_index=record_index,
                    normalized_record=normalized,
                    action=reason_code,
                    created_at=created_at,
                    reason_code=reason_code,
                    reason_message=reason_message,
                    rule_id="",
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
            record_index = resolve_debug_record_index(normalized)
            self._gold_rejected_rows.append(
                build_gold_rejected_row(
                    run_id=self._run_id,
                    workflow_id=self._workflow_id,
                    pipeline_id=self._pipeline_id,
                    provider_id=self._provider_id,
                    record_index=record_index,
                    normalized_record=normalized,
                    action="fail",
                    created_at=created_at,
                    reason_code="GOLD_CONTRACT_VIOLATION",
                    reason_message=error_text,
                    rule_id=_extract_rule_id(error_text),
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
            build_lineage_row(
                run_id=self._run_id,
                workflow_id=self._workflow_id,
                pipeline_id=self._pipeline_id,
                provider_id=self._provider_id,
                fragment_id=fragment_id,
                edge_type=edge_type,
                node_id=node_id,
                raw_record=raw_record,
                created_at=created_at,
            )
        )


__all__ = ["DebugExportGoldRowsMixin"]
