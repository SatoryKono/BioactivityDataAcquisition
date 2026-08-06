"""Focused unit coverage for stream-2 critical residual fixes."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bioetl.application.core.base_transformer._structural_policy_coercion import (
    _coerce_integer_from_string,
)
from bioetl.application.core.batch_transformer_streaming import StreamingBatchProcessor
from bioetl.composition.bootstrap.runtime.pipeline_context_builder import (
    _build_vacuum_config,
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


def test_vacuum_retention_none_defaults_zero_not_silently_coerced() -> None:
    options_none = SimpleNamespace(vacuum_after_run=True, vacuum_retention_days=None)
    vacuum_default = _build_vacuum_config(options_none)  # type: ignore[arg-type]
    assert vacuum_default.retention_days == 7

    # Explicit 0 must NOT be rewritten to 7 via or; domain rejects non-positive.
    options_zero = SimpleNamespace(vacuum_after_run=True, vacuum_retention_days=0)
    with pytest.raises(ValueError, match="retention_days must be positive"):
        _build_vacuum_config(options_zero)  # type: ignore[arg-type]
