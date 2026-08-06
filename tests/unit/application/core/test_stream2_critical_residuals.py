"""Focused unit coverage for stream-2 critical residual fixes."""

from __future__ import annotations

import pytest

from bioetl.application.core.base_transformer._structural_policy_coercion import (
    _coerce_integer_from_string,
)
from bioetl.application.core.batch_transformer_streaming import StreamingBatchProcessor
from bioetl.composition.bootstrap.runtime.pipeline_context_builder import (
    _build_vacuum_config,
)
from bioetl.infrastructure.storage.metadata.metadata_helpers import (
    build_and_validate_metadata,
)
from bioetl.infrastructure.storage.support.retention_dedup import (
    primary_key_sort_key,
    primary_key_tuple,
)

pytestmark = pytest.mark.unit


def test_coerce_integer_rejects_non_finite_decimal_strings() -> None:
    assert _coerce_integer_from_string("NaN", allow_string_coercion=True) is None
    assert _coerce_integer_from_string("Infinity", allow_string_coercion=True) is None
    assert _coerce_integer_from_string("-Infinity", allow_string_coercion=True) is None
    assert _coerce_integer_from_string("42", allow_string_coercion=True) == 42


@pytest.mark.asyncio
async def test_streaming_chunk_size_must_be_positive() -> None:
    class _Stub:
        async def transform_stream(self, records, batch_id, start_index=0):
            raise AssertionError("should not run")

    processor = StreamingBatchProcessor(transformer=_Stub())
    with pytest.raises(ValueError, match="chunk_size"):
        async for _ in processor.process_in_chunks(
            records=[{"a": 1}],
            batch_id="b1",  # type: ignore[arg-type]
            chunk_size=0,
        ):
            pass


def test_metadata_uses_caller_key() -> None:
    assert build_and_validate_metadata("run_id", "abc") == {"run_id": "abc"}


def test_primary_key_sort_key_total_orders_none() -> None:
    rows = [
        {"id": None, "v": 1},
        {"id": "b", "v": 2},
        {"id": "a", "v": 3},
        {"id": None, "v": 4},
    ]
    keys = [primary_key_tuple(row, ("id",)) for row in rows]
    # Must not raise TypeError when ranking mixed None/str PK components.
    ranked = sorted(keys, key=primary_key_sort_key)
    assert ranked[0] == (None,)
    assert ranked[1] == (None,)
    assert {ranked[2], ranked[3]} == {("a",), ("b",)}


def test_vacuum_retention_none_defaults_zero_not_silently_coerced() -> None:
    from types import SimpleNamespace

    options_none = SimpleNamespace(vacuum_after_run=True, vacuum_retention_days=None)
    vacuum_default = _build_vacuum_config(options_none)  # type: ignore[arg-type]
    assert vacuum_default.retention_days == 7

    # Explicit 0 must NOT be rewritten to 7 via ``or``; domain rejects non-positive.
    options_zero = SimpleNamespace(vacuum_after_run=True, vacuum_retention_days=0)
    with pytest.raises(ValueError, match="retention_days must be positive"):
        _build_vacuum_config(options_zero)  # type: ignore[arg-type]
