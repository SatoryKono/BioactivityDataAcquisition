"""Focused unit coverage for stream-2 critical residual fixes."""

from __future__ import annotations

from typing import Any, cast

import pytest

from bioetl.application.core.base_transformer._structural_policy_coercion import (
    _coerce_integer_from_string,
)
from bioetl.application.core.batch_transformer_streaming import StreamingBatchProcessor
from bioetl.domain.types.identifiers import BatchID
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

pytestmark = pytest.mark.unit


def test_coerce_integer_rejects_non_finite_decimal_strings() -> None:
    assert _coerce_integer_from_string("NaN", allow_string_coercion=True) is None
    assert _coerce_integer_from_string("Infinity", allow_string_coercion=True) is None
    assert _coerce_integer_from_string("-Infinity", allow_string_coercion=True) is None
    assert _coerce_integer_from_string("42", allow_string_coercion=True) == 42


@pytest.mark.asyncio
async def test_streaming_chunk_size_must_be_positive() -> None:
    class _Stub:
        async def transform_stream(
            self,
            records: object,
            batch_id: object,
            start_index: int = 0,
        ) -> None:
            _ = (records, batch_id, start_index)
            raise AssertionError("should not run")

    processor = StreamingBatchProcessor(transformer=cast(Any, _Stub()))
    with pytest.raises(ValueError, match="chunk_size"):
        async for _ in processor.process_in_chunks(
            records=[{"a": 1}],
            batch_id=BatchID(deterministic_uuid_from_callsite("streaming-chunk")),
            chunk_size=0,
        ):
            pass
