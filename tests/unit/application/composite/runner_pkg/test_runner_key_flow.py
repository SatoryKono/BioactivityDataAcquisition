"""Focused tests for composite runner key extraction flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.composite.runner_pkg.runner_key_flow import (
    CompositeEnrichmentKeyRequest,
    extract_enrichment_keys,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_enrichment_keys_returns_dataframe_and_logs_count() -> None:
    key_extractor = MagicMock()
    key_extractor.extract = AsyncMock()
    keys_df = MagicMock()
    keys_df.__len__.return_value = 3
    key_extractor.extract.return_value = keys_df
    logger = MagicMock()
    request = CompositeEnrichmentKeyRequest(
        composite_name="test_composite",
        silver_table="silver.seed",
        output_keys=("compound_id", "assay_id"),
    )

    result = await extract_enrichment_keys(
        key_extractor=key_extractor,
        logger=logger,
        request=request,
    )

    assert result.keys_df is keys_df
    assert result.keys_count == 3
    key_extractor.extract.assert_awaited_once_with(
        silver_table="silver.seed",
        keys=("compound_id", "assay_id"),
    )
    logger.info.assert_called_once_with(
        "Extracted keys for enrichment",
        composite="test_composite",
        keys_count=3,
    )
