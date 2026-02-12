import os
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