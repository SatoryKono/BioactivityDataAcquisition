"""Async flush of Gold outcome quarantine accumulated by sync validation."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.application.core._gold_outcome_disposition import (
    GoldQuarantineEntry,
    GoldQuarantineRuleRecord,
)
from bioetl.application.core._quarantine_write_support import (
    write_quarantine_requests_with_events,
)
from bioetl.domain.deterministic_identity import deterministic_id
from bioetl.domain.exceptions import SchemaViolationError
from bioetl.domain.types import BatchID, ErrorType, JsonDict, RunID
from bioetl.domain.types.gold_contracts import (
    GoldWriteCategory,
    GoldWriteReceipt,
    resolve_gold_contract_version,
)

if TYPE_CHECKING:
    from bioetl.application.observability.domain_event_emitter import (
        DomainEventEmitterProtocol,
    )
    from bioetl.domain.ports import QuarantinePort, QuarantineWriteRequest

__all__ = [
    "empty_gold_receipt",
    "flush_gold_outcome_quarantine",
    "record_gold_outcome_quarantine_metrics",
]


async def flush_gold_outcome_quarantine(
    *,
    quarantine: QuarantinePort | None,
    items: tuple[GoldQuarantineEntry, ...],
    pipeline_name: str,
    batch_id: BatchID | None,
    run_id: RunID | None,
    ingestion_ts: datetime,
    emitter: DomainEventEmitterProtocol | None = None,
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
    await write_quarantine_requests_with_events(
        quarantine=quarantine,
        requests=requests,
        emitter=emitter,
        pipeline_name=pipeline_name,
        error_codes=tuple(request["error_code"] for request in requests),
        error_messages=tuple(_request_message(request) for request in requests),
        batch_id=batch_id,
        run_id=run_id,
        ingestion_ts=ingestion_ts,
    )


def record_gold_outcome_quarantine_metrics(
    writer: object,
    items: tuple[GoldQuarantineEntry, ...],
) -> None:
    """Count Gold outcome quarantine on the writer's batch metrics recorder."""
    if not items:
        return
    metrics = getattr(writer, "_batch_metrics", None)
    track = getattr(metrics, "track_quarantined_records", None)
    if not callable(track):
        return
    counts: dict[ErrorType, int] = {}
    for item in items:
        error_type = _item_error_type(item)
        counts[error_type] = counts.get(error_type, 0) + 1
    for error_type in sorted(counts, key=lambda item: item.value):
        track(
            error_type,
            counts[error_type],
            stage="gold",
            reason_code="gold_rule_outcome",
        )


def empty_gold_receipt(schema: object, table_name: str) -> GoldWriteReceipt:
    """Receipt for a batch whose every row was routed to quarantine."""
    return GoldWriteReceipt(
        physical_table=table_name,
        contract_version=resolve_gold_contract_version(schema),
        category=GoldWriteCategory.COMPLETE,
    )


def _quarantine_request(
    item: GoldQuarantineEntry,
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
        "entry_id": _outcome_entry_id(item, batch_id),
        "metadata": metadata,
        "ingestion_ts": ingestion_ts,
    }


def _outcome_entry_id(item: GoldQuarantineEntry, batch_id: BatchID) -> str:
    """Stable id for one row and its rule set inside a batch."""
    return deterministic_id(
        "gold-rule-outcome",
        {
            "batch_id": batch_id,
            "rule_ids": [rule.rule_id for rule in item.rules],
            "source_index": item.source_index,
        },
    )


def _item_error_type(item: GoldQuarantineEntry) -> ErrorType:
    if item.rules and all(rule.rule_id.startswith("schema.") for rule in item.rules):
        return ErrorType.SCHEMA_VIOLATION
    return ErrorType.DATA_QUALITY


def _request_message(request: QuarantineWriteRequest) -> str:
    metadata = request.get("metadata")
    details = metadata.get("error_details") if isinstance(metadata, dict) else None
    message = details.get("message") if isinstance(details, dict) else None
    if isinstance(message, str) and message:
        return message
    return request["error_code"]


def _rule_payload(rule: GoldQuarantineRuleRecord) -> JsonDict:
    return {
        "rule_id": rule.rule_id,
        "contract_ref": rule.contract_ref,
        "config_path": rule.config_path,
        "disposition": rule.disposition,
    }
