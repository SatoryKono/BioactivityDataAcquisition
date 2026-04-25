"""Silver layer writer (Delta Lake with merge/upsert)."""

from __future__ import annotations

import asyncio as _asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast

import pyarrow as pa
from deltalake import DeltaTable as _DeltaTable
from deltalake import write_deltalake as _write_deltalake

from bioetl.domain.config import KeyNullabilityRule
from bioetl.domain.medallion import SilverWriteMode, WriteMode
from bioetl.domain.ports import (
    LoggerPort,
)
from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.storage.base_delta_writer import (
    BaseDeltaWriter,
)
from bioetl.infrastructure.storage.silver.compatibility_mixins import (
    SilverWriterDQCompatibilityMixin,
    SilverWriterMergedCompatibilityMixin,
    SilverWriterWriteCompatibilityMixin,
)
from bioetl.infrastructure.storage.silver.delta_helpers import (
    _DeltaWriteRequest,
)
from bioetl.infrastructure.storage.silver.finalization_compatibility_mixins import (
    SilverWriterAuditMetadataCompatibilityMixin,
    SilverWriterFinalizationCompatibilityMixin,
)
from bioetl.infrastructure.storage.silver.maintenance_mixin import (
    SilverWriterMaintenanceMixin,
)

# SilverWriterValidationMixin removed; validation handled by SilverValidationOperations service
from bioetl.infrastructure.storage.silver.operations.validation_operations import (
    _prepare_silver_write_payload_impl,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import TracingPort
    from bioetl.domain.types.contract_rollout import ContractRolloutPolicy
    from bioetl.domain.value_objects.silver_result import SilverWriteResult
    from bioetl.infrastructure.storage.silver.operations.arrow_operations import (
        SilverArrowOperations,
    )
    from bioetl.infrastructure.storage.silver.operations.delta_operations import (
        SilverDeltaOperations,
    )
    from bioetl.infrastructure.storage.silver.operations.maintenance_operations import (
        SilverMaintenanceOperations,
    )
    from bioetl.infrastructure.storage.silver.operations.merged_operations import (
        SilverMergedOperations,
    )
    from bioetl.infrastructure.storage.silver.operations.metadata_operations import (
        SilverMetadataOperations,
    )
    from bioetl.infrastructure.storage.silver.operations.postwrite_operations import (
        SilverPostwriteOperations,
    )
    from bioetl.infrastructure.storage.silver.operations.validation_operations import (
        SilverValidationOperations,
    )
    from bioetl.infrastructure.storage.silver.postwrite_mixin import (
        _SilverWriterPostwriteSelf,
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
)
from bioetl.infrastructure.storage.silver.validation_operations import (
    _PreparedSilverWritePayload,
    _SilverWritePreparationRequest,
    _ValidatedSilverWriteContext,
)
from bioetl.infrastructure.storage.silver.writer_runtime_support import (
    _assign_runtime_services,
    _AwaitTrackingAsyncCallable,
    _coerce_silver_write_invocation,
    _pop_legacy_runtime_kwargs,
    _resolve_runtime_services_for_writer,
    _rewire_runtime_services,
    _write_dual_targets,
    _write_single_target_impl,
)

# Backward-compatible module aliases for tests patching historical symbols.
asyncio = _asyncio
DeltaTable = _DeltaTable
write_deltalake = _write_deltalake
# Architecture marker imports keep SilverWriter policy/schema hooks discoverable
# in this root module while the implementations live in split validation helpers.


__all__ = ["SilverWriteMode", "SilverWriter", "_SilverWriteExecutionContext"]


async def _write_single_target(
    writer: SilverWriter,
    *,
    invocation: _SilverWriteInvocation,
) -> SilverWriteResult | None:
    """Execute one physical Silver write target with root-module tracing seam."""
    return await _write_single_target_impl(
        writer,
        invocation=invocation,
        execute_with_tracing=execute_silver_write_with_tracing,
        module_name=__name__,
    )


class SilverWriter(
    SilverWriterWriteCompatibilityMixin,
    SilverWriterMergedCompatibilityMixin,
    SilverWriterDQCompatibilityMixin,
    SilverWriterFinalizationCompatibilityMixin,
    SilverWriterAuditMetadataCompatibilityMixin,
    BaseDeltaWriter,
    SilverWriterMaintenanceMixin,
):
    """Writer for Silver layer (normalized data in Delta Lake)."""

    _tracing: TracingPort | None
    _contract_rollout_policy: ContractRolloutPolicy | None
    _maintenance: SilverMaintenanceOperations | None
    _metadata: SilverMetadataOperations | None
    _validation: SilverValidationOperations | None
    _delta: SilverDeltaOperations | None
    _arrow: SilverArrowOperations | None
    _merged: SilverMergedOperations | None
    _postwrite: SilverPostwriteOperations | None
    _host: object | None

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
        self._host = self
        object.__setattr__(
            self,
            "_check_schema_drift",
            _AwaitTrackingAsyncCallable(self._check_schema_drift),
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

            SilverWriterValidationMixin._enforce_write_policy(
                cast(SilverWriterValidationMixin, self),
                mode,
                table_name,
            )

    def _sync_validate_and_build_arrow(
        self,
        request: _SilverWritePreparationRequest,
    ) -> _ValidatedSilverWriteContext:
        """Delegate arrow validation and building to the validation service."""
        if self._validation:
            return self._validation._sync_validate_and_build_arrow(request)
        else:
            # Fallback to mixin for backward compatibility
            from bioetl.infrastructure.storage.silver.validation_mixin import (
                SilverWriterValidationMixin,
            )

            return SilverWriterValidationMixin._sync_validate_and_build_arrow(
                cast(SilverWriterValidationMixin, self), request
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

            return SilverWriterValidationMixin._validate_write_mode(mode)

    def _to_policy_write_mode(self, mode: SilverWriteMode) -> WriteMode:
        """Delegate write mode policy conversion to the validation service."""
        if self._validation:
            return self._validation._to_policy_write_mode(mode)
        else:
            # Fallback to mixin for backward compatibility
            from bioetl.infrastructure.storage.silver.validation_mixin import (
                SilverWriterValidationMixin,
            )

            return SilverWriterValidationMixin._to_policy_write_mode(mode)

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

    async def _dispatch_write_with_domain_errors(
        self,
        *,
        table_name: str,
        request: _DeltaWriteRequest,
    ) -> None:
        """Dispatch Delta write through runtime services or legacy mixin fallback."""
        if self._delta is not None:
            await self._delta._dispatch_write_with_domain_errors(
                table_name=table_name,
                request=request,
            )
            return

        from bioetl.infrastructure.storage.silver.delta_mixin import (
            SilverWriterDeltaMixin,
        )

        await SilverWriterDeltaMixin._dispatch_write_with_domain_errors(
            cast(SilverWriterDeltaMixin, self),
            table_name=table_name,
            request=request,
        )

    async def _complete_silver_write_pipeline(
        self,
        *,
        ctx: _SilverWriteExecutionContext,
        payload: _PreparedSilverWritePayload,
    ) -> SilverWriteResult | None:
        """Run postwrite finalization through services or legacy mixin fallback."""
        if self._postwrite is not None:
            return await self._postwrite._complete_silver_write_pipeline(
                ctx=ctx,
                payload=payload,
            )

        from bioetl.infrastructure.storage.silver.postwrite_mixin import (
            SilverWriterPostwriteMixin,
        )

        return await SilverWriterPostwriteMixin._complete_silver_write_pipeline(
            cast("_SilverWriterPostwriteSelf", self),
            ctx=ctx,
            payload=payload,
        )
