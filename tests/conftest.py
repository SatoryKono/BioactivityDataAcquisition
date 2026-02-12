import os
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlparse

from hypothesis import settings
import pytest
import vcr as vcrpy

# --- Hypothesis Configuration ---
# Profiles defined in docs/03-guides/testing.md
# ci: max_examples=10
# fast: max_examples=5
# dev: max_examples=50 (default)
# thorough: max_examples=200

settings.register_profile("ci", max_examples=10)
settings.register_profile("fast", max_examples=5)
settings.register_profile("dev", max_examples=50)
settings.register_profile("thorough", max_examples=200)

# Load profile from env or default to 'dev'
profile = os.getenv("HYPOTHESIS_PROFILE", "dev")
settings.load_profile(profile)


@pytest.fixture(scope="session", autouse=True)
def default_vcr_record_mode() -> None:
    """Set deterministic default VCR mode for local runs.

    - CI remains strict (`none`) to prevent silent cassette rewrites.
    - Local runs default to `once` to allow recording missing interactions.
    - Explicit VCR_RECORD_MODE always has priority.
    """
    if "VCR_RECORD_MODE" in os.environ:
        return

    os.environ["VCR_RECORD_MODE"] = "none" if os.getenv("CI") else "once"


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


@pytest.fixture
def isolated_registry() -> Any:
    """Return a fresh pipeline registry instance for test isolation."""
    from bioetl.composition.registry import create_registry

    return create_registry()


@pytest.fixture
def populated_isolated_registry(isolated_registry: Any) -> Any:
    """Return isolated registry pre-populated with all pipelines."""
    from bioetl.composition.factories.pipeline_factories import register_all_pipelines

    register_all_pipelines(registry=isolated_registry)
    return isolated_registry


# --- VCR Configuration ---
@pytest.fixture(scope="module")
def vcr_config() -> dict[str, object]:
    """VCR configuration for integration tests."""
    return {
        "filter_headers": ["authorization", "x-api-key", "cookie"],
        "filter_query_parameters": ["api_key", "key"],
        "ignore_localhost": True,
        "record_mode": "once",
    }


def _strip_email_query(uri: str) -> list[tuple[str, str]]:
    """Return query params excluding email for VCR matching."""
    query_params = parse_qsl(urlparse(uri).query, keep_blank_values=True)
    return [(key, value) for key, value in query_params if key.lower() != "email"]


def query_ignore_email(request_1: Any, request_2: Any) -> bool:
    """Custom VCR matcher that ignores email query parameter."""
    return _strip_email_query(request_1.uri) == _strip_email_query(request_2.uri)


@pytest.fixture(scope="module")
def vcr(vcr_config: dict[str, object]) -> Any:  # type: ignore[override]
    """Configure VCR instance with custom matchers."""
    vcr_instance = vcrpy.VCR(**vcr_config)
    vcr_instance.register_matcher("query_ignore_email", query_ignore_email)
    return vcr_instance
