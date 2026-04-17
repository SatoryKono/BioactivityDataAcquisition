"""Unit tests for SubcellularFractionDataSource wrapper."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.subcellular_fraction_data_source import (
    SubcellularFractionDataSource,
)
from bioetl.domain.ports import FilterableDataSourcePort
from bioetl.domain.types import HealthStatus


class MockDataSource:
    """Mock data source that yields assay records."""

    provider_name = "chembl"

    def __init__(self, assays: list[dict] | None = None):
        self._assays = assays or []
        self.fetch_calls: list[dict[str, object]] = []
        self.__aenter__ = AsyncMock(return_value=self)
        self.__aexit__ = AsyncMock(return_value=None)
        self.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
        self.aclose = AsyncMock()

    async def fetch(self, entity_type: str, **kwargs):
        await asyncio.sleep(0)
        self.fetch_calls.append({"entity_type": entity_type, **kwargs})
        for assay in self._assays:
            yield assay


class MockFilterableDataSource:
    """Mock data source that implements FilterableDataSourcePort."""

    provider_name = "chembl"

    def __init__(self, assays: list[dict] | None = None):
        self._assays = assays or []
        self.__aenter__ = AsyncMock(return_value=self)
        self.__aexit__ = AsyncMock(return_value=None)
        self.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
        self.aclose = AsyncMock()

    async def fetch(self, entity_type: str, **kwargs):
        await asyncio.sleep(0)
        for assay in self._assays:
            yield assay

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ):
        await asyncio.sleep(0)
        for assay in self._assays:
            yield assay

    async def fetch_multi_filtered(
        self,
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ):
        await asyncio.sleep(0)
        for assay in self._assays:
            yield assay

    async def fetch_filtered_with_fallback(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ):
        await asyncio.sleep(0)
        for assay in self._assays:
            yield assay


assert isinstance(MockFilterableDataSource(), FilterableDataSourcePort)


# Sample assay records
ASSAY_WITH_FRACTION = {
    "assay_id": "CHEMBL1000",
    "assay_subcellular_fraction": "Microsomes",
    "assay_type": "B",
}

ASSAY_WITH_FRACTION_2 = {
    "assay_id": "CHEMBL1001",
    "assay_subcellular_fraction": "Cytosol",
    "assay_type": "F",
}

ASSAY_DUPLICATE_FRACTION = {
    "assay_id": "CHEMBL1002",
    "assay_subcellular_fraction": "Microsomes",  # Same as ASSAY_WITH_FRACTION
    "assay_type": "B",
}

ASSAY_WITHOUT_FRACTION = {
    "assay_id": "CHEMBL2000",
    "assay_subcellular_fraction": None,
    "assay_type": "B",
}

ASSAY_EMPTY_FRACTION = {
    "assay_id": "CHEMBL3000",
    "assay_subcellular_fraction": "",
    "assay_type": "B",
}

ASSAY_WHITESPACE_FRACTION = {
    "assay_id": "CHEMBL3001",
    "assay_subcellular_fraction": "  ",
    "assay_type": "B",
}


@pytest.mark.unit
class TestSubcellularFractionDataSourceInit:
    """Tests for initialization."""

    def test_initialization(self) -> None:
        source = MockDataSource()
        wrapper = SubcellularFractionDataSource(data_source=source)

        assert wrapper._data_source is source
        assert wrapper._seen_fractions == set()

    def test_provider_name(self) -> None:
        source = MockDataSource()
        wrapper = SubcellularFractionDataSource(data_source=source)

        assert wrapper.provider_name == "chembl"

    def test_entity_type_constants(self) -> None:
        assert SubcellularFractionDataSource.SOURCE_ENTITY_TYPE == "assay"
        assert (
            SubcellularFractionDataSource.TARGET_ENTITY_TYPE == "subcellular_fraction"
        )


@pytest.mark.unit
class TestSubcellularFractionDataSourceContextManager:
    """Tests for async context manager."""

    @pytest.mark.asyncio
    async def test_aenter_delegates_and_resets_cache(self) -> None:
        source = MockDataSource()
        wrapper = SubcellularFractionDataSource(data_source=source)
        wrapper._seen_fractions = {"old"}

        result = await wrapper.__aenter__()

        assert result is wrapper
        source.__aenter__.assert_called_once()
        assert wrapper._seen_fractions == set()

    @pytest.mark.asyncio
    async def test_aexit_delegates(self) -> None:
        source = MockDataSource()
        wrapper = SubcellularFractionDataSource(data_source=source)

        await wrapper.__aexit__(None, None, None)

        source.__aexit__.assert_called_once_with(None, None, None)

    @pytest.mark.asyncio
    async def test_context_manager_full_cycle(self) -> None:
        source = MockDataSource()
        wrapper = SubcellularFractionDataSource(data_source=source)

        async with wrapper as w:
            assert w is wrapper

        source.__aenter__.assert_called_once()
        source.__aexit__.assert_called_once()


@pytest.mark.unit
class TestSubcellularFractionDataSourceFetch:
    """Tests for fetch method."""

    @pytest.mark.asyncio
    async def test_fetch_subcellular_fraction_extracts_fractions(self) -> None:
        source = MockDataSource(
            assays=[ASSAY_WITH_FRACTION, ASSAY_WITH_FRACTION_2, ASSAY_WITHOUT_FRACTION]
        )
        wrapper = SubcellularFractionDataSource(data_source=source)

        records = []
        async for record in wrapper.fetch("subcellular_fraction"):
            records.append(record)

        assert len(records) == 2
        fractions = {r["subcellular_fraction"] for r in records}
        assert fractions == {"Microsomes", "Cytosol"}

    @pytest.mark.asyncio
    async def test_fetch_deduplication(self) -> None:
        source = MockDataSource(
            assays=[
                ASSAY_WITH_FRACTION,
                ASSAY_DUPLICATE_FRACTION,
                ASSAY_WITH_FRACTION_2,
            ]
        )
        wrapper = SubcellularFractionDataSource(data_source=source)

        records = []
        async for record in wrapper.fetch("subcellular_fraction"):
            records.append(record)

        assert len(records) == 2
        fractions = [r["subcellular_fraction"] for r in records]
        assert "Microsomes" in fractions
        assert "Cytosol" in fractions

    @pytest.mark.asyncio
    async def test_fetch_with_limit(self) -> None:
        source = MockDataSource(assays=[ASSAY_WITH_FRACTION, ASSAY_WITH_FRACTION_2])
        wrapper = SubcellularFractionDataSource(data_source=source)

        records = []
        async for record in wrapper.fetch("subcellular_fraction", limit=1):
            records.append(record)

        assert len(records) == 1

    @pytest.mark.asyncio
    async def test_fetch_other_entity_delegates(self) -> None:
        source = MockDataSource(assays=[ASSAY_WITH_FRACTION])
        wrapper = SubcellularFractionDataSource(data_source=source)

        records = []
        async for record in wrapper.fetch("assay"):
            records.append(record)

        assert len(records) == 1
        assert records[0]["assay_id"] == "CHEMBL1000"

    @pytest.mark.asyncio
    async def test_fetch_other_entity_forwards_offset(self) -> None:
        source = MockDataSource(assays=[ASSAY_WITH_FRACTION])
        wrapper = SubcellularFractionDataSource(data_source=source)

        async for _ in wrapper.fetch("assay", offset=12):
            pass

        assert source.fetch_calls[-1]["entity_type"] == "assay"
        assert source.fetch_calls[-1]["offset"] == 12

    @pytest.mark.asyncio
    async def test_fetch_skips_none_fractions(self) -> None:
        source = MockDataSource(assays=[ASSAY_WITHOUT_FRACTION])
        wrapper = SubcellularFractionDataSource(data_source=source)

        records = []
        async for record in wrapper.fetch("subcellular_fraction"):
            records.append(record)

        assert len(records) == 0

    @pytest.mark.asyncio
    async def test_fetch_skips_empty_string_fractions(self) -> None:
        source = MockDataSource(assays=[ASSAY_EMPTY_FRACTION])
        wrapper = SubcellularFractionDataSource(data_source=source)

        records = []
        async for record in wrapper.fetch("subcellular_fraction"):
            records.append(record)

        assert len(records) == 0

    @pytest.mark.asyncio
    async def test_fetch_skips_whitespace_only_fractions(self) -> None:
        source = MockDataSource(assays=[ASSAY_WHITESPACE_FRACTION])
        wrapper = SubcellularFractionDataSource(data_source=source)

        records = []
        async for record in wrapper.fetch("subcellular_fraction"):
            records.append(record)

        assert len(records) == 0

    @pytest.mark.asyncio
    async def test_fetch_resets_seen_fractions(self) -> None:
        """Each fetch call should reset deduplication cache."""
        source = MockDataSource(assays=[ASSAY_WITH_FRACTION])
        wrapper = SubcellularFractionDataSource(data_source=source)

        # First fetch
        records1 = []
        async for record in wrapper.fetch("subcellular_fraction"):
            records1.append(record)
        assert len(records1) == 1

        # Second fetch should still yield because _seen_fractions is reset
        records2 = []
        async for record in wrapper.fetch("subcellular_fraction"):
            records2.append(record)
        assert len(records2) == 1

    @pytest.mark.asyncio
    async def test_fetch_no_assays_yields_nothing(self) -> None:
        source = MockDataSource(assays=[])
        wrapper = SubcellularFractionDataSource(data_source=source)

        records = []
        async for record in wrapper.fetch("subcellular_fraction"):
            records.append(record)

        assert len(records) == 0


@pytest.mark.unit
class TestSubcellularFractionRecordFormat:
    """Tests for record format and entity_id computation."""

    @pytest.mark.asyncio
    async def test_record_has_required_fields(self) -> None:
        source = MockDataSource(assays=[ASSAY_WITH_FRACTION])
        wrapper = SubcellularFractionDataSource(data_source=source)

        records = []
        async for record in wrapper.fetch("subcellular_fraction"):
            records.append(record)

        assert len(records) == 1
        r = records[0]
        assert "entity_id" in r
        assert "subcellular_fraction" in r
        assert "example_assay_id" in r
        assert "assay_count" in r

    @pytest.mark.asyncio
    async def test_entity_id_is_hex(self) -> None:
        source = MockDataSource(assays=[ASSAY_WITH_FRACTION])
        wrapper = SubcellularFractionDataSource(data_source=source)

        records = []
        async for record in wrapper.fetch("subcellular_fraction"):
            records.append(record)

        entity_id = records[0]["entity_id"]
        assert len(entity_id) == 16
        assert all(c in "0123456789abcdef" for c in entity_id)

    @pytest.mark.asyncio
    async def test_entity_id_deterministic(self) -> None:
        source1 = MockDataSource(assays=[ASSAY_WITH_FRACTION])
        source2 = MockDataSource(assays=[ASSAY_WITH_FRACTION])
        wrapper1 = SubcellularFractionDataSource(data_source=source1)
        wrapper2 = SubcellularFractionDataSource(data_source=source2)

        records1, records2 = [], []
        async for record in wrapper1.fetch("subcellular_fraction"):
            records1.append(record)
        async for record in wrapper2.fetch("subcellular_fraction"):
            records2.append(record)

        assert records1[0]["entity_id"] == records2[0]["entity_id"]

    @pytest.mark.asyncio
    async def test_entity_id_unique_per_fraction(self) -> None:
        source = MockDataSource(assays=[ASSAY_WITH_FRACTION, ASSAY_WITH_FRACTION_2])
        wrapper = SubcellularFractionDataSource(data_source=source)

        records = []
        async for record in wrapper.fetch("subcellular_fraction"):
            records.append(record)

        ids = [r["entity_id"] for r in records]
        assert len(ids) == len(set(ids))

    @pytest.mark.asyncio
    async def test_example_assay_id_preserved(self) -> None:
        source = MockDataSource(assays=[ASSAY_WITH_FRACTION])
        wrapper = SubcellularFractionDataSource(data_source=source)

        records = []
        async for record in wrapper.fetch("subcellular_fraction"):
            records.append(record)

        assert records[0]["example_assay_id"] == "CHEMBL1000"

    @pytest.mark.asyncio
    async def test_assay_without_chembl_id(self) -> None:
        source = MockDataSource(assays=[{"assay_subcellular_fraction": "Microsomes"}])
        wrapper = SubcellularFractionDataSource(data_source=source)

        records = []
        async for record in wrapper.fetch("subcellular_fraction"):
            records.append(record)

        assert len(records) == 1
        assert records[0]["example_assay_id"] is None


@pytest.mark.unit
class TestSubcellularFractionDataSourceDelegation:
    """Tests for delegation to wrapped data source."""

    @pytest.mark.asyncio
    async def test_health_check_delegates(self) -> None:
        source = MockDataSource()
        wrapper = SubcellularFractionDataSource(data_source=source)

        result = await wrapper.health_check()

        assert result == HealthStatus.HEALTHY
        source.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_aclose_delegates(self) -> None:
        source = MockDataSource()
        wrapper = SubcellularFractionDataSource(data_source=source)

        await wrapper.aclose()

        source.aclose.assert_called_once()

    def test_get_source_metadata_delegates(self) -> None:
        source = MockDataSource()
        source.get_source_metadata = MagicMock(return_value="metadata")
        wrapper = SubcellularFractionDataSource(data_source=source)

        result = wrapper.get_source_metadata(api_version="v1")

        assert result == "metadata"
        source.get_source_metadata.assert_called_once_with("v1")

    def test_get_source_metadata_returns_none_when_not_supported(self) -> None:
        source = MockDataSource()
        wrapper = SubcellularFractionDataSource(data_source=source)

        result = wrapper.get_source_metadata()

        assert result is None


@pytest.mark.unit
class TestSubcellularFractionFilterable:
    """Tests for FilterableDataSourcePort methods."""

    @pytest.mark.asyncio
    async def test_fetch_filtered_subcellular_fraction(self) -> None:
        source = MockFilterableDataSource(
            assays=[ASSAY_WITH_FRACTION, ASSAY_WITH_FRACTION_2]
        )
        wrapper = SubcellularFractionDataSource(data_source=source)

        records = []
        async for record in wrapper.fetch_filtered(
            entity_type="subcellular_fraction",
            filter_ids=["CHEMBL1000"],
            filter_field="assay_id",
        ):
            records.append(record)

        assert len(records) == 2

    @pytest.mark.asyncio
    async def test_fetch_filtered_other_entity_delegates(self) -> None:
        source = MockFilterableDataSource(assays=[ASSAY_WITH_FRACTION])
        wrapper = SubcellularFractionDataSource(data_source=source)

        records = []
        async for record in wrapper.fetch_filtered(
            entity_type="assay",
            filter_ids=["CHEMBL1000"],
            filter_field="assay_id",
        ):
            records.append(record)

        assert len(records) == 1
        assert records[0]["assay_id"] == "CHEMBL1000"

    @pytest.mark.asyncio
    async def test_fetch_filtered_with_limit(self) -> None:
        source = MockFilterableDataSource(
            assays=[ASSAY_WITH_FRACTION, ASSAY_WITH_FRACTION_2]
        )
        wrapper = SubcellularFractionDataSource(data_source=source)

        records = []
        async for record in wrapper.fetch_filtered(
            entity_type="subcellular_fraction",
            filter_ids=["CHEMBL1000"],
            filter_field="assay_id",
            limit=1,
        ):
            records.append(record)

        assert len(records) == 1

    @pytest.mark.asyncio
    async def test_fetch_filtered_deduplication(self) -> None:
        source = MockFilterableDataSource(
            assays=[ASSAY_WITH_FRACTION, ASSAY_DUPLICATE_FRACTION]
        )
        wrapper = SubcellularFractionDataSource(data_source=source)

        records = []
        async for record in wrapper.fetch_filtered(
            entity_type="subcellular_fraction",
            filter_ids=["CHEMBL1000"],
            filter_field="assay_id",
        ):
            records.append(record)

        assert len(records) == 1

    @pytest.mark.asyncio
    async def test_ensure_filterable_raises_for_non_filterable(self) -> None:
        source = MockDataSource()  # Not FilterableDataSourcePort
        wrapper = SubcellularFractionDataSource(data_source=source)

        with pytest.raises(
            TypeError, match="does not implement FilterableDataSourcePort"
        ):
            async for _ in wrapper.fetch_filtered(
                entity_type="subcellular_fraction",
                filter_ids=["CHEMBL1000"],
                filter_field="assay_id",
            ):
                pass

    @pytest.mark.asyncio
    async def test_fetch_multi_filtered_subcellular_fraction(self) -> None:
        source = MockFilterableDataSource(
            assays=[ASSAY_WITH_FRACTION, ASSAY_WITH_FRACTION_2]
        )
        wrapper = SubcellularFractionDataSource(data_source=source)

        records = []
        async for record in wrapper.fetch_multi_filtered(
            entity_type="subcellular_fraction",
            filters={"assay_id": ["CHEMBL1000"]},
        ):
            records.append(record)

        assert len(records) == 2

    @pytest.mark.asyncio
    async def test_fetch_multi_filtered_other_entity(self) -> None:
        source = MockFilterableDataSource(assays=[ASSAY_WITH_FRACTION])
        wrapper = SubcellularFractionDataSource(data_source=source)

        records = []
        async for record in wrapper.fetch_multi_filtered(
            entity_type="assay",
            filters={"assay_id": ["CHEMBL1000"]},
        ):
            records.append(record)

        assert len(records) == 1

    @pytest.mark.asyncio
    async def test_fetch_multi_filtered_with_limit(self) -> None:
        source = MockFilterableDataSource(
            assays=[ASSAY_WITH_FRACTION, ASSAY_WITH_FRACTION_2]
        )
        wrapper = SubcellularFractionDataSource(data_source=source)

        records = []
        async for record in wrapper.fetch_multi_filtered(
            entity_type="subcellular_fraction",
            filters={"assay_id": ["CHEMBL1000"]},
            limit=1,
        ):
            records.append(record)

        assert len(records) == 1

    @pytest.mark.asyncio
    async def test_fetch_multi_filtered_raises_for_non_filterable(self) -> None:
        source = MockDataSource()
        wrapper = SubcellularFractionDataSource(data_source=source)

        with pytest.raises(
            TypeError, match="does not implement FilterableDataSourcePort"
        ):
            async for _ in wrapper.fetch_multi_filtered(
                entity_type="subcellular_fraction",
                filters={"assay_id": ["CHEMBL1000"]},
            ):
                pass

    @pytest.mark.asyncio
    async def test_fetch_filtered_with_fallback_subcellular_fraction(self) -> None:
        source = MockFilterableDataSource(
            assays=[ASSAY_WITH_FRACTION, ASSAY_WITH_FRACTION_2]
        )
        wrapper = SubcellularFractionDataSource(data_source=source)

        records = []
        async for record in wrapper.fetch_filtered_with_fallback(
            entity_type="subcellular_fraction",
            filter_ids=["CHEMBL1000"],
            filter_field="assay_id",
            fallback_mapping={"CHEMBL1000": "Test Assay"},
        ):
            records.append(record)

        assert len(records) == 2

    @pytest.mark.asyncio
    async def test_fetch_filtered_with_fallback_other_entity(self) -> None:
        source = MockFilterableDataSource(assays=[ASSAY_WITH_FRACTION])
        wrapper = SubcellularFractionDataSource(data_source=source)

        records = []
        async for record in wrapper.fetch_filtered_with_fallback(
            entity_type="assay",
            filter_ids=["CHEMBL1000"],
            filter_field="assay_id",
            fallback_mapping={"CHEMBL1000": "Test"},
        ):
            records.append(record)

        assert len(records) == 1

    @pytest.mark.asyncio
    async def test_fetch_filtered_with_fallback_limit(self) -> None:
        source = MockFilterableDataSource(
            assays=[ASSAY_WITH_FRACTION, ASSAY_WITH_FRACTION_2]
        )
        wrapper = SubcellularFractionDataSource(data_source=source)

        records = []
        async for record in wrapper.fetch_filtered_with_fallback(
            entity_type="subcellular_fraction",
            filter_ids=["CHEMBL1000"],
            filter_field="assay_id",
            fallback_mapping={"CHEMBL1000": "Test"},
            limit=1,
        ):
            records.append(record)

        assert len(records) == 1

    @pytest.mark.asyncio
    async def test_fetch_filtered_with_fallback_keeps_upstream_limit_unbounded(
        self,
    ) -> None:
        class _RecordingFilterableDataSource(MockFilterableDataSource):
            def __init__(self, assays: list[dict] | None = None):
                super().__init__(assays)
                self.fallback_calls: list[dict[str, object]] = []

            async def fetch_filtered_with_fallback(
                self,
                entity_type: str,
                filter_ids: list[str],
                filter_field: str,
                fallback_mapping: dict[str, str],
                limit: int | None = None,
            ):
                await asyncio.sleep(0)
                self.fallback_calls.append(
                    {
                        "entity_type": entity_type,
                        "filter_ids": filter_ids,
                        "filter_field": filter_field,
                        "fallback_mapping": fallback_mapping,
                        "limit": limit,
                    }
                )
                async for assay in super().fetch_filtered_with_fallback(
                    entity_type=entity_type,
                    filter_ids=filter_ids,
                    filter_field=filter_field,
                    fallback_mapping=fallback_mapping,
                    limit=limit,
                ):
                    yield assay

        source = _RecordingFilterableDataSource(
            assays=[ASSAY_WITH_FRACTION, ASSAY_WITH_FRACTION_2]
        )
        wrapper = SubcellularFractionDataSource(data_source=source)

        async for _ in wrapper.fetch_filtered_with_fallback(
            entity_type="subcellular_fraction",
            filter_ids=["CHEMBL1000"],
            filter_field="assay_id",
            fallback_mapping={"CHEMBL1000": "Test"},
            limit=1,
        ):
            pass

        assert source.fallback_calls[-1]["entity_type"] == "assay"
        assert source.fallback_calls[-1]["limit"] is None

    @pytest.mark.asyncio
    async def test_fetch_filtered_with_fallback_raises_for_non_filterable(self) -> None:
        source = MockDataSource()
        wrapper = SubcellularFractionDataSource(data_source=source)

        with pytest.raises(
            TypeError, match="does not implement FilterableDataSourcePort"
        ):
            async for _ in wrapper.fetch_filtered_with_fallback(
                entity_type="subcellular_fraction",
                filter_ids=["CHEMBL1000"],
                filter_field="assay_id",
                fallback_mapping={},
            ):
                pass
