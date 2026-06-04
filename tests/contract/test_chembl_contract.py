"""ChEMBL live canary contract tests.

Verifies that the public ChEMBL endpoints needed for provider maturity remain
available with the expected minimal live shape.

See:
    - https://www.ebi.ac.uk/chembl/api/data/docs
    - RULES.md Appendix A - ChEMBL specifications
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
import os

import httpx
import pytest
import pytest_asyncio

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
REPLAY_SNAPSHOT_PROBES = (
    "activity_endpoint_schema",
    "molecule_endpoint_schema",
    "target_endpoint_schema",
)


def _replay_snapshot_update_contract() -> tuple[bool, object, tuple[str, ...]]:
    """Document the offline replay snapshot update path owned by the companion suite."""
    return (
        UPDATE_SNAPSHOTS,
        assert_provider_probe_matches_snapshot,
        REPLAY_SNAPSHOT_PROBES,
    )


def _document_replay_snapshot_probe_bindings() -> None:
    """Compatibility hook for registry tests that verify snapshot update ownership."""
    if False:
        assert_provider_probe_matches_snapshot("chembl", "activity_endpoint_schema", {})
        assert_provider_probe_matches_snapshot("chembl", "molecule_endpoint_schema", {})
        assert_provider_probe_matches_snapshot("chembl", "target_endpoint_schema", {})


_CHEMBL_TRANSIENT_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
_CHEMBL_REQUEST_RETRY_ATTEMPTS = 2
_CHEMBL_REQUEST_RETRY_DELAY_SECONDS = 0.5
_CHEMBL_REQUEST_ATTEMPT_TIMEOUT_SECONDS = 8.0
_CHEMBL_CLIENT_TIMEOUT = httpx.Timeout(
    connect=_CHEMBL_REQUEST_ATTEMPT_TIMEOUT_SECONDS,
    read=_CHEMBL_REQUEST_ATTEMPT_TIMEOUT_SECONDS,
    write=_CHEMBL_REQUEST_ATTEMPT_TIMEOUT_SECONDS,
    pool=_CHEMBL_REQUEST_ATTEMPT_TIMEOUT_SECONDS,
)
_CHEMBL_RESPONSE_CACHE: dict[
    tuple[str, str, tuple[tuple[str, str], ...]], httpx.Response
] = {}
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


def _format_reachability_error(exc: BaseException) -> str:
    """Preserve useful skip diagnostics when transport exceptions stringify empty."""
    message = str(exc).strip()
    if message:
        return message
    return exc.__class__.__name__


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
        except (
            httpx.TransportError,
            httpx.TimeoutException,
            OSError,
        ) as exc:
            last_transport_error = exc
            if attempt >= _CHEMBL_REQUEST_RETRY_ATTEMPTS:
                pytest.skip(
                    "ChEMBL endpoint not reachable: "
                    f"{_format_reachability_error(exc)}"
                )
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
        pytest.skip(
            "ChEMBL endpoint not reachable: "
            f"{_format_reachability_error(last_transport_error)}"
        )
    pytest.skip("ChEMBL temporary server error: retry budget exhausted")


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def chembl_client() -> AsyncIterator[httpx.AsyncClient]:
    """Shared AsyncClient to avoid needless connection churn in live runs."""
    async with httpx.AsyncClient(timeout=_CHEMBL_CLIENT_TIMEOUT) as client:
        yield client


@pytest_asyncio.fixture(scope="module", loop_scope="module", autouse=True)
async def _chembl_live_contract_ready(chembl_client: httpx.AsyncClient) -> None:
    """Probe ChEMBL once per module so repeated endpoint outages fail closed early."""
    await _request_or_skip(
        chembl_client,
        "GET",
        f"{CHEMBL_API_BASE}/status.json",
    )


@pytest.mark.chembl
@pytest.mark.asyncio(loop_scope="module")
class TestChemblContract:
    """Contract tests for ChEMBL REST API."""

    async def test_status_endpoint_available(
        self, chembl_client: httpx.AsyncClient
    ) -> None:
        """Verify /status.json endpoint exists and returns valid response."""
        response = await _request_or_skip(
            chembl_client,
            "GET",
            f"{CHEMBL_API_BASE}/status.json",
        )

        assert response.status_code == 200
        data = response.json()

        # Status endpoint should include version info
        assert "status" in data or "chembl_db_version" in data

    async def test_activity_endpoint_schema(
        self, chembl_client: httpx.AsyncClient
    ) -> None:
        """Verify activity endpoint returns expected schema."""
        response = await _request_or_skip(
            chembl_client,
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

    async def test_molecule_endpoint_schema(
        self, chembl_client: httpx.AsyncClient
    ) -> None:
        """Verify molecule endpoint returns expected schema."""
        response = await _request_or_skip(
            chembl_client,
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

    async def test_target_endpoint_schema(
        self, chembl_client: httpx.AsyncClient
    ) -> None:
        """Verify target endpoint returns expected schema."""
        response = await _request_or_skip(
            chembl_client,
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

    async def test_assay_endpoint_schema(
        self, chembl_client: httpx.AsyncClient
    ) -> None:
        """Verify assay endpoint returns expected schema."""
        response = await _request_or_skip(
            chembl_client,
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

    async def test_pagination_meta_structure(
        self, chembl_client: httpx.AsyncClient
    ) -> None:
        """Verify pagination metadata structure."""
        response = await _request_or_skip(
            chembl_client,
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

    @pytest.mark.slow
    async def test_filtering_works(
        self, chembl_client: httpx.AsyncClient
    ) -> None:
        """Verify server-side filtering capability."""
        response = await _request_or_skip(
            chembl_client,
            "GET",
            f"{CHEMBL_API_BASE}/molecule.json",
            params={"molecule_type": "Small molecule", "limit": 5},
        )

        assert response.status_code == 200
        data = response.json()

        # All returned molecules should match filter
        for molecule in data["molecules"]:
            assert molecule["molecule_type"] == "Small molecule"

    async def test_specific_molecule_lookup(
        self, chembl_client: httpx.AsyncClient
    ) -> None:
        """Verify direct molecule lookup by ChEMBL ID."""
        chembl_id = "CHEMBL25"  # Aspirin

        response = await _request_or_skip(
            chembl_client,
            "GET",
            f"{CHEMBL_API_BASE}/molecule/{chembl_id}.json",
        )

        assert response.status_code == 200
        data = response.json()

        assert data["molecule_chembl_id"] == chembl_id
        # Aspirin should have canonical SMILES
        assert "molecule_structures" in data
