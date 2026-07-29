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
