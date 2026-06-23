"""Unit tests for ChEMBL multi-filter fetch mixin."""

from __future__ import annotations

import importlib.util
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]


def _load_fetch_multi_filter_mixin() -> type:
    module_path = (
        Path(__file__).resolve().parents[6]
        / "src"
        / "bioetl"
        / "infrastructure"
        / "adapters"
        / "chembl"
        / "fetch_multi_filter_mixin.py"
    )
    spec = importlib.util.spec_from_file_location(
        "_test_fetch_multi_filter_mixin_module",
        module_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ChemblFetchMultiFilterMixin


ChemblFetchMultiFilterMixin = _load_fetch_multi_filter_mixin()


class _TestChemblFetchMultiFilterAdapter(ChemblFetchMultiFilterMixin):
    """Minimal stub exercising mixin behavior without full adapter wiring."""

    def __init__(self) -> None:
        self._filter_batch_size = 8
        self._logger = MagicMock()
        self._mapper = SimpleNamespace(
            get_resource_url=lambda entity_type: f"https://example.test/{entity_type}"
        )
        self.projected_lengths: list[int] = []
        self.page_responses: list[tuple[list[dict[str, object]], bool]] = []
        self.fetch_calls: list[tuple[str, dict[str, object], str]] = []
        self.loop_calls: list[tuple[str, dict[str, str], str, str, set[str]]] = []

    def _build_params(self, offset: int, entity_type: str) -> dict[str, object]:
        return {"offset": offset, "entity_type": entity_type}

    def _build_filter_in_params(
        self, filters: dict[str, list[str] | str]
    ) -> dict[str, str]:
        params: dict[str, str] = {}
        for key, value in filters.items():
            if isinstance(value, list):
                params[f"{key}__in"] = ",".join(value)
            else:
                params[f"{key}__in"] = value
        return params

    def _get_projected_url_length(self, url: str, params: dict[str, object]) -> int:
        assert url.startswith("https://example.test/")
        assert "entity_type" in params
        return self.projected_lengths.pop(0)

    def _get_api_pk_field(self, entity_type: str) -> str:
        return "chembl_id"

    def _normalize_filter_field(self, entity_type: str, filter_field: str) -> str:
        return f"api_{filter_field}"

    def _batch_ids(self, ids: list[str], batch_size: int) -> Iterator[list[str]]:
        for start in range(0, len(ids), batch_size):
            yield ids[start : start + batch_size]

    async def _fetch_page(
        self, url: str, params: dict[str, object], entity_type: str
    ) -> tuple[list[dict[str, object]], bool]:
        self.fetch_calls.append((url, params.copy(), entity_type))
        return self.page_responses.pop(0)

    def _is_duplicate_record(
        self,
        record: dict[str, object],
        pk_field: str,
        seen_ids: set[str],
        entity_type: str,
    ) -> bool:
        pk = str(record.get(pk_field, ""))
        if not pk:
            return False
        if pk in seen_ids:
            return True
        seen_ids.add(pk)
        return False


def _collect_ids(records: list[dict[str, object]]) -> list[str]:
    return [str(record["chembl_id"]) for record in records]


def test_determine_multi_filter_batch_size_keeps_size_when_url_fits() -> None:
    adapter = _TestChemblFetchMultiFilterAdapter()
    adapter._filter_batch_size = 4
    adapter.projected_lengths = [900]

    batch_size = adapter._determine_multi_filter_batch_size(
        "https://example.test/activity",
        {"molecule": ["A", "B", "C"]},
        "activity",
    )

    assert batch_size == 4
    adapter._logger.info.assert_not_called()


def test_determine_multi_filter_batch_size_returns_one_without_projection_checks() -> (
    None
):
    adapter = _TestChemblFetchMultiFilterAdapter()
    adapter._filter_batch_size = 1

    batch_size = adapter._determine_multi_filter_batch_size(
        "https://example.test/activity",
        {"molecule": ["A", "B"]},
        "activity",
    )

    assert batch_size == 1
    assert adapter.projected_lengths == []
    adapter._logger.info.assert_not_called()


def test_determine_multi_filter_batch_size_halves_until_url_fits() -> None:
    adapter = _TestChemblFetchMultiFilterAdapter()
    adapter.projected_lengths = [1400, 1200, 900]

    batch_size = adapter._determine_multi_filter_batch_size(
        "https://example.test/activity",
        {"molecule": ["A", "B", "C", "D"], "target": ["T1", "T2", "T3", "T4"]},
        "activity",
    )

    assert batch_size == 2
    assert adapter._logger.info.call_count == 2


@pytest.mark.asyncio
async def test_fetch_multi_filter_page_loop_paginates_and_deduplicates() -> None:
    adapter = _TestChemblFetchMultiFilterAdapter()
    adapter.page_responses = [
        ([{"chembl_id": "1"}, {"chembl_id": "2"}], True),
        ([{"chembl_id": "2"}, {"chembl_id": "3"}], False),
    ]

    records = [
        record
        async for record in adapter._fetch_multi_filter_page_loop(
            "https://example.test/activity",
            {"molecule__in": "CHEMBL1,CHEMBL2"},
            "activity",
            "chembl_id",
            set(),
        )
    ]

    assert _collect_ids(records) == ["1", "2", "3"]
    assert adapter.fetch_calls == [
        (
            "https://example.test/activity",
            {
                "offset": 0,
                "entity_type": "activity",
                "molecule__in": "CHEMBL1,CHEMBL2",
            },
            "activity",
        ),
        (
            "https://example.test/activity",
            {
                "offset": 2,
                "entity_type": "activity",
                "molecule__in": "CHEMBL1,CHEMBL2",
            },
            "activity",
        ),
    ]


@pytest.mark.asyncio
async def test_fetch_multi_filter_page_loop_stops_when_page_is_empty() -> None:
    adapter = _TestChemblFetchMultiFilterAdapter()
    adapter.page_responses = [([], True)]

    records = [
        record
        async for record in adapter._fetch_multi_filter_page_loop(
            "https://example.test/activity",
            {"molecule__in": "CHEMBL1"},
            "activity",
            "chembl_id",
            set(),
        )
    ]

    assert records == []
    assert adapter.fetch_calls == [
        (
            "https://example.test/activity",
            {
                "offset": 0,
                "entity_type": "activity",
                "molecule__in": "CHEMBL1",
            },
            "activity",
        )
    ]


@pytest.mark.asyncio
async def test_fetch_multi_filtered_returns_nothing_for_empty_filters() -> None:
    adapter = _TestChemblFetchMultiFilterAdapter()

    records = [
        record
        async for record in adapter.fetch_multi_filtered("activity", {}, limit=None)
    ]

    assert records == []
    assert adapter.loop_calls == []


@pytest.mark.asyncio
async def test_fetch_multi_filtered_batches_filters_and_honors_limit() -> None:
    adapter = _TestChemblFetchMultiFilterAdapter()
    adapter._filter_batch_size = 2
    adapter.projected_lengths = [800]

    async def _fake_page_loop(
        url: str,
        filter_params: dict[str, str],
        entity_type: str,
        pk_field: str,
        seen_ids: set[str],
    ) -> AsyncIterator[dict[str, object]]:
        adapter.loop_calls.append(
            (url, filter_params.copy(), entity_type, pk_field, set(seen_ids))
        )
        for value in filter_params.values():
            for item in value.split(","):
                yield {"chembl_id": item, "filters": filter_params.copy()}

    adapter._fetch_multi_filter_page_loop = _fake_page_loop  # type: ignore[method-assign]

    records = [
        record
        async for record in adapter.fetch_multi_filtered(
            "activity",
            {
                "molecule": ["M1", "M2", "M3"],
                "target": ["T1", "T2", "T3"],
            },
            limit=3,
        )
    ]

    assert _collect_ids(records) == ["M1", "M2", "T1"]
    assert len(adapter.loop_calls) == 1

    loop_url, loop_params, loop_entity_type, loop_pk_field, loop_seen = (
        adapter.loop_calls[0]
    )
    assert loop_url == "https://example.test/activity"
    assert loop_entity_type == "activity"
    assert loop_pk_field == "chembl_id"
    assert loop_seen == set()
    assert loop_params == {
        "api_molecule__in": "M1,M2",
        "api_target__in": "T1,T2",
    }


@pytest.mark.asyncio
async def test_fetch_multi_filtered_exhausts_all_batch_combinations_without_limit() -> (
    None
):
    adapter = _TestChemblFetchMultiFilterAdapter()
    adapter._filter_batch_size = 2
    adapter.projected_lengths = [800]

    async def _fake_page_loop(
        url: str,
        filter_params: dict[str, str],
        entity_type: str,
        pk_field: str,
        seen_ids: set[str],
    ) -> AsyncIterator[dict[str, object]]:
        adapter.loop_calls.append(
            (url, filter_params.copy(), entity_type, pk_field, set(seen_ids))
        )
        molecule_ids = filter_params["api_molecule__in"].split(",")
        target_ids = filter_params["api_target__in"].split(",")
        if molecule_ids == ["M3"] and target_ids == ["T3"]:
            return
        yield {
            "chembl_id": f"{molecule_ids[0]}:{target_ids[0]}",
            "filters": filter_params.copy(),
        }

    adapter._fetch_multi_filter_page_loop = _fake_page_loop  # type: ignore[method-assign]

    records = [
        record
        async for record in adapter.fetch_multi_filtered(
            "activity",
            {
                "molecule": ["M1", "M2", "M3"],
                "target": ["T1", "T2", "T3"],
            },
            limit=None,
        )
    ]

    assert _collect_ids(records) == ["M1:T1", "M1:T3", "M3:T1"]
    assert [call[1] for call in adapter.loop_calls] == [
        {"api_molecule__in": "M1,M2", "api_target__in": "T1,T2"},
        {"api_molecule__in": "M1,M2", "api_target__in": "T3"},
        {"api_molecule__in": "M3", "api_target__in": "T1,T2"},
        {"api_molecule__in": "M3", "api_target__in": "T3"},
    ]
