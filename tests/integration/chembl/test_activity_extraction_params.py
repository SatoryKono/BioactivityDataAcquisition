"""Integration test: extraction_params applied to ChEMBL Activity API requests.

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
class TestActivityExtractionParams:
    """Verify extraction_params flow from config to API request and metadata."""

    @pytest.fixture
    def extraction_params(self) -> ExtractionParams:
        """Activity-specific extraction params matching ADR-028 §3."""
        return ExtractionParams(
            params={
                "standard_type__in": "IC50,Ki",
                "standard_units": "nM",
                "standard_relation": "=",
                "assay_type__in": "B,F",
                "potential_duplicate": 0,
                "data_validity_comment__isnull": True,
                "pchembl_value__isnull": False,
                "standard_flag": 1,
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

        params = adapter._build_params(offset=0, entity_type="activity")

        # Standard pagination params present
        assert params["format"] == "json"
        assert params["limit"] == 500
        assert params["offset"] == 0

        # All 8 extraction params present
        assert params["standard_type__in"] == "IC50,Ki"
        assert params["standard_units"] == "nM"
        assert params["standard_relation"] == "="
        assert params["assay_type__in"] == "B,F"
        assert params["potential_duplicate"] == 0
        assert params["data_validity_comment__isnull"] is True
        assert params["pchembl_value__isnull"] is False
        assert params["standard_flag"] == 1

    def test_source_metadata_contains_query_string(
        self,
        extraction_params: ExtractionParams,
    ) -> None:
        """SourceMetadata.query_string includes all extraction params."""
        qs = extraction_params.to_query_string()

        assert "standard_type__in=IC50,Ki" in qs
        assert "pchembl_value__isnull=False" in qs
        assert "standard_units=nM" in qs
        assert "assay_type__in=B,F" in qs
        assert "potential_duplicate=0" in qs
        assert "data_validity_comment__isnull=True" in qs
        assert "standard_relation==" in qs
        assert "standard_flag=1" in qs

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
        assert "standard_type__in=IC50,Ki" in metadata.query_string
        assert "pchembl_value__isnull=False" in metadata.query_string

    def test_get_source_metadata_no_query_string_without_params(
        self,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """get_source_metadata has no query_string when extraction_params empty."""
        adapter = ChemblAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
        )

        metadata = adapter.get_source_metadata()

        assert metadata.query_string is None

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
        assert kwargs["param_count"] == 8
        assert "standard_type__in" in kwargs["query_string"]

    @pytest.mark.vcr("chembl_activity_filtered.yaml")
    @pytest.mark.skipif(
        not (CASSETTE_DIR / "chembl_activity_filtered.yaml").exists(),
        reason="VCR cassette not yet recorded. "
        "Record with: VCR_RECORD_MODE=new_episodes pytest -k test_filtered_api_request",
    )
    async def test_filtered_api_request(
        self,
        token_bucket: Any,
        circuit_breaker: Any,
        mock_logger: MagicMock,
    ) -> None:
        """Full flow: adapter sends filtered request to ChEMBL API.

        This test requires a VCR cassette recorded with the filtered URL.
        Record with:
            VCR_RECORD_MODE=new_episodes pytest -k test_filtered_api_request
        """
        from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

        ep = ExtractionParams(
            params={
                "standard_type__in": "IC50,Ki",
                "standard_units": "nM",
                "pchembl_value__isnull": False,
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
            async for record in adapter.fetch("activity", limit=5):
                records.append(record)

            assert len(records) > 0
            for record in records:
                assert "activity_id" in record

            # Metadata should contain extraction params
            metadata = adapter.get_source_metadata()
            assert metadata.query_string is not None
            assert "standard_type__in=IC50,Ki" in metadata.query_string
