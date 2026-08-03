# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Integration test: extraction_params applied to ChEMBL Target API requests."""

from __future__ import annotations

from typing import Any

import pytest

from tests.integration.chembl.extraction_params_support import (
    ExtractionParamsCase,
    InputFilterExtractionParamsSuiteBase,
)


TARGET_CASE = ExtractionParamsCase(
    entity_type="target",
    params={
        "target_type": "SINGLE PROTEIN",
        "organism__isnull": False,
        "tax_id__isnull": False,
    },
    expected_query_parts=(
        "target_type=SINGLE PROTEIN",
        "organism__isnull=False",
        "tax_id__isnull=False",
    ),
    record_id_field="target_chembl_id",
    input_filter_field="target_id",
)


@pytest.mark.integration
class TestTargetExtractionParams(InputFilterExtractionParamsSuiteBase):
    """Verify extraction_params flow from config to API request and metadata."""

    CASE = TARGET_CASE

    @pytest.mark.asyncio(loop_scope="module")
    @pytest.mark.vcr
    async def test_target_filtered_api_request(
        self,
        token_bucket: Any,
        circuit_breaker: Any,
        mock_logger: Any,
    ) -> None:
        await self.assert_filtered_api_request(
            token_bucket=token_bucket,
            circuit_breaker=circuit_breaker,
            mock_logger=mock_logger,
        )
