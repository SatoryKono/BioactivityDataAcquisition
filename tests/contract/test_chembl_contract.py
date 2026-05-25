"""ChEMBL API contract tests.

Verifies that ChEMBL API endpoints and response schemas haven't changed.
These tests make live API calls and require BIOETL_LIVE_API_TESTS=true.

See:
    - https://www.ebi.ac.uk/chembl/api/data/docs
    - RULES.md Appendix A - ChEMBL specifications
"""

from __future__ import annotations

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
pytestmark = pytest.mark.network


async def _request_or_skip(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs: object,
) -> httpx.Response:
    """Execute request and skip only on clearly transient network/provider outages."""
    try:
        response = await client.request(method, url, **kwargs)
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
        pytest.skip(f"ChEMBL endpoint not reachable: {exc}")

    # Live provider contract probes should fail only on durable schema drift, not
    # on upstream transport or transient server outages beyond repo control.
    if response.status_code == 429 or 500 <= response.status_code < 600:
        pytest.skip(f"ChEMBL temporary server error: HTTP {response.status_code}")
    return response


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
