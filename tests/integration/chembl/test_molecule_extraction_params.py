"""Integration test: extraction_params applied to ChEMBL Molecule API requests."""

from __future__ import annotations

from typing import Any

import pytest

from tests.integration.chembl.extraction_params_support import (
    ExtractionParamsCase,
    InputFilterExtractionParamsSuiteBase,
    build_missing_cassette_reason,
    has_any_cassette,
)


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
class TestMoleculeExtractionParams(InputFilterExtractionParamsSuiteBase):
    """Verify extraction_params flow from config to API request and metadata."""

    CASE = MOLECULE_CASE

    @pytest.mark.vcr
    @pytest.mark.skipif(
        not has_any_cassette(*MOLECULE_CASE.cassette_names),
        reason=build_missing_cassette_reason(MOLECULE_CASE.cassette_hint),
    )
    async def test_molecule_filtered_api_request(
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
