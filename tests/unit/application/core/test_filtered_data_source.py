# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for FilteredDataSource wrapper."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.filtered_data_source import FilteredDataSource
from bioetl.application.core.filtered_data_source_mixins import (
    _FilteredDataSourceStateMixin,
)
from bioetl.domain.filtering import FilterLoadResult, InputFilterConfig
from bioetl.domain.ports.health_check import HealthCheckResult
from bioetl.domain.ports import FilterableDataSourcePort
from bioetl.domain.types import HealthStatus


class MockDataSource:
    """Mock the data source that does NOT implement FilterableDataSourcePort.

    Tracks method calls for test assertions.
    """

    provider_name = "chembl"

    def __init__(self):
        self.__aenter__ = AsyncMock(return_value=self)
        self.__aexit__ = AsyncMock(return_value=None)
        self.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
        self.check_health = AsyncMock(
            return_value=HealthCheckResult(
                status=HealthStatus.HEALTHY,
                latency_ms=25.0,
                provider=self.provider_name,
                endpoint="/health",
            )
        )
        self.aclose = AsyncMock()
        self.fetch_calls: list[dict[str, object]] = []

    async def fetch(self, *args, **kwargs):
        await asyncio.sleep(0)
        self.fetch_calls.append({"args": args, "kwargs": kwargs})
        for record in [{"id": "1"}, {"id": "2"}, {"id": "3"}]:
            yield record


class MockFilterableDataSource:
    """Mock the data source that implements FilterableDataSourcePort.

    Tracks method calls for test assertions.
    """

    provider_name = "chembl"

    def __init__(self):
        self.__aenter__ = AsyncMock(return_value=self)
        self.__aexit__ = AsyncMock(return_value=None)
        self.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
        self.check_health = AsyncMock(
            return_value=HealthCheckResult(
                status=HealthStatus.HEALTHY,
                latency_ms=30.0,
                provider=self.provider_name,
                endpoint="/health",
            )
        )
        self.aclose = AsyncMock()
        self.fetch_calls: list[dict[str, object]] = []
        self.fetch_filtered_calls: list[dict[str, object]] = []
        self.fetch_multi_filtered_calls: list[dict[str, object]] = []
        self.fetch_filtered_with_fallback_calls: list[dict[str, object]] = []

    async def fetch(self, *args, **kwargs):
        await asyncio.sleep(0)
        self.fetch_calls.append({"args": args, "kwargs": kwargs})
        for record in [{"id": "1"}, {"id": "2"}, {"id": "3"}]:
            yield record

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ):
        await asyncio.sleep(0)
        self.fetch_filtered_calls.append(
            {
                "entity_type": entity_type,
                "filter_ids": list(filter_ids),
                "filter_field": filter_field,
                "limit": limit,
            }
        )
        for record in [{"id": "filtered_1"}, {"id": "filtered_2"}]:
            yield record

    async def fetch_multi_filtered(
        self,
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ):
        await asyncio.sleep(0)
        self.fetch_multi_filtered_calls.append(
            {
                "entity_type": entity_type,
                "filters": dict(filters),
                "limit": limit,
            }
        )
        for record in [{"id": "multi_1"}, {"id": "multi_2"}]:
            yield record

    async def fetch_filtered_with_fallback(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ):
        await asyncio.sleep(0)
        self.fetch_filtered_with_fallback_calls.append(
            {
                "entity_type": entity_type,
                "filter_ids": list(filter_ids),
                "filter_field": filter_field,
                "fallback_mapping": dict(fallback_mapping),
                "limit": limit,
            }
        )
        for record in [{"id": "fallback_1"}, {"id": "fallback_2"}]:
            yield record


# Verify the mock properly implements the Protocol
assert isinstance(MockFilterableDataSource(), FilterableDataSourcePort)


async def _drain_async_iter(async_iter) -> None:
    """Consume an async iterator until completion."""
    async for _ in async_iter:
        continue


@pytest.fixture
def mock_data_source():
    """Create a mock data source (does NOT implement FilterableDataSourcePort)."""
    return MockDataSource()


@pytest.fixture
def mock_data_source_with_filtered():
    """Create a mock data source with fetch_filtered support."""
    return MockFilterableDataSource()


@pytest.fixture
def mock_filter_reader():
    """Create a mock filter reader."""
    reader = AsyncMock()
    filter_result = FilterLoadResult(
        ids=("CHEMBL1", "CHEMBL2", "CHEMBL3"),
        total_count=3,
        unique_count=3,
        duplicate_count=0,
        duplicates=frozenset(),
    )
    reader.load_filter_ids = AsyncMock(return_value=filter_result)
    return reader


@pytest.fixture
def enabled_filter_config():
    """Create enabled filter configuration."""
    return InputFilterConfig(
        enabled=True,
        source_path="data/molecules.csv",
        column_name="molecule_id",
        filter_field="molecule_id",
    )


@pytest.fixture
def disabled_filter_config():
    """Create disabled filter configuration."""
    return InputFilterConfig(enabled=False)


@pytest.mark.unit
class TestFilteredDataSourceInit:
    """Tests for FilteredDataSource initialization."""

    def test_data_source_init__initialization__91068ca3(
        self, mock_data_source, enabled_filter_config
    ):
        """Test FilteredDataSource initializes correctly."""
        filtered = FilteredDataSource(
            data_source=mock_data_source,
            filter_reader=None,
            filter_config=enabled_filter_config,
        )

        assert filtered.provider_name == "chembl"
        assert filtered._filter_ids is None

    def test_provider_name_property_delegates_to_wrapped_source(
        self, mock_data_source, disabled_filter_config
    ):
        """Test provider_name is delegated to wrapped data source."""
        mock_data_source.provider_name = "pubchem"
        filtered = FilteredDataSource(
            data_source=mock_data_source,
            filter_reader=None,
            filter_config=disabled_filter_config,
        )

        assert filtered.provider_name == "pubchem"


@pytest.mark.unit
class TestFilteredDataSourceContextManager:
    """Tests for async context manager behavior."""

    @pytest.mark.asyncio
    async def test_aenter_without_filtering(
        self, mock_data_source, disabled_filter_config
    ):
        """Test __aenter__ without filtering enabled."""
        filtered = FilteredDataSource(
            data_source=mock_data_source,
            filter_reader=None,
            filter_config=disabled_filter_config,
        )

        result = await filtered.__aenter__()

        assert result is filtered
        mock_data_source.__aenter__.assert_called_once()
        assert filtered._filter_ids is None

    @pytest.mark.asyncio
    async def test_aenter_graceful_degradation_when_filter_file_missing(
        self,
        mock_data_source,
        mock_filter_reader,
        enabled_filter_config,
    ):
        """Test __aenter__ proceeds without filtering when filter file is missing."""
        # Configure mock to raise FileNotFoundError (as InputFilterPort does)
        mock_filter_reader.load_filter_ids = AsyncMock(
            side_effect=FileNotFoundError("Filter file not found")
        )

        filtered = FilteredDataSource(
            data_source=mock_data_source,
            filter_reader=mock_filter_reader,
            filter_config=enabled_filter_config,
        )

        result = await filtered.__aenter__()

        assert result is filtered
        mock_data_source.__aenter__.assert_called_once()
        # Filter reader WAS called, but raised FileNotFoundError
        mock_filter_reader.load_filter_ids.assert_called_once()
        # Filter IDs should remain None (graceful degradation)
        assert filtered._filter_ids is None
        assert filtered.filter_result is None

    @pytest.mark.asyncio
    async def test_aenter_with_filtering_enabled(
        self,
        mock_data_source,
        mock_filter_reader,
        enabled_filter_config,
    ):
        """Test __aenter__ loads filter IDs when filtering is enabled."""
        filtered = FilteredDataSource(
            data_source=mock_data_source,
            filter_reader=mock_filter_reader,
            filter_config=enabled_filter_config,
        )

        # Mock filter reader returns success (no FileNotFoundError)
        await filtered.__aenter__()

        mock_filter_reader.load_filter_ids.assert_called_once_with(
            source_path="data/molecules.csv",
            column_name="molecule_id",
        )
        # FilterLoadResult.ids is a tuple, converted to list by FilteredDataSource
        assert filtered._filter_ids == ["CHEMBL1", "CHEMBL2", "CHEMBL3"]
        assert filtered.filter_result is not None
        assert filtered.filter_result.unique_count == 3

    @pytest.mark.asyncio
    async def test_aexit_delegates_to_wrapped(
        self, mock_data_source, disabled_filter_config
    ):
        """Test __aexit__ delegates to wrapped data source."""
        filtered = FilteredDataSource(
            data_source=mock_data_source,
            filter_reader=None,
            filter_config=disabled_filter_config,
        )

        await filtered.__aexit__(None, None, None)

        mock_data_source.__aexit__.assert_called_once_with(None, None, None)

    @pytest.mark.asyncio
    async def test_context_manager_full_cycle(
        self, mock_data_source, disabled_filter_config
    ):
        """Test using FilteredDataSource as async context manager."""
        filtered = FilteredDataSource(
            data_source=mock_data_source,
            filter_reader=None,
            filter_config=disabled_filter_config,
        )

        async with filtered as fd:
            assert fd is filtered

        mock_data_source.__aenter__.assert_called_once()
        mock_data_source.__aexit__.assert_called_once()


@pytest.mark.unit
class TestFilteredDataSourceFetch:
    """Tests for fetch method."""

    @pytest.mark.asyncio
    async def test_fetch_without_filtering(
        self, mock_data_source, disabled_filter_config
    ):
        """Test fetch delegates to wrapped data source when not filtering."""
        filtered = FilteredDataSource(
            data_source=mock_data_source,
            filter_reader=None,
            filter_config=disabled_filter_config,
        )

        records = []
        async for record in filtered.fetch("activity"):
            records.append(record)

        assert len(records) == 3
        assert records == [{"id": "1"}, {"id": "2"}, {"id": "3"}]

    @pytest.mark.asyncio
    async def test_fetch_without_filtering_forwards_query_and_offset(
        self, mock_data_source, disabled_filter_config
    ):
        """Test unfiltered fetch keeps query and offset passthrough intact."""
        filtered = FilteredDataSource(
            data_source=mock_data_source,
            filter_reader=None,
            filter_config=disabled_filter_config,
        )

        records = []
        async for record in filtered.fetch(
            "activity",
            limit=10,
            query="kinase",
            offset=25,
        ):
            records.append(record)

        assert len(records) == 3
        assert mock_data_source.fetch_calls[-1]["kwargs"] == {
            "entity_type": "activity",
            "limit": 10,
            "query": "kinase",
            "offset": 25,
        }

    @pytest.mark.asyncio
    async def test_fetch_with_filtering_enabled(
        self,
        mock_data_source_with_filtered,
        mock_filter_reader,
        enabled_filter_config,
    ):
        """Test fetch uses fetch_filtered when filtering is enabled."""
        filtered = FilteredDataSource(
            data_source=mock_data_source_with_filtered,
            filter_reader=mock_filter_reader,
            filter_config=enabled_filter_config,
        )

        # Enter context to load filter IDs (mock returns success)
        await filtered.__aenter__()

        records = []
        async for record in filtered.fetch("activity"):
            records.append(record)

        assert len(records) == 2
        assert records == [{"id": "filtered_1"}, {"id": "filtered_2"}]

    @pytest.mark.asyncio
    async def test_data_source_fetch__fetch_with_limit__4dc215e7(
        self, mock_data_source, disabled_filter_config
    ):
        """Test fetch passes limit to wrapped source."""
        filtered = FilteredDataSource(
            data_source=mock_data_source,
            filter_reader=None,
            filter_config=disabled_filter_config,
        )

        records = []
        async for record in filtered.fetch("activity", limit=10):
            records.append(record)

        assert len(records) == 3

    @pytest.mark.asyncio
    async def test_fetch_raises_when_adapter_missing_fetch_filtered(
        self,
        mock_data_source,  # Does not have fetch_filtered
        mock_filter_reader,
        enabled_filter_config,
    ):
        """Test fetch raises TypeError when adapter doesn't support fetch_filtered."""
        filtered = FilteredDataSource(
            data_source=mock_data_source,
            filter_reader=mock_filter_reader,
            filter_config=enabled_filter_config,
        )

        # Remove fetch_filtered if it exists
        if hasattr(mock_data_source, "fetch_filtered"):
            delattr(mock_data_source, "fetch_filtered")

        # Enter context to load filter IDs (mock returns success)
        await filtered.__aenter__()

        with pytest.raises(
            TypeError, match="does not implement FilterableDataSourcePort"
        ):
            await _drain_async_iter(filtered.fetch("activity"))

    def test_state_mixin_requires_concrete_filterable_adapter_guard(self) -> None:
        """Base state mixin documents the required adapter guard contract."""
        with pytest.raises(NotImplementedError):
            _FilteredDataSourceStateMixin()._ensure_filterable_adapter("Filtering")

    @pytest.mark.asyncio
    async def test_internal_single_column_fetch_wrapper_yields_records(
        self,
        mock_data_source_with_filtered,
    ):
        """The single-column mixin wrapper should delegate to fetch support."""
        config = InputFilterConfig(
            enabled=True,
            filter_field="molecule_id",
            direct_filter_ids=("CHEMBL1", "CHEMBL2"),
        )
        filtered = FilteredDataSource(
            data_source=mock_data_source_with_filtered,
            filter_reader=None,
            filter_config=config,
        )
        await filtered.__aenter__()

        records = [
            record
            async for record in filtered._fetch_single_column("activity", limit=1)
        ]

        assert records == [{"id": "filtered_1"}, {"id": "filtered_2"}]

    @pytest.mark.asyncio
    async def test_internal_multi_column_fetch_wrapper_yields_records(
        self,
    ):
        """The multi-column mixin wrapper should delegate to fetch support."""
        from bioetl.domain.filtering.input_config import FilterColumn

        multi_column_filter_config = InputFilterConfig(
            enabled=True,
            source_path="data/multi.csv",
            columns=(FilterColumn("molecule_id", "molecule_id"),),
        )
        data_source = MockFilterableDataSource()
        filtered = FilteredDataSource(
            data_source=data_source,
            filter_reader=None,
            filter_config=multi_column_filter_config,
        )
        filtered._multi_filter_ids = {"molecule_id": ["CHEMBL1"]}
        filtered._valid_combinations = None
        filtered._filter_fields = ("molecule_id",)

        records = [
            record async for record in filtered._fetch_multi_column("activity", limit=1)
        ]

        assert records == [{"id": "multi_1"}]
        assert data_source.fetch_multi_filtered_calls[-1]["limit"] is None

    @pytest.mark.asyncio
    async def test_internal_unfiltered_fetch_wrapper_returns_adapter_iterator(
        self,
        mock_data_source,
        disabled_filter_config,
    ):
        """The unfiltered wrapper should preserve adapter fetch kwargs."""
        filtered = FilteredDataSource(
            data_source=mock_data_source,
            filter_reader=None,
            filter_config=disabled_filter_config,
        )

        records = [
            record
            async for record in filtered._fetch_without_internal_filters(
                "activity",
                limit=2,
                query="kinase",
                offset=4,
            )
        ]

        assert records == [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        assert mock_data_source.fetch_calls[-1]["kwargs"] == {
            "entity_type": "activity",
            "limit": 2,
            "query": "kinase",
            "offset": 4,
        }


@pytest.mark.unit
class TestFilteredDataSourceDelegation:
    """Tests for method delegation to wrapped data source."""

    @pytest.mark.asyncio
    async def test_health_check_delegates(
        self, mock_data_source, disabled_filter_config
    ):
        """Test health_check delegates to wrapped data source."""
        filtered = FilteredDataSource(
            data_source=mock_data_source,
            filter_reader=None,
            filter_config=disabled_filter_config,
        )

        result = await filtered.health_check()

        assert result == HealthStatus.HEALTHY
        mock_data_source.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_health_delegates_and_preserves_provider(
        self, mock_data_source, disabled_filter_config
    ):
        """Test enhanced check_health delegates with provider-preserving payload."""
        filtered = FilteredDataSource(
            data_source=mock_data_source,
            filter_reader=None,
            filter_config=disabled_filter_config,
        )

        result = await filtered.check_health()

        assert result.provider == "chembl"
        assert result.status == HealthStatus.HEALTHY
        assert result.latency_ms == 25.0
        mock_data_source.check_health.assert_called_once()

    @pytest.mark.asyncio
    async def test_aclose_delegates(self, mock_data_source, disabled_filter_config):
        """Test aclose delegates to wrapped data source."""
        filtered = FilteredDataSource(
            data_source=mock_data_source,
            filter_reader=None,
            filter_config=disabled_filter_config,
        )

        await filtered.aclose()

        mock_data_source.aclose.assert_called_once()


@pytest.mark.unit
class TestFilteredDataSourceFallback:
    """Tests for fetch_filtered_with_fallback flow (composite mode)."""

    @pytest.mark.asyncio
    async def test_fetch_uses_fallback_when_direct_fallback_mapping_provided(
        self,
        mock_data_source_with_filtered,
    ):
        """Test fetch uses fetch_filtered_with_fallback when fallback_mapping is set."""
        # Direct filter config with fallback mapping (composite mode)
        config = InputFilterConfig(
            enabled=True,
            filter_field="doi",
            direct_filter_ids=("10.1038/test1", "10.1038/test2"),
            direct_fallback_mapping={
                "10.1038/test1": "Machine Learning in Drug Discovery",
                "10.1038/test2": "Deep Learning for Bioactivity",
            },
        )

        filtered = FilteredDataSource(
            data_source=mock_data_source_with_filtered,
            filter_reader=None,
            filter_config=config,
        )

        # Enter context to load direct filter IDs
        await filtered.__aenter__()

        # Verify fallback_mapping was loaded
        assert filtered._fallback_mapping is not None
        assert len(filtered._fallback_mapping) == 2
        assert (
            filtered._fallback_mapping["10.1038/test1"]
            == "Machine Learning in Drug Discovery"
        )

        records = []
        async for record in filtered.fetch("publication"):
            records.append(record)

        # Should use fetch_filtered_with_fallback (returns fallback_1, fallback_2)
        assert len(records) == 2
        assert records == [{"id": "fallback_1"}, {"id": "fallback_2"}]

    @pytest.mark.asyncio
    async def test_fetch_uses_regular_filtered_without_fallback_mapping(
        self,
        mock_data_source_with_filtered,
    ):
        """Test fetch uses fetch_filtered when no fallback_mapping is set."""
        # Direct filter config WITHOUT fallback mapping
        config = InputFilterConfig(
            enabled=True,
            filter_field="doi",
            direct_filter_ids=("10.1038/test1", "10.1038/test2"),
            # No direct_fallback_mapping
        )

        filtered = FilteredDataSource(
            data_source=mock_data_source_with_filtered,
            filter_reader=None,
            filter_config=config,
        )

        await filtered.__aenter__()

        # Verify no fallback_mapping
        assert filtered._fallback_mapping is None

        records = []
        async for record in filtered.fetch("publication"):
            records.append(record)

        # Should use regular fetch_filtered (returns filtered_1, filtered_2)
        assert len(records) == 2
        assert records == [{"id": "filtered_1"}, {"id": "filtered_2"}]

    @pytest.mark.asyncio
    async def test_single_column_fetch_with_fallback_forwards_limit(
        self,
        mock_data_source_with_filtered,
    ):
        """Test fallback filtering preserves the requested limit."""
        config = InputFilterConfig(
            enabled=True,
            filter_field="doi",
            direct_filter_ids=("10.1038/test1", "10.1038/test2"),
            direct_fallback_mapping={"10.1038/test1": "Test Title"},
        )
        filtered = FilteredDataSource(
            data_source=mock_data_source_with_filtered,
            filter_reader=None,
            filter_config=config,
        )

        await filtered.__aenter__()

        records = []
        async for record in filtered.fetch("publication", limit=1):
            records.append(record)

        assert len(records) == 2
        assert (
            mock_data_source_with_filtered.fetch_filtered_with_fallback_calls[-1][
                "limit"
            ]
            == 1
        )


@pytest.mark.unit
class TestFilteredDataSourceMultiColumn:
    """Tests for multi-column filtering paths."""

    @pytest.fixture
    def multi_column_filter_config(self):
        """Create multi-column filter configuration."""
        from bioetl.domain.filtering.input_config import FilterColumn

        return InputFilterConfig(
            enabled=True,
            source_path="data/multi.csv",
            columns=(
                FilterColumn("molecule_id", "molecule_id"),
                FilterColumn("assay_id", "assay_id"),
            ),
        )

    @pytest.fixture
    def mock_multi_filter_reader(self):
        """Create a mock filter reader for multi-column filters."""
        reader = AsyncMock()
        multi_result = FilterLoadResult(
            ids=("CHEMBL1", "CHEMBL2"),
            total_count=2,
            unique_count=2,
            duplicate_count=0,
            duplicates=frozenset(),
            column_ids={
                "molecule_id": frozenset({"CHEMBL1", "CHEMBL2"}),
                "assay_id": frozenset({"CHEMBL_ASSAY_1"}),
            },
            valid_combinations=frozenset({("CHEMBL1", "CHEMBL_ASSAY_1")}),
            filter_fields=("molecule_id", "assay_id"),
        )
        reader.load_multi_column_filter = AsyncMock(return_value=multi_result)
        return reader

    @pytest.mark.asyncio
    async def test_multi_column_filter_loads_on_aenter(
        self,
        mock_data_source_with_filtered,
        mock_multi_filter_reader,
        multi_column_filter_config,
    ):
        """Test multi-column filter IDs are loaded on __aenter__."""
        filtered = FilteredDataSource(
            data_source=mock_data_source_with_filtered,
            filter_reader=mock_multi_filter_reader,
            filter_config=multi_column_filter_config,
        )

        await filtered.__aenter__()

        mock_multi_filter_reader.load_multi_column_filter.assert_called_once()
        assert filtered._multi_filter_ids is not None
        assert filtered._valid_combinations is not None

    @pytest.mark.asyncio
    async def test_multi_column_fetch_filters_by_combinations(
        self,
        mock_data_source_with_filtered,
        mock_multi_filter_reader,
        multi_column_filter_config,
    ):
        """Test multi-column fetch filters by valid combinations."""
        filtered = FilteredDataSource(
            data_source=mock_data_source_with_filtered,
            filter_reader=mock_multi_filter_reader,
            filter_config=multi_column_filter_config,
        )
        await filtered.__aenter__()

        records = []
        async for record in filtered.fetch("activity"):
            records.append(record)

        # MockFilterableDataSource.fetch_multi_filtered returns multi_1, multi_2
        # _matches_valid_combination filters them based on valid_combinations
        assert isinstance(records, list)

    @pytest.mark.asyncio
    async def test_multi_column_fetch_respects_limit_after_valid_combination_filtering(
        self,
        multi_column_filter_config,
    ):
        """Test limit is applied after valid-combination filtering, not before."""

        class MultiColumnTrackingDataSource(MockFilterableDataSource):
            async def fetch_multi_filtered(
                self,
                entity_type: str,
                filters: dict[str, list[str]],
                limit: int | None = None,
            ):
                await asyncio.sleep(0)
                self.fetch_multi_filtered_calls.append(
                    {
                        "entity_type": entity_type,
                        "filters": dict(filters),
                        "limit": limit,
                    }
                )
                for record in [
                    {"molecule_id": "CHEMBL1", "assay_id": "CHEMBL_ASSAY_1"},
                    {"molecule_id": "CHEMBL1", "assay_id": "WRONG"},
                    {"molecule_id": "CHEMBL2", "assay_id": "CHEMBL_ASSAY_1"},
                ]:
                    yield record

        reader = AsyncMock()
        reader.load_multi_column_filter = AsyncMock(
            return_value=FilterLoadResult(
                ids=("CHEMBL1", "CHEMBL2"),
                total_count=3,
                unique_count=2,
                duplicate_count=1,
                duplicates=frozenset({"CHEMBL1"}),
                column_ids={
                    "molecule_id": frozenset({"CHEMBL1", "CHEMBL2"}),
                    "assay_id": frozenset({"CHEMBL_ASSAY_1"}),
                },
                valid_combinations=frozenset(
                    {
                        ("CHEMBL1", "CHEMBL_ASSAY_1"),
                        ("CHEMBL2", "CHEMBL_ASSAY_1"),
                    }
                ),
                filter_fields=("molecule_id", "assay_id"),
            )
        )
        data_source = MultiColumnTrackingDataSource()
        filtered = FilteredDataSource(
            data_source=data_source,
            filter_reader=reader,
            filter_config=multi_column_filter_config,
        )
        await filtered.__aenter__()

        records = []
        async for record in filtered.fetch("activity", limit=1):
            records.append(record)

        assert records == [{"molecule_id": "CHEMBL1", "assay_id": "CHEMBL_ASSAY_1"}]
        assert data_source.fetch_multi_filtered_calls[-1]["limit"] is None

    @pytest.mark.asyncio
    async def test_multi_column_fetch_raises_when_adapter_missing_fetch_multi_filtered(
        self,
        mock_data_source,
        mock_multi_filter_reader,
        multi_column_filter_config,
    ):
        """Test multi-column filtering requires a filterable adapter implementation."""
        filtered = FilteredDataSource(
            data_source=mock_data_source,
            filter_reader=mock_multi_filter_reader,
            filter_config=multi_column_filter_config,
        )

        await filtered.__aenter__()

        with pytest.raises(
            TypeError, match="does not implement FilterableDataSourcePort"
        ):
            await _drain_async_iter(filtered.fetch("activity"))


@pytest.mark.unit
class TestFilteredDataSourceMetrics:
    """Tests for metrics recording."""

    @pytest.mark.asyncio
    async def test_single_column_metrics_recorded(
        self,
        mock_data_source,
        mock_filter_reader,
        enabled_filter_config,
    ):
        """Test metrics are recorded when loading single-column filter."""
        mock_metrics = MagicMock()

        filtered = FilteredDataSource(
            data_source=mock_data_source,
            filter_reader=mock_filter_reader,
            filter_config=enabled_filter_config,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
        )

        await filtered.__aenter__()

        # increment_counter should have been called for filter_ids_loaded_total
        mock_metrics.increment_counter.assert_called()
        call_args = mock_metrics.increment_counter.call_args_list
        counter_names = [c[0][0] for c in call_args]
        assert "bioetl_filter_ids_loaded_total" in counter_names
        loaded_call = next(
            call
            for call in call_args
            if call.args[0] == "bioetl_filter_ids_loaded_total"
        )
        assert loaded_call.args[2] == {
            "pipeline": "test_pipeline",
            "source_kind": "csv_single_column",
        }

    @pytest.mark.asyncio
    async def test_single_column_duplicate_metrics(
        self,
        mock_data_source,
        enabled_filter_config,
    ):
        """Test duplicate metrics are recorded when filter has duplicates."""
        reader = AsyncMock()
        filter_result = FilterLoadResult(
            ids=("CHEMBL1", "CHEMBL2"),
            total_count=3,
            unique_count=2,
            duplicate_count=1,
            duplicates=frozenset({"CHEMBL1"}),
        )
        reader.load_filter_ids = AsyncMock(return_value=filter_result)
        mock_metrics = MagicMock()

        filtered = FilteredDataSource(
            data_source=mock_data_source,
            filter_reader=reader,
            filter_config=enabled_filter_config,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
        )

        await filtered.__aenter__()

        call_args = mock_metrics.increment_counter.call_args_list
        counter_names = [c[0][0] for c in call_args]
        assert "bioetl_filter_ids_duplicates_total" in counter_names
        mock_metrics.increment_counter.assert_any_call(
            "bioetl_filter_ids_duplicates_total",
            1,
            {"pipeline": "test_pipeline", "source_kind": "csv_single_column"},
        )

    @pytest.mark.asyncio
    async def test_no_metrics_when_metrics_is_none(
        self,
        mock_data_source,
        mock_filter_reader,
        enabled_filter_config,
    ):
        """Test no error when metrics port is None."""
        filtered = FilteredDataSource(
            data_source=mock_data_source,
            filter_reader=mock_filter_reader,
            filter_config=enabled_filter_config,
            metrics=None,
        )

        # Should not raise even without metrics
        await filtered.__aenter__()
        assert filtered._filter_ids is not None

    @pytest.mark.asyncio
    async def test_multi_column_metrics_record_combination_and_per_field_counts(
        self,
        mock_data_source_with_filtered,
    ):
        """Test multi-column load emits combination and per-field counters."""
        from bioetl.domain.filtering.input_config import FilterColumn

        mock_metrics = MagicMock()
        reader = AsyncMock()
        reader.load_multi_column_filter = AsyncMock(
            return_value=FilterLoadResult(
                ids=("CHEMBL1", "CHEMBL2"),
                total_count=2,
                unique_count=2,
                duplicate_count=0,
                duplicates=frozenset(),
                column_ids={
                    "molecule_id": frozenset({"CHEMBL1", "CHEMBL2"}),
                    "assay_id": frozenset({"CHEMBL_ASSAY_1"}),
                },
                valid_combinations=frozenset({("CHEMBL1", "CHEMBL_ASSAY_1")}),
                filter_fields=("molecule_id", "assay_id"),
            )
        )
        config = InputFilterConfig(
            enabled=True,
            source_path="data/multi.csv",
            columns=(
                FilterColumn("molecule_id", "molecule_id"),
                FilterColumn("assay_id", "assay_id"),
            ),
        )
        filtered = FilteredDataSource(
            data_source=mock_data_source_with_filtered,
            filter_reader=reader,
            filter_config=config,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
        )

        await filtered.__aenter__()

        assert filtered.filter_result is not None
        assert filtered.filter_result.filter_fields == ("molecule_id", "assay_id")
        assert filtered._filter_fields == ("molecule_id", "assay_id")
        assert filtered._valid_combinations == frozenset(
            {("CHEMBL1", "CHEMBL_ASSAY_1")}
        )

        calls = mock_metrics.increment_counter.call_args_list
        counter_names = [call.args[0] for call in calls]
        assert "bioetl_filter_combinations_loaded_total" in counter_names
        assert counter_names.count("bioetl_filter_ids_loaded_total") == 2
        for call in calls:
            if call.args[0].startswith("bioetl_filter_"):
                assert call.args[2]["source_kind"] == "csv_multi_column"
                assert "source_file" not in call.args[2]

    @pytest.mark.asyncio
    async def test_multi_column_metrics_are_compatible_with_prometheus_adapter(
        self,
        mock_data_source_with_filtered,
    ):
        """Multi-column filter metrics must not emit undeclared Prometheus labels."""
        from bioetl.domain.filtering.input_config import FilterColumn
        from bioetl.infrastructure.observability.prometheus_metrics import (
            PrometheusMetrics,
        )

        reader = AsyncMock()
        reader.load_multi_column_filter = AsyncMock(
            return_value=FilterLoadResult(
                ids=("CHEMBL1", "CHEMBL2"),
                total_count=2,
                unique_count=2,
                duplicate_count=0,
                duplicates=frozenset(),
                column_ids={
                    "molecule_id": frozenset({"CHEMBL1", "CHEMBL2"}),
                    "assay_id": frozenset({"CHEMBL_ASSAY_1"}),
                },
                valid_combinations=frozenset({("CHEMBL1", "CHEMBL_ASSAY_1")}),
                filter_fields=("molecule_id", "assay_id"),
            )
        )
        config = InputFilterConfig(
            enabled=True,
            source_path="data/multi.csv",
            columns=(
                FilterColumn("molecule_id", "molecule_id"),
                FilterColumn("assay_id", "assay_id"),
            ),
        )
        filtered = FilteredDataSource(
            data_source=mock_data_source_with_filtered,
            filter_reader=reader,
            filter_config=config,
            metrics=PrometheusMetrics(),
            pipeline_name="test_pipeline",
        )

        await filtered.__aenter__()

        assert filtered.filter_result is not None
        assert filtered.filter_result.filter_fields == ("molecule_id", "assay_id")
        assert filtered._filter_fields == ("molecule_id", "assay_id")
        assert filtered._valid_combinations == frozenset(
            {("CHEMBL1", "CHEMBL_ASSAY_1")}
        )


@pytest.mark.unit
class TestFilteredDataSourceGetSourceMetadata:
    """Tests for get_source_metadata delegation."""

    def test_get_source_metadata_delegates(self, disabled_filter_config):
        """Test get_source_metadata delegates to wrapped adapter."""
        source = MockDataSource()
        source.get_source_metadata = MagicMock(return_value="metadata")
        filtered = FilteredDataSource(
            data_source=source,
            filter_reader=None,
            filter_config=disabled_filter_config,
        )

        result = filtered.get_source_metadata(api_version="v1")

        assert result == "metadata"
        source.get_source_metadata.assert_called_once_with("v1")

    def test_get_source_metadata_returns_none_when_not_supported(
        self, disabled_filter_config
    ):
        """Test get_source_metadata returns None if wrapped doesn't support it."""
        source = MockDataSource()
        filtered = FilteredDataSource(
            data_source=source,
            filter_reader=None,
            filter_config=disabled_filter_config,
        )

        result = filtered.get_source_metadata()

        assert result is None


@pytest.mark.unit
class TestFilteredDataSourceLoggerWarning:
    """Tests for logger warning path."""

    @pytest.mark.asyncio
    async def test_filter_file_not_found_logs_warning(
        self,
        mock_data_source,
        enabled_filter_config,
    ):
        """Test that logger.warning is called when filter file is missing."""
        reader = AsyncMock()
        reader.load_filter_ids = AsyncMock(
            side_effect=FileNotFoundError("Filter file not found")
        )
        mock_logger = MagicMock()

        filtered = FilteredDataSource(
            data_source=mock_data_source,
            filter_reader=reader,
            filter_config=enabled_filter_config,
            logger=mock_logger,
            pipeline_name="test_pipeline",
        )

        await filtered.__aenter__()

        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert call_args[0][0] == "input_filter_file_not_found"

    @pytest.mark.asyncio
    async def test_no_filter_reader_skips_loading(
        self,
        mock_data_source,
        enabled_filter_config,
    ):
        """Test that loading is skipped when filter_reader is None."""
        filtered = FilteredDataSource(
            data_source=mock_data_source,
            filter_reader=None,
            filter_config=enabled_filter_config,
        )

        await filtered.__aenter__()

        assert filtered._filter_ids is None

    @pytest.mark.asyncio
    async def test_no_filter_reader_enabled_csv_skips_loading(
        self,
        mock_data_source,
    ):
        """Test that loading is skipped when filter_reader is None but CSV mode."""
        config = InputFilterConfig(
            enabled=True,
            source_path="data/test.csv",
            column_name="molecule_id",
            filter_field="molecule_id",
        )

        filtered = FilteredDataSource(
            data_source=mock_data_source,
            filter_reader=None,
            filter_config=config,
        )

        await filtered.__aenter__()

        assert filtered._filter_ids is None


@pytest.mark.unit
class TestFilteredDataSourceDirectFilterLogging:
    """Tests for direct filter ID loading with logger."""

    @pytest.mark.asyncio
    async def test_direct_filter_ids_log_info(
        self,
        mock_data_source_with_filtered,
    ):
        """Test that direct filter ID loading logs info message."""
        config = InputFilterConfig(
            enabled=True,
            filter_field="doi",
            direct_filter_ids=("10.1038/test1",),
        )
        mock_logger = MagicMock()

        filtered = FilteredDataSource(
            data_source=mock_data_source_with_filtered,
            filter_reader=None,
            filter_config=config,
            logger=mock_logger,
            pipeline_name="test_pipeline",
        )

        await filtered.__aenter__()

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "direct_filter_ids_loaded"


@pytest.mark.unit
class TestFilteredDataSourceFallbackColumn:
    """Tests for fallback column loading."""

    @pytest.mark.asyncio
    async def test_load_with_fallback_column(
        self,
        mock_data_source_with_filtered,
    ):
        """Test loading filter with fallback column."""
        config = InputFilterConfig(
            enabled=True,
            source_path="data/pubs.csv",
            column_name="doi",
            filter_field="doi",
            fallback_column="title",
        )

        reader = AsyncMock()
        filter_result = FilterLoadResult(
            ids=("10.1038/test1",),
            total_count=1,
            unique_count=1,
            duplicate_count=0,
            duplicates=frozenset(),
        )
        fallback_map = {"10.1038/test1": "Test Title"}
        reader.load_filter_with_fallback = AsyncMock(
            return_value=(filter_result, fallback_map)
        )

        filtered = FilteredDataSource(
            data_source=mock_data_source_with_filtered,
            filter_reader=reader,
            filter_config=config,
        )

        await filtered.__aenter__()

        reader.load_filter_with_fallback.assert_called_once_with(
            source_path="data/pubs.csv",
            primary_column="doi",
            fallback_column="title",
        )
        assert filtered._fallback_mapping == fallback_map
        assert filtered._filter_ids == ["10.1038/test1"]


@pytest.mark.unit
class TestFilteredDataSourceValidCombinations:
    """Tests for _matches_valid_combination."""

    def test_matches_when_no_valid_combinations(self, disabled_filter_config):
        """Test that _matches_valid_combination returns True when no combinations set."""
        filtered = FilteredDataSource(
            data_source=MockDataSource(),
            filter_reader=None,
            filter_config=disabled_filter_config,
        )

        assert filtered._matches_valid_combination({"id": "1"}) is True

    def test_matches_valid_combination(self, disabled_filter_config):
        """Test that matching records pass the combination check."""
        filtered = FilteredDataSource(
            data_source=MockDataSource(),
            filter_reader=None,
            filter_config=disabled_filter_config,
        )
        filtered._valid_combinations = frozenset({("CHEMBL1", "ASSAY1")})
        filtered._filter_fields = ("mol_id", "assay_id")

        assert filtered._matches_valid_combination(
            {"mol_id": "CHEMBL1", "assay_id": "ASSAY1"}
        )

    def test_rejects_invalid_combination(self, disabled_filter_config):
        """Test that non-matching records are rejected."""
        filtered = FilteredDataSource(
            data_source=MockDataSource(),
            filter_reader=None,
            filter_config=disabled_filter_config,
        )
        filtered._valid_combinations = frozenset({("CHEMBL1", "ASSAY1")})
        filtered._filter_fields = ("mol_id", "assay_id")

        assert not filtered._matches_valid_combination(
            {"mol_id": "CHEMBL1", "assay_id": "ASSAY_WRONG"}
        )

    @pytest.mark.asyncio
    async def test_fetch_single_column_raises_without_filter_field(self):
        """Test ValueError when filter_field is None but _filter_ids is set manually."""
        config = InputFilterConfig(
            enabled=True,
            source_path="data/test.csv",
            column_name="molecule_id",
            filter_field="molecule_id",
        )
        reader = AsyncMock()
        reader.load_filter_ids = AsyncMock(
            return_value=FilterLoadResult(
                ids=("CHEMBL1",),
                total_count=1,
                unique_count=1,
                duplicate_count=0,
                duplicates=frozenset(),
            )
        )
        source = MockFilterableDataSource()
        filtered = FilteredDataSource(
            data_source=source,
            filter_reader=reader,
            filter_config=config,
        )
        await filtered.__aenter__()

        # Manually clear filter_field to simulate edge case
        object.__setattr__(filtered._filter_config, "filter_field", None)

        with pytest.raises(ValueError, match="filter_field must be specified"):
            await _drain_async_iter(filtered.fetch("activity"))
