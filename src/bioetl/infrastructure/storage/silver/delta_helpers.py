"""Silver Delta write helpers."""

from __future__ import annotations

import asyncio as asyncio

from bioetl.infrastructure.storage.silver.delta_merge_helpers import (
    ReplaySafeRerunContract,
    _build_content_changed_predicate,
    _build_merge_condition,
    _build_merge_execute_callable,
    _build_merge_update_predicate,
    _delta_table_has_parquet_data,
    _merge_records_with_timeout,
    _MergeExecutionTimeoutError,
    build_replay_safe_rerun_contract,
)
from bioetl.infrastructure.storage.silver.delta_request_models import (
    _build_dispatch_policy,
    _DeltaWriteDispatchPolicy,
    _DeltaWriteHandler,
    _DeltaWriteRequest,
    _dispatch_request_by_mode,
    _dispatch_request_with_domain_errors,
    _raise_domain_write_error,
    _select_dispatch_handler,
)
from bioetl.infrastructure.storage.silver.delta_write_execution import (
    _build_plain_delta_write_kwargs,
    _evolve_delta_schema_with_empty_append,
    _is_duplicate_field_name_schema_error,
    _load_delta_table,
    _write_plain_delta_request,
)

__all__ = [
    "ReplaySafeRerunContract",
    "_DeltaWriteDispatchPolicy",
    "_DeltaWriteHandler",
    "_DeltaWriteRequest",
    "_MergeExecutionTimeoutError",
    "_build_content_changed_predicate",
    "_build_dispatch_policy",
    "_build_merge_condition",
    "_build_merge_execute_callable",
    "_build_merge_update_predicate",
    "_build_plain_delta_write_kwargs",
    "_delta_table_has_parquet_data",
    "_dispatch_request_by_mode",
    "_dispatch_request_with_domain_errors",
    "_evolve_delta_schema_with_empty_append",
    "_is_duplicate_field_name_schema_error",
    "_load_delta_table",
    "_merge_records_with_timeout",
    "_raise_domain_write_error",
    "_select_dispatch_handler",
    "_write_plain_delta_request",
    "asyncio",
    "build_replay_safe_rerun_contract",
]
