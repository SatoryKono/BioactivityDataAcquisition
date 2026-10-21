"""A missing filtered publication cohort must not become an unfiltered read."""

from unittest.mock import Mock

import pytest

from bioetl.application.core.publication_term_data_source import (
    PublicationTermDataSource,
)

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_missing_filtered_publication_ids_do_not_fetch_remote_records():
    adapter = Mock()
    source = PublicationTermDataSource(adapter)
    rows = [
        row
        async for row in source._fetch_filtered_publication_terms(
            adapter, None, "publication_id", None
        )
    ]
    assert rows == []
    adapter.fetch_filtered.assert_not_called()
