"""Contract tests configuration and fixtures.

Provides common fixtures for live API contract testing.
"""

from __future__ import annotations

import os
import socket
import threading
from functools import lru_cache

import pytest

_CONTRACT_PATH_TOKEN_POSIX = "/contract/"
_CONTRACT_PATH_TOKEN_WINDOWS = "\\contract\\"
_NETWORK_PROBE_HOSTS = (
    "www.ebi.ac.uk",
    "pubchem.ncbi.nlm.nih.gov",
    "rest.uniprot.org",
    "eutils.ncbi.nlm.nih.gov",
    "api.crossref.org",
    "api.openalex.org",
    "api.semanticscholar.org",
)
_NETWORK_PROBE_PORT = 443
_NETWORK_PROBE_TIMEOUT_SECONDS = 2.0
_NETWORK_PROBE_WALL_CLOCK_TIMEOUT_SECONDS = 2.5
_TRUTHY_ENV_VALUES = frozenset({"1", "true", "yes", "on"})


def pytest_configure(config: pytest.Config) -> None:
    """Register contract-suite markers used during collection-time mutation.

    ``network`` and ``pilot_soak`` are applied dynamically during collection,
    so keep a local fallback registration here even though the canonical marker
    inventory also lives in ``pyproject.toml``.
    """
    config.addinivalue_line("markers", "network: outbound-network contract tests")
    config.addinivalue_line("markers", "pilot_soak: richer pilot-only contract suites")
    config.addinivalue_line(
        "markers", "no_api: contract checks that do not require live API access"
    )
    config.addinivalue_line("markers", "chembl: ChEMBL contract provider tests")
    config.addinivalue_line("markers", "pubchem: PubChem contract provider tests")
    config.addinivalue_line("markers", "uniprot: UniProt contract provider tests")
    config.addinivalue_line("markers", "pubmed: PubMed contract provider tests")
    config.addinivalue_line("markers", "crossref: CrossRef contract provider tests")
    config.addinivalue_line("markers", "openalex: OpenAlex contract provider tests")
    config.addinivalue_line("markers", "semanticscholar: contract provider tests")


def _is_contract_test_path(path_str: str) -> bool:
    return (
        _CONTRACT_PATH_TOKEN_POSIX in path_str
        or _CONTRACT_PATH_TOKEN_WINDOWS in path_str
    )


def _is_truthy_env_var(name: str) -> bool:
    raw_value = os.environ.get(name, "")
    normalized_value = raw_value.strip().strip("\"'").lower()
    return normalized_value in _TRUTHY_ENV_VALUES


def _probe_host_connectivity(host: str) -> bool:
    try:
        with socket.create_connection(
            (host, _NETWORK_PROBE_PORT),
            timeout=_NETWORK_PROBE_TIMEOUT_SECONDS,
        ):
            return True
    except OSError:
        return False


def _probe_host_connectivity_bounded(host: str) -> bool:
    """Run one host probe with a hard wall-clock timeout.

    ``socket.create_connection`` bounds connect/read timeouts, but name
    resolution may still block in ``getaddrinfo`` on some platforms. Run the
    probe in a daemon thread so contract-test setup fail-closes quickly instead
    of hanging the whole suite.
    """

    outcome: list[bool] = []

    def _worker() -> None:
        outcome.append(_probe_host_connectivity(host))

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    thread.join(_NETWORK_PROBE_WALL_CLOCK_TIMEOUT_SECONDS)
    if thread.is_alive():
        return False
    return outcome[0] if outcome else False


@lru_cache(maxsize=1)
def _has_outbound_connectivity() -> bool:
    """Best-effort outbound connectivity probe for contract tests."""
    for host in _NETWORK_PROBE_HOSTS:
        if _probe_host_connectivity_bounded(host):
            return True
    return False


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skip contract tests if BIOETL_LIVE_API_TESTS is not set.

    Tests marked with 'no_api' are exempt from this requirement as they don't
    require live API access (e.g., schema introspection tests).
    """
    live_tests_enabled = bool(config.getoption("--live-api")) or _is_truthy_env_var(
        "BIOETL_LIVE_API_TESTS"
    )
    pilot_soak_enabled = bool(config.getoption("--pilot-soak")) or _is_truthy_env_var(
        "BIOETL_PILOT_SOAK_TESTS"
    )

    for item in items:
        if not _is_contract_test_path(str(item.fspath)):
            continue

        # Contract tests explicitly marked no_api are pure schema/contract checks
        # and must run without outbound connectivity.
        requires_network = "no_api" not in item.keywords
        if requires_network:
            item.add_marker(pytest.mark.network)

            if not live_tests_enabled:
                item.add_marker(
                    pytest.mark.skip(
                        reason=(
                            "Live API tests disabled. Enable via --live-api "
                            "or BIOETL_LIVE_API_TESTS=true."
                        )
                    )
                )

        if "pilot_soak" in item.keywords and not pilot_soak_enabled:
            item.add_marker(
                pytest.mark.skip(
                    reason=(
                        "Pilot soak tests disabled. Enable via --pilot-soak "
                        "or BIOETL_PILOT_SOAK_TESTS=true."
                    )
                )
            )


@pytest.fixture(scope="session")
def no_network(pytestconfig: pytest.Config) -> bool:
    """Return True when network tests must be skipped.

    Network tests require both:
    - explicit opt-in via `--network` or `BIOETL_NETWORK_TESTS=true`
    - successful outbound connectivity probe
    """
    network_opt_in = bool(pytestconfig.getoption("--network")) or _is_truthy_env_var(
        "BIOETL_NETWORK_TESTS"
    )
    if not network_opt_in:
        return True
    return not _has_outbound_connectivity()


@pytest.fixture(autouse=True)
def _network_guard(request: pytest.FixtureRequest, no_network: bool) -> None:
    """Skip network-marked tests when connectivity guard is active."""
    if no_network and "network" in request.node.keywords:
        pytest.skip(
            "Network tests disabled. Enable --network or BIOETL_NETWORK_TESTS=true."
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
