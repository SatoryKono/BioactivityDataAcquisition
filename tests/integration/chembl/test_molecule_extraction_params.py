"""Integration test: extraction_params applied to ChEMBL Molecule API requests.

Uses VCR.py cassette with pre-recorded filtered response.
Verifies that extraction_params from YAML config are correctly
appended to API request query string and recorded in Bronze SourceMetadata.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from bioetl.domain.models.filter import ExtractionParams
from bioetl.domain.resilience import AdapterConfig
from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter

# VCR cassette directory for ChEMBL extraction params tests
CASSETTE_DIR = Path(__file__).parent.parent.parent / "fixtures" / "vcr" / "chembl"


@pytest.fixture(scope="module")
def vcr_config() -> dict[str, Any]:
    """Configure VCR for ChEMBL extraction params tests."""
    return {
        "cassette_library_dir": str(CASSETTE_DIR),
        "record_mode": os.environ.get("VCR_RECORD_MODE", "none"),
        "match_on": ["method", "scheme", "host", "port", "path", "query"],
        "decode_compressed_response": True,
    }


@pytest.mark.integration
class TestMoleculeExtractionParams:
    """Verify extraction_params flow from config to API request and metadata."""

    @pytest.fixture
    def extraction_params(self) -> ExtractionParams:
        """Molecule-specific extraction params matching ADR-028 §3."""
        return ExtractionParams(
            params={
                "molecule_type": "Small molecule",
                "structure_type": "MOL",
                "inorganic_flag": 0,
            }
        )

    @pytest.fixture
    def mock_logger(self) -> MagicMock:
        """Create a mock logger for testing."""
        return MagicMock()

    @pytest.fixture
    def mock_http_client(self) -> MagicMock:
        """Create a mock HTTP client."""
        from bioetl.domain.types import CircuitBreakerState

        client = MagicMock()
        client.circuit_breaker = MagicMock()
        client.circuit_breaker.get_state.return_value = CircuitBreakerState.CLOSED
        client.circuit_breaker.get_failure_count.return_value = 0
        return client

    def test_build_params_includes_extraction_params(
        self,
        extraction_params: ExtractionParams,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """_build_params merges extraction_params into query dict."""
        adapter = ChemblAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            adapter_config=AdapterConfig(page_size=500),
            extraction_params=extraction_params,
        )

        params = adapter._build_params(offset=0, entity_type="molecule")

        # Standard pagination params present
        assert params["format"] == "json"
        assert params["limit"] == 500
        assert params["offset"] == 0

        # All 3 molecule extraction params present
        assert params["molecule_type"] == "Small molecule"
        assert params["structure_type"] == "MOL"
        assert params["inorganic_flag"] == 0

    def test_source_metadata_contains_query_string(
        self,
        extraction_params: ExtractionParams,
    ) -> None:
        """SourceMetadata.query_string includes all extraction params."""
        qs = extraction_params.to_query_string()

        assert "molecule_type=Small molecule" in qs
        assert "structure_type=MOL" in qs
        assert "inorganic_flag=0" in qs

    def test_source_metadata_query_string_deterministic(
        self,
        extraction_params: ExtractionParams,
    ) -> None:
        """query_string is deterministic (sorted keys) across invocations."""
        qs1 = extraction_params.to_query_string()
        qs2 = extraction_params.to_query_string()

        assert qs1 == qs2
        # Keys must be sorted alphabetically
        keys = [part.split("=")[0] for part in qs1.split("&")]
        assert keys == sorted(keys)

    def test_get_source_metadata_records_extraction_params(
        self,
        extraction_params: ExtractionParams,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """get_source_metadata writes extraction_params to query_string."""
        adapter = ChemblAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            extraction_params=extraction_params,
        )

        metadata = adapter.get_source_metadata()

        assert metadata.query_string is not None
        assert "molecule_type=Small molecule" in metadata.query_string
        assert "structure_type=MOL" in metadata.query_string

    def test_extraction_params_logged_at_init(
        self,
        extraction_params: ExtractionParams,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Adapter logs extraction_params at initialization for audit."""
        ChemblAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            extraction_params=extraction_params,
        )

        info_calls = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and c.args[0] == "chembl_extraction_params_configured"
        ]
        assert len(info_calls) == 1
        kwargs = info_calls[0].kwargs
        assert kwargs["param_count"] == 3
        assert "molecule_type" in kwargs["query_string"]

    def test_no_overlap_with_molecule_input_filter(
        self,
        extraction_params: ExtractionParams,
    ) -> None:
        """Molecule extraction_params do not overlap with input_filter.filter_field.

        The molecule input_filter uses filter_field="molecule_id", which is not
        present in extraction_params keys.
        """
        molecule_input_filter_field = "molecule_id"
        assert molecule_input_filter_field not in extraction_params.params

    @pytest.mark.vcr("chembl_molecule_filtered.yaml")
    @pytest.mark.skipif(
        not (CASSETTE_DIR / "chembl_molecule_filtered.yaml").exists(),
        reason="VCR cassette not yet recorded. "
        "Record with: VCR_RECORD_MODE=new_episodes pytest -k test_molecule_filtered_api_request",
    )
    async def test_molecule_filtered_api_request(
        self,
        token_bucket: Any,
        circuit_breaker: Any,
        mock_logger: MagicMock,
    ) -> None:
        """Full flow: adapter sends filtered request to ChEMBL API.

        This test requires a VCR cassette recorded with the filtered URL.
        Record with:
            VCR_RECORD_MODE=new_episodes pytest -k test_molecule_filtered_api_request
        """
        from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

        ep = ExtractionParams(
            params={
                "molecule_type": "Small molecule",
                "structure_type": "MOL",
                "inorganic_flag": 0,
            }
        )

        client = UnifiedHTTPClient(
            rate_limiter=token_bucket,
            circuit_breaker=circuit_breaker,
            timeout=30.0,
        )

        async with client:
            adapter = ChemblAdapter(
                http_client=client,
                logger=mock_logger,
                adapter_config=AdapterConfig(page_size=10),
                extraction_params=ep,
            )

            records: list[dict[str, Any]] = []
            async for record in adapter.fetch("molecule", limit=5):
                records.append(record)

            assert len(records) > 0
            for record in records:
                assert "molecule_chembl_id" in record

            # Metadata should contain extraction params
            metadata = adapter.get_source_metadata()
            assert metadata.query_string is not None
            assert "molecule_type=Small molecule" in metadata.query_string
