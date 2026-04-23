"""Silver layer writer (Delta Lake with merge/upsert)."""

from __future__ import annotations

import asyncio as _asyncio
import time
from collections.abc import Callable, Mapping
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Literal, cast

import pyarrow as pa
from deltalake import DeltaTable as _DeltaTable
from deltalake import write_deltalake as _write_deltalake

from bioetl.domain.config import KeyNullabilityRule
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.medallion import SilverWriteMode, WriteMode, WriteModePolicy
from bioetl.domain.ports import (
    AuditPort,
    MetadataCoordinatorPort,
    MetadataWriterPort,
    MetricsPort,
    SilverValidatorPort,
    TracingPort,
)
from bioetl.domain.services.dq_metrics_calculator import DQMetricsCalculator
from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.export.csv_exporter import CsvExporter
from bioetl.infrastructure.storage.base_delta_writer import (
    BaseDeltaWriter,
)
from bioetl.infrastructure.storage.delta.resilience import (
    SilverMergeResiliencePolicy,
)
from bioetl.infrastructure.storage.silver.compatibility_mixins import (
    SilverWriterDQCompatibilityMixin,
    SilverWriterMergedCompatibilityMixin,
    SilverWriterWriteCompatibilityMixin,
)
from bioetl.infrastructure.storage.silver.finalization_compatibility_mixins import (
    SilverWriterAuditMetadataCompatibilityMixin,
    SilverWriterFinalizationCompatibilityMixin,
)
from bioetl.infrastructure.storage.silver.maintenance_mixin import (
    SilverWriterMaintenanceMixin,
)
from bioetl.infrastructure.storage.silver.operations.postwrite_operations import (
    SilverPostwriteOperations,
)

# SilverWriterValidationMixin removed; validation handled by SilverValidationOperations service
from bioetl.infrastructure.storage.silver.operations.validation_operations import (
    _prepare_silver_write_payload_impl,
    _PreparedSilverWritePayload,
    _SilverWritePreparationRequest,
)

# SilverWriterArrowMixin removed from inheritance (composition pattern)
# Arrow operations now handled by SilverArrowOperations service
# SilverWriterDeltaMixin removed from inheritance (composition pattern)
# Delta operations now handled by SilverDeltaOperations service
# SilverWriterMergedMixin removed from inheritance (composition pattern)
# Merged operations now handled by SilverMergedOperations service
from bioetl.infrastructure.storage.silver.pipeline_helpers import (
    _SilverWriteExecutionContext,
    _SilverWriteInvocation,
    execute_silver_write_with_tracing,
)

# SilverWriterPostwriteMixin removed from inheritance (composition pattern)
# Postwrite operations now handled by SilverPostwriteOperations service
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

# Backward-compatible module aliases for tests patching historical symbols.
asyncio = _asyncio
DeltaTable = _DeltaTable
write_deltalake = _write_deltalake
# Architecture marker imports keep SilverWriter policy/schema hooks discoverable
# in this root module while the implementations live in split validation helpers.

if TYPE_CHECKING:
    from bioetl.domain.ports import LineageStorePort, LoggerPort
    from bioetl.domain.value_objects.silver_result import SilverWriteResult
__all__ = ["SilverWriteMode", "SilverWriter", "_SilverWriteExecutionContext"]

_UTC_OFFSET_SUFFIX = "+00:00"


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
    writer: SilverWriter,
    base_path: str | Path,
    runtime_services: SilverWriterRuntimeServices | None,
    runtime_request: SilverWriterRuntimeServicesRequest,
) -> SilverWriterRuntimeServices:
    """Build runtime services for the writer when callers did not provide them."""
    if runtime_services is not None:
        return runtime_services
    resolved_request = SilverWriterRuntimeServicesRequest(
        csv_exporter=runtime_request.csv_exporter,
        tracing=runtime_request.tracing,
        write_policy=runtime_request.write_policy,
        metrics=runtime_request.metrics,
        audit=runtime_request.audit,
        logger=writer.logger,
        silver_validator=runtime_request.silver_validator,
        metadata_writer=runtime_request.metadata_writer,
        metadata_coordinator=runtime_request.metadata_coordinator,
        lineage_store=runtime_request.lineage_store,
        dq_calculator=runtime_request.dq_calculator,
        merge_resilience_policy=runtime_request.merge_resilience_policy,
        contract_rollout_policy=runtime_request.contract_rollout_policy,
        base_path=base_path,
        pipeline_name=writer._pipeline_name,
    )
    return build_silver_writer_runtime_services(resolved_request)


def _assign_runtime_services(
    writer: SilverWriter,
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


def _rewire_runtime_services(writer: SilverWriter) -> None:
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


def _normalize_iso_datetime(value: datetime | str) -> datetime:
    """Normalize ISO string timestamps into aware datetimes."""
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", _UTC_OFFSET_SUFFIX))
    return value


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


async def _write_single_target(
    writer: SilverWriter,
    *,
    invocation: _SilverWriteInvocation,
) -> SilverWriteResult | None:
    """Execute one physical Silver write target with tracing."""
    started_at, start_perf = datetime.now(UTC), time.perf_counter()
    return await execute_silver_write_with_tracing(
        tracing=writer._tracing,
        module_name=__name__,
        invocation=invocation,
        started_at=started_at,
        start_perf=start_perf,
        execute_pipeline=writer._execute_silver_write_pipeline,
    )


async def _write_dual_targets(
    writer: SilverWriter,
    *,
    invocation: _SilverWriteInvocation,
) -> SilverWriteResult | None:
    """Write all versioned Silver targets and fail the logical write on any error."""
    assert writer._contract_rollout_policy is not None  # guarded by caller

    active_result: SilverWriteResult | None = None
    write_versions = writer._contract_rollout_policy.write_versions

    # Use common functions to reduce duplication
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


class SilverWriter(  # type: ignore[misc]  # Callable vs async-def in MRO
    SilverWriterWriteCompatibilityMixin,
    SilverWriterMergedCompatibilityMixin,
    SilverWriterDQCompatibilityMixin,
    SilverWriterFinalizationCompatibilityMixin,
    SilverWriterAuditMetadataCompatibilityMixin,
    BaseDeltaWriter,
    SilverWriterMaintenanceMixin,
):
    """Writer for Silver layer (normalized data in Delta Lake)."""

    def __setattr__(self, name: str, value: object) -> None:
        """Keep validation service host wiring in sync for direct test assignment."""
        object.__setattr__(self, name, value)
        if name == "_validation" and value is not None and hasattr(value, "_host"):
            object.__setattr__(value, "_host", self)

    def __init__(
        self,
        base_path: str | Path,
        logger: LoggerPort,
        transform_version: str | None = None,
        transform_steps: tuple[str, ...] | None = None,
        runtime_services: SilverWriterRuntimeServices | None = None,
        flat_structure: bool = False,
        pipeline_name: str | None = None,
        **legacy_kwargs: object,
    ) -> None:
        """Initialize Silver writer.

        Args:
            base_path: Root directory for Silver layer Delta Lake tables.
            logger: Structured logger for write events and errors.
            transform_version: Optional version string embedded in Silver metadata.
            transform_steps: Optional tuple of transform step names for lineage.
            runtime_services: Optional grouped runtime collaborators for tracing,
                validation, metadata, DQ, resilience, and optional CSV export.
            flat_structure: When True, omit the table-based subdirectory hierarchy.
            pipeline_name: Optional pipeline name for metric labeling.
        """
        self._pipeline_name = pipeline_name
        runtime_request = _pop_legacy_runtime_kwargs(dict(legacy_kwargs))
        super().__init__(base_path, logger, flat_structure=flat_structure)
        services = _resolve_runtime_services_for_writer(
            writer=self,
            base_path=base_path,
            runtime_services=runtime_services,
            runtime_request=runtime_request,
        )
        _assign_runtime_services(self, services)
        _rewire_runtime_services(self)
        self._transform_version = transform_version
        self._transform_steps = transform_steps or ()
        self._check_schema_drift = _AwaitTrackingAsyncCallable(  # type: ignore[method-assign]
            self._check_schema_drift
        )

    def _should_dual_write(self) -> bool:
        """Return True when rollout policy requires Silver shadow writes."""
        if self._contract_rollout_policy is None:
            return False
        return (
            self._contract_rollout_policy.mode
            in {
                "dual_write",
                "dual_read_write",
            }
            and len(self._contract_rollout_policy.write_versions) > 1
        )

    def _get_dispatch_write_method(
        self,
    ) -> Callable[
        ...,
        Any,  # Any: Bound dispatch methods return backend-specific awaitable payloads.
    ]:
        """Get the dispatch write method from delta operations service or fallback to mixin."""
        if self._delta:
            return self._delta._dispatch_write_with_domain_errors
        else:
            # Fallback to mixin for backward compatibility
            from bioetl.infrastructure.storage.silver.delta_mixin import (
                SilverWriterDeltaMixin,
            )

            return SilverWriterDeltaMixin._dispatch_write_with_domain_errors.__get__(
                self, SilverWriter
            )

    def _enforce_write_policy(
        self,
        mode: SilverWriteMode,
        table_name: str,
    ) -> None:
        """Delegate Silver write-mode enforcement to the validation service."""
        if self._validation:
            self._validation._enforce_write_policy(mode, table_name)
        else:
            # Fallback to mixin for backward compatibility
            from bioetl.infrastructure.storage.silver.validation_mixin import (
                SilverWriterValidationMixin,
            )

            SilverWriterValidationMixin._enforce_write_policy(self, mode, table_name)

    def _sync_validate_and_build_arrow(
        self,
        request: _SilverWritePreparationRequest,
    ) -> _PreparedSilverWritePayload:
        """Delegate arrow validation and building to the validation service."""
        if self._validation:
            return self._validation._sync_validate_and_build_arrow(request)
        else:
            # Fallback to mixin for backward compatibility
            from bioetl.infrastructure.storage.silver.validation_mixin import (
                SilverWriterValidationMixin,
            )

            return SilverWriterValidationMixin._sync_validate_and_build_arrow(
                self, request
            )

    async def _prepare_silver_write_payload(
        self,
        *,
        table_name: str,
        records: list[BronzeRecord],
        primary_keys: list[str],
        schema: pa.Schema,
        mode: str,
        on_schema_mismatch: Literal["error", "evolve", "ignore"],
        column_order: list[str] | None,
        partition_cols: list[str] | None,
        key_nullability_rules: list[KeyNullabilityRule] | None,
    ) -> _PreparedSilverWritePayload:
        """Compatibility seam for payload preparation.

        Tests historically patch writer-level validation hooks directly, so the
        writer keeps this orchestration surface even though the implementation is
        split into operation services.
        """
        return await _prepare_silver_write_payload_impl(
            self,
            table_name=table_name,
            records=records,
            primary_keys=primary_keys,
            schema=schema,
            mode=mode,
            on_schema_mismatch=on_schema_mismatch,
            column_order=column_order,
            partition_cols=partition_cols,
            key_nullability_rules=key_nullability_rules,
        )

    def _validate_write_mode(self, mode: str) -> SilverWriteMode:
        """Delegate write mode validation to the validation service."""
        if self._validation:
            return self._validation._validate_write_mode(mode)
        else:
            # Fallback to mixin for backward compatibility
            from bioetl.infrastructure.storage.silver.validation_mixin import (
                SilverWriterValidationMixin,
            )

            return SilverWriterValidationMixin._validate_write_mode(self, mode)

    def _to_policy_write_mode(self, mode: SilverWriteMode) -> WriteMode:
        """Delegate write mode policy conversion to the validation service."""
        if self._validation:
            return self._validation._to_policy_write_mode(mode)
        else:
            # Fallback to mixin for backward compatibility
            from bioetl.infrastructure.storage.silver.validation_mixin import (
                SilverWriterValidationMixin,
            )

            return SilverWriterValidationMixin._to_policy_write_mode(self, mode)

    async def _write_single_target(
        self,
        *,
        invocation: _SilverWriteInvocation | None = None,
        **legacy_kwargs: object,
    ) -> SilverWriteResult | None:
        """Compatibility seam for direct test patching and dual-write orchestration."""
        resolved_invocation = _coerce_silver_write_invocation(
            invocation=invocation,
            legacy_kwargs=legacy_kwargs,
        )
        return await _write_single_target(
            self,
            invocation=resolved_invocation,
        )

    async def _write_dual_targets(
        self,
        *,
        invocation: _SilverWriteInvocation | None = None,
        **legacy_kwargs: object,
    ) -> SilverWriteResult | None:
        """Compatibility seam for direct test patching and dual-write orchestration."""
        resolved_invocation = _coerce_silver_write_invocation(
            invocation=invocation,
            legacy_kwargs=legacy_kwargs,
            table_key="logical_table_name",
        )
        return await _write_dual_targets(
            self,
            invocation=resolved_invocation,
        )
