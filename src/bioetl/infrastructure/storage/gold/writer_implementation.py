"""Write implementation helpers for Gold writer."""

from __future__ import annotations

from time import perf_counter
from typing import TYPE_CHECKING, cast

from bioetl.domain.exceptions import BioETLError
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
) -> None:
    """Execute one physical Gold write target through the standard pipeline."""
    started_at = perf_counter()
    prepared: _PreparedGoldWriteContext | None = None
    terminal_status = "failure"
    GOLD_WRITE_ATTEMPTS_TOTAL.labels(**_gold_write_metric_labels(request)).inc()
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
        await writer._dispatch_write(
            _GoldWriteDispatchContext(
                prepared=prepared,
                request=request,
            )
        )
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
        terminal_status = "success"
    except ValueError as error:
        if prepared is None:
            terminal_status = "validation_failure"
            GOLD_VALIDATION_FAILURES_TOTAL.labels(
                **_gold_validation_metric_labels(request, error)
            ).inc()
        raise
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
) -> None:
    """Write all versioned Gold targets and fail on the first error."""
    from bioetl.infrastructure.storage.gold.pipeline_helpers import (
        GoldWriteRequest,
    )

    assert writer._contract_rollout_policy is not None

    write_versions = writer._contract_rollout_policy.write_versions
    validate_write_versions(write_versions)
    write_targets = get_write_targets(request.table_name, write_versions)

    for contract_version, physical_table in iterate_write_targets(
        write_versions, write_targets
    ):
        target_schema = schema_policy.for_version(contract_version)
        if target_schema is None:
            raise ValueError(
                f"No Gold schema configured for contract version {contract_version}"
            )
        target_request = GoldWriteRequest(
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
        try:
            await writer._write_single_target(request=target_request)
        except (BioETLError, OSError, RuntimeError, ValueError):
            writer.logger.error(
                "gold_dual_write_failed",
                logical_table=request.table_name,
                failed_contract_version=contract_version,
                failed_target_table=physical_table,
                active_contract_version=writer._contract_rollout_policy.active_version,
                write_versions=writer._contract_rollout_policy.write_versions,
            )
            raise
