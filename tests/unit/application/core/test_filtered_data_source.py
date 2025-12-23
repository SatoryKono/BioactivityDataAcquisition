"""Unit tests for FilteredDataSource wrapper."""

from unittest.mock import AsyncMock

import pytest

from bioetl.application.core.filtered_data_source import FilteredDataSource
from bioetl.domain.filter_config import FilterLoadResult, InputFilterConfig
from bioetl.domain.types import HealthStatus, Watermark


@pytest.fixture
def mock_data_source():
    """Create a mock data source."""
    source = AsyncMock()
    source.provider_name = "chembl"

    async def mock_fetch(*args, **kwargs):
        for record in [{"id": "1"}, {"id": "2"}, {"id": "3"}]:
            yield record

    source.fetch = mock_fetch
    source.__aenter__ = AsyncMock(return_value=source)
    source.__aexit__ = AsyncMock(return_value=None)
    source.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
    source.aclose = AsyncMock()
    return source


@pytest.fixture
def mock_data_source_with_filtered():
    """Create a mock data source with fetch_filtered support."""
    source = AsyncMock()
    source.provider_name = "chembl"

    async def mock_fetch(*args, **kwargs):
        for record in [{"id": "1"}, {"id": "2"}, {"id": "3"}]:
            yield record

    async def mock_fetch_filtered(*args, **kwargs):
        for record in [{"id": "filtered_1"}, {"id": "filtered_2"}]:
            yield record

    source.fetch = mock_fetch
    source.fetch_filtered = mock_fetch_filtered
    source.__aenter__ = AsyncMock(return_value=source)
    source.__aexit__ = AsyncMock(return_value=None)
    source.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
    source.aclose = AsyncMock()
    return source


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
        column_name="molecule_chembl_id",
        filter_field="molecule_chembl_id",
    )


@pytest.fixture
def disabled_filter_config():
    """Create disabled filter configuration."""
    return InputFilterConfig(enabled=False)


@pytest.mark.unit
class TestFilteredDataSourceInit:
    """Tests for FilteredDataSource initialization."""

    def test_initialization(self, mock_data_source, enabled_filter_config):
        """Test FilteredDataSource initializes correctly."""
        filtered = FilteredDataSource(
            data_source=mock_data_source,
            filter_reader=None,
            filter_config=enabled_filter_config,
        )

        assert filtered.provider_name == "chembl"
        assert filtered._filter_ids is None

    def test_provider_name_from_wrapped(self, mock_data_source, disabled_filter_config):
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

        await filtered.__aenter__()

        mock_filter_reader.load_filter_ids.assert_called_once_with(
            source_path="data/molecules.csv",
            column_name="molecule_chembl_id",
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

        # Simulate entering context to load filter IDs
        await filtered.__aenter__()

        records = []
        async for record in filtered.fetch("activity"):
            records.append(record)

        assert len(records) == 2
        assert records == [{"id": "filtered_1"}, {"id": "filtered_2"}]

    @pytest.mark.asyncio
    async def test_fetch_with_watermark_and_limit(
        self, mock_data_source, disabled_filter_config
    ):
        """Test fetch passes watermark and limit to wrapped source."""
        filtered = FilteredDataSource(
            data_source=mock_data_source,
            filter_reader=None,
            filter_config=disabled_filter_config,
        )

        watermark = Watermark.from_timestamp("2024-01-01T00:00:00Z")

        records = []
        async for record in filtered.fetch("activity", watermark=watermark, limit=10):
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

        # Simulate entering context to load filter IDs
        await filtered.__aenter__()

        with pytest.raises(TypeError, match="does not support fetch_filtered"):
            async for _ in filtered.fetch("activity"):
                pass


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
    async def test_aclose_delegates(self, mock_data_source, disabled_filter_config):
        """Test aclose delegates to wrapped data source."""
        filtered = FilteredDataSource(
            data_source=mock_data_source,
            filter_reader=None,
            filter_config=disabled_filter_config,
        )

        await filtered.aclose()

        mock_data_source.aclose.assert_called_once()
