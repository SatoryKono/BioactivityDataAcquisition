import enum
import os
import asyncio
import sys
from functools import cache
from pathlib import Path
from typing import Any

import pytest
from tests.helpers.vcr_config import (
    build_base_vcr_config,
    ensure_default_vcr_record_mode,
    is_vcr_recording_mode,
    is_git_lfs_pointer,
    query_ignore_email,
    resolve_requested_cassette_path,
)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register global test options."""
    parser.addoption(
        "--network",
        action="store_true",
        default=False,
        help="Enable tests that require outbound network connectivity.",
    )
    parser.addoption(
        "--live-api",
        action="store_true",
        default=False,
        help="Enable live API contract tests (equivalent to BIOETL_LIVE_API_TESTS=true).",
    )
    parser.addoption(
        "--pilot-soak",
        action="store_true",
        default=False,
        help="Enable richer pilot-only live contract suites (equivalent to BIOETL_PILOT_SOAK_TESTS=true).",
    )


def pytest_cmdline_main(config):
    # Workaround for xdist serialization error with enum-valued options
    # (historically syrupy's diff_mode). Avoid scanning every option attribute
    # because collection startup cost compounds across large suites.
    if hasattr(config, "option"):
        _normalize_enum_option(config.option, "diff_mode")


def pytest_configure(config):
    # Keep it here as well just in case
    _normalize_enum_option(config.option, "diff_mode")
    _configure_windows_asyncio(config)
    if _selected_paths_need_hypothesis(config):
        _configure_hypothesis_profiles()


def _configure_windows_asyncio(config: pytest.Config) -> None:
    """Tune pytest-asyncio defaults for Windows socket pressure."""
    if not sys.platform.startswith("win"):
        return

    # On Windows/Python 3.13, function-scoped loop creation across thousands of
    # async tests can exhaust socket buffers during socketpair() setup.
    config.inicfg["asyncio_default_test_loop_scope"] = "module"
    config.inicfg["asyncio_default_fixture_loop_scope"] = "module"


@pytest.fixture(scope="session")
def event_loop_policy() -> Any:
    """Use Selector policy on Windows to avoid Proactor loop socket pressure."""
    if sys.platform.startswith("win"):
        return asyncio.WindowsSelectorEventLoopPolicy()
    return asyncio.get_event_loop_policy()


def _normalize_enum_option(option_namespace: object, option_name: str) -> None:
    """Convert a known enum option to its primitive value for xdist safety."""
    if not hasattr(option_namespace, option_name):
        return
    try:
        value = getattr(option_namespace, option_name)
        if isinstance(value, enum.Enum):
            setattr(option_namespace, option_name, value.value)
    except (AttributeError, TypeError, ValueError):
        return


_PUBLICATION_CLASSIFICATION_TEST_PREFIXES = (
    "tests/integration/test_cross_provider_doi_normalization.py",
    "tests/integration/pipelines/test_crossref_date_normalization.py",
    "tests/integration/pipelines/test_pubmed_date_normalization.py",
    "tests/e2e/test_chembl_publication_e2e.py",
    "tests/e2e/test_chembl_publication_term_e2e.py",
    "tests/e2e/test_crossref_publication_e2e.py",
    "tests/e2e/test_openalex_publication_e2e.py",
    "tests/e2e/test_pubmed_publication_e2e.py",
    "tests/e2e/test_semanticscholar_publication_e2e.py",
)

_HYPOTHESIS_TEST_PREFIXES = (
    "tests/unit/domain/",
    "tests/architecture/",
    "tests/unit/application/composite/test_join_key_resolution_property.py",
)


def _selected_paths_need_hypothesis(config: pytest.Config) -> bool:
    """Load Hypothesis profiles only when the selected paths can execute them."""
    selected_args = getattr(config, "args", ())
    if not selected_args:
        return True

    normalized_args = []
    for arg in selected_args:
        if arg.startswith("-"):
            continue
        normalized = arg.split("::", 1)[0].replace("\\", "/")
        if normalized in {"tests", "tests/", "."}:
            return True
        normalized_args.append(normalized)

    if not normalized_args:
        return True

    return any(
        any(path.startswith(prefix) for prefix in _HYPOTHESIS_TEST_PREFIXES)
        for path in normalized_args
    )


def _configure_hypothesis_profiles() -> None:
    """Register project Hypothesis profiles lazily during pytest startup."""
    try:
        from hypothesis import settings as _hyp_settings
    except ImportError:  # pragma: no cover
        return

    _hyp_settings.register_profile("ci", max_examples=10)
    _hyp_settings.register_profile("fast", max_examples=5)
    _hyp_settings.register_profile("dev", max_examples=50)
    _hyp_settings.register_profile("thorough", max_examples=200)
    _hyp_settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "fast"))


@cache
def _load_vcrpy() -> Any:
    """Import vcr lazily so collect-only runs skip this dependency cost."""
    try:
        import vcr as vcrpy
    except ImportError:  # pragma: no cover
        return None
    return vcrpy


def _selected_tests_need_publication_type_classification(
    request: pytest.FixtureRequest,
) -> bool:
    """Return True when the current selection needs classification bootstrap."""
    items = getattr(request.session, "items", ())
    if not items:
        # Collect-only and nested collection runs do not execute publication
        # transformers and should avoid the global bootstrap cost.
        return False
    return any(
        item.nodeid.startswith(_PUBLICATION_CLASSIFICATION_TEST_PREFIXES)
        for item in items
    )


@pytest.fixture(scope="session", autouse=True)
def _init_publication_type_classification(request: pytest.FixtureRequest) -> None:
    """Initialize publication type classification data only for non-unit suites."""
    if not _selected_tests_need_publication_type_classification(request):
        return

    from bioetl.composition.bootstrap.runtime.classification_init import (
        initialize_publication_type_classification,
    )

    initialize_publication_type_classification(Path("configs"))


@pytest.fixture(scope="session", autouse=True)
def _sanitize_bioetl_env_vars() -> None:
    """Strip inline comments from BIOETL_ env vars.

    Some CI environments load .env.example with inline comments
    (e.g. ``100  # 1-10000``), which Pydantic interprets as invalid
    string values. This fixture strips everything after ``#`` for
    all BIOETL_ variables so Settings() can parse them correctly.
    """
    for key in tuple(os.environ):
        if key.startswith("BIOETL_"):
            val = os.environ[key]
            cleaned = _strip_inline_env_comment(val)
            if cleaned != val:
                os.environ[key] = cleaned


def _strip_inline_env_comment(value: str) -> str:
    hash_index = value.find("#")
    if hash_index == -1:
        return value
    prefix = value[:hash_index]
    stripped = prefix.rstrip()
    return stripped if stripped != value else value


@pytest.fixture(scope="session", autouse=True)
def default_vcr_record_mode() -> None:
    """Set deterministic default VCR mode for local runs.

    - CI remains strict (`none`) to prevent silent cassette rewrites.
    - Local runs also default to strict replay (`none`).
    - Explicit VCR_RECORD_MODE always has priority.
    """
    if "VCR_RECORD_MODE" not in os.environ:
        os.environ["VCR_RECORD_MODE"] = "none"
    ensure_default_vcr_record_mode()


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return repository root for path-based architecture checks."""
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def src_dir(project_root: Path) -> Path:
    """Return the `src` directory used by architecture tests."""
    src_path = project_root / "src"
    if not src_path.exists():
        pytest.skip("Source directory not found: src")
    return src_path


@pytest.fixture(scope="session")
def pyproject_toml(project_root: Path) -> Path:
    """Return path to pyproject.toml."""
    return project_root / "pyproject.toml"


@pytest.fixture
def isolated_registry() -> Any:
    """Return a fresh pipeline registry instance for test isolation."""
    from bioetl.composition.registry_api import create_registry

    return create_registry()


@pytest.fixture
def populated_isolated_registry(isolated_registry: Any) -> Any:
    """Return isolated registry pre-populated with all pipelines."""
    from bioetl.composition.factories.pipeline.registry import register_all_pipelines

    register_all_pipelines(registry=isolated_registry)
    return isolated_registry


@pytest.fixture(autouse=True)
def _vcr_marker(request: pytest.FixtureRequest) -> None:
    """Open pytest-vcr cassettes, skipping unresolved Git LFS pointers safely."""
    marker = request.node.get_closest_marker("vcr")
    if marker is None:
        return

    cassette_path = resolve_requested_cassette_path(request)
    if cassette_path is not None and is_git_lfs_pointer(cassette_path):
        if is_vcr_recording_mode():
            cassette_path.unlink(missing_ok=True)
        else:
            pytest.skip(
                "VCR cassette is a Git LFS pointer; run git lfs pull before replaying "
                f"this cassette: {cassette_path}"
            )

    request.getfixturevalue("vcr_cassette")


@pytest.fixture(scope="module")
def vcr_config() -> dict[str, object]:
    """VCR configuration for integration tests."""
    return build_base_vcr_config(
        filter_headers=["authorization", "x-api-key", "cookie"],
        filter_query_parameters=["api_key", "key"],
        ignore_localhost=True,
    )


@cache
def _load_pandas() -> Any:
    """Import pandas lazily so pytest collection stays lightweight."""
    try:
        import pandas as pd
    except ImportError:  # pragma: no cover
        return None
    return pd


@pytest.fixture
def vcr(  # type: ignore[override]
    vcr_config: dict[str, object],
    vcr_cassette_dir: Path | str,
) -> Any:
    """Configure VCR instance with custom matchers."""
    vcrpy = _load_vcrpy()
    if vcrpy is None:
        pytest.skip("vcrpy not installed")
    kwargs: dict[str, object] = {
        "cassette_library_dir": str(vcr_cassette_dir),
        "path_transformer": vcrpy.VCR.ensure_suffix(".yaml"),
    }
    kwargs.update(vcr_config)
    vcr_instance = vcrpy.VCR(**kwargs)
    vcr_instance.register_matcher("query_ignore_email", query_ignore_email)
    return vcr_instance


@pytest.fixture
def noop_logger():
    """Minimal no-op logger for tests."""
    from bioetl.infrastructure.observability.noop_logger import NoOpLogger

    return NoOpLogger()


# --- Publication Fixtures (Minimal DataFrames for Validation) ---

from tests.helpers.publication_fixtures import (
    CHEMBL_SPECIFIC,
    CROSSREF_SPECIFIC,
    OPENALEX_SPECIFIC,
    PUBMED_SPECIFIC,
    SEMANTIC_SCHOLAR_SPECIFIC,
    create_minimal_df as _create_minimal_df,
)


@pytest.fixture
def minimal_pubmed_publication_df():
    df = _create_minimal_df(
        PUBMED_SPECIFIC, "pubmed", "pubmed_12345678", "pmid", "12345678"
    )
    df["abstract_structured"] = False
    # Fix for TestPublicationTypeValid::test_pub_type_present
    df["publication_type"] = "Journal Article"
    return df


@pytest.fixture
def minimal_chembl_publication_df():
    df = _create_minimal_df(
        CHEMBL_SPECIFIC, "chembl", "CHEMBL123", "publication_id", "CHEMBL123"
    )
    df["publication_type"] = "journal-article"
    return df


@pytest.fixture
def minimal_semanticscholar_publication_df():
    return _create_minimal_df(
        SEMANTIC_SCHOLAR_SPECIFIC,
        "semanticscholar",
        "s2_" + "a" * 40,
        "paper_id",
        "a" * 40,
    )


@pytest.fixture
def minimal_openalex_publication_df():
    df = _create_minimal_df(
        OPENALEX_SPECIFIC, "openalex", "W12345678", "openalex_id", "W12345678"
    )
    df["is_retracted"] = False
    return df


@pytest.fixture
def minimal_crossref_publication_df():
    return _create_minimal_df(
        CROSSREF_SPECIFIC, "crossref", "10.1001/test", "doi", "10.1001/test"
    )
