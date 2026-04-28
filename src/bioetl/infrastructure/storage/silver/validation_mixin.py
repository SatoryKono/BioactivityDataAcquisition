"""Validation and policy helpers for SilverWriter."""

from __future__ import annotations

__all__ = ["SilverWriterValidationMixin", "_PreparedSilverWritePayload"]

from collections.abc import Awaitable, Callable

import pyarrow as pa

from bioetl.domain.config import KeyNullabilityRule
from bioetl.domain.medallion import SilverWriteMode, WriteMode, WriteModePolicy
from bioetl.domain.ports import LoggerPort, MetricsPort, SilverValidatorPort
from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.storage.silver.operations.validation_operations import (
    _SilverValidationOperationFacade,
)
from bioetl.infrastructure.storage.silver.validation_operations import (
    _deduplicate_by_primary_keys_impl,
    _PreparedSilverWritePayload,
    _to_policy_write_mode_impl,
    _validate_key_nullability_impl,
    _validate_write_mode_impl,
)


class SilverWriterValidationMixin(_SilverValidationOperationFacade):
    """Mixin with write policy and schema validation logic."""

    _host: object | None = None
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


SilverWriterValidationMixin._validate_write_mode = staticmethod(
    _validate_write_mode_impl
)
SilverWriterValidationMixin._deduplicate_by_primary_keys = staticmethod(
    _deduplicate_by_primary_keys_impl
)
SilverWriterValidationMixin._to_policy_write_mode = staticmethod(
    _to_policy_write_mode_impl
)
SilverWriterValidationMixin._validate_key_nullability = staticmethod(
    _validate_key_nullability_impl
)
