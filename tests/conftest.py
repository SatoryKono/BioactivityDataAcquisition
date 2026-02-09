from __future__ import annotations

import importlib.util
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    from vcr.request import Request

    from bioetl.domain.types import RunID

# VCR.py imports (for API recording)
try:
    import vcr

    VCR_AVAILABLE = True
except ImportError:
    vcr = None  # type: ignore[assignment]
    VCR_AVAILABLE = False

# Query parameters to ignore when matching VCR requests
# These parameters vary between test runs but don't affect the response content
_VCR_IGNORED_QUERY_PARAMS = {"email", "api_key", "apikey", "retmode"}


def _parse_query_params(uri: str) -> dict[str, list[str]]:
    """Parse query parameters from URI, returning sorted dict."""
    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(uri)
    return parse_qs(parsed.query)


def _query_matcher_ignoring_params(r1: Request, r2: Request) -> bool:
    """Custom VCR query matcher that ignores certain parameters.

    Ignores email, api_key parameters which vary between test runs
    but don't affect the API response content.
    """
    params1 = _parse_query_params(r1.uri)
    params2 = _parse_query_params(r2.uri)

    # Remove ignored parameters from comparison
    for param in _VCR_IGNORED_QUERY_PARAMS:
        params1.pop(param, None)
        params2.pop(param, None)

    return params1 == params2


# Register custom matcher with VCR at module level
# Monkey-patch the VCR class to include our custom matcher in default matchers
if VCR_AVAILABLE and vcr is not None:
    # Store original __init__ to chain call
    _original_vcr_init = vcr.VCR.__init__

    def _patched_vcr_init(self: Any, *args: Any, **kwargs: Any) -> None:
        _original_vcr_init(self, *args, **kwargs)
        # Register custom matcher on each VCR instance
        self.register_matcher("query_ignore_email", _query_matcher_ignoring_params)

    vcr.VCR.__init__ = _patched_vcr_init


def _is_plugin_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register placeholders for missing optional plugins."""
    if not _is_plugin_available("pytest_asyncio"):
        parser.addini(
            "asyncio_mode",
            "Asyncio plugin not installed; placeholder ini option to avoid config error",
            default="auto",
        )
        parser.addini(
            "asyncio_default_fixture_loop_scope",
            "Asyncio plugin not installed; placeholder ini option to avoid config error",
            default="function",
        )

    if not _is_plugin_available("pytest_cov"):
        parser.addoption(
            "--cov",
            action="append",
            dest="cov",
            default=[],
            help="pytest-cov not installed; install extras via pip install -e '.[dev]'",
        )
        parser.addoption(
            "--cov-report",
            action="append",
            dest="cov_report",
            default=[],
            help="pytest-cov not installed; install extras via pip install -e '.[dev]'",
        )


def pytest_configure() -> None:
    """Add src directory to Python path and mock missing modules."""
    import os

    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src"
    sys.path.insert(0, str(src_dir))

    # Set BIOETL_ENV to staging for tests to avoid dev environment validation
    # requiring endpoint_url
    os.environ.setdefault("BIOETL_ENV", "staging")

    # Configure Hypothesis profiles for CI vs local development
    # CI profile uses fewer examples for faster execution
    # IMPORTANT: Tests should NOT override max_examples in @settings() decorator
    # to allow profile settings to control test speed. See OPTIMIZATION.md.
    try:
        from hypothesis import Phase, Verbosity, settings

        # CI profile: faster execution with fewer examples
        # Used automatically in GitHub Actions (CI=true)
        settings.register_profile(
            "ci",
            max_examples=10,
            deadline=None,
            suppress_health_check=[],
            verbosity=Verbosity.quiet,
            phases=[Phase.explicit, Phase.reuse, Phase.generate],
        )
        # Fast profile: minimal examples for quick smoke tests
        # Use with: HYPOTHESIS_PROFILE=fast pytest ...
        settings.register_profile(
            "fast",
            max_examples=5,
            deadline=None,
            verbosity=Verbosity.quiet,
            phases=[Phase.explicit, Phase.reuse, Phase.generate],
        )
        # Dev profile: standard development settings
        # Default for local development
        settings.register_profile(
            "dev",
            max_examples=50,
            deadline=None,
            verbosity=Verbosity.normal,
        )
        # Thorough profile: comprehensive testing before releases
        # Use with: HYPOTHESIS_PROFILE=thorough pytest ...
        settings.register_profile(
            "thorough",
            max_examples=200,
            deadline=None,
            verbosity=Verbosity.normal,
        )

        # Select profile based on environment
        profile = os.environ.get("HYPOTHESIS_PROFILE", "dev")
        if os.environ.get("CI"):
            profile = "ci"
        settings.load_profile(profile)
    except ImportError:
        pass  # Hypothesis not installed

    # Mock pubchempy if not installed
    try:
        __import__("pubchempy")
    except ImportError:
        sys.modules["pubchempy"] = MagicMock()

    missing_plugins = []
    for plugin_name, install_hint in (
        ("pytest_asyncio", "pip install -e '.[dev]'"),
        ("pytest_cov", "pip install -e '.[dev]'"),
    ):
        if not _is_plugin_available(plugin_name):
            missing_plugins.append((plugin_name, install_hint))

    if missing_plugins:
        formatted = "\n".join(
            f"- {name} (установите: {hint})" for name, hint in missing_plugins
        )
        pytest.exit(
            "Отсутствуют обязательные плагины для тестов:\n"
            f"{formatted}\n"
            "Повторите установку зависимостей: pip install -e '.[dev]'",
            returncode=3,
        )


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Returns the root directory of the project."""
    # Assuming tests/conftest.py is one level deep in tests/
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def src_dir(project_root: Path) -> Path:
    return project_root / "src"


@pytest.fixture(scope="session")
def docs_dir(project_root: Path) -> Path:
    return project_root / "docs"


@pytest.fixture(scope="session")
def pyproject_toml(project_root: Path) -> Path:
    return project_root / "pyproject.toml"


@pytest.fixture(scope="session")
def requirements_md(project_root: Path) -> Path:
    return project_root / "REQUIREMENTS.md"


# =============================================================================
# VCR.py Configuration (RULES.md Section 4.2)
# =============================================================================


def _sanitize_request(request: Request) -> Request:
    """Sanitize secrets from recorded requests.

    Removes:
    - Authorization headers
    - API keys from query params and headers
    - PII data patterns

    Requirements:
    - REQ-TEST-002: Secret sanitization in before_record hook
    """
    if not VCR_AVAILABLE:
        return request

    # Sanitize headers
    headers_to_sanitize = [
        "Authorization",
        "X-API-Key",
        "Api-Key",
        "X-Api-Key",
        "Cookie",
        "Set-Cookie",
    ]
    for header in headers_to_sanitize:
        if header in request.headers:
            request.headers[header] = "REDACTED"
        # Also check lowercase
        if header.lower() in request.headers:
            request.headers[header.lower()] = "REDACTED"

    # Sanitize API keys in query params
    if "?" in request.uri:
        base_url, query = request.uri.split("?", 1)
        # Patterns to sanitize in query string
        patterns = [
            (r"api_key=[^&]+", "api_key=REDACTED"),
            (r"apikey=[^&]+", "apikey=REDACTED"),
            (r"access_token=[^&]+", "access_token=REDACTED"),
            (r"token=[^&]+", "token=REDACTED"),
        ]
        for pattern, replacement in patterns:
            query = re.sub(pattern, replacement, query, flags=re.IGNORECASE)
        request.uri = f"{base_url}?{query}"

    return request


def _sanitize_response(response: dict[str, Any]) -> dict[str, Any]:
    """Sanitize secrets and PII from recorded responses.

    Removes:
    - Sensitive headers (Set-Cookie, X-Request-Id)
    - Email addresses from response body (PII protection)

    Requirements:
    - REQ-TEST-002: Secret sanitization in before_record hook
    - REQ-SECRET-004: PII sanitization in VCR cassettes
    """
    # Remove sensitive headers from response
    headers_to_remove = ["Set-Cookie", "X-Request-Id"]
    if "headers" in response:
        for header in headers_to_remove:
            response["headers"].pop(header, None)
            response["headers"].pop(header.lower(), None)

    # Sanitize email addresses from response body (PII protection)
    # Pattern matches standard email format
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    email_pattern_bytes = rb"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

    if "body" in response:
        body = response["body"]
        # Handle string body
        if isinstance(body, str):
            response["body"] = re.sub(email_pattern, "redacted@example.com", body)
        # Handle bytes body
        elif isinstance(body, bytes):
            response["body"] = re.sub(
                email_pattern_bytes, b"redacted@example.com", body
            )
        # Handle dict with 'string' key (VCR internal format)
        elif isinstance(body, dict) and "string" in body:
            string_body = body["string"]
            if isinstance(string_body, str):
                body["string"] = re.sub(
                    email_pattern, "redacted@example.com", string_body
                )
            elif isinstance(string_body, bytes):
                body["string"] = re.sub(
                    email_pattern_bytes, b"redacted@example.com", string_body
                )

    return response


@pytest.fixture(scope="module")
def vcr_cassette_dir(request: pytest.FixtureRequest, project_root: Path) -> Path:
    """Return the directory for VCR cassettes based on test module.

    Supports provider-specific cassette directories:
    - tests/fixtures/vcr/chembl/ - ChEMBL adapter and pipeline tests
    - tests/fixtures/vcr/uniprot/ - UniProt adapter tests
    - tests/fixtures/vcr/pubmed/ - PubMed adapter tests
    - tests/fixtures/vcr/pubchem/ - PubChem tests
    - tests/fixtures/vcr/crossref/ - CrossRef tests
    - tests/fixtures/vcr/openalex/ - OpenAlex tests
    - tests/fixtures/vcr/semanticscholar/ - SemanticScholar tests
    - tests/fixtures/vcr/ - Cross-provider and general E2E tests

    Falls back to test module path if no provider-specific directory exists.
    """
    test_file = Path(request.fspath)
    test_filename = test_file.stem  # e.g., "test_pubmed" or "test_chembl_activity_e2e"

    # Provider-specific directory mapping based on test filename
    provider_dirs = {
        "chembl": ["chembl", "test_chembl"],
        "uniprot": ["uniprot", "test_uniprot"],
        "pubmed": ["pubmed", "test_pubmed"],
        "pubchem": ["pubchem", "test_pubchem"],
        "crossref": ["crossref", "test_crossref"],
        "openalex": ["openalex", "test_openalex"],
        "semanticscholar": ["semanticscholar", "test_semantic"],
    }

    vcr_base = project_root / "tests" / "fixtures" / "vcr"

    # Check for provider-specific directory
    for provider, patterns in provider_dirs.items():
        if any(pattern in test_filename.lower() for pattern in patterns):
            provider_dir = vcr_base / provider
            if provider_dir.exists():
                return provider_dir

    # Fallback to test module path structure
    relative_path = test_file.relative_to(project_root / "tests")
    cassette_dir = vcr_base / relative_path.parent
    cassette_dir.mkdir(parents=True, exist_ok=True)
    return cassette_dir


@pytest.fixture(scope="module")
def vcr_config(project_root: Path) -> dict[str, Any]:
    """VCR.py configuration.

    CI mode: record_mode="none" - fail if cassette missing
    Local recording: pytest --vcr-record=new_episodes
    """
    import os

    cassette_library_dir = project_root / "tests" / "fixtures" / "vcr"
    cassette_library_dir.mkdir(parents=True, exist_ok=True)

    # Use "none" in CI (fail if cassette missing), "new_episodes" locally
    record_mode = os.environ.get("VCR_RECORD_MODE", "none")

    return {
        "cassette_library_dir": str(cassette_library_dir),
        # CI mode: fail if cassette is missing
        # Override with VCR_RECORD_MODE=new_episodes for local recording
        "record_mode": record_mode,
        # Custom query matcher ignores email/api_key parameters
        # which vary between test runs but don't affect API responses
        "match_on": [
            "method",
            "scheme",
            "host",
            "port",
            "path",
            "query_ignore_email",
        ],
        "before_record_request": _sanitize_request,
        "before_record_response": _sanitize_response,
        "filter_headers": [
            "Authorization",
            "X-API-Key",
            "Cookie",
            "Set-Cookie",
        ],
        "decode_compressed_response": True,
    }


# =============================================================================
# Test Fixtures for Infrastructure Components
# =============================================================================


@pytest.fixture
def run_id() -> RunID:
    """Generate a unique run ID for tests."""
    return uuid4()


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear the settings cache before and after each test."""
    try:
        from bioetl.infrastructure.config import get_pipeline_config, get_settings

        get_settings.cache_clear()
        get_pipeline_config.cache_clear()
        yield
        get_settings.cache_clear()
        get_pipeline_config.cache_clear()
    except ImportError:
        yield


@pytest.fixture(scope="module")
def token_bucket():
    """Token bucket rate limiter for testing.

    Module-scoped for performance: TokenBucket is stateless for tests.
    """
    from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket

    return TokenBucket(rate=100.0, capacity=100)


@pytest.fixture(scope="module")
def circuit_breaker():
    """Circuit breaker for testing.

    Module-scoped for performance: CircuitBreaker state is reset per module.
    """
    from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker

    return CircuitBreaker(provider="test", failure_threshold=5, recovery_timeout=60)


# =============================================================================
# Shared Mock Fixtures (Performance Optimization)
# Consolidates commonly duplicated fixtures across test modules
# =============================================================================


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing.

    Consolidated fixture to avoid duplication across test modules.
    Provides bind() method that returns self for chaining.
    """
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    return logger


@pytest.fixture(scope="module")
def noop_logger():
    """Provide a NoOpLogger for tests.

    Module-scoped for performance: NoOpLogger is stateless.
    """
    from bioetl.infrastructure.observability.noop_logger import NoOpLogger

    return NoOpLogger()


@pytest.fixture(scope="module")
def noop_metrics():
    """Provide NoOpMetrics for tests.

    Module-scoped for performance: NoOpMetrics is stateless.
    """
    from bioetl.infrastructure.observability.noop_metrics import NoOpMetrics

    return NoOpMetrics()


@pytest.fixture(scope="module")
def noop_tracer():
    """Provide NoOpTracing for tests.

    Module-scoped for performance: NoOpTracing is stateless.
    """
    from bioetl.infrastructure.observability.noop_tracing import NoOpTracing

    return NoOpTracing()


# =============================================================================
# Isolated Registry Fixtures for Test Isolation
# =============================================================================


@pytest.fixture
def isolated_registry():
    """Create an isolated PipelineRegistry for test isolation.

    Use this fixture for tests that need to register/unregister pipelines
    without affecting other tests or global state.

    Returns:
        A new empty PipelineRegistry instance.

    Example:
        def test_my_feature(isolated_registry):
            from bioetl.composition.factories.pipeline_factories import register_all_pipelines
            register_all_pipelines(registry=isolated_registry)
            # Test uses isolated_registry...
    """
    from bioetl.composition.registry import create_registry

    return create_registry()


@pytest.fixture
def populated_isolated_registry(isolated_registry):
    """Create an isolated PipelineRegistry with all pipelines registered.

    Use this fixture when you need a fully-populated registry that is
    isolated from other tests. Ideal for parallel test execution.

    Returns:
        A PipelineRegistry instance with all pipelines registered.

    Example:
        def test_pipeline_lookup(populated_isolated_registry):
            definition = populated_isolated_registry.get("chembl_activity")
            assert definition.factory.pipeline_name == "chembl_activity"
    """
    from bioetl.composition.factories.pipeline_factories import register_all_pipelines

    register_all_pipelines(registry=isolated_registry)
    return isolated_registry


# =============================================================================
# DQ Config Test Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def test_dq_configs_path() -> Path:
    """Path to test DQ config fixtures.

    Returns:
        Path to tests/fixtures/configs directory with test DQ configs.

    Example:
        def test_dq_loading(test_dq_configs_path):
            loader = DQConfigLoader(test_dq_configs_path)
            config = loader.load("test_provider", "test_entity")
    """
    return Path(__file__).parent / "fixtures" / "configs"


@pytest.fixture
def isolated_dq_loader(tmp_path: Path) -> Any:
    """Create DQConfigLoader with isolated test configs.

    Copies test fixtures to a temporary directory for test isolation.
    Use this when tests need to modify configs without affecting other tests.

    Args:
        tmp_path: pytest tmp_path fixture.

    Returns:
        DQConfigLoader instance with isolated configs.

    Example:
        def test_dq_modification(isolated_dq_loader):
            config = isolated_dq_loader.load("test_provider", "test_entity")
            assert config.soft_fail_threshold == 0.05
    """
    import shutil

    from bioetl.infrastructure.config.dq_config_loader import DQConfigLoader

    # Copy fixtures to tmp_path for isolation
    fixtures = Path(__file__).parent / "fixtures" / "configs" / "dq"
    if fixtures.exists():
        shutil.copytree(fixtures, tmp_path / "dq")

    return DQConfigLoader(tmp_path)


@pytest.fixture(scope="module")
def real_dq_loader() -> Any:
    """Create DQConfigLoader with real production configs.

    Module-scoped for performance. Use for integration tests that need
    to verify behavior against real config files.

    Returns:
        DQConfigLoader instance pointing to configs/ directory.

    Example:
        @pytest.mark.integration
        def test_chembl_dq(real_dq_loader):
            config = real_dq_loader.load("chembl", "activity")
            assert config.hard_fail_threshold == 0.15
    """
    from bioetl.infrastructure.config.dq_config_loader import DQConfigLoader

    return DQConfigLoader(Path("configs"))


# =============================================================================
# Publication Validation Test Fixtures
# (Migrated from tests_generated/conftest.py)
# =============================================================================


@pytest.fixture
def minimal_chembl_publication_df() -> Any:
    """Minimal valid ChEMBL publication record."""
    import pandas as pd

    return pd.DataFrame(
        [
            {
                # Primary identifier
                "document_chembl_id": "CHEMBL1234567",
                # ETL metadata (required by ETLRecordSchema)
                "entity_id": "CHEMBL1234567",
                "_run_id": str(uuid4()),
                "_run_type": "incremental",
                "_ingestion_ts": datetime.now().isoformat(),
                "_source_batch_id": None,
                "_index": 0,
                # Cross-reference identifiers
                "pmid": "12345678",
                "doi": "10.1234/test.2024.001",
                "pmc_id": "PMC1234567",
                # Core content
                "title": "Test Publication Title",
                "abstract": "Test abstract text for validation.",
                "authors": '["Author A", "Author B"]',
                "affiliation_list": '["Institution A"]',
                # Journal information
                "journal": "Test Journal",
                "volume": "10",
                "issue": "5",
                "page_first": "100",
                "page_last": "110",
                # Publication metadata
                "publication_year": 2024,
                "publication_date": "2024-01-15",
                "publication_type": "PUBLICATION",
                "language": "eng",
                # Metrics
                "citations_received": 10,
                "citations_made": 5,
                "is_oa": True,
                # Author identifiers
                "author_orcids": None,
                # Provider-specific
                "src_id": 123,
                "chembl_release": "CHEMBL_34",
                "creation_date": "2024-01-01",
                # System fields
                "content_hash": "a" * 64,
                "_source": "chembl",
                "_lookup_method": "direct",
                "_original_id": "CHEMBL1234567",
                "_dq_warn": False,
                "_dq_error": False,
            }
        ]
    )


@pytest.fixture
def minimal_pubmed_publication_df() -> Any:
    """Minimal valid PubMed publication record."""
    import pandas as pd

    return pd.DataFrame(
        [
            {
                # Primary identifier
                "pmid": "12345678",
                # ETL metadata (required by ETLRecordSchema)
                "entity_id": "12345678",
                "_run_id": str(uuid4()),
                "_run_type": "incremental",
                "_ingestion_ts": datetime.now().isoformat(),
                "_source_batch_id": None,
                "_index": 0,
                # Cross-reference identifiers
                "doi": "10.1234/test.2024.001",
                "pmc_id": "PMC1234567",
                # Core content
                "title": "Test PubMed Publication",
                "abstract": "Test abstract for PubMed validation.",
                "authors": '["Author A", "Author B"]',
                "affiliation_list": '["Institution A"]',
                "author_count": 2,
                # Journal information
                "journal": "Test Journal",
                "journal_name_short": "Test J",
                "issn": "1234-5678",
                "country": "USA",
                "page_first": "100",
                "page_last": "110",
                # Publication metadata
                "publication_year": 2024,
                "publication_date": "2024-01-15",
                "publication_type": "PUBLICATION",
                "language": "eng",
                # Metrics
                "citations_received": 10,
                "citations_made": 5,
                "is_oa": True,
                # PubMed-specific fields (nullable strings)
                "pii": None,
                "mid": None,
                "publisher_id": None,
                "abstract_structured": None,
                "journal_iso_abbrev": None,
                "journal_issn_type": None,
                "nlm_unique_id": None,
                "medline_pgn": None,
                "page_range": None,
                # PubMed int fields (use real values to avoid int64 coercion issues)
                "pub_month": 1,
                "pub_day": 15,
                "publication_status": None,
                "publication_type_list": None,
                "date_completed": "2024-01-10",
                "date_revised": "2024-02-01",
                "citation_subset": None,
                "affiliation_structured": None,
                "mesh_heading_count": 0,
                "keyword_count": 0,
                "grant_count": 0,
                "chemical_count": 0,
                "subject_mesh": None,
                "chemicals": None,
                "subject_keywords": None,
                "databanks": None,
                "gene_symbols": None,
                "publication_types": None,
                "authors_with_affiliations": None,
                # Author identifiers
                "author_orcids": None,
                # System fields
                "content_hash": "b" * 64,
                "_source": "pubmed",
                "_lookup_method": "direct",
                "_original_id": "12345678",
                "_dq_warn": False,
                "_dq_error": False,
            }
        ]
    )


@pytest.fixture
def minimal_crossref_publication_df() -> Any:
    """Minimal valid CrossRef publication record."""
    import pandas as pd

    return pd.DataFrame(
        [
            {
                # Primary identifier
                "doi": "10.1234/test.2024.001",
                # ETL metadata (required by ETLRecordSchema)
                "entity_id": "10.1234/test.2024.001",
                "_run_id": str(uuid4()),
                "_run_type": "incremental",
                "_ingestion_ts": datetime.now().isoformat(),
                "_source_batch_id": None,
                "_index": 0,
                # Cross-reference identifiers
                "pmid": "12345678",
                "pmc_id": None,
                # Core content
                "title": "Test CrossRef Publication",
                "abstract": "Test abstract for CrossRef validation.",
                "authors": '["Author A", "Author B"]',
                "affiliation_list": '["Institution A"]',
                # Journal information
                "journal": "Test Journal",
                "issn": "1234-5678",
                "publisher": "Test Publisher",
                "page_first": "100",
                "page_last": "110",
                # Publication metadata
                "publication_year": 2024,
                "publication_date": "2024-01-15",
                "publication_type": "journal-article",
                "language": "en",
                # Metrics
                "citations_received": 10,
                "citations_made": 5,
                "is_oa": True,
                # CrossRef-specific fields (all nullable)
                "issn_list": None,
                "published_print": None,
                "published_online": None,
                "license_url": None,
                "subject_keywords": None,
                "content_domain_domains": None,
                "content_domain_crossmark_restriction": None,
                "alternative_id": None,
                "published": None,
                "journal_name_short": None,
                "issn_print": None,
                "issn_electronic": None,
                "author_orcids": None,
                "author_details": None,
                "references": None,
                # System fields
                "content_hash": "c" * 64,
                "_source": "crossref",
                "_lookup_method": "doi",
                "_original_id": "10.1234/test.2024.001",
                "_dq_warn": False,
                "_dq_error": False,
            }
        ]
    )


@pytest.fixture
def minimal_openalex_publication_df() -> Any:
    """Minimal valid OpenAlex publication record."""
    import pandas as pd

    return pd.DataFrame(
        [
            {
                # Primary identifier
                "openalex_id": "W2148763428",
                # ETL metadata (required by ETLRecordSchema)
                "entity_id": "W2148763428",
                "_run_id": str(uuid4()),
                "_run_type": "incremental",
                "_ingestion_ts": datetime.now().isoformat(),
                "_source_batch_id": None,
                "_index": 0,
                # Cross-reference identifiers
                "doi": "10.1234/test.2024.001",
                "pmid": "12345678",
                "pmc_id": "PMC1234567",
                # Core content
                "title": "Test OpenAlex Publication",
                "abstract": "Test abstract for OpenAlex validation.",
                "authors": '["Author A", "Author B"]',
                "affiliation_list": '["Institution A"]',
                # Journal information
                "journal": "Test Journal",
                "page_first": "100",
                "page_last": "110",
                # Publication metadata
                "publication_year": 2024,
                "publication_date": "2024-01-15",
                "publication_type": "article",
                "language": "en",
                # Metrics
                "citations_received": 10,
                "citations_made": 5,
                "is_oa": True,
                "oa_status": "gold",
                "fwci": 1.5,
                "is_retracted": False,
                # OpenAlex-specific fields (all nullable)
                "issn": None,
                "publisher": None,
                "volume": None,
                "issue": None,
                "subject_topics": None,
                "primary_topic": None,
                "grants": None,
                "subject_mesh": None,
                "subject_keywords": None,
                "mag_id": None,
                "author_orcids": None,
                "author_openalex_ids": None,
                "institution_ids": None,
                "institution_country_codes": None,
                "ror_ids": None,
                # System fields
                "content_hash": "d" * 64,
                "_source": "openalex",
                "_lookup_method": "doi",
                "_original_id": "10.1234/test.2024.001",
                "_dq_warn": False,
                "_dq_error": False,
            }
        ]
    )


@pytest.fixture
def minimal_semanticscholar_publication_df() -> Any:
    """Minimal valid SemanticScholar publication record."""
    import pandas as pd

    return pd.DataFrame(
        [
            {
                # Primary identifier (40-char hex)
                "paper_id": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
                # ETL metadata (required by ETLRecordSchema)
                "entity_id": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
                "_run_id": str(uuid4()),
                "_run_type": "incremental",
                "_ingestion_ts": datetime.now().isoformat(),
                "_source_batch_id": None,
                "_index": 0,
                # Cross-reference identifiers
                "doi": "10.1234/test.2024.001",
                "pmid": "12345678",
                "pmc_id": None,
                "corpus_id": 12345,
                # Core content
                "title": "Test S2 Publication",
                "abstract": "Test abstract for SemanticScholar validation.",
                "authors": '["Author A", "Author B"]',
                "affiliation_list": '["Institution A"]',
                # Journal information
                "journal": "Test Journal",
                "page_first": "100",
                "page_last": "110",
                # Publication metadata
                "publication_year": 2024,
                "publication_date": "2024-01-15",
                "publication_type": "JournalArticle",
                "language": None,
                # Metrics
                "citations_received": 10,
                "citations_made": 5,
                "influential_citation_count": 5,
                "is_oa": True,
                "oa_status": "gold",
                # SemanticScholar-specific fields (all nullable)
                "dblp_id": None,
                "tldr": None,
                "volume": None,
                "page_range": None,
                "open_access_url": None,
                "subject_fields": None,
                "publication_types": None,
                "author_s2_ids": None,
                "author_orcids": None,
                "author_h_indices": None,
                "citation_contexts": None,
                # System fields
                "content_hash": "e" * 64,
                "_source": "semanticscholar",
                "_lookup_method": "doi",
                "_original_id": "10.1234/test.2024.001",
                "_dq_warn": False,
                "_dq_error": False,
            }
        ]
    )
