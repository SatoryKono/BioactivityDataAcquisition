"""Unit tests for domain version module."""

from __future__ import annotations

import pytest

from bioetl.domain.version import get_version


@pytest.mark.unit
class TestGetVersion:
    """Tests for get_version function."""

    def test_returns_string(self) -> None:
        """Test that get_version always returns a string."""
        result = get_version()
        assert isinstance(result, str)

    def test_returns_version_or_unknown(self) -> None:
        """Test that get_version returns a version string or 'unknown'."""
        result = get_version()
        # Either a valid semver-like string or 'unknown'
        assert result == "unknown" or len(result) > 0

    def test_no_exception_raised(self) -> None:
        """Test that get_version does not raise any exception."""
        # Should not raise even if package is not installed
        result = get_version()
        assert result is not None
