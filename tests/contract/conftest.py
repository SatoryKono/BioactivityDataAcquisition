"""Contract tests configuration and fixtures."""


import os
import socket
import threading
from functools import lru_cache

import pytest
import pytest_asyncio
from bioetl.domain.types import JsonDict
from tests.contract._provider_contract_replay import (
    PROVIDER_CONTRACT_REPLAY_PROBES,
    ProviderContractReplayProbe,
    load_provider_contract_replay_payload,
)


def _get_replay_probe(provider: str, probe: str) -> ProviderContractReplayProbe:
    for case in PROVIDER_CONTRACT_REPLAY_PROBES:
        if case.provider == provider and case.probe == probe:
            return case
    raise pytest.UsageError(
        f"No replay probe configured for {provider}.{probe}"
    )


def _load_semanticscholar_replay_payload(probe: str) -> object:
    case = _get_replay_probe("semanticscholar", probe)
    return load_provider_contract_replay_payload(case)


@pytest_asyncio.fixture
async def semanticscholar_search_payload() -> JsonDict:
    """Replay payload for Semantic Scholar free-text search contract."""
    payload = _load_semanticscholar_replay_payload("paper_search_endpoint")
    if not isinstance(payload, dict):
        raise AssertionError(
            "Semantic Scholar paper search replay payload must be a mapping"
        )
    return payload


@pytest_asyncio.fixture
async def semanticscholar_batch_payload() -> list[JsonDict | None]:
    """Replay payload for Semantic Scholar DOI batch lookup contract."""
    payload = _load_semanticscholar_replay_payload("paper_batch_lookup_by_doi")
    if not isinstance(payload, list):
        raise AssertionError(
            "Semantic Scholar DOI batch replay payload must be a list"
        )
    return payload

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

        if "pilot_soak" in item.keywords and not pilot_soak_enabled:
            item.add_marker(pytest.mark.pilot_soak)


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
    pilot_soak_enabled = bool(request.config.getoption("--pilot-soak")) or _is_truthy_env_var(
        "BIOETL_PILOT_SOAK_TESTS"
    )

    should_skip_network = no_network and "network" in request.node.keywords
    should_skip_pilot = (
        "pilot_soak" in request.node.keywords and not pilot_soak_enabled
    )
    if should_skip_network or should_skip_pilot:
        pytest.skip(
            "Pilot soak tests disabled. Enable via --pilot-soak "
            "or BIOETL_PILOT_SOAK_TESTS=true."
            if should_skip_pilot
            else "Network tests disabled. Enable --network or BIOETL_NETWORK_TESTS=true."
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
