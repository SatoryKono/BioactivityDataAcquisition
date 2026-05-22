"""Validation operations service for SilverWriter (composition pattern)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal, Protocol, cast

import pyarrow as pa

from bioetl.domain.config import KeyNullabilityRule
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
)
from bioetl.domain.medallion import SilverWriteMode, WriteMode, WriteModePolicy
from bioetl.domain.ports import LoggerPort, MetricsPort, SilverValidatorPort
from bioetl.domain.types import BronzeRecord
from bioetl.domain.value_objects.dq_metrics import SchemaDriftInfo
from bioetl.infrastructure.storage.silver.validation_operations import (
    _build_prepared_silver_write_payload,
    _check_schema_drift,
    _detect_schema_drift,
    _enforce_write_policy,
    _finalize_silver_write_payload,
    _PreparedSilverWritePayload,
    _SilverSchemaPolicyRequest,
    _SilverWritePreparationRequest,
    _sync_validate_and_build_arrow,
    _validate_records,
    _validate_silver_pandera,
    _ValidatedSilverWriteContext,
)


class _SilverPayloadPreparationHostProtocol(Protocol):
    """Shared host contract for Silver payload preparation orchestration."""

    _host: object | None

    def _resolve_table_path(self, table_name: str) -> str: ...

    def _sync_validate_and_build_arrow(
        self,
        request: _SilverWritePreparationRequest,
    ) -> _ValidatedSilverWriteContext: ...


class _SilverPayloadPreparationRuntimeProtocol(Protocol):
    """Runtime host contract used after synchronous validation completes."""

    def _resolve_table_path(self, table_name: str) -> str: ...

    async def _check_schema_drift(
        self,
        table_name: str,
        records: list[BronzeRecord],
        on_schema_mismatch: Literal["error", "evolve", "ignore"],
    ) -> None: ...


def _strict_replay_merge_contract_required(
    runtime_host: object,
) -> bool:
    """Return whether the active Silver write must enforce replay-safe merge guards."""
    coordinator = getattr(runtime_host, "_metadata_coordinator", None)
    run_context = getattr(coordinator, "run_context", None)
    raw_required_profile = getattr(run_context, "required_persistence_profile", "")
    raw_exact_replay = getattr(run_context, "exact_replay", False)
    required_profile = (
        raw_required_profile.strip().lower()
        if isinstance(raw_required_profile, str)
        else ""
    )
    exact_replay = raw_exact_replay if isinstance(raw_exact_replay, bool) else False
    return exact_replay or required_profile in STRICT_PERSISTENCE_PROFILES


def _enforce_replay_safe_merge_contract(
    *,
    runtime_host: object,
    table_name: str,
    validated_mode: SilverWriteMode,
    arrow_data: pa.Table,
) -> None:
    """Fail closed when strict merge replay would otherwise downgrade to full-row updates."""
    if validated_mode != SilverWriteMode.MERGE:
        return
    if not _strict_replay_merge_contract_required(runtime_host):
        return
    if "content_hash" in arrow_data.schema.names:
        return
    raise ValueError(
        "Replay-capable Silver merge requires content_hash in the prepared payload: "
        f"table={table_name}"
    )


def _resolve_payload_runtime_host(
    host: _SilverPayloadPreparationHostProtocol,
) -> _SilverPayloadPreparationRuntimeProtocol:
    """Return the runtime host that owns schema-drift hooks and path resolution."""
    runtime_host = getattr(host, "_host", None)
    if runtime_host is not None:
        return cast(_SilverPayloadPreparationRuntimeProtocol, runtime_host)
    return cast(_SilverPayloadPreparationRuntimeProtocol, host)


async def _prepare_silver_write_payload_impl(
    host: _SilverPayloadPreparationHostProtocol,
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
    """Run the shared Silver payload preparation flow."""
    request = _SilverWritePreparationRequest(
        table_name=table_name,
        records=records,
        primary_keys=primary_keys,
        schema=schema,
        mode=mode,
        column_order=column_order,
        partition_cols=partition_cols,
        key_nullability_rules=key_nullability_rules,
    )

    validated = await asyncio.to_thread(
        host._sync_validate_and_build_arrow,
        request,
    )
    schema_request = _SilverSchemaPolicyRequest(
        table_name=table_name,
        records=validated.records,
        on_schema_mismatch=on_schema_mismatch,
        validated_mode=validated.validated_mode,
        arrow_data=validated.arrow_data,
    )
    runtime_host = _resolve_payload_runtime_host(host)
    _enforce_replay_safe_merge_contract(
        runtime_host=runtime_host,
        table_name=table_name,
        validated_mode=validated.validated_mode,
        arrow_data=validated.arrow_data,
    )
    await runtime_host._check_schema_drift(
        schema_request.table_name,
        schema_request.records,
        schema_request.on_schema_mismatch,
    )
    return _build_prepared_silver_write_payload(
        table_path=runtime_host._resolve_table_path(schema_request.table_name),
        schema_request=schema_request,
    )


class _SilverValidationOperationFacade:
    """Shared validation lifecycle facade for mixin and composition service paths."""

    _host: object | None
    logger: LoggerPort
    _write_policy: WriteModePolicy
    _metrics: MetricsPort | None
    _silver_validator: SilverValidatorPort
    _get_table_schema: Callable[[str], Awaitable[pa.Schema | None]]
    _resolve_table_path: Callable[[str], str]
    _prepare_arrow_data: Callable[..., pa.Table]
    _validate_write_mode: Callable[[str], SilverWriteMode]
    _deduplicate_by_primary_keys: Callable[
        [list[BronzeRecord], list[str]],
        list[BronzeRecord],
    ]
    _to_policy_write_mode: Callable[[SilverWriteMode], WriteMode]
    _validate_key_nullability: Callable[
        [
            list[BronzeRecord],
            list[str],
            list[str] | None,
            list[KeyNullabilityRule] | None,
            str,
        ],
        None,
    ]

    def _sync_validate_and_build_arrow(
        self,
        request: _SilverWritePreparationRequest,
    ) -> _ValidatedSilverWriteContext:
        """Run synchronous Silver validation steps and build Arrow payload."""
        return _sync_validate_and_build_arrow(self, request)

    def _enforce_write_policy(
        self,
        mode: SilverWriteMode,
        table_name: str,
    ) -> None:
        """Enforce write mode policy for Silver layer."""
        _enforce_write_policy(self, mode, table_name)

    def _validate_records(
        self,
        records: list[BronzeRecord],
        table_name: str,
        schema: pa.Schema,
    ) -> None:
        """Validate records have required metadata fields."""
        _validate_records(self, records, table_name, schema)

    def _validate_silver_pandera(
        self,
        records: list[BronzeRecord],
        table_name: str,
    ) -> None:
        """Validate records using Pandera schema before writing to Silver."""
        _validate_silver_pandera(self, records, table_name)

    async def _check_schema_drift(
        self,
        table_name: str,
        records: list[BronzeRecord],
        on_schema_mismatch: Literal["error", "evolve", "ignore"],
    ) -> None:
        """Check schema drift and handle according to configured policy."""
        await _check_schema_drift(self, table_name, records, on_schema_mismatch)

    async def _detect_schema_drift(
        self,
        table_name: str,
        records: list[BronzeRecord],
    ) -> SchemaDriftInfo | None:
        """Detect schema drift between existing table and incoming records."""
        return await _detect_schema_drift(self, table_name, records)

    async def _finalize_silver_write_payload(
        self,
        schema_request: _SilverSchemaPolicyRequest,
    ) -> _PreparedSilverWritePayload:
        """Run schema policy checks and build the final Silver payload."""
        return await _finalize_silver_write_payload(self, schema_request)

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
        """Run full validation chain and prepare Arrow data for write."""
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


@dataclass
class SilverValidationOperations(_SilverValidationOperationFacade):
    """Validation operations service for Silver layer writes.

    This service encapsulates all validation logic previously in SilverWriterValidationMixin,
    following the composition pattern for better separation of concerns and testability.
    """

    logger: LoggerPort
    _write_policy: WriteModePolicy
    _metrics: MetricsPort | None
    _silver_validator: SilverValidatorPort
    _get_table_schema: Callable[[str], Awaitable[pa.Schema | None]]
    _resolve_table_path: Callable[[str], str]
    _prepare_arrow_data: Callable[..., pa.Table]
    _validate_write_mode: Callable[[str], SilverWriteMode]
    _deduplicate_by_primary_keys: Callable[
        [list[BronzeRecord], list[str]],
        list[BronzeRecord],
    ]
    _to_policy_write_mode: Callable[[SilverWriteMode], WriteMode]
    _validate_key_nullability: Callable[
        [
            list[BronzeRecord],
            list[str],
            list[str] | None,
            list[KeyNullabilityRule] | None,
            str,
        ],
        None,
    ]
    _host: object | None = None
