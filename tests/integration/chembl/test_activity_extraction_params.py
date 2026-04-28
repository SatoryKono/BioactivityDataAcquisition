"""Integration test: extraction_params applied to ChEMBL Activity API requests."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from tests.integration.chembl.extraction_params_support import (
    ExtractionParamsCase,
    assert_build_params,
    assert_extraction_params_logged_at_init,
    assert_metadata_records_extraction_params,
    assert_query_string_contains,
    assert_query_string_is_deterministic,
    build_chembl_adapter,
    build_missing_cassette_reason,
    has_any_cassette,
    run_filtered_api_request_test,
)

pytest_plugins = ("tests.integration.chembl.extraction_params_support",)

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
    cassette_names=(
        "TestActivityExtractionParams.test_filtered_api_request",
        "TestActivityExtractionParams.test_filtered_api_request.yaml",
        "chembl_activity_filtered.yaml",
    ),
    cassette_hint="test_filtered_api_request",
)


@pytest.mark.integration
class TestActivityExtractionParams:
    """Verify extraction_params flow from config to API request and metadata."""

    @pytest.fixture
    def extraction_case(self) -> ExtractionParamsCase:
        return ACTIVITY_CASE

    def test_build_params_includes_extraction_params(
        self,
        extraction_case: ExtractionParamsCase,
        extraction_params: Any,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        adapter = build_chembl_adapter(
            case=extraction_case,
            http_client=mock_http_client,
            logger=mock_logger,
            page_size=500,
        )
        params = adapter._build_params(offset=0, entity_type=extraction_case.entity_type)
        assert_build_params(case=extraction_case, params=params, page_size=500)

    def test_source_metadata_contains_query_string(
        self,
        extraction_case: ExtractionParamsCase,
        extraction_params: Any,
    ) -> None:
        assert_query_string_contains(
            case=extraction_case,
            query_string=extraction_params.to_query_string(),
        )

    def test_source_metadata_query_string_deterministic(
        self,
        extraction_params: Any,
    ) -> None:
        assert_query_string_is_deterministic(extraction_params)

    def test_get_source_metadata_records_extraction_params(
        self,
        extraction_case: ExtractionParamsCase,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        adapter = build_chembl_adapter(
            case=extraction_case,
            http_client=mock_http_client,
            logger=mock_logger,
        )
        assert_metadata_records_extraction_params(case=extraction_case, adapter=adapter)

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

    def test_extraction_params_logged_at_init(
        self,
        extraction_case: ExtractionParamsCase,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        build_chembl_adapter(
            case=extraction_case,
            http_client=mock_http_client,
            logger=mock_logger,
        )
        assert_extraction_params_logged_at_init(
            case=extraction_case,
            logger=mock_logger,
        )

    @pytest.mark.vcr
    @pytest.mark.skipif(
        not has_any_cassette(*ACTIVITY_CASE.cassette_names),
        reason=build_missing_cassette_reason(ACTIVITY_CASE.cassette_hint),
    )
    async def test_filtered_api_request(
        self,
        token_bucket: Any,
        circuit_breaker: Any,
        mock_logger: MagicMock,
    ) -> None:
        await run_filtered_api_request_test(
            case=ACTIVITY_CASE,
            token_bucket=token_bucket,
            circuit_breaker=circuit_breaker,
            logger=mock_logger,
        )
