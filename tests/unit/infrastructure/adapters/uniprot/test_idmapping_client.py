"""Unit tests for UniProt ID Mapping client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.uniprot.idmapping_client import (
    IDMappingJobError,
    IDMappingTimeoutError,
    UniProtIDMappingClient,
)


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client."""
    return MagicMock()


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.debug = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture
def idmapping_client(mock_http_client, mock_logger):
    """Create UniProt ID Mapping client with mocks."""
    return UniProtIDMappingClient(
        http_client=mock_http_client,
        logger=mock_logger,
        base_url="https://rest.uniprot.org",
    )


@pytest.mark.unit
class TestUniProtIDMappingClient:
    """Tests for UniProtIDMappingClient."""

    @pytest.mark.asyncio
    async def test_map_ids_empty_list(self, idmapping_client):
        """Test map_ids returns empty dict for empty input."""
        result = await idmapping_client.map_ids("ChEMBL", "UniProtKB", [])
        assert result == {}

    @pytest.mark.asyncio
    async def test_map_ids_single_id_found(self, idmapping_client, mock_http_client):
        """Test mapping a single ID that is found."""
        # Mock job submission
        submit_response = MagicMock()
        submit_response.status_code = 200
        submit_response.json.return_value = {"jobId": "test-job-123"}

        # Mock status polling
        status_response = MagicMock()
        status_response.status_code = 200
        status_response.json.return_value = {"jobStatus": "FINISHED"}

        # Mock results with full entry metadata
        results_response = MagicMock()
        results_response.status_code = 200
        results_response.json.return_value = {
            "results": [
                {
                    "from": "CHEMBL204",
                    "to": {
                        "primaryAccession": "P00742",
                        "uniProtkbId": "FA10_HUMAN",
                        "entryType": "UniProtKB reviewed (Swiss-Prot)",
                        "organism": {"scientificName": "Homo sapiens", "taxonId": 9606},
                        "annotationScore": 5,
                    },
                }
            ]
        }
        results_response.headers = {}

        mock_http_client.post = AsyncMock(return_value=submit_response)
        mock_http_client.get = AsyncMock(
            side_effect=[status_response, results_response]
        )

        result = await idmapping_client.map_ids("ChEMBL", "UniProtKB", ["CHEMBL204"])

        # Verify dict format with entry metadata
        assert "CHEMBL204" in result
        entry_data = result["CHEMBL204"]
        assert entry_data is not None
        assert entry_data["uniprot_accession"] == "P00742"
        assert entry_data["uniprot_entry_name"] == "FA10_HUMAN"
        assert entry_data["reviewed"] is True
        assert entry_data["taxonomy_id"] == 9606

    @pytest.mark.asyncio
    async def test_map_ids_single_id_not_found(
        self, idmapping_client, mock_http_client
    ):
        """Test mapping a single ID that is not found."""
        # Mock job submission
        submit_response = MagicMock()
        submit_response.status_code = 200
        submit_response.json.return_value = {"jobId": "test-job-456"}

        # Mock status polling
        status_response = MagicMock()
        status_response.status_code = 200
        status_response.json.return_value = {"jobStatus": "FINISHED"}

        # Mock empty results
        results_response = MagicMock()
        results_response.status_code = 200
        results_response.json.return_value = {"results": []}
        results_response.headers = {}

        mock_http_client.post = AsyncMock(return_value=submit_response)
        mock_http_client.get = AsyncMock(
            side_effect=[status_response, results_response]
        )

        result = await idmapping_client.map_ids(
            "ChEMBL", "UniProtKB", ["CHEMBL9999999999"]
        )

        assert result == {"CHEMBL9999999999": None}

    @pytest.mark.asyncio
    async def test_map_ids_multiple_ids_mixed_results(
        self, idmapping_client, mock_http_client
    ):
        """Test mapping multiple IDs with mixed results."""
        # Mock job submission
        submit_response = MagicMock()
        submit_response.status_code = 200
        submit_response.json.return_value = {"jobId": "test-job-789"}

        # Mock status polling
        status_response = MagicMock()
        status_response.status_code = 200
        status_response.json.return_value = {"jobStatus": "FINISHED"}

        # Mock results with some found, some not
        results_response = MagicMock()
        results_response.status_code = 200
        results_response.json.return_value = {
            "results": [
                {
                    "from": "CHEMBL204",
                    "to": {"primaryAccession": "P00742", "uniProtkbId": "FA10_HUMAN"},
                },
                {
                    "from": "CHEMBL205",
                    "to": {"primaryAccession": "P00915", "uniProtkbId": "CAH1_HUMAN"},
                },
            ]
        }
        results_response.headers = {}

        mock_http_client.post = AsyncMock(return_value=submit_response)
        mock_http_client.get = AsyncMock(
            side_effect=[status_response, results_response]
        )

        result = await idmapping_client.map_ids(
            "ChEMBL", "UniProtKB", ["CHEMBL204", "CHEMBL205", "CHEMBL206"]
        )

        # Verify found entries have dict format
        assert result["CHEMBL204"]["uniprot_accession"] == "P00742"
        assert result["CHEMBL205"]["uniprot_accession"] == "P00915"
        # Not found should be None
        assert result["CHEMBL206"] is None

    @pytest.mark.asyncio
    async def test_map_ids_job_error(self, idmapping_client, mock_http_client):
        """Test handling of job error from API."""
        # Mock job submission
        submit_response = MagicMock()
        submit_response.status_code = 200
        submit_response.json.return_value = {"jobId": "test-job-error"}

        # Mock error status
        status_response = MagicMock()
        status_response.status_code = 200
        status_response.json.return_value = {
            "jobStatus": "ERROR",
            "errorMessage": "Invalid database",
        }

        mock_http_client.post = AsyncMock(return_value=submit_response)
        mock_http_client.get = AsyncMock(return_value=status_response)

        with pytest.raises(IDMappingJobError) as exc_info:
            await idmapping_client.map_ids("InvalidDB", "UniProtKB", ["CHEMBL204"])

        assert "Invalid database" in str(exc_info.value)
        assert exc_info.value.job_id == "test-job-error"

    @pytest.mark.asyncio
    async def test_map_ids_submission_failure(self, idmapping_client, mock_http_client):
        """Test handling of job submission failure."""
        # Mock failed submission
        submit_response = MagicMock()
        submit_response.status_code = 500

        mock_http_client.post = AsyncMock(return_value=submit_response)

        with pytest.raises(IDMappingJobError) as exc_info:
            await idmapping_client.map_ids("ChEMBL", "UniProtKB", ["CHEMBL204"])

        assert "Job submission failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_map_ids_no_job_id_in_response(
        self, idmapping_client, mock_http_client
    ):
        """Test handling of missing jobId in response."""
        # Mock submission without jobId
        submit_response = MagicMock()
        submit_response.status_code = 200
        submit_response.json.return_value = {}  # No jobId

        mock_http_client.post = AsyncMock(return_value=submit_response)

        with pytest.raises(IDMappingJobError) as exc_info:
            await idmapping_client.map_ids("ChEMBL", "UniProtKB", ["CHEMBL204"])

        assert "No jobId" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_map_ids_direct_string_mapping(
        self, idmapping_client, mock_http_client
    ):
        """Test handling of direct string mapping (not entry object)."""
        # Mock job submission
        submit_response = MagicMock()
        submit_response.status_code = 200
        submit_response.json.return_value = {"jobId": "test-job-str"}

        # Mock status polling
        status_response = MagicMock()
        status_response.status_code = 200
        status_response.json.return_value = {"jobStatus": "FINISHED"}

        # Mock results with direct string mapping (some DBs return simple strings)
        results_response = MagicMock()
        results_response.status_code = 200
        results_response.json.return_value = {
            "results": [{"from": "CHEMBL204", "to": "P00742"}]  # Direct string
        }
        results_response.headers = {}

        mock_http_client.post = AsyncMock(return_value=submit_response)
        mock_http_client.get = AsyncMock(
            side_effect=[status_response, results_response]
        )

        result = await idmapping_client.map_ids("ChEMBL", "UniProtKB", ["CHEMBL204"])

        # Direct string mapping wraps accession in minimal dict format
        assert result["CHEMBL204"]["uniprot_accession"] == "P00742"

    @pytest.mark.asyncio
    async def test_i_d_mapping_client__health_check_healthy__882bedee(
        self, idmapping_client, mock_http_client
    ):
        """Test health check returns HEALTHY."""
        # Mock successful health check
        health_response = MagicMock()
        health_response.status_code = 200

        mock_http_client.get_once = AsyncMock(return_value=health_response)

        status = await idmapping_client.health_check()

        assert status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_i_d_mapping_client__check_degraded__d80bb99a(
        self, idmapping_client, mock_http_client
    ):
        """Test health check returns DEGRADED on non-200."""
        # Mock degraded health check
        health_response = MagicMock()
        health_response.status_code = 503

        mock_http_client.get_once = AsyncMock(return_value=health_response)

        status = await idmapping_client.health_check()

        assert status == HealthStatus.DEGRADED

    def test_get_next_page_url_with_link_header(self, idmapping_client):
        """Test extraction of next page URL from Link header."""
        headers = {"Link": '<https://rest.uniprot.org/next>; rel="next"'}

        url = idmapping_client._get_next_page_url(headers)

        assert url == "https://rest.uniprot.org/next"

    def test_get_next_page_url_no_link_header(self, idmapping_client):
        """Test handling of missing Link header."""
        headers = {}

        url = idmapping_client._get_next_page_url(headers)

        assert url is None

    def test_get_next_page_url_no_next_rel(self, idmapping_client):
        """Test handling of Link header without next rel."""
        headers = {"Link": '<https://rest.uniprot.org/prev>; rel="prev"'}

        url = idmapping_client._get_next_page_url(headers)

        assert url is None

    @pytest.mark.asyncio
    async def test_poll_returns_redirect_url_used_by_fetch(
        self, idmapping_client, mock_http_client
    ):
        """Test that redirect URL from polling is forwarded to fetch_results."""
        # Mock job submission
        submit_response = MagicMock()
        submit_response.status_code = 200
        submit_response.json.return_value = {"jobId": "test-job-redirect"}

        # Mock status polling with redirect URL (simulating 303 → followed)
        status_response = MagicMock()
        status_response.status_code = 200
        # The real redirect URL contains /uniprotkb/results/ not /results/
        status_response.url = (
            "https://rest.uniprot.org/idmapping/uniprotkb/results/test-job-redirect"
        )
        status_response.json.return_value = {"results": []}

        # Mock results fetched from the redirect URL
        results_response = MagicMock()
        results_response.status_code = 200
        results_response.json.return_value = {
            "results": [
                {
                    "from": "CHEMBL204",
                    "to": {
                        "primaryAccession": "P00742",
                        "uniProtkbId": "FA10_HUMAN",
                    },
                }
            ]
        }
        results_response.headers = {}

        mock_http_client.post = AsyncMock(return_value=submit_response)
        mock_http_client.get = AsyncMock(
            side_effect=[status_response, results_response]
        )

        result = await idmapping_client.map_ids("ChEMBL", "UniProtKB", ["CHEMBL204"])

        assert result["CHEMBL204"]["uniprot_accession"] == "P00742"

        # Verify the second GET call used the redirect URL, not the generic one
        get_calls = mock_http_client.get.call_args_list
        assert len(get_calls) == 2
        results_call_url = get_calls[1][0][0]
        assert "/idmapping/uniprotkb/results/" in results_call_url

    def test_i_d_mapping_client__repr__b3cb96ef(self, idmapping_client):
        """Test string representation."""
        repr_str = repr(idmapping_client)

        assert "UniProtIDMappingClient" in repr_str
        assert "rest.uniprot.org" in repr_str

    def test_i_d_mapping_client__provider_name__543e9538(self, idmapping_client):
        """Test provider name attribute."""
        assert idmapping_client.provider_name == "uniprot_idmapping"


@pytest.mark.unit
class TestIDMappingJobError:
    """Tests for IDMappingJobError exception."""

    def test_i_d_mapping_job_error__error_message__791afc94(self):
        """Test error message format."""
        error = IDMappingJobError("test-job-123", "Test error message")

        assert "test-job-123" in str(error)
        assert "Test error message" in str(error)
        assert error.job_id == "test-job-123"


@pytest.mark.unit
class TestIDMappingTimeoutError:
    """Tests for IDMappingTimeoutError exception."""

    def test_timeout_message(self):
        """Test timeout error message format."""
        error = IDMappingTimeoutError("test-job-456", 100)

        assert "test-job-456" in str(error)
        assert "100" in str(error)
        assert error.job_id == "test-job-456"
        assert error.attempts == 100
