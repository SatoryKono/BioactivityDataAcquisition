"""Compound-record AND filtering must not multiply remote batch counts."""

from types import SimpleNamespace

import pytest

from bioetl.infrastructure.adapters.chembl.fetch_multi_filter_mixin import (
    ChemblFetchMultiFilterMixin,
)


class Adapter(ChemblFetchMultiFilterMixin):
    _filter_batch_size = 2
    _mapper = SimpleNamespace(
        get_resource_url=lambda entity: "https://example.test/records"
    )

    def __init__(self):
        self.calls = []
        self.records = [
            {"record_id": 1, "molecule_chembl_id": "M1", "document_chembl_id": "D1"},
            {"record_id": 2, "molecule_chembl_id": "M2", "document_chembl_id": "D1"},
            {"record_id": 3, "molecule_chembl_id": "M3", "document_chembl_id": "D2"},
            {
                "record_id": 4,
                "molecule_chembl_id": "OUTSIDE",
                "document_chembl_id": "D1",
            },
            {
                "record_id": 5,
                "molecule_chembl_id": "M1",
                "document_chembl_id": "OUTSIDE",
            },
        ]

    def _get_api_pk_field(self, entity):
        return "record_id"

    def _normalize_filter_field(self, entity, key):
        return {
            "molecule_id": "molecule_chembl_id",
            "publication_id": "document_chembl_id",
        }.get(key, key)

    def _build_params(self, offset, entity):
        return {"offset": offset}

    def _get_projected_url_length(self, url, params):
        return 100

    def _build_filter_in_params(self, filters):
        return {key + "__in": ",".join(values) for key, values in filters.items()}

    def _batch_ids(self, values, size):
        return [values[index : index + size] for index in range(0, len(values), size)]

    async def _fetch_page(self, url, params, entity):
        self.calls.append(params)
        conditions = {
            key[:-4]: set(value.split(","))
            for key, value in params.items()
            if key.endswith("__in")
        }
        selected = [
            record
            for record in self.records
            if all(record.get(key) in values for key, values in conditions.items())
        ]
        offset = params["offset"]
        # Exercise real pagination as well as local rejection and output limits.
        return selected[offset : offset + 2], offset + 2 < len(selected)


@pytest.mark.asyncio
async def test_intersection_preserves_and_semantics_and_pagination():
    adapter = Adapter()
    filters = {
        "molecule_id": [f"M{i}" for i in range(25)],
        "publication_id": [f"D{i}" for i in range(21)],
    }
    result = [
        row async for row in adapter.fetch_multi_filtered("compound_record", filters)
    ]
    assert [row["record_id"] for row in result] == [1, 2, 3]
    assert len(adapter.calls) == 12  # 11 document batches, one additional page.
    assert all("molecule_chembl_id__in" not in call for call in adapter.calls)


@pytest.mark.asyncio
@pytest.mark.parametrize("limit,expected", [(0, []), (1, [1]), (2, [1, 2])])
async def test_output_limit_counts_only_matching_records(limit, expected):
    adapter = Adapter()
    result = [
        row
        async for row in adapter.fetch_multi_filtered(
            "compound_record",
            {"molecule_id": ["M1", "M2"], "publication_id": ["D1"]},
            limit=limit,
        )
    ]
    assert [row["record_id"] for row in result] == expected
    if limit == 0:
        assert not adapter.calls


@pytest.mark.asyncio
async def test_empty_conjunct_does_not_fetch():
    adapter = Adapter()
    assert [
        row
        async for row in adapter.fetch_multi_filtered(
            "compound_record", {"molecule_id": ["M1"], "publication_id": []}
        )
    ] == []
    assert not adapter.calls
