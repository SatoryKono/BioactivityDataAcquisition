import os
from pathlib import Path

import pytest
from hypothesis import settings, Verbosity

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

# --- VCR Configuration ---
@pytest.fixture(scope="module")
def vcr_config():
    """VCR configuration for integration tests."""
    return {
        "filter_headers": ["authorization", "x-api-key", "cookie"],
        "filter_query_parameters": ["api_key", "key"],
        "ignore_localhost": True,
        "record_mode": "once",
    }