# pyright: reportUninitializedInstanceVariable=false
# pyright: reportAttributeAccessIssue=false
# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Gold validation and lineage row recording for debug export collectors."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from bioetl.domain.types import (
    GOLD_CONTRACT_VERSION_UNKNOWN,
    BronzeRecord,
    GoldRecord,
    GoldRejectReason,
    GoldRejectReasonCode,
)

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

    _run_id: str
    _workflow_id: str
    _pipeline_id: str
    _provider_id: str
    _gold_rejected_rows: list[dict[str, object]]
    _lineage_rows: list[dict[str, object]]

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
            resolved_reason_code = _canonical_gold_filter_reason_code(reason_code)
            self._gold_rejected_rows.append(
                build_gold_rejected_row(
                    run_id=self._run_id,
                    workflow_id=self._workflow_id,
                    pipeline_id=self._pipeline_id,
                    provider_id=self._provider_id,
                    record_index=record_index,
                    normalized_record=normalized,
                    action=resolved_reason_code,
                    created_at=created_at,
                    reason_code=resolved_reason_code,
                    reason_message=reason_message,
                    rule_id="",
                    failed_field="",
                    contract_version=_record_contract_version(normalized),
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
        reject_reason = _extract_gold_reject_reason(errors)
        for record in records:
            normalized = _record_payload(record)
            record_index = resolve_debug_record_index(normalized)
            reason_code = (
                reject_reason.reason_code.value
                if reject_reason is not None
                else GoldRejectReasonCode.CONTRACT_SCHEMA_FAILURE.value
            )
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
                    reason_code=reason_code,
                    reason_message=(
                        reject_reason.message
                        if reject_reason is not None and reject_reason.message
                        else error_text
                    ),
                    rule_id=(
                        reject_reason.rule_id
                        if reject_reason is not None
                        else _extract_rule_id(error_text)
                    ),
                    failed_field=(
                        reject_reason.field
                        if reject_reason is not None and reject_reason.field
                        else _infer_failed_field(normalized, error_text)
                    ),
                    contract_version=(
                        reject_reason.contract_version
                        if reject_reason is not None
                        else _record_contract_version(normalized)
                    ),
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


def _record_contract_version(record: dict[str, object]) -> str:
    value = record.get("contract_version")
    return (
        str(value).strip()
        if value is not None and str(value).strip()
        else GOLD_CONTRACT_VERSION_UNKNOWN
    )


def _canonical_gold_filter_reason_code(reason_code: str) -> str:
    if reason_code.startswith("gold_semantic_"):
        return reason_code
    return GoldRejectReasonCode.SEMANTIC_BUSINESS_EXCLUSION.value


def _extract_gold_reject_reason(errors: object) -> GoldRejectReason | None:
    reject_reason = getattr(errors, "reject_reason", None)
    return reject_reason if isinstance(reject_reason, GoldRejectReason) else None
