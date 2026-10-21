# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Gold-layer prepare/validate helpers for BatchWriter IO paths."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, cast

from bioetl.application.core._gold_outcome_disposition import (
    GoldQuarantineEntry,
    plan_gold_outcome_write,
    supports_outcome_channel,
)
from bioetl.application.core._gold_outcome_quarantine_write import (
    empty_gold_receipt,
    flush_gold_outcome_quarantine,
    record_gold_outcome_quarantine_metrics,
)
from bioetl.application.services.run_reports.observations import record_gold_observation
from bioetl.domain.behavior.dq_contract_rule_source import (
    has_explicit_outcome_policy,
)
from bioetl.domain.config.dq import DQConfig
from bioetl.domain.exceptions import SchemaViolationError
from bioetl.domain.types import JsonDict
from bioetl.domain.types.dq_record_attribution import DQOutcomeChannel
from bioetl.domain.types.gold_contracts import GoldWriteReceipt

if TYPE_CHECKING:
    from bioetl.application.core.batch_writer_io_mixin import BatchWriterIOMixin
    from bioetl.domain.ports import GoldValidatorPort
    from bioetl.domain.types import GoldRecord, GoldSchemaType


class _GoldWriterHost(Protocol):
    """Minimal BatchWriter surface for Gold prepare/validate helpers."""

    _gold_schema: GoldSchemaType
    _gold_validator: GoldValidatorPort

    def _get_schema_columns(self, schema: object) -> set[str] | None: ...

    def _collect_record_columns(self, records: list[GoldRecord]) -> list[str]: ...


def prepare_gold_records(
    writer: _GoldWriterHost,
    records: list[GoldRecord],
    *,
    schema: object | None = None,
) -> tuple[list[GoldRecord], list[str]]:
    """Project records to schema and compute available columns."""
    target_schema = schema if schema is not None else writer._gold_schema
    schema_columns = writer._get_schema_columns(target_schema)
    if not schema_columns:
        return records, writer._collect_record_columns(records)

    ordered_columns = sorted(schema_columns)
    dq_defaults = {"_dq_warn": False, "_dq_error": False}
    projected = [
        {
            key: record.get(key, dq_defaults.get(key))
            for key in ordered_columns
            if key in record or key in dq_defaults
        }
        for record in records
    ]
    return projected, ordered_columns


async def release_pending_gold_quarantine(
    writer: BatchWriterIOMixin,
    records: list[GoldRecord],
    schema_payload: object,
) -> GoldWriteReceipt | None:
    """Flush the sync accumulator and receipt an all-quarantine batch."""
    writer._last_gold_outcome_quarantine_count = 0
    pending = tuple(writer._pending_gold_outcome_quarantine)
    writer._pending_gold_outcome_quarantine = ()
    batch_id = writer._gold_quarantine_batch_id or writer._context.source_batch_id
    await flush_gold_outcome_quarantine(
        quarantine=writer._gold_quarantine_port,  # type: ignore[arg-type]
        items=pending,  # type: ignore[arg-type]
        pipeline_name=writer._config.pipeline_name,
        batch_id=batch_id,
        run_id=writer._context.run_id,
        ingestion_ts=writer._resolve_gold_ingestion_ts(),
        emitter=getattr(writer, "_gold_outcome_emitter", None),
    )
    writer._last_gold_outcome_quarantine_count = len(pending)
    indexes: list[int] = []
    for item in pending:
        source_index = getattr(item, "source_index", None)
        if isinstance(source_index, int) and not isinstance(source_index, bool):
            indexes.append(source_index)
    writer._gold_outcome_quarantine_indexes = tuple(indexes)
    record_gold_outcome_quarantine_metrics(writer, pending)  # type: ignore[arg-type]
    if records or not pending:
        return None
    return empty_gold_receipt(schema_payload, writer._gold_table_name)


def validate_gold_records(
    writer: _GoldWriterHost,
    records: list[GoldRecord],
    *,
    schema: object | None = None,
    apply_contract_rules: bool = True,
) -> tuple[list[GoldRecord], tuple[GoldQuarantineEntry, ...]]:
    """Validate Gold records and return the rows that may be written.

    Explicit outcome policy routes attributable ``QUARANTINE`` violations into
    the returned accumulator. ``FAIL``, ``SKIP``, unattributable violations,
    and validators without that policy stay on fail-closed ``.validate()``.
    ``apply_contract_rules=False`` is the structural re-check after column
    projection and does not reopen the outcome channel.
    """
    validator = writer._gold_validator
    target_schema = schema if schema is not None else writer._gold_schema
    if schema is not None:
        validator = cast(
            "GoldValidatorPort",
            rebind_gold_validator_schema(validator, target_schema),
        )

    if apply_contract_rules and _use_outcome_channel(validator):
        channel = _call_outcome_channel(validator, records)
        if isinstance(channel, DQOutcomeChannel):
            config = cast("DQConfig | None", getattr(validator, "_dq_config", None))
            plan = plan_gold_outcome_write(records, channel, config)
            if not plan.fail_closed:
                record_gold_observation(True, len(records))
                kept = cast("list[GoldRecord]", list(plan.records_to_write))
                return kept, plan.quarantine_items
            _raise_fail_closed(writer, records, validator, plan.fail_closed_reasons)
    result = validator.validate(records)
    record_gold_observation(result.valid, len(records))
    if not result.valid:
        _export_gold_failure(writer, records, list(result.errors))
        raise SchemaViolationError("gold", result.errors)
    return records, ()


def _call_outcome_channel(validator: object, records: list[JsonDict]) -> object:
    method = getattr(type(validator), "validate_with_outcomes", None)
    if not callable(method):
        return None
    return method(validator, records)


def _use_outcome_channel(validator: object) -> bool:
    if not supports_outcome_channel(validator):
        return False
    config = getattr(validator, "_dq_config", None)
    if not isinstance(config, DQConfig):
        return False
    return has_explicit_outcome_policy(config)


def _raise_fail_closed(
    writer: _GoldWriterHost,
    records: list[GoldRecord],
    validator: object,
    reasons: tuple[str, ...],
) -> None:
    validate = getattr(validator, "validate", None)
    errors = list(reasons)
    if callable(validate):
        result = validate(records)
        if not getattr(result, "valid", True):
            errors = list(getattr(result, "errors", None) or reasons)
    if not errors:
        errors = ["gold outcome channel fail-closed"]
    record_gold_observation(False, len(records))
    _export_gold_failure(writer, records, errors)
    raise SchemaViolationError("gold", errors)


def _export_gold_failure(
    writer: _GoldWriterHost,
    records: list[GoldRecord],
    errors: list[str],
) -> None:
    debug_export_service = getattr(writer, "_debug_export_service", None)
    if debug_export_service is not None:
        debug_export_service.record_gold_validation_failure(
            records=records,
            errors=errors,
        )


def rebind_gold_validator_schema(
    validator: object,
    schema: object,
) -> object:
    """Rebind schema-aware validators via their owned rebind/clone API."""
    rebind = getattr(validator, "rebind_schema", None)
    if callable(rebind):
        return rebind(schema)
    # Validators without a rebind surface keep their original schema binding.
    return validator


def should_defer_gold_validation_to_storage(writer: object) -> bool:
    """Whether Gold validation/projection must happen per-version in storage."""
    policy = getattr(writer, "_gold_schema_policy_by_version", None)
    return bool(policy is not None and policy.is_multi_version)


def prepare_validated_gold_write(
    writer: BatchWriterIOMixin, records: list[GoldRecord]
) -> tuple[list[GoldRecord], list[str], object]:
    """Prepare one Gold write, retaining storage-owned versioned validation."""
    writer._pending_gold_outcome_quarantine = ()
    writer._gold_outcome_quarantine_indexes = ()
    if should_defer_gold_validation_to_storage(writer):
        available_cols = writer._collect_record_columns(records)
        schema_payload: object = writer._gold_schema_policy_by_version
    else:
        records, available_cols = prepare_gold_records(writer, records)
        records, quarantined = validate_gold_records(writer, records)
        column_order_preview, _rename_preview = writer._resolve_layer_columns(
            "gold", available_cols
        )
        schema_payload = writer._project_schema_for_layer(
            "gold",
            writer._gold_schema,
            column_order_preview,
        )
        if schema_payload is not None and schema_payload is not writer._gold_schema:
            records, available_cols = prepare_gold_records(
                writer,
                records,
                schema=schema_payload,
            )
            records, more = validate_gold_records(
                writer,
                records,
                schema=schema_payload,
                apply_contract_rules=False,
            )
            quarantined = (*quarantined, *more)
        writer._pending_gold_outcome_quarantine = quarantined
    return records, available_cols, schema_payload
