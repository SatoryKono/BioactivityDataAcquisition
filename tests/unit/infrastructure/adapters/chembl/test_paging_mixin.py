"""Unit tests for ChEMBL paging mixin refactoring."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from bioetl.infrastructure.adapters.chembl.fetch_paging_mixin import (
    ChemblFetchPagingMixin,
)


class TestPageIteratorRefactoring:
    """Test suite for refactored ChEMBL paging mixin."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mixin = ChemblFetchPagingMixin()
        self.mixin._mapper = MagicMock()
        self.mixin._fetch_page = AsyncMock()
        self.mixin._build_params = MagicMock()

        # Mock mapper to return test URL
        self.mixin._mapper.get_resource_url.return_value = "https://test.chembl.org/api"

        self.mixin._build_params.return_value = {
            "limit": 100,
            "offset": 0,
            "format": "json",
        }

        self.mixin._fetch_page.return_value = (
            [{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}],
            False,
        )

    @pytest.mark.asyncio
    async def test_calculate_page_limit_no_limit(self):
        """Test page limit calculation when no overall limit is set."""
        params = {"limit": 100}
        result = self.mixin._calculate_page_limit(params, None, 0)
        assert result == 100

    @pytest.mark.asyncio
    async def test_calculate_page_limit_with_remaining(self):
        """Test page limit calculation when records remain within limit."""
        params = {"limit": 100}
        result = self.mixin._calculate_page_limit(params, 200, 50)
        assert result == 100

    @pytest.mark.asyncio
    async def test_calculate_page_limit_partial_page(self):
        """Test page limit when remaining records fit in smaller page."""
        params = {"limit": 100}
        result = self.mixin._calculate_page_limit(params, 200, 150)
        assert result == 50

    @pytest.mark.asyncio
    async def test_calculate_page_limit_exhausted(self):
        """Test page limit calculation when limit is exhausted."""
        params = {"limit": 100}
        result = self.mixin._calculate_page_limit(params, 100, 100)
        assert result is None  # Signal to stop iteration

    @pytest.mark.asyncio
    async def test_calculate_page_limit_over_exhausted(self):
        """Test page limit when records exceed limit."""
        params = {"limit": 100}
        result = self.mixin._calculate_page_limit(params, 100, 101)
        assert result is None  # Signal to stop iteration

    @pytest.mark.asyncio
    async def test_calculate_page_limit_no_limit_param(self):
        """Test page limit when params have no limit field."""
        params = {}
        result = self.mixin._calculate_page_limit(params, 200, 0)
        assert result is None

    @pytest.mark.asyncio
    async def test_page_iterator_limit_exhausted(self):
        """Test pagination stops when limit is exhausted."""
        self.mixin._fetch_page.return_value = ([{"id": 1}], False)

        results = []
        async for page in self.mixin._page_iterator(
            "activity", limit=1, start_offset=0
        ):
            results.extend(page)

        assert len(results) == 1
        assert self.mixin._fetch_page.call_count == 1

    @pytest.mark.asyncio
    async def test_page_iterator_no_limit(self):
        """Test pagination without limit fetches all pages."""
        # Mock multiple pages
        self.mixin._fetch_page.side_effect = [
            ([{"id": 1}], True),  # Page 1 with has_next=True
            ([{"id": 2}], True),  # Page 2 with has_next=True
            ([{"id": 3}], False),  # Page 3 with has_next=False
        ]

        results = []
        async for page in self.mixin._page_iterator(
            "activity", limit=None, start_offset=0
        ):
            results.extend(page)

        assert len(results) == 3
        assert self.mixin._fetch_page.call_count == 3

    @pytest.mark.asyncio
    async def test_page_iterator_with_offset(self):
        """Test pagination starts from specified offset."""
        self.mixin._fetch_page.return_value = ([{"id": 1}], False)

        # Check that _build_params is called with correct offset
        async for _ in self.mixin._page_iterator("activity", limit=1, start_offset=50):
            break

        # Verify _build_params was called with offset=50
        call_args = self.mixin._build_params.call_args
        assert call_args[0][0] == 50  # First argument is offset

    @pytest.mark.asyncio
    async def test_page_iterator_empty_response(self):
        """Test pagination handles empty API responses."""
        self.mixin._fetch_page.return_value = ([], False)

        results = []
        async for page in self.mixin._page_iterator(
            "activity", limit=10, start_offset=0
        ):
            results.extend(page)

        assert len(results) == 0
        assert self.mixin._fetch_page.call_count == 1

    @pytest.mark.asyncio
    async def test_page_iterator_error_handling(self):
        """Test pagination handles API errors gracefully."""
        self.mixin._fetch_page.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            async for _ in self.mixin._page_iterator(
                "activity", limit=10, start_offset=0
            ):
                pytest.fail("Iterator should not yield records after fetch failure")

    @pytest.mark.asyncio
    async def test_calculate_page_limit_edge_cases(self):
        """Test edge cases in page limit calculation."""
        # Zero limit
        params = {"limit": 100}
        result = self.mixin._calculate_page_limit(params, 0, 0)
        assert result is None

        # Negative remaining (shouldn't happen but handle gracefully)
        params = {"limit": 100}
        result = self.mixin._calculate_page_limit(params, 50, 100)
        assert result is None

    @pytest.mark.asyncio
    async def test_page_limit_adjustment(self):
        """Test that page limit is properly adjusted when remaining records are less than page size."""
        params = {"limit": 100}
        result = self.mixin._calculate_page_limit(params, 100, 25)
        assert result == 75  # 100 - 25 = 75 remaining

    @pytest.mark.asyncio
    async def test_page_iterator_preserves_params(self):
        """Test that original params are preserved when no limit adjustment needed."""
        original_params = {"limit": 100, "format": "json"}
        self.mixin._build_params.return_value = original_params.copy()
        self.mixin._fetch_page.return_value = ([{"id": 1}], False)

        async for _ in self.mixin._page_iterator(
            "activity", limit=None, start_offset=0
        ):
            break

        # Debug: print what was actually called
        print(f"Fetch page called with: {self.mixin._fetch_page.call_args}")

        # Verify params weren't modified when no limit adjustment needed
        # call_args is a tuple of (args, kwargs)
        args, kwargs = self.mixin._fetch_page.call_args

        # The second positional argument should be our params dict
        if len(args) > 1 and isinstance(args[1], dict):
            actual_params = args[1]
        else:
            actual_params = kwargs

        print(f"Actual params: {actual_params}")
        # Check that limit is preserved
        assert actual_params.get("limit") == 100  # Original limit preserved
        # Check that format is preserved
        assert actual_params.get("format") == "json"  # Other params preserved
