"""Integration test: extraction_params applied to ChEMBL Document API requests."""

from __future__ import annotations

from typing import Any

import pytest

from tests.integration.chembl.extraction_params_support import (
    ExtractionParamsCase,
    InputFilterExtractionParamsSuiteBase,
)

# Ownership anchor for VCR metadata catalog reachability; pytest-vcr still
# resolves this cassette from the test class and method name automatically.
VCR_CASSETTE_NAME = (
    "TestPublicationExtractionParams.test_publication_filtered_api_request.yaml"
)


PUBLICATION_CASE = ExtractionParamsCase(
    entity_type="publication",
    params={
        "doc_type": "PUBLICATION",
        "year__gte": 1950,
        "year__lte": 2050,
    },
    expected_query_parts=(
        "doc_type=PUBLICATION",
        "year__gte=1950",
        "year__lte=2050",
    ),
    record_id_field="document_chembl_id",
    input_filter_field="publication_id",
)


@pytest.mark.integration
class TestPublicationExtractionParams(InputFilterExtractionParamsSuiteBase):
    """Verify extraction_params flow from config to API request and metadata."""

    CASE = PUBLICATION_CASE

    @pytest.mark.vcr
    async def test_publication_filtered_api_request(
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
