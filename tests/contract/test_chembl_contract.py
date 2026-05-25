"""ChEMBL API contract tests.

Verifies that ChEMBL API endpoints and response schemas haven't changed.
These tests make live API calls and require BIOETL_LIVE_API_TESTS=true.

See:
    - https://www.ebi.ac.uk/chembl/api/data/docs
    - RULES.md Appendix A - ChEMBL specifications
"""

from __future__ import annotations

import asyncio
import os

import httpx
import pytest

from tests.contract._provider_contract_drift import (
    assert_provider_probe_matches_snapshot,
)
from tests.contract.conftest import (
    CHEMBL_ACTIVITY_REQUIRED_FIELDS,
    CHEMBL_MOLECULE_REQUIRED_FIELDS,
    CHEMBL_TARGET_REQUIRED_FIELDS,
)

CHEMBL_API_BASE = "https://www.ebi.ac.uk/chembl/api/data"
CHEMBL_TARGET_CONTRACT_PARAMS = {"target_chembl_id": "CHEMBL1824", "limit": 1}
UPDATE_SNAPSHOTS = os.environ.get("UPDATE_SNAPSHOTS", "0") == "1"
_CHEMBL_TRANSIENT_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
_CHEMBL_REQUEST_RETRY_ATTEMPTS = 3
_CHEMBL_REQUEST_RETRY_DELAY_SECONDS = 2.0
_CHEMBL_RESPONSE_CACHE: dict[tuple[str, str, tuple[tuple[str, str], ...]], httpx.Response] = {}
pytestmark = pytest.mark.network


def _request_cache_key(
    method: str,
    url: str,
    **kwargs: object,
) -> tuple[str, str, tuple[tuple[str, str], ...]]:
    params = kwargs.get("params")
    if params is None:
        normalized_params: tuple[tuple[str, str], ...] = ()
    else:
        normalized_params = tuple(
            sorted(
                (str(key), str(value))
                for key, value in httpx.QueryParams(params).multi_items()
            )
        )
    return (method.upper(), url, normalized_params)


async def _request_or_skip(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs: object,
) -> httpx.Response:
    """Execute request with light retry and cache for transient provider outages."""
    cache_key = _request_cache_key(method, url, **kwargs)
    cached_response = _CHEMBL_RESPONSE_CACHE.get(cache_key)
    if cached_response is not None:
        return cached_response

    last_transport_error: Exception | None = None
    for attempt in range(1, _CHEMBL_REQUEST_RETRY_ATTEMPTS + 1):
        try:
            response = await client.request(method, url, **kwargs)
            await response.aread()
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
            last_transport_error = exc
            if attempt >= _CHEMBL_REQUEST_RETRY_ATTEMPTS:
                pytest.skip(f"ChEMBL endpoint not reachable: {exc}")
        else:
            if response.status_code not in _CHEMBL_TRANSIENT_STATUS_CODES:
                _CHEMBL_RESPONSE_CACHE[cache_key] = response
                return response
            if attempt >= _CHEMBL_REQUEST_RETRY_ATTEMPTS:
                pytest.skip(
                    f"ChEMBL temporary server error after {_CHEMBL_REQUEST_RETRY_ATTEMPTS} attempts: "
                    f"HTTP {response.status_code}"
                )

        await asyncio.sleep(_CHEMBL_REQUEST_RETRY_DELAY_SECONDS * attempt)

    if last_transport_error is not None:
        pytest.skip(f"ChEMBL endpoint not reachable: {last_transport_error}")
    pytest.skip("ChEMBL temporary server error: retry budget exhausted")


@pytest.fixture(scope="module", autouse=True)
async def _chembl_live_contract_ready() -> None:
    """Probe ChEMBL once per module so repeated endpoint outages fail closed early."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        await _request_or_skip(
            client,
            "GET",
            f"{CHEMBL_API_BASE}/status.json",
        )


@pytest.mark.chembl
class TestChemblContract:
    """Contract tests for ChEMBL REST API."""

    @pytest.mark.asyncio
    async def test_status_endpoint_available(self) -> None:
        """Verify /status.json endpoint exists and returns valid response."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{CHEMBL_API_BASE}/status.json",
            )

        assert response.status_code == 200
        data = response.json()

        # Status endpoint should include version info
        assert "status" in data or "chembl_db_version" in data

    @pytest.mark.asyncio
    async def test_activity_endpoint_schema(self) -> None:
        """Verify activity endpoint returns expected schema."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{CHEMBL_API_BASE}/activity.json",
                params={"limit": 1},
            )

        assert response.status_code == 200
        data = response.json()

        # Response should have paginated structure
        assert "activities" in data
        assert "page_meta" in data

        # Verify at least one activity record
        activities = data["activities"]
        assert len(activities) >= 1

        # Verify required fields present
        activity = activities[0]
        missing_fields = CHEMBL_ACTIVITY_REQUIRED_FIELDS - set(activity.keys())
        assert not missing_fields, f"Missing required fields: {missing_fields}"

    @pytest.mark.asyncio
    async def test_activity_snapshot_contract(self) -> None:
        """Verify the provider-facing activity payload matches the snapshot."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{CHEMBL_API_BASE}/activity.json",
                params={"limit": 1},
            )

        assert response.status_code == 200
        assert_provider_probe_matches_snapshot(
            "chembl",
            "activity_endpoint_schema",
            response.json(),
            update_snapshots=UPDATE_SNAPSHOTS,
        )

    @pytest.mark.asyncio
    async def test_molecule_endpoint_schema(self) -> None:
        """Verify molecule endpoint returns expected schema."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{CHEMBL_API_BASE}/molecule.json",
                params={"limit": 1},
            )

        assert response.status_code == 200
        data = response.json()

        assert "molecules" in data
        molecules = data["molecules"]
        assert len(molecules) >= 1

        molecule = molecules[0]
        missing_fields = CHEMBL_MOLECULE_REQUIRED_FIELDS - set(molecule.keys())
        assert not missing_fields, f"Missing required fields: {missing_fields}"

    @pytest.mark.asyncio
    async def test_molecule_snapshot_contract(self) -> None:
        """Verify the provider-facing molecule payload matches the snapshot."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{CHEMBL_API_BASE}/molecule.json",
                params={"limit": 1},
            )

        assert response.status_code == 200
        assert_provider_probe_matches_snapshot(
            "chembl",
            "molecule_endpoint_schema",
            response.json(),
            update_snapshots=UPDATE_SNAPSHOTS,
        )

    @pytest.mark.asyncio
    async def test_target_endpoint_schema(self) -> None:
        """Verify target endpoint returns expected schema."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{CHEMBL_API_BASE}/target.json",
                params=CHEMBL_TARGET_CONTRACT_PARAMS,
            )

        assert response.status_code == 200
        data = response.json()

        assert "targets" in data
        targets = data["targets"]
        assert len(targets) >= 1

        target = targets[0]
        missing_fields = CHEMBL_TARGET_REQUIRED_FIELDS - set(target.keys())
        assert not missing_fields, f"Missing required fields: {missing_fields}"

    @pytest.mark.asyncio
    async def test_target_snapshot_contract(self) -> None:
        """Verify the provider-facing target payload matches the snapshot."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{CHEMBL_API_BASE}/target.json",
                params=CHEMBL_TARGET_CONTRACT_PARAMS,
            )

        assert response.status_code == 200
        assert_provider_probe_matches_snapshot(
            "chembl",
            "target_endpoint_schema",
            response.json(),
            update_snapshots=UPDATE_SNAPSHOTS,
        )

    @pytest.mark.asyncio
    async def test_assay_endpoint_schema(self) -> None:
        """Verify assay endpoint returns expected schema."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{CHEMBL_API_BASE}/assay.json",
                params={"limit": 1},
            )

        assert response.status_code == 200
        data = response.json()

        assert "assays" in data
        assays = data["assays"]
        assert len(assays) >= 1

        # Verify assay has key identifiers
        assay = assays[0]
        assert "assay_chembl_id" in assay
        assert "assay_type" in assay

    @pytest.mark.asyncio
    async def test_pagination_meta_structure(self) -> None:
        """Verify pagination metadata structure."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{CHEMBL_API_BASE}/molecule.json",
                params={"limit": 5},
            )

        assert response.status_code == 200
        data = response.json()

        page_meta = data["page_meta"]
        assert "limit" in page_meta
        assert "offset" in page_meta
        assert "total_count" in page_meta

        # Verify pagination is working
        assert page_meta["limit"] == 5

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_filtering_works(self) -> None:
        """Verify server-side filtering capability."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Filter molecules by type
            response = await _request_or_skip(
                client,
                "GET",
                f"{CHEMBL_API_BASE}/molecule.json",
                params={"molecule_type": "Small molecule", "limit": 5},
            )

        assert response.status_code == 200
        data = response.json()

        # All returned molecules should match filter
        for molecule in data["molecules"]:
            assert molecule["molecule_type"] == "Small molecule"

    @pytest.mark.asyncio
    async def test_specific_molecule_lookup(self) -> None:
        """Verify direct molecule lookup by ChEMBL ID."""
        chembl_id = "CHEMBL25"  # Aspirin

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{CHEMBL_API_BASE}/molecule/{chembl_id}.json",
            )

        assert response.status_code == 200
        data = response.json()

        assert data["molecule_chembl_id"] == chembl_id
        # Aspirin should have canonical SMILES
        assert "molecule_structures" in data
