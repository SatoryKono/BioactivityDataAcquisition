import os
from pathlib import Path
from typing import Any

import pytest
from hypothesis import settings

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
