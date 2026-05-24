"""Integration test: extraction_params applied to ChEMBL Activity API requests."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from tests.integration.chembl.extraction_params_support import (
    ExtractionParamsCase,
    ExtractionParamsSuiteBase,
    build_chembl_adapter,
)

# Ownership anchor for VCR metadata catalog reachability; pytest-vcr still
# resolves this cassette from the test class and method name automatically.
VCR_CASSETTE_NAME = "TestActivityExtractionParams.test_filtered_api_request.yaml"


ACTIVITY_CASE = ExtractionParamsCase(
    entity_type="activity",
    params={
        "standard_type__in": "IC50,Ki",
        "standard_units": "nM",
        "standard_relation": "=",
        "assay_type__in": "B,F",
        "potential_duplicate": 0,
        "data_validity_comment__isnull": True,
        "pchembl_value__isnull": False,
        "standard_flag": 1,
    },
    expected_query_parts=(
        "standard_type__in=IC50,Ki",
        "pchembl_value__isnull=False",
        "standard_units=nM",
        "assay_type__in=B,F",
        "potential_duplicate=0",
        "data_validity_comment__isnull=True",
        "standard_relation==",
        "standard_flag=1",
    ),
    record_id_field="activity_id",
)


@pytest.mark.integration
class TestActivityExtractionParams(ExtractionParamsSuiteBase):
    """Verify extraction_params flow from config to API request and metadata."""

    CASE = ACTIVITY_CASE

    def test_get_source_metadata_no_query_string_without_params(
        self,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        adapter = build_chembl_adapter(
            case=ExtractionParamsCase(
                entity_type="activity",
                params={},
                expected_query_parts=(),
                record_id_field="activity_id",
            ),
            http_client=mock_http_client,
            logger=mock_logger,
        )
        metadata = adapter.get_source_metadata()
        assert metadata.query_string is None

    @pytest.mark.vcr
    async def test_filtered_api_request(
        self,
        token_bucket: Any,
        circuit_breaker: Any,
        mock_logger: MagicMock,
    ) -> None:
        await self.assert_filtered_api_request(
            token_bucket=token_bucket,
            circuit_breaker=circuit_breaker,
            mock_logger=mock_logger,
        )
