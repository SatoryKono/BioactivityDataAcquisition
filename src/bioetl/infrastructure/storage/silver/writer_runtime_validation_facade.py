# pyright: reportUninitializedInstanceVariable=false
# pyright: reportAttributeAccessIssue=false
# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Validation delegation facade for Silver writer runtime methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import pyarrow as pa

from bioetl.domain.config import KeyNullabilityRule
from bioetl.domain.medallion import SilverWriteMode, WriteMode
from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.storage.silver.validation_operations import (
    _PreparedSilverWritePayload,
    _SilverWritePreparationRequest,
    _ValidatedSilverWriteContext,
)
from bioetl.infrastructure.storage.silver.writer_runtime_invocation import (
    _prepare_silver_write_payload_via_validation,
)

if TYPE_CHECKING:
    from bioetl.infrastructure.storage.silver.operations.validation_operations import (
        SilverValidationOperations,
    )

__all__ = ["_SilverWriterRuntimeValidationFacade"]

_SILVER_VALIDATION_OPERATIONS_REQUIRED = "Silver validation operations are required"


class _SilverWriterRuntimeValidationFacade:
    """Validation-service delegation methods for the runtime facade."""

    _validation: SilverValidationOperations | None

    def _enforce_write_policy(self, mode: SilverWriteMode, table_name: str) -> None:
        """Delegate Silver write-mode enforcement to the validation service."""
        if self._validation is None:
            raise RuntimeError(_SILVER_VALIDATION_OPERATIONS_REQUIRED)
        self._validation._enforce_write_policy(mode, table_name)

    def _sync_validate_and_build_arrow(
        self,
        request: _SilverWritePreparationRequest,
    ) -> _ValidatedSilverWriteContext:
        """Delegate arrow validation and building to the validation service."""
        if self._validation is None:
            raise RuntimeError(_SILVER_VALIDATION_OPERATIONS_REQUIRED)
        return self._validation._sync_validate_and_build_arrow(request)

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
        """Prepare a validated Silver payload through the validation service."""
        return await _prepare_silver_write_payload_via_validation(
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
        if self._validation is None:
            raise RuntimeError(_SILVER_VALIDATION_OPERATIONS_REQUIRED)
        return self._validation._validate_write_mode(mode)

    def _to_policy_write_mode(self, mode: SilverWriteMode) -> WriteMode:
        """Delegate write mode policy conversion to the validation service."""
        if self._validation is None:
            raise RuntimeError(_SILVER_VALIDATION_OPERATIONS_REQUIRED)
        return self._validation._to_policy_write_mode(mode)

    def _validate_silver_pandera(
        self,
        records: list[BronzeRecord],
        table_name: str,
    ) -> None:
        """Validate Silver records through the validation service."""
        if self._validation is None:
            raise RuntimeError(_SILVER_VALIDATION_OPERATIONS_REQUIRED)
        self._validation._validate_silver_pandera(records, table_name)

    async def _check_schema_drift(
        self,
        table_name: str,
        records: list[BronzeRecord],
        on_schema_mismatch: Literal["error", "evolve", "ignore"],
    ) -> None:
        """Check schema drift through the validation service."""
        if self._validation is None:
            raise RuntimeError(_SILVER_VALIDATION_OPERATIONS_REQUIRED)
        await self._validation._check_schema_drift(
            table_name, records, on_schema_mismatch
        )
