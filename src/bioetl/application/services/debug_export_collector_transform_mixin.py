"""Bronze and transform-row recording for debug export collectors."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from bioetl.domain.types import (
    GOLD_CONTRACT_VERSION_UNKNOWN,
    BatchID,
    BronzeRecord,
    ErrorType,
    GoldRejectReasonCode,
)

from .debug_export_collector_helpers import source_metadata_attrs
from .debug_export_helpers import (
    _base_row,
    _extract_rejection_details_mapping,
    _extract_rejection_diagnostics,
    _extract_rule_id,
    _infer_reason_code,
    _jsonable_payload,
    _normalize_text,
    _payload_hash,
    _record_payload,
)

_GOLD_SEMANTIC_FILTER_EXCLUDED_MSG = "Gold semantic filter excluded the record."


class DebugExportTransformRowsMixin:
    """Record Bronze/Silver transform rows into collector-owned tables."""

    _run_id: str
    _workflow_id: str
    _pipeline_id: str
    _provider_id: str
    _bronze_rows: list[dict[str, object]]
    _silver_full_rows: list[dict[str, object]]
    _silver_rejected_rows: list[dict[str, object]]
    _silver_quarantine_rows: list[dict[str, object]]
    _gold_full_rows: list[dict[str, object]]
    _gold_rejected_rows: list[dict[str, object]]
    _gold_record_index_by_hash: dict[str, int]

    def record_bronze_batch(
        self,
        *,
        records: Sequence[BronzeRecord],
        batch_id: BatchID,
        start_index: int,
        created_at: datetime,
        source_metadata: object | None = None,
    ) -> None:
        source_attrs = source_metadata_attrs(source_metadata)
        for offset, raw_record in enumerate(records):
            raw_payload = _record_payload(raw_record)
            row = _base_row(
                identity=(
                    self._run_id,
                    self._workflow_id,
                    self._pipeline_id,
                    self._provider_id,
                ),
                stage="bronze",
                record_index=start_index + offset,
                records=(raw_payload, raw_payload),
                status="included",
                created_at=created_at,
                failure=(
                    "extract",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                ),
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
                identity=(self._run_id, self._workflow_id, self._pipeline_id, self._provider_id),
                stage="silver",
                record_index=record_index,
                records=(raw_payload, silver_payload),
                status="included",
                created_at=created_at,
                failure=("include", "", "", "", "", "", "", "", ""),
            )
        )
        if gold_record is not None:
            self._record_gold_success(
                raw_payload, record_index, gold_record, created_at
            )
        elif gold_excluded_by_contract:
            self._record_gold_contract_exclusion(
                raw_payload,
                silver_payload,
                record_index,
                gold_filter_details,
                created_at,
            )

    def _record_gold_success(
        self,
        raw_payload: dict[str, object],
        record_index: int,
        gold_record: BronzeRecord,
        created_at: datetime,
    ) -> None:
        gold_payload = _record_payload(gold_record)
        self._gold_record_index_by_hash[
            _payload_hash(provider_id=self._provider_id, record=gold_payload)
        ] = record_index
        self._gold_full_rows.append(
            _base_row(
                identity=(self._run_id, self._workflow_id, self._pipeline_id, self._provider_id),
                stage="gold",
                record_index=record_index,
                records=(raw_payload, gold_payload),
                status="included",
                created_at=created_at,
                failure=("include", "", "", "", "", "", "", "", ""),
            )
        )

    def _record_gold_contract_exclusion(
        self,
        raw_payload: dict[str, object],
        silver_payload: dict[str, object],
        record_index: int,
        gold_filter_details: object | None,
        created_at: datetime,
    ) -> None:
        detail_mapping = _extract_rejection_details_mapping(gold_filter_details)
        failed_field, failed_value, expected_constraint = (
            _extract_rejection_diagnostics(
                record=silver_payload,
                details=gold_filter_details,
                message=_GOLD_SEMANTIC_FILTER_EXCLUDED_MSG,
            )
        )
        self._gold_rejected_rows.append(
            _base_row(
                identity=(self._run_id, self._workflow_id, self._pipeline_id, self._provider_id),
                stage="gold",
                record_index=record_index,
                records=(raw_payload, silver_payload),
                status="rejected",
                created_at=created_at,
                failure=("filter", _gold_filter_reason_code(detail_mapping), _gold_filter_message(detail_mapping), _gold_filter_rule_id(detail_mapping), "gold", failed_field, failed_value, expected_constraint, _gold_filter_contract_version(detail_mapping)),
            )
        )

    def record_transform_failure(
        self,
        *,
        raw_record: BronzeRecord,
        record_index: int,
        error_type: ErrorType | None = None,
        details: str = "",
        details_payload: object | None = None,
        policy: str | None = None,
        created_at: datetime,
    ) -> None:
        reason_code = _infer_reason_code(
            error_type=error_type, details=details, policy=policy
        )
        reason_message = details or f"{error_type.value if error_type else 'Unknown'}"
        raw_payload = _record_payload(raw_record)
        failed_field, failed_value, expected_constraint = (
            _extract_rejection_diagnostics(
                record=raw_payload,
                details=details_payload,
                message=details,
            )
        )
        target_rows = (
            self._silver_quarantine_rows
            if policy == "quarantine"
            else self._silver_rejected_rows
        )
        target_rows.append(
            _base_row(
                identity=(self._run_id, self._workflow_id, self._pipeline_id, self._provider_id),
                stage="silver",
                record_index=record_index,
                records=(raw_payload, raw_payload),
                status="quarantined" if policy == "quarantine" else "rejected",
                created_at=created_at,
                failure=(policy or reason_code, reason_code, reason_message, _extract_rule_id(details), "silver", failed_field, failed_value, expected_constraint, ""),
            )
        )


def _gold_filter_message(detail_mapping: dict[str, object] | None) -> str:
    if detail_mapping is None:
        return _GOLD_SEMANTIC_FILTER_EXCLUDED_MSG
    return (
        _normalize_text(detail_mapping.get("message"))
        or _GOLD_SEMANTIC_FILTER_EXCLUDED_MSG
    )


def _gold_filter_rule_id(detail_mapping: dict[str, object] | None) -> str:
    if detail_mapping is None:
        return ""
    return _normalize_text(detail_mapping.get("rule_type")) or _normalize_text(
        detail_mapping.get("reason_code")
    )


def _gold_filter_reason_code(detail_mapping: dict[str, object] | None) -> str:
    if detail_mapping is not None:
        existing = _normalize_text(detail_mapping.get("reason_code"))
        if existing.startswith("gold_semantic_"):
            return existing
        scope = (
            _normalize_text(detail_mapping.get("semantic_scope"))
            or _normalize_text(detail_mapping.get("rule_type"))
            or existing
        ).lower()
        if "profile" in scope:
            return GoldRejectReasonCode.SEMANTIC_PROFILE_EXCLUSION.value
    return GoldRejectReasonCode.SEMANTIC_BUSINESS_EXCLUSION.value


def _gold_filter_contract_version(detail_mapping: dict[str, object] | None) -> str:
    if detail_mapping is None:
        return GOLD_CONTRACT_VERSION_UNKNOWN
    contract_version = _normalize_text(detail_mapping.get("contract_version")).strip()
    return contract_version or GOLD_CONTRACT_VERSION_UNKNOWN


__all__ = ["DebugExportTransformRowsMixin"]
