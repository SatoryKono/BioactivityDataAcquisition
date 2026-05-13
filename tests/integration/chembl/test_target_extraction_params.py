"""Integration test: extraction_params applied to ChEMBL Target API requests."""

from __future__ import annotations

from typing import Any

import pytest

from tests.integration.chembl.extraction_params_support import (
    ExtractionParamsCase,
    InputFilterExtractionParamsSuiteBase,
    build_missing_cassette_reason,
    has_any_cassette,
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
    cassette_names=(
        "TestTargetExtractionParams.test_target_filtered_api_request",
        "TestTargetExtractionParams.test_target_filtered_api_request.yaml",
        "chembl_target_filtered.yaml",
    ),
    cassette_hint="test_target_filtered_api_request",
)


@pytest.mark.integration
class TestTargetExtractionParams(InputFilterExtractionParamsSuiteBase):
    """Verify extraction_params flow from config to API request and metadata."""

    CASE = TARGET_CASE

    @pytest.mark.vcr
    @pytest.mark.skipif(
        not has_any_cassette(*TARGET_CASE.cassette_names),
        reason=build_missing_cassette_reason(TARGET_CASE.cassette_hint),
    )
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
