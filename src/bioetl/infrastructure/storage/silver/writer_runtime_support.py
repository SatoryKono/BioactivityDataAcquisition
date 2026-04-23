"""Runtime and dispatch helpers for ``SilverWriter``."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Protocol, cast

from bioetl.domain.exceptions import BioETLError
from bioetl.domain.medallion import WriteModePolicy
from bioetl.domain.ports import (
    AuditPort,
    LineageStorePort,
    LoggerPort,
    MetadataCoordinatorPort,
    MetadataWriterPort,
    MetricsPort,
    SilverValidatorPort,
    TracingPort,
)
from bioetl.domain.services.dq_metrics_calculator import DQMetricsCalculator
from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.export.csv_exporter import CsvExporter
from bioetl.infrastructure.storage.delta.resilience import (
    SilverMergeResiliencePolicy,
)
from bioetl.infrastructure.storage.silver.operations.postwrite_operations import (
    SilverPostwriteOperations,
)
from bioetl.infrastructure.storage.silver.pipeline_helpers import _SilverWriteInvocation
from bioetl.infrastructure.storage.silver.runtime_helpers import (
    SilverWriterRuntimeServices,
    SilverWriterRuntimeServicesRequest,
    build_silver_writer_runtime_services,
)
from bioetl.infrastructure.storage.writer_common import (
    get_write_targets,
    iterate_write_targets,
    validate_write_versions,
)


class _AwaitTrackingAsyncCallable:
    """Tiny await-tracking proxy for compatibility seams used in tests."""

    def __init__(self, func: Callable[..., object]) -> None:
        self._func = func
        self.await_count = 0
        self.await_args: SimpleNamespace | None = None

    async def __call__(self, *args: object, **kwargs: object) -> object:
        self.await_count += 1
        self.await_args = SimpleNamespace(args=args, kwargs=kwargs)
        result = self._func(*args, **kwargs)
        if hasattr(result, "__await__"):
            return await result  # type: ignore[misc]
        return result

    def assert_awaited_once_with(self, *args: object, **kwargs: object) -> None:
        if self.await_count != 1:
            raise AssertionError(f"Expected one await, observed {self.await_count}")
        actual = self.await_args
        if actual is None or actual.args != args or actual.kwargs != kwargs:
            raise AssertionError(
                f"Await args mismatch: expected args={args}, kwargs={kwargs}; "
                f"got args={getattr(actual, 'args', None)}, "
                f"kwargs={getattr(actual, 'kwargs', None)}"
            )


class _SilverWriterDispatchHost(Protocol):
    """Minimal SilverWriter surface required by runtime helpers."""

    logger: LoggerPort | None
    _pipeline_name: str | None
    _tracing: TracingPort | None
    _contract_rollout_policy: WriteModePolicy | None

    async def _execute_silver_write_pipeline(self, **kwargs: object): ...

    async def _write_single_target(self, **kwargs: object): ...


def _pop_legacy_runtime_kwargs(
    legacy_kwargs: dict[str, object],
) -> SilverWriterRuntimeServicesRequest:
    """Translate historical SilverWriter kwargs into a runtime-services request."""
    csv_exporter = cast("CsvExporter | None", legacy_kwargs.pop("csv_exporter", None))
    tracing = cast("TracingPort | None", legacy_kwargs.pop("tracing", None))
    write_policy = cast(
        "WriteModePolicy | None",
        legacy_kwargs.pop("write_policy", None),
    )
    metrics = cast("MetricsPort | None", legacy_kwargs.pop("metrics", None))
    audit = cast("AuditPort | None", legacy_kwargs.pop("audit", None))
    silver_validator = cast(
        "SilverValidatorPort | None",
        legacy_kwargs.pop("silver_validator", None),
    )
    metadata_writer = cast(
        "MetadataWriterPort | None",
        legacy_kwargs.pop("metadata_writer", None),
    )
    metadata_coordinator = cast(
        "MetadataCoordinatorPort | None",
        legacy_kwargs.pop("metadata_coordinator", None),
    )
    lineage_store = cast(
        "LineageStorePort | None",
        legacy_kwargs.pop("lineage_store", None),
    )
    dq_calculator = cast(
        "DQMetricsCalculator | None",
        legacy_kwargs.pop("dq_calculator", None),
    )
    merge_resilience_policy = cast(
        "SilverMergeResiliencePolicy | None",
        legacy_kwargs.pop("merge_resilience_policy", None),
    )
    if legacy_kwargs:
        unexpected = ", ".join(sorted(legacy_kwargs))
        raise TypeError(f"Unexpected SilverWriter options: {unexpected}")
    return SilverWriterRuntimeServicesRequest(
        csv_exporter=csv_exporter,
        tracing=tracing,
        write_policy=write_policy,
        metrics=metrics,
        audit=audit,
        logger=None,
        silver_validator=silver_validator,
        metadata_writer=metadata_writer,
        metadata_coordinator=metadata_coordinator,
        lineage_store=lineage_store,
        dq_calculator=dq_calculator,
        merge_resilience_policy=merge_resilience_policy,
    )


def _resolve_runtime_services_for_writer(
    *,
    writer: _SilverWriterDispatchHost,
    base_path: str | Path,
    runtime_services: SilverWriterRuntimeServices | None,
    runtime_request: SilverWriterRuntimeServicesRequest,
) -> SilverWriterRuntimeServices:
    """Build runtime services for the writer when callers did not provide them."""
    if runtime_services is not None:
        return runtime_services
    resolved_request = cast(
        "SilverWriterRuntimeServicesRequest",
        replace(
            runtime_request,
            logger=writer.logger,
            base_path=base_path,
            pipeline_name=writer._pipeline_name,
        ),
    )
    return build_silver_writer_runtime_services(request=resolved_request)


def _assign_runtime_services(
    writer: Any,
    services: SilverWriterRuntimeServices,
) -> None:
    """Copy grouped runtime collaborators onto the writer instance."""
    writer.csv_exporter = services.csv_exporter
    writer._metrics = services.metrics
    writer._audit = services.audit
    writer._tracing = services.tracing
    writer._write_policy = services.write_policy
    writer._silver_validator = services.silver_validator
    writer._metadata_writer = services.metadata_writer
    writer._metadata_coordinator = services.metadata_coordinator
    writer._lineage_store = services.lineage_store
    writer._dq_calculator = services.dq_calculator
    writer._merge_resilience_policy = services.merge_resilience_policy
    writer._contract_rollout_policy = services.contract_rollout_policy
    writer._maintenance = services.maintenance_operations
    writer._metadata = services.metadata_operations
    writer._validation = services.validation_operations
    writer._delta = services.delta_operations
    writer._arrow = services.arrow_operations
    writer._merged = services.merged_operations
    writer._postwrite = services.postwrite_operations


def _rewire_runtime_services(writer: Any) -> None:
    """Bind runtime collaborators that need the fully initialized writer instance."""
    if writer._merged is not None:
        writer._merged = replace(
            writer._merged,
            _write_silver_merged_metadata=writer._write_silver_merged_metadata,
        )
    if writer._validation is not None:
        writer._validation = replace(
            writer._validation,
            _get_table_schema=writer._get_table_schema,
        )
    if writer._postwrite is None:
        writer._postwrite = SilverPostwriteOperations(writer)
    if writer._metadata is not None:
        writer._metadata = replace(writer._metadata, _host=writer)


def _project_records_for_contract_version(
    records: list[BronzeRecord],
    *,
    contract_version: str,
) -> list[BronzeRecord]:
    """Project write-time content hash for one target contract version."""
    projected_records: list[BronzeRecord] = []
    for record in records:
        versioned_hashes = record.get("_content_hashes_by_version")
        projected = dict(record)
        if isinstance(versioned_hashes, dict):
            selected_hash = versioned_hashes.get(contract_version)
            if selected_hash is not None:
                projected["content_hash"] = selected_hash
        projected.pop("_content_hashes_by_version", None)
        projected_records.append(projected)
    return projected_records


def _coerce_silver_write_invocation(
    *,
    invocation: _SilverWriteInvocation | None,
    legacy_kwargs: Mapping[str, object],
    table_key: str = "table_name",
) -> _SilverWriteInvocation:
    """Accept the canonical invocation object while preserving legacy kwargs."""
    if invocation is not None:
        if legacy_kwargs:
            unexpected = ", ".join(sorted(legacy_kwargs))
            raise TypeError(
                "unexpected legacy keyword arguments when invocation is provided: "
                f"{unexpected}"
            )
        return invocation

    payload = dict(legacy_kwargs)
    if (
        table_key != "table_name"
        and table_key in payload
        and "table_name" not in payload
    ):
        payload["table_name"] = payload.pop(table_key)
    return _SilverWriteInvocation(**payload)  # type: ignore[arg-type]


async def _write_single_target_impl(
    writer: _SilverWriterDispatchHost,
    *,
    invocation: _SilverWriteInvocation,
    execute_with_tracing,
    module_name: str,
):
    """Execute one physical Silver write target with tracing."""
    started_at, start_perf = datetime.now(UTC), time.perf_counter()
    return await execute_with_tracing(
        tracing=writer._tracing,
        module_name=module_name,
        invocation=invocation,
        started_at=started_at,
        start_perf=start_perf,
        execute_pipeline=writer._execute_silver_write_pipeline,
    )


async def _write_dual_targets(
    writer: _SilverWriterDispatchHost,
    *,
    invocation: _SilverWriteInvocation,
):
    """Write all versioned Silver targets and fail the logical write on any error."""
    assert writer._contract_rollout_policy is not None

    active_result = None
    write_versions = writer._contract_rollout_policy.write_versions
    validate_write_versions(write_versions)
    write_targets = get_write_targets(invocation.table_name, write_versions)

    for contract_version, physical_table in iterate_write_targets(
        write_versions, write_targets
    ):
        try:
            result = await writer._write_single_target(
                table_name=physical_table,
                records=_project_records_for_contract_version(
                    invocation.records,
                    contract_version=contract_version,
                ),
                primary_keys=invocation.primary_keys,
                schema=invocation.schema,
                mode=invocation.mode,
                partition_cols=invocation.partition_cols,
                on_schema_mismatch=invocation.on_schema_mismatch,
                column_order=invocation.column_order,
                bronze_refs=invocation.bronze_refs,
                key_nullability_rules=invocation.key_nullability_rules,
                run_id=invocation.run_id,
                run_type=invocation.run_type,
                source_batch_id=invocation.source_batch_id,
                ingestion_ts=invocation.ingestion_ts,
                quarantined_count=invocation.quarantined_count,
                validation_errors=invocation.validation_errors,
            )
        except (BioETLError, OSError, RuntimeError, ValueError) as exc:
            writer.logger.error(
                "silver_dual_write_failed",
                logical_table=invocation.table_name,
                failed_contract_version=contract_version,
                failed_target_table=physical_table,
                active_contract_version=writer._contract_rollout_policy.active_version,
                write_versions=writer._contract_rollout_policy.write_versions,
                error_type=type(exc).__name__,
            )
            raise
        if contract_version == writer._contract_rollout_policy.active_version:
            active_result = result
    return active_result
