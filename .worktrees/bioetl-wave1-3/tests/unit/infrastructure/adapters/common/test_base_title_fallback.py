"""Unit tests for BaseTitleFallbackHandler provider_prefix feature.

Tests the auto-generation of event names using provider_prefix parameter.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.adapters.common.base_title_fallback import (
    BaseTitleFallbackHandler,
)


class ConcreteFallbackHandler(BaseTitleFallbackHandler):
    """Concrete implementation for testing."""

    async def _search_by_title(self, title: str) -> dict[str, Any] | None:
        """Stub implementation."""
        return None


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger."""
    return MagicMock()


@pytest.mark.unit
class TestProviderPrefixEventNames:
    """Tests for provider_prefix event name auto-generation."""

    def test_event_names_with_provider_prefix(self, mock_logger: MagicMock) -> None:
        """Test all event names use provider prefix when provided."""
        handler = ConcreteFallbackHandler(mock_logger, provider_prefix="test_provider")

        assert handler._event_no_fallback_title == "test_provider_no_fallback_title"
        assert handler._event_fallback_attempt == "test_provider_title_fallback_attempt"
        assert handler._event_fallback_success == "test_provider_title_fallback_success"
        assert (
            handler._event_fallback_not_found
            == "test_provider_title_fallback_not_found"
        )
        assert handler._event_title_only_attempt == "test_provider_title_only_attempt"
        assert handler._event_title_only_success == "test_provider_title_only_success"
        assert (
            handler._event_title_only_not_found == "test_provider_title_only_not_found"
        )

    def test_event_names_without_provider_prefix(self, mock_logger: MagicMock) -> None:
        """Test default event names when provider_prefix is None."""
        handler = ConcreteFallbackHandler(mock_logger)

        assert handler._event_no_fallback_title == "no_fallback_title"
        assert handler._event_fallback_attempt == "title_fallback_attempt"
        assert handler._event_fallback_success == "title_fallback_success"
        assert handler._event_fallback_not_found == "title_fallback_not_found"
        assert handler._event_title_only_attempt == "title_only_attempt"
        assert handler._event_title_only_success == "title_only_success"
        assert handler._event_title_only_not_found == "title_only_not_found"

    def test_crossref_provider_prefix(self, mock_logger: MagicMock) -> None:
        """Test event names with crossref provider prefix."""
        handler = ConcreteFallbackHandler(mock_logger, provider_prefix="crossref")

        assert handler._event_no_fallback_title == "crossref_no_fallback_title"
        assert handler._event_fallback_attempt == "crossref_title_fallback_attempt"

    def test_openalex_provider_prefix(self, mock_logger: MagicMock) -> None:
        """Test event names with openalex provider prefix."""
        handler = ConcreteFallbackHandler(mock_logger, provider_prefix="openalex")

        assert handler._event_no_fallback_title == "openalex_no_fallback_title"
        assert handler._event_fallback_attempt == "openalex_title_fallback_attempt"

    def test_pubmed_provider_prefix(self, mock_logger: MagicMock) -> None:
        """Test event names with pubmed provider prefix."""
        handler = ConcreteFallbackHandler(mock_logger, provider_prefix="pubmed")

        assert handler._event_no_fallback_title == "pubmed_no_fallback_title"
        assert handler._event_fallback_attempt == "pubmed_title_fallback_attempt"


@pytest.mark.unit
class TestDefaultProcessFoundResult:
    """Tests for default _process_found_result implementation."""

    def test_process_found_result_adds_lookup_method(
        self, mock_logger: MagicMock
    ) -> None:
        """Test default _process_found_result adds _lookup_method."""
        handler = ConcreteFallbackHandler(mock_logger)
        result: dict[str, Any] = {"id": "123", "title": "Test"}

        processed = handler._process_found_result(result, "10.1234/test")

        assert processed["_lookup_method"] == "title_fallback"
        assert processed["_original_id"] == "10.1234/test"
        assert processed["id"] == "123"
        assert processed["title"] == "Test"

    def test_process_found_result_overwrites_existing_keys(
        self, mock_logger: MagicMock
    ) -> None:
        """Test _process_found_result overwrites existing keys."""
        handler = ConcreteFallbackHandler(mock_logger)
        result: dict[str, Any] = {
            "id": "123",
            "_lookup_method": "old_method",
            "_original_id": "old_id",
        }

        processed = handler._process_found_result(result, "10.1234/new")

        assert processed["_lookup_method"] == "title_fallback"
        assert processed["_original_id"] == "10.1234/new"


@pytest.mark.unit
class TestDefaultGetResultIdentifier:
    """Tests for default _get_result_identifier implementation."""

    def test_get_result_identifier_default(self, mock_logger: MagicMock) -> None:
        """Test default _get_result_identifier returns found_id."""
        handler = ConcreteFallbackHandler(mock_logger)
        result = {"id": "W123456789"}

        field_name, value = handler._get_result_identifier(result)

        assert field_name == "found_id"
        assert value == "W123456789"

    def test_get_result_identifier_missing_id(self, mock_logger: MagicMock) -> None:
        """Test _get_result_identifier with missing id returns 'unknown'."""
        handler = ConcreteFallbackHandler(mock_logger)
        result: dict[str, Any] = {"title": "Test"}

        field_name, value = handler._get_result_identifier(result)

        assert field_name == "found_id"
        assert value == "unknown"
