"""Tests for metadata helpers."""

import pytest

from bioetl.infrastructure.storage.metadata.metadata_helpers import (
    build_and_validate_metadata,
)


def test_build_and_validate_metadata_success():
    """Test build_and_validate_metadata function with valid data."""
    key = "test_key"
    value = "test_value"
    result = build_and_validate_metadata(key, value)
    assert result == {"key": value}


def test_build_and_validate_metadata_failure():
    """Test build_and_validate_metadata function with empty metadata."""
    # Mock the metadata to be empty
    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "bioetl.infrastructure.storage.metadata.metadata_helpers.build_and_validate_metadata",
            lambda x, y: {},
        )
        with pytest.raises(ValueError, match="Metadata is empty"):
            build_and_validate_metadata("test_key", "test_value")
