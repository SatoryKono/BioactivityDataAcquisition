# pyright: reportArgumentType=false
"""S3 record-quarantine-fetch residual coverage (#7772-#7847 pack)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core._fetch_forwarding import (
    _UNSET_FETCH_ARG,
    _FetchArgSentinel,
    build_forwarded_fetch_kwargs,
)
from bioetl.application.core._filtered_data_source_fetch_support import fetch_records
from bioetl.application.core._quarantine_write_support import (
    write_quarantine_requests_with_events,
)
from bioetl.application.core.normalization_fallbacks import __all__ as FALLBACK_ALL
from bioetl.domain.types import BatchID, RunID
from tests.helpers.deterministic_ids import deterministic_batch_uuid
from datetime import datetime, timezone

pytestmark = pytest.mark.unit


def test_fetch_arg_sentinel_is_enum_member() -> None:
    assert isinstance(_UNSET_FETCH_ARG, _FetchArgSentinel)
    kwargs = build_forwarded_fetch_kwargs(entity_type="activity")
    assert "filter_ids" not in kwargs
    assert "filter_field" not in kwargs
    kwargs2 = build_forwarded_fetch_kwargs(
        entity_type="activity",
        filter_ids=["a"],
        filter_field="id",
    )
    assert kwargs2["filter_ids"] == ["a"]
    assert kwargs2["filter_field"] == "id"


def test_normalize_plain_text_exported() -> None:
    assert "normalize_plain_text" in FALLBACK_ALL


@dataclass
class _FetchState:
    _data_source: Any
    _filter_config: Any
    _filter_ids: list[str] | None = None
    _multi_filter_ids: dict[str, list[str]] | None = None
    _valid_combinations: frozenset[tuple[str, ...]] | None = None
    _filter_fields: tuple[str, ...] | None = None
    _fallback_mapping: dict[str, str] | None = None
    ensure_calls: list[str] = field(default_factory=list)

    def _ensure_filterable_adapter(self, mode: str) -> None:
        self.ensure_calls.append(mode)


class _AsyncRecords:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def __aiter__(self):
        self._iter = iter(self._rows)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


@pytest.mark.asyncio
async def test_fetch_records_dispatches_multi_single_and_unfiltered() -> None:
    class _Cfg:
        enabled = True
        filter_field = "assay_id"

    class _DS:
        def __init__(self) -> None:
            self.calls: list[str] = []

        async def fetch_multi_filtered(self, **kwargs):  # type: ignore[no-untyped-def]
            self.calls.append("multi")
            async for row in _AsyncRecords([{"assay_id": "A1", "x": 1}]):
                yield row

        async def fetch_filtered(self, **kwargs):  # type: ignore[no-untyped-def]
            self.calls.append("single")
            async for row in _AsyncRecords([{"assay_id": "A2"}]):
                yield row

        async def fetch(self, **kwargs):  # type: ignore[no-untyped-def]
            self.calls.append("plain")
            async for row in _AsyncRecords([{"id": 1}]):
                yield row

    ds = _DS()

    multi_state = _FetchState(
        _data_source=ds,
        _filter_config=_Cfg(),
        _multi_filter_ids={"assay_id": ["A1"]},
        _valid_combinations=frozenset({("A1",)}),
        _filter_fields=("assay_id",),
    )
    rows = [r async for r in fetch_records(multi_state, "activity", limit=5)]
    assert rows and ds.calls[-1] == "multi"

    single_state = _FetchState(
        _data_source=ds,
        _filter_config=_Cfg(),
        _filter_ids=["A2"],
    )
    rows = [r async for r in fetch_records(single_state, "activity", limit=5)]
    assert rows and ds.calls[-1] == "single"

    class _Disabled:
        enabled = False
        filter_field = None

    plain_state = _FetchState(_data_source=ds, _filter_config=_Disabled())
    rows = [r async for r in fetch_records(plain_state, "activity", limit=5)]
    assert rows and ds.calls[-1] == "plain"


@pytest.mark.asyncio
async def test_write_quarantine_requests_rejects_length_mismatch() -> None:
    quarantine = AsyncMock()
    with pytest.raises(ValueError, match="equal lengths"):
        await write_quarantine_requests_with_events(
            quarantine=quarantine,
            requests=[{"pipeline": "p", "error_code": "E", "payload": {}, "bronze_batch_id": deterministic_batch_uuid("s3-rqf-residual-1"), "ingestion_ts": datetime.now(timezone.utc)}],  # type: ignore[list-item]
            emitter=None,
            pipeline_name="p",
            error_codes=("E", "E2"),
            error_messages=("m",),
            batch_id=deterministic_batch_uuid("s3-rqf-residual-2"),
            run_id=None,
            ingestion_ts=datetime.now(timezone.utc),
        )
    quarantine.write_many.assert_not_called()
