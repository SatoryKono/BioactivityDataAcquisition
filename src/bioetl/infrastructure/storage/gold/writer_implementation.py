"""Write implementation helpers for Gold writer."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from time import perf_counter
from typing import TYPE_CHECKING, cast

from bioetl.domain.exceptions.gold_write import GoldWriteCancelled, GoldWriteFailure
from bioetl.domain.types.gold_contracts import GoldWriteCategory, GoldWriteReceipt
from bioetl.infrastructure.observability.metrics import (
    GOLD_VALIDATION_FAILURES_TOTAL,
    GOLD_WRITE_ATTEMPTS_TOTAL,
    GOLD_WRITE_DURATION_SECONDS,
    GOLD_WRITE_OUTCOMES_TOTAL,
)
from bioetl.infrastructure.storage.gold.pipeline_helpers import (
    GoldWriteDispatchContext as _GoldWriteDispatchContext,
)
from bioetl.infrastructure.storage.gold.pipeline_helpers import (
    GoldWritePostwriteContext as _GoldWritePostwriteContext,
)
from bioetl.infrastructure.storage.gold.pipeline_helpers import (
    GoldWriteRequest as _GoldWriteRequest,
)
from bioetl.infrastructure.storage.gold.pipeline_helpers import (
    PreparedGoldWriteContext as _PreparedGoldWriteContext,
)
from bioetl.infrastructure.storage.gold.writer_metrics import (
    _gold_validation_metric_labels,
    _gold_write_metric_labels,
)
from bioetl.infrastructure.storage.gold.writer_protocols import _GoldWriterHost
from bioetl.infrastructure.storage.gold.writer_schema_helpers import (
    _project_records_for_gold_schema,
)
from bioetl.infrastructure.storage.writer_common import (
    get_write_targets,
    iterate_write_targets,
    validate_write_versions,
)

if TYPE_CHECKING:
    from pandera.polars import DataFrameSchema

    from bioetl.domain.types import GoldSchemaPolicyByVersion

__all__ = [
    "_write_dual_targets_impl",
    "_write_single_target_impl",
]


async def _write_single_target_impl(
    writer: _GoldWriterHost,
    *,
    request: _GoldWriteRequest,
) -> GoldWriteReceipt:
    """Execute one physical Gold write target through the standard pipeline."""
    started_at = perf_counter()
    prepared: _PreparedGoldWriteContext | None = None
    terminal_status = "failure"
    GOLD_WRITE_ATTEMPTS_TOTAL.labels(**_gold_write_metric_labels(request)).inc()
    receipt = GoldWriteReceipt(
        request.table_name,
        request.contract_version or "0.0.0",
        GoldWriteCategory.NOT_COMMITTED,
    )
    try:
        try:
            prepared = await writer._prepare_write_gold(
                table_name=request.table_name,
                records=request.records,
                mode=request.mode,
                schema=request.schema,
                scd_config=request.scd_config,
                ingestion_ts=request.ingestion_ts,
                contract_version=request.contract_version,
            )
        except Exception as original:
            if isinstance(original, ValueError):
                terminal_status = "validation_failure"
                GOLD_VALIDATION_FAILURES_TOTAL.labels(
                    **_gold_validation_metric_labels(request, original)
                ).inc()
            raise GoldWriteFailure(receipt) from original
        receipt = replace(receipt, category=GoldWriteCategory.UNKNOWN)
        try:
            await writer._dispatch_write(
                _GoldWriteDispatchContext(prepared=prepared, request=request)
            )
        except (GoldWriteFailure, GoldWriteCancelled) as outcome:
            bound = replace(
                outcome.receipt,
                physical_table=request.table_name,
                contract_version=receipt.contract_version,
                committed_targets=(request.table_name,)
                if outcome.receipt.category
                in (
                    GoldWriteCategory.COMPLETE,
                    GoldWriteCategory.COMMITTED_POSTWRITE_PENDING,
                )
                else (),
            )
            raise type(outcome)(bound) from (outcome.__cause__ or outcome)
        except Exception as original:
            raise GoldWriteFailure(receipt) from original
        receipt = replace(
            receipt,
            category=GoldWriteCategory.COMMITTED_POSTWRITE_PENDING,
            committed_targets=(request.table_name,),
        )
        try:
            await writer._post_write_gold(
                _GoldWritePostwriteContext(
                    prepared=prepared,
                    records=request.records,
                    ingestion_ts=request.ingestion_ts,
                    run_id=request.run_id,
                    scd_config=request.scd_config,
                    silver_refs=request.silver_refs,
                    schema=request.schema,
                )
            )
        except asyncio.CancelledError as original:
            raise GoldWriteCancelled(receipt) from original
        except Exception as original:
            raise GoldWriteFailure(receipt) from original
        terminal_status = "success"
        return replace(receipt, category=GoldWriteCategory.COMPLETE)
    except asyncio.CancelledError as original:
        if isinstance(original, GoldWriteCancelled):
            raise
        raise GoldWriteCancelled(receipt) from original
    finally:
        GOLD_WRITE_OUTCOMES_TOTAL.labels(
            **_gold_write_metric_labels(request, status=terminal_status)
        ).inc()
        GOLD_WRITE_DURATION_SECONDS.labels(
            **_gold_write_metric_labels(request, status=terminal_status)
        ).observe(perf_counter() - started_at)


async def _write_dual_targets_impl(
    writer: _GoldWriterHost,
    *,
    request: _GoldWriteRequest,
    schema_policy: GoldSchemaPolicyByVersion,
) -> GoldWriteReceipt:
    """Write all versioned Gold targets and fail on the first error.

    Partial dual-write recovery: track successfully committed targets. When a
    later target fails, surface the committed set in structured logs so operators
    can compensate without silent split-brain (auto-rollback of Delta commits is
    intentionally not attempted here — versions may already be visible).
    """
    assert writer._contract_rollout_policy is not None

    write_versions = writer._contract_rollout_policy.write_versions
    validate_write_versions(write_versions)
    write_targets = get_write_targets(request.table_name, write_versions)
    committed_targets: list[dict[str, str]] = []

    for contract_version, physical_table in iterate_write_targets(
        write_versions, write_targets
    ):
        attempted = False
        try:
            target_schema = schema_policy.for_version(contract_version)
            if target_schema is None:
                raise ValueError(
                    f"No Gold schema configured for contract version {contract_version}"
                )
            target_request = _GoldWriteRequest(
                table_name=physical_table,
                records=_project_records_for_gold_schema(
                    request.records,
                    schema=target_schema,
                ),
                schema=cast("DataFrameSchema", target_schema),
                primary_keys=request.primary_keys,
                mode=request.mode,
                partition_cols=request.partition_cols,
                scd_config=request.scd_config,
                column_order=request.column_order,
                ingestion_ts=request.ingestion_ts,
                run_id=request.run_id,
                silver_refs=request.silver_refs,
                contract_version=contract_version,
            )
            attempted = True
            receipt = await writer._write_single_target(request=target_request)
            _validate_target_receipt(receipt, physical_table, contract_version)
            committed_targets.append(
                {
                    "contract_version": contract_version,
                    "physical_table": physical_table,
                }
            )
        except (Exception, asyncio.CancelledError) as original:
            receipt = _retain_target_failure(
                original, physical_table, contract_version, attempted, committed_targets
            )
            writer.logger.error(
                "gold_dual_write_failed",
                logical_table=request.table_name,
                failed_contract_version=contract_version,
                failed_target_table=physical_table,
                committed_targets=list(committed_targets),
                partial_dual_write=bool(committed_targets),
                recovery_action=(
                    "operator_compensate_committed_targets"
                    if committed_targets
                    else "none"
                ),
                active_contract_version=writer._contract_rollout_policy.active_version,
                write_versions=writer._contract_rollout_policy.write_versions,
            )
            cause: BaseException = original
            if (
                isinstance(original, (GoldWriteFailure, GoldWriteCancelled))
                and original.__cause__ is not None
            ):
                cause = original.__cause__
            if isinstance(original, asyncio.CancelledError):
                raise GoldWriteCancelled(receipt) from cause
            raise GoldWriteFailure(receipt) from cause
    return GoldWriteReceipt(
        request.table_name,
        writer._contract_rollout_policy.active_version,
        GoldWriteCategory.COMPLETE,
        tuple(item["physical_table"] for item in committed_targets),
    )


def _validate_target_receipt(
    receipt: object, physical_table: str, contract_version: str
) -> None:
    """Validate target identity and completeness without manufacturing commit proof."""
    if not isinstance(receipt, GoldWriteReceipt):
        raise TypeError("Gold target must return a GoldWriteReceipt")
    proven = receipt.category in (
        GoldWriteCategory.COMPLETE,
        GoldWriteCategory.COMMITTED_POSTWRITE_PENDING,
    )
    if (
        receipt.physical_table != physical_table
        or receipt.contract_version != contract_version
    ):
        raise TypeError("Gold receipt identity does not match requested target")
    if proven and receipt.committed_targets != (physical_table,):
        raise TypeError("Gold receipt identity does not match requested target")
    if receipt.category != GoldWriteCategory.COMPLETE:
        raise GoldWriteFailure(receipt)


def _retain_target_failure(
    original: BaseException,
    physical_table: str,
    contract_version: str,
    attempted: bool,
    committed_targets: list[dict[str, str]],
) -> GoldWriteReceipt:
    """Retain only proven targets and preserve unknown physical attempts."""
    category = (
        GoldWriteCategory.UNKNOWN if attempted else GoldWriteCategory.NOT_COMMITTED
    )
    receipt = (
        original.receipt
        if isinstance(original, (GoldWriteFailure, GoldWriteCancelled))
        else GoldWriteReceipt(physical_table, contract_version, category)
    )
    if receipt.category in (
        GoldWriteCategory.COMPLETE,
        GoldWriteCategory.COMMITTED_POSTWRITE_PENDING,
    ):
        committed_targets.append(
            {"contract_version": contract_version, "physical_table": physical_table}
        )
    return replace(
        receipt,
        committed_targets=tuple(item["physical_table"] for item in committed_targets),
    )
