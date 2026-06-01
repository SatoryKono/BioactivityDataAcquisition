"""Tests for config helpers."""

import pytest

from bioetl.infrastructure.config.config_helpers import load_and_validate_config


pytestmark = pytest.mark.unit

def test_load_and_validate_config_success():
    """Test load_and_validate_config function with valid config."""
    # Mock the load_config function
    config = {"key": "value"}
    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "bioetl.infrastructure.config.config_helpers.load_config",
            lambda x: config,
        )
        result = load_and_validate_config("test_path")
        assert result == config


def test_load_and_validate_config_failure():
    """Test load_and_validate_config function with invalid config."""
    # Mock the load_config function to return None
    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "bioetl.infrastructure.config.config_helpers.load_config",
            lambda x: None,
        )
        with pytest.raises(ValueError, match="Config not found"):
            load_and_validate_config("test_path")
