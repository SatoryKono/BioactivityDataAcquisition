"""Async flush of Gold outcome quarantine accumulated by sync validation."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.application.core._gold_outcome_disposition import (
    GoldOutcomeQuarantineItem,
    GoldOutcomeQuarantineRule,
)
from bioetl.application.core._quarantine_write_support import write_quarantine_requests
from bioetl.domain.exceptions import SchemaViolationError
from bioetl.domain.types import BatchID, ErrorType, JsonDict, RunID
from bioetl.domain.types.gold_contracts import (
    GoldWriteCategory,
    GoldWriteReceipt,
    resolve_gold_contract_version,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import QuarantinePort, QuarantineWriteRequest

__all__ = [
    "empty_gold_receipt",
    "flush_gold_outcome_quarantine",
]


async def flush_gold_outcome_quarantine(
    *,
    quarantine: QuarantinePort | None,
    items: tuple[GoldOutcomeQuarantineItem, ...],
    pipeline_name: str,
    batch_id: BatchID | None,
    run_id: RunID | None,
    ingestion_ts: datetime,
) -> None:
    """Send accumulated per-record quarantine requests. Validators stay sync."""
    if not items:
        return
    if quarantine is None or batch_id is None:
        raise SchemaViolationError(
            "gold",
            ["quarantine routing is unavailable for attributable DQ outcomes"],
        )
    requests = [
        _quarantine_request(
            item,
            pipeline_name=pipeline_name,
            batch_id=batch_id,
            run_id=run_id,
            ingestion_ts=ingestion_ts,
        )
        for item in items
    ]
    await write_quarantine_requests(quarantine, requests)


def empty_gold_receipt(schema: object, table_name: str) -> GoldWriteReceipt:
    """Receipt for a batch whose every row was routed to quarantine."""
    return GoldWriteReceipt(
        physical_table=table_name,
        contract_version=resolve_gold_contract_version(schema),
        category=GoldWriteCategory.COMPLETE,
    )


def _quarantine_request(
    item: GoldOutcomeQuarantineItem,
    *,
    pipeline_name: str,
    batch_id: BatchID,
    run_id: RunID | None,
    ingestion_ts: datetime,
) -> QuarantineWriteRequest:
    primary = item.rules[0]
    rules = [_rule_payload(rule) for rule in item.rules]
    message = "; ".join(rule.rule_id for rule in item.rules)
    error_code = (
        ErrorType.SCHEMA_VIOLATION.value
        if all(rule.rule_id.startswith("schema.") for rule in item.rules)
        else ErrorType.DATA_QUALITY.value
    )
    metadata: JsonDict = {
        "classification": "dq_rule_outcome",
        "quarantine_category": "gold_rule_outcome",
        "rule_id": primary.rule_id,
        "contract_ref": primary.contract_ref,
        "config_path": primary.config_path,
        "source_index": item.source_index,
        "record_key": item.record_key,
        "rules": rules,
        "error_details": {"message": message},
    }
    return {
        "pipeline": pipeline_name,
        "error_code": error_code,
        "payload": item.record,
        "bronze_batch_id": batch_id,
        "run_id": run_id,
        "metadata": metadata,
        "ingestion_ts": ingestion_ts,
    }


def _rule_payload(rule: GoldOutcomeQuarantineRule) -> JsonDict:
    return {
        "rule_id": rule.rule_id,
        "contract_ref": rule.contract_ref,
        "config_path": rule.config_path,
        "disposition": rule.disposition,
    }
