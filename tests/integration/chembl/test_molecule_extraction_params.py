"""Integration test: extraction_params applied to ChEMBL Molecule API requests."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from tests.integration.chembl.extraction_params_support import (
    ExtractionParamsCase,
    assert_build_params,
    assert_extraction_params_logged_at_init,
    assert_input_filter_field_not_overlapping,
    assert_metadata_records_extraction_params,
    assert_query_string_contains,
    assert_query_string_is_deterministic,
    build_chembl_adapter,
    build_missing_cassette_reason,
    has_any_cassette,
    run_filtered_api_request_test,
)

pytest_plugins = ("tests.integration.chembl.extraction_params_support",)

MOLECULE_CASE = ExtractionParamsCase(
    entity_type="molecule",
    params={
        "molecule_type": "Small molecule",
        "structure_type": "MOL",
        "inorganic_flag": 0,
    },
    expected_query_parts=(
        "molecule_type=Small molecule",
        "structure_type=MOL",
        "inorganic_flag=0",
    ),
    record_id_field="molecule_chembl_id",
    input_filter_field="molecule_id",
    cassette_names=(
        "TestMoleculeExtractionParams.test_molecule_filtered_api_request",
        "TestMoleculeExtractionParams.test_molecule_filtered_api_request.yaml",
        "chembl_molecule_filtered.yaml",
    ),
    cassette_hint="test_molecule_filtered_api_request",
)


@pytest.mark.integration
class TestMoleculeExtractionParams:
    """Verify extraction_params flow from config to API request and metadata."""

    @pytest.fixture
    def extraction_case(self) -> ExtractionParamsCase:
        return MOLECULE_CASE

    def test_build_params_includes_extraction_params(
        self,
        extraction_case: ExtractionParamsCase,
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

    def test_no_overlap_with_molecule_input_filter(
        self,
        extraction_case: ExtractionParamsCase,
    ) -> None:
        assert_input_filter_field_not_overlapping(extraction_case)

    @pytest.mark.vcr
    @pytest.mark.skipif(
        not has_any_cassette(*MOLECULE_CASE.cassette_names),
        reason=build_missing_cassette_reason(MOLECULE_CASE.cassette_hint),
    )
    async def test_molecule_filtered_api_request(
        self,
        token_bucket: Any,
        circuit_breaker: Any,
        mock_logger: MagicMock,
    ) -> None:
        await run_filtered_api_request_test(
            case=MOLECULE_CASE,
            token_bucket=token_bucket,
            circuit_breaker=circuit_breaker,
            logger=mock_logger,
        )
