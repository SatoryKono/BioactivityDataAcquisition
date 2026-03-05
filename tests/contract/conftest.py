"""Contract tests configuration and fixtures.

Provides common fixtures for live API contract testing.
"""

from __future__ import annotations

import os
import socket
from functools import lru_cache

import pytest

_CONTRACT_PATH_TOKEN_POSIX = "/contract/"
_CONTRACT_PATH_TOKEN_WINDOWS = "\\contract\\"
_NETWORK_PROBE_HOSTS = (
    "www.ebi.ac.uk",
    "pubchem.ncbi.nlm.nih.gov",
    "rest.uniprot.org",
    "eutils.ncbi.nlm.nih.gov",
)
_NETWORK_PROBE_PORT = 443
_NETWORK_PROBE_TIMEOUT_SECONDS = 2.0
_TRUTHY_ENV_VALUES = frozenset({"1", "true", "yes", "on"})


def _is_contract_test_path(path_str: str) -> bool:
    return (
        _CONTRACT_PATH_TOKEN_POSIX in path_str
        or _CONTRACT_PATH_TOKEN_WINDOWS in path_str
    )


@lru_cache(maxsize=1)
def _has_outbound_connectivity() -> bool:
    """Best-effort outbound connectivity probe for contract tests."""
    for host in _NETWORK_PROBE_HOSTS:
        try:
            with socket.create_connection(
                (host, _NETWORK_PROBE_PORT),
                timeout=_NETWORK_PROBE_TIMEOUT_SECONDS,
            ):
                return True
        except OSError:
            continue
    return False


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers for contract tests."""
    config.addinivalue_line(
        "markers",
        "network: tests requiring outbound network access (opt-in via --network)",
    )
    config.addinivalue_line("markers", "chembl: ChEMBL API contract tests")
    config.addinivalue_line("markers", "pubchem: PubChem API contract tests")
    config.addinivalue_line("markers", "uniprot: UniProt API contract tests")
    config.addinivalue_line("markers", "pubmed: PubMed API contract tests")
    config.addinivalue_line(
        "markers", "slow: Tests that may be slow due to rate limits"
    )
    config.addinivalue_line(
        "markers", "no_api: Contract tests that don't require live API access"
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skip contract tests if BIOETL_LIVE_API_TESTS is not set.

    Tests marked with 'no_api' are exempt from this requirement as they don't
    require live API access (e.g., schema introspection tests).
    """
    raw_live_value = os.environ.get("BIOETL_LIVE_API_TESTS", "")
    normalized_live_value = raw_live_value.strip().strip("\"'").lower()
    live_tests_enabled = normalized_live_value in _TRUTHY_ENV_VALUES

    if not live_tests_enabled:
        skip_marker = pytest.mark.skip(
            reason="Live API tests disabled. Set BIOETL_LIVE_API_TESTS=true to enable."
        )
        for item in items:
            fspath_str = str(item.fspath)
            if _is_contract_test_path(fspath_str):
                item.add_marker(pytest.mark.network)
                # Skip tests that require live API access (not marked with no_api)
                if "no_api" not in item.keywords:
                    item.add_marker(skip_marker)
    else:
        for item in items:
            if _is_contract_test_path(str(item.fspath)):
                item.add_marker(pytest.mark.network)


@pytest.fixture(scope="session")
def no_network(pytestconfig: pytest.Config) -> bool:
    """Return True when network tests must be skipped.

    Network tests require both:
    - explicit opt-in via `--network`
    - successful outbound connectivity probe
    """
    network_opt_in = bool(pytestconfig.getoption("--network"))
    if not network_opt_in:
        return True
    return not _has_outbound_connectivity()


@pytest.fixture(autouse=True)
def _network_guard(request: pytest.FixtureRequest, no_network: bool) -> None:
    """Skip network-marked tests when connectivity guard is active."""
    if no_network and "network" in request.node.keywords:
        pytest.skip(
            "Network tests disabled. Use --network with outbound connectivity to run."
        )


@pytest.fixture
def chembl_api_key() -> str | None:
    """Get ChEMBL API key from environment."""
    return os.environ.get("BIOETL_CHEMBL_API_KEY")


@pytest.fixture
def pubmed_api_key() -> str | None:
    """Get PubMed API key from environment."""
    return os.environ.get("BIOETL_PUBMED_API_KEY")


@pytest.fixture
def uniprot_api_key() -> str | None:
    """Get UniProt API key from environment."""
    return os.environ.get("BIOETL_UNIPROT_API_KEY")


# Common expected schema fields for contract verification
CHEMBL_ACTIVITY_REQUIRED_FIELDS = frozenset(
    {
        "activity_id",
        "assay_chembl_id",
        "molecule_chembl_id",
    }
)

CHEMBL_MOLECULE_REQUIRED_FIELDS = frozenset(
    {
        "molecule_chembl_id",
        "molecule_type",
    }
)

CHEMBL_TARGET_REQUIRED_FIELDS = frozenset(
    {
        "target_chembl_id",
        "target_type",
    }
)

UNIPROT_PROTEIN_REQUIRED_FIELDS = frozenset(
    {
        "primaryAccession",
        "uniProtkbId",
        "entryType",
    }
)

PUBCHEM_COMPOUND_REQUIRED_FIELDS = frozenset(
    {
        "molecule_id",
    }
)
