"""Integration test: extraction_params applied to ChEMBL Assay API requests."""

from __future__ import annotations

from typing import Any

import pytest

from tests.integration.chembl.extraction_params_support import (
    ExtractionParamsCase,
    InputFilterExtractionParamsSuiteBase,
    build_missing_cassette_reason,
    has_any_cassette,
)


ASSAY_CASE = ExtractionParamsCase(
    entity_type="assay",
    params={
        "assay_type__in": "B,F",
        "confidence_score__gte": 8,
        "relationship_type": "D",
        "target_chembl_id__isnull": False,
    },
    expected_query_parts=(
        "assay_type__in=B,F",
        "confidence_score__gte=8",
        "relationship_type=D",
        "target_chembl_id__isnull=False",
    ),
    record_id_field="assay_chembl_id",
    input_filter_field="assay_id",
    cassette_names=(
        "TestAssayExtractionParams.test_assay_filtered_api_request",
        "TestAssayExtractionParams.test_assay_filtered_api_request.yaml",
        "chembl_assay_filtered.yaml",
    ),
    cassette_hint="test_assay_filtered_api_request",
)


@pytest.mark.integration
class TestAssayExtractionParams(InputFilterExtractionParamsSuiteBase):
    """Verify extraction_params flow from config to API request and metadata."""

    CASE = ASSAY_CASE

    @pytest.mark.vcr
    @pytest.mark.skipif(
        not has_any_cassette(*ASSAY_CASE.cassette_names),
        reason=build_missing_cassette_reason(ASSAY_CASE.cassette_hint),
    )
    async def test_assay_filtered_api_request(
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
