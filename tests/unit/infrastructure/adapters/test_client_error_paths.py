"""Tests for API client error handling paths.

Tests that silent failures have been replaced with proper logging
and configurable error handling based on BIOETL_STRICT_ERROR_HANDLING.
"""

import logging
import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


@pytest.fixture(autouse=True)
def reset_settings_cache():
    """Reset settings cache before each test."""
    from bioetl.infrastructure.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def mock_settings_strict():
    """Mock settings with strict_error_handling=True."""
    env_vars = {
        "BIOETL_STRICT_ERROR_HANDLING": "true",
        "BIOETL_ENV": "staging",  # Avoid endpoint_url validation
    }
    with patch.dict(os.environ, env_vars):
        from bioetl.infrastructure.config import get_settings

        get_settings.cache_clear()
        yield get_settings()
        get_settings.cache_clear()


@pytest.fixture
def mock_settings_lenient():
    """Mock settings with strict_error_handling=False."""
    env_vars = {
        "BIOETL_STRICT_ERROR_HANDLING": "false",
        "BIOETL_ENV": "staging",  # Avoid endpoint_url validation
    }
    with patch.dict(os.environ, env_vars):
        from bioetl.infrastructure.config import get_settings

        get_settings.cache_clear()
        yield get_settings()
        get_settings.cache_clear()


class TestUniProtClientErrorPaths:
    """Tests for UniProt client error handling."""

    @pytest.fixture
    def mock_http_client(self):
        """Create a mock httpx.AsyncClient."""
        client = AsyncMock(spec=httpx.AsyncClient)
        return client

    @pytest.fixture
    def mock_circuit_breaker(self):
        """Create a mock circuit breaker that raises an exception."""
        from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker

        cb = MagicMock(spec=CircuitBreaker)
        cb.call = AsyncMock(side_effect=ConnectionError("Network error"))
        return cb

    async def test_fetch_next_page_logs_error_on_failure(
        self, mock_http_client, caplog
    ):
        """Test that _fetch_next_page logs error when fetch fails."""
        from bioetl.infrastructure.adapters.uniprot.client import UniProtClient

        with patch.dict(
            os.environ,
            {"BIOETL_STRICT_ERROR_HANDLING": "false", "BIOETL_ENV": "staging"},
        ):
            client = UniProtClient()
            client.http_client = mock_http_client

            # Make circuit_breaker.call raise an exception
            client.circuit_breaker.call = AsyncMock(
                side_effect=ConnectionError("Network error")
            )

            with caplog.at_level(logging.ERROR):
                results, cursor = await client._fetch_next_page(
                    query="test", size=10, fetched=0, limit=100, cursor=None
                )

            # Should return empty results on failure
            assert results == []
            assert cursor is None

            # Should have logged the error
            assert "UniProt protein fetch failed" in caplog.text
            # Check that the exception info is in the log
            error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
            assert len(error_records) >= 1
            assert "Network error" in error_records[0].exc_text

    async def test_fetch_next_page_raises_in_strict_mode(self, mock_http_client):
        """Test that _fetch_next_page raises exception in strict mode."""
        from bioetl.infrastructure.adapters.uniprot.client import UniProtClient

        with patch.dict(
            os.environ,
            {"BIOETL_STRICT_ERROR_HANDLING": "true", "BIOETL_ENV": "staging"},
        ):
            from bioetl.infrastructure.config import get_settings

            get_settings.cache_clear()

            client = UniProtClient()
            client.http_client = mock_http_client

            # Make circuit_breaker.call raise an exception
            client.circuit_breaker.call = AsyncMock(
                side_effect=ConnectionError("Network error")
            )

            with pytest.raises(ConnectionError, match="Network error"):
                await client._fetch_next_page(
                    query="test", size=10, fetched=0, limit=100, cursor=None
                )

    async def test_fetch_features_logs_warning_on_failure(
        self, mock_http_client, caplog
    ):
        """Test that _fetch_features logs warning when fetch fails."""
        from bioetl.infrastructure.adapters.uniprot.client import UniProtClient

        with patch.dict(
            os.environ,
            {"BIOETL_STRICT_ERROR_HANDLING": "false", "BIOETL_ENV": "staging"},
        ):
            from bioetl.infrastructure.config import get_settings

            get_settings.cache_clear()

            client = UniProtClient()
            client.http_client = mock_http_client

            # Make circuit_breaker.call raise an exception
            client.circuit_breaker.call = AsyncMock(
                side_effect=TimeoutError("Request timeout")
            )

            with caplog.at_level(logging.WARNING):
                results = [r async for r in client._fetch_features("P12345", limit=10)]

            # Should return empty results on failure
            assert results == []

            # Should have logged the warning
            assert "UniProt feature fetch failed" in caplog.text
            # Check that the exception info is in the log
            warning_records = [
                r for r in caplog.records if r.levelno == logging.WARNING
            ]
            assert len(warning_records) >= 1
            assert "Request timeout" in warning_records[0].exc_text

    async def test_fetch_features_raises_in_strict_mode(self, mock_http_client):
        """Test that _fetch_features raises exception in strict mode."""
        from bioetl.infrastructure.adapters.uniprot.client import UniProtClient

        with patch.dict(
            os.environ,
            {"BIOETL_STRICT_ERROR_HANDLING": "true", "BIOETL_ENV": "staging"},
        ):
            from bioetl.infrastructure.config import get_settings

            get_settings.cache_clear()

            client = UniProtClient()
            client.http_client = mock_http_client

            # Make circuit_breaker.call raise an exception
            client.circuit_breaker.call = AsyncMock(
                side_effect=TimeoutError("Request timeout")
            )

            with pytest.raises(TimeoutError, match="Request timeout"):
                _ = [r async for r in client._fetch_features("P12345", limit=10)]

    async def test_fetch_sequences_logs_warning_on_failure(
        self, mock_http_client, caplog
    ):
        """Test that _fetch_sequences logs warning when fetch fails."""
        from bioetl.infrastructure.adapters.uniprot.client import UniProtClient

        with patch.dict(
            os.environ,
            {"BIOETL_STRICT_ERROR_HANDLING": "false", "BIOETL_ENV": "staging"},
        ):
            from bioetl.infrastructure.config import get_settings

            get_settings.cache_clear()

            client = UniProtClient()
            client.http_client = mock_http_client

            # Make circuit_breaker.call raise an exception
            client.circuit_breaker.call = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Server error",
                    request=MagicMock(),
                    response=MagicMock(status_code=500),
                )
            )

            with caplog.at_level(logging.WARNING):
                results = [
                    r async for r in client._fetch_sequences("gene:TP53", limit=10)
                ]

            # Should return empty results on failure
            assert results == []

            # Should have logged the warning
            assert "UniProt sequence fetch failed" in caplog.text

    async def test_fetch_sequences_raises_in_strict_mode(self, mock_http_client):
        """Test that _fetch_sequences raises exception in strict mode."""
        from bioetl.infrastructure.adapters.uniprot.client import UniProtClient

        with patch.dict(
            os.environ,
            {"BIOETL_STRICT_ERROR_HANDLING": "true", "BIOETL_ENV": "staging"},
        ):
            from bioetl.infrastructure.config import get_settings

            get_settings.cache_clear()

            client = UniProtClient()
            client.http_client = mock_http_client

            # Make circuit_breaker.call raise an exception
            error = httpx.HTTPStatusError(
                "Server error",
                request=MagicMock(),
                response=MagicMock(status_code=500),
            )
            client.circuit_breaker.call = AsyncMock(side_effect=error)

            with pytest.raises(httpx.HTTPStatusError):
                _ = [r async for r in client._fetch_sequences("gene:TP53", limit=10)]


class TestPubChemClientErrorPaths:
    """Tests for PubChem client error handling."""

    @pytest.fixture
    def mock_pubchempy(self):
        """Mock pubchempy module."""
        mock_pcp = MagicMock()
        mock_pcp.get_compounds = MagicMock(return_value=[])
        return mock_pcp

    async def test_fetch_compounds_incremental_logs_error_on_failure(self, caplog):
        """Test that _fetch_compounds_incremental logs error when fetch fails."""
        from bioetl.infrastructure.adapters.pubchem.client import PubChemClient

        with patch.dict(
            os.environ,
            {"BIOETL_STRICT_ERROR_HANDLING": "false", "BIOETL_ENV": "staging"},
        ):
            from bioetl.infrastructure.config import get_settings

            get_settings.cache_clear()

            client = PubChemClient()

            # Make circuit_breaker.call raise an exception
            client.circuit_breaker.call = AsyncMock(
                side_effect=[
                    ConnectionError("PubChem API error"),
                    [],  # Second call returns empty to break loop
                ]
            )

            with caplog.at_level(logging.ERROR):
                results = []
                async for result in client._fetch_compounds_incremental(
                    watermark=1000, limit=50
                ):
                    results.append(result)

            # Should continue after error (returns empty due to second mock call)
            assert "PubChem compound batch fetch failed" in caplog.text
            # Check that the exception info is in the log
            error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
            assert len(error_records) >= 1
            assert "PubChem API error" in error_records[0].exc_text

    async def test_fetch_compounds_incremental_raises_in_strict_mode(self):
        """Test that _fetch_compounds_incremental raises exception in strict mode."""
        from bioetl.infrastructure.adapters.pubchem.client import PubChemClient

        with patch.dict(
            os.environ,
            {"BIOETL_STRICT_ERROR_HANDLING": "true", "BIOETL_ENV": "staging"},
        ):
            from bioetl.infrastructure.config import get_settings

            get_settings.cache_clear()

            client = PubChemClient()

            # Make circuit_breaker.call raise an exception
            client.circuit_breaker.call = AsyncMock(
                side_effect=ConnectionError("PubChem API error")
            )

            with pytest.raises(ConnectionError, match="PubChem API error"):
                _ = [
                    r
                    async for r in client._fetch_compounds_incremental(
                        watermark=1000, limit=50
                    )
                ]


class TestStrictErrorHandlingConfig:
    """Tests for the strict_error_handling configuration."""

    def test_default_is_false(self):
        """Test that strict_error_handling defaults to False."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear any existing env vars that might affect the test
            os.environ.pop("BIOETL_STRICT_ERROR_HANDLING", None)

            from bioetl.infrastructure.config import Settings

            settings = Settings(test_mode=True)
            assert settings.strict_error_handling is False

    def test_can_be_enabled_via_env_var(self):
        """Test that strict_error_handling can be enabled via env var."""
        with patch.dict(
            os.environ,
            {"BIOETL_STRICT_ERROR_HANDLING": "true", "BIOETL_ENV": "staging"},
        ):
            from bioetl.infrastructure.config import Settings

            settings = Settings(test_mode=True)
            assert settings.strict_error_handling is True

    def test_env_var_case_insensitive(self):
        """Test that env var values are case-insensitive."""
        with patch.dict(
            os.environ,
            {"BIOETL_STRICT_ERROR_HANDLING": "True", "BIOETL_ENV": "staging"},
        ):
            from bioetl.infrastructure.config import Settings

            settings = Settings(test_mode=True)
            assert settings.strict_error_handling is True

        with patch.dict(
            os.environ,
            {"BIOETL_STRICT_ERROR_HANDLING": "TRUE", "BIOETL_ENV": "staging"},
        ):
            from bioetl.infrastructure.config import Settings

            settings = Settings(test_mode=True)
            assert settings.strict_error_handling is True
