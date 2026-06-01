"""Tests for validation helpers."""

import pytest

from bioetl.domain.behavior.validation_helpers import validate_data


pytestmark = pytest.mark.unit

def test_validate_data_success():
    """Test validate_data function with valid data."""
    data = "test_data"
    validate_data(data)  # Should not raise an exception


def test_validate_data_failure():
    """Test validate_data function with empty data."""
    data = None
    with pytest.raises(ValueError, match="Data is empty"):
        validate_data(data)
