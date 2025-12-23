"""Tests for API client error handling paths.

Tests that silent failures have been replaced with proper logging
and configurable error handling based on BIOETL_STRICT_ERROR_HANDLING.
"""

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
    def mock_logger(self):
        """Create a mock logger."""
        return MagicMock()

    @pytest.fixture
    def mock_circuit_breaker(self):
        """Create a mock circuit breaker that raises an exception."""
        from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker

        cb = MagicMock(spec=CircuitBreaker)
        cb.call = AsyncMock(side_effect=ConnectionError("Network error"))
        return cb

    async def test_fetch_proteins_logs_error_on_failure(self, mock_http_client, mock_logger):
        """Test that _fetch_proteins logs error when fetch fails."""
        from bioetl.infrastructure.adapters.uniprot.client import UniProtClient

        with patch.dict(
            os.environ,
            {"BIOETL_STRICT_ERROR_HANDLING": "false", "BIOETL_ENV": "staging"},
        ):
            # Make http_client.get raise an exception
            mock_http_client.get = AsyncMock(
                side_effect=ConnectionError("Network error")
            )
            client = UniProtClient(http_client=mock_http_client, logger=mock_logger)

            results = [
                r
                async for r in client._fetch_proteins(
                    query="test", watermark=None, limit=100
                )
            ]

            # Should return empty results on failure
            assert results == []

            # Should have logged the error via injected logger
            mock_logger.error.assert_called()
            # Verify the error message contains expected context
            call_args = mock_logger.error.call_args
            assert "protein fetch" in str(call_args).lower() or "network error" in str(call_args).lower()

    async def test_fetch_proteins_raises_in_strict_mode(self, mock_http_client, mock_logger):
        """Test that _fetch_proteins raises exception in strict mode."""
        from bioetl.infrastructure.adapters.uniprot.client import UniProtClient

        # Make http_client.get raise an exception
        mock_http_client.get = AsyncMock(side_effect=ConnectionError("Network error"))
        client = UniProtClient(http_client=mock_http_client, logger=mock_logger, strict_error_handling=True)

        with pytest.raises(ConnectionError, match="Network error"):
            _ = [
                r
                async for r in client._fetch_proteins(
                    query="test", watermark=None, limit=100
                )
            ]

    async def test_fetch_features_logs_error_on_failure(self, mock_http_client, mock_logger):
        """Test that _fetch_features logs error when fetch fails."""
        from bioetl.infrastructure.adapters.uniprot.client import UniProtClient

        with patch.dict(
            os.environ,
            {"BIOETL_STRICT_ERROR_HANDLING": "false", "BIOETL_ENV": "staging"},
        ):
            from bioetl.infrastructure.config import get_settings

            get_settings.cache_clear()

            # Make http_client.get raise an exception
            mock_http_client.get = AsyncMock(
                side_effect=TimeoutError("Request timeout")
            )
            client = UniProtClient(http_client=mock_http_client, logger=mock_logger)

            results = [
                r
                async for r in client._fetch_features(
                    "P12345", watermark=None, limit=10
                )
            ]

            # Should return empty results on failure
            assert results == []

            # Should have logged the error via injected logger
            mock_logger.error.assert_called()
            # Verify the error message contains expected context
            call_args = mock_logger.error.call_args
            assert "feature fetch" in str(call_args).lower() or "timeout" in str(call_args).lower()

    async def test_fetch_features_raises_in_strict_mode(self, mock_http_client, mock_logger):
        """Test that _fetch_features raises exception in strict mode."""
        from bioetl.infrastructure.adapters.uniprot.client import UniProtClient

        # Make http_client.get raise an exception
        mock_http_client.get = AsyncMock(side_effect=TimeoutError("Request timeout"))
        client = UniProtClient(http_client=mock_http_client, logger=mock_logger, strict_error_handling=True)

        with pytest.raises(TimeoutError, match="Request timeout"):
            _ = [
                r
                async for r in client._fetch_features(
                    "P12345", watermark=None, limit=10
                )
            ]

    async def test_fetch_sequences_logs_error_on_failure(
        self, mock_http_client, mock_logger
    ):
        """Test that _fetch_sequences logs error when fetch fails."""
        from bioetl.infrastructure.adapters.uniprot.client import UniProtClient

        with patch.dict(
            os.environ,
            {"BIOETL_STRICT_ERROR_HANDLING": "false", "BIOETL_ENV": "staging"},
        ):
            from bioetl.infrastructure.config import get_settings

            get_settings.cache_clear()

            # Make http_client.get raise an exception
            mock_http_client.get = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Server error",
                    request=MagicMock(),
                    response=MagicMock(status_code=500),
                )
            )
            client = UniProtClient(http_client=mock_http_client, logger=mock_logger)

            results = [
                r
                async for r in client._fetch_sequences(
                    "gene:TP53", watermark=None, limit=10
                )
            ]

            # Should return empty results on failure
            assert results == []

            # Should have logged the error via injected logger
            mock_logger.error.assert_called()
            # Verify the error message contains expected context
            call_args = mock_logger.error.call_args
            assert "sequence fetch" in str(call_args).lower() or "server error" in str(call_args).lower()

    async def test_fetch_sequences_raises_in_strict_mode(self, mock_http_client, mock_logger):
        """Test that _fetch_sequences raises exception in strict mode."""
        from bioetl.infrastructure.adapters.uniprot.client import UniProtClient

        # Make http_client.get raise an exception
        error = httpx.HTTPStatusError(
            "Server error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )
        mock_http_client.get = AsyncMock(side_effect=error)
        client = UniProtClient(http_client=mock_http_client, logger=mock_logger, strict_error_handling=True)

        with pytest.raises(httpx.HTTPStatusError):
            _ = [
                r
                async for r in client._fetch_sequences(
                    "gene:TP53", watermark=None, limit=10
                )
            ]


class TestPubChemClientErrorPaths:
    """Tests for PubChem client error handling."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return MagicMock()

    @pytest.fixture
    def mock_pubchempy(self):
        """Mock pubchempy module."""
        mock_pcp = MagicMock()
        mock_pcp.get_compounds = MagicMock(return_value=[])
        return mock_pcp

    async def test_fetch_compounds_incremental_logs_error_on_failure(self, mock_logger):
        """Test that _fetch_compounds_incremental logs error when fetch fails."""
        from bioetl.infrastructure.adapters.pubchem.client import PubChemClient

        with patch.dict(
            os.environ,
            {"BIOETL_STRICT_ERROR_HANDLING": "false", "BIOETL_ENV": "staging"},
        ):
            from bioetl.infrastructure.config import get_settings

            get_settings.cache_clear()

            client = PubChemClient(logger=mock_logger)

            # Make circuit_breaker.call raise an exception then return empty
            # Need 3 consecutive empty batches to break the loop (max_consecutive_empty=3)
            client.circuit_breaker.call = AsyncMock(
                side_effect=[
                    ConnectionError("PubChem API error"),  # First: error → empty
                    [],  # Second: empty
                    [],  # Third: empty → breaks loop
                ]
            )

            results = []
            async for result in client._fetch_compounds_incremental(
                watermark=1000, limit=50
            ):
                results.append(result)

            # Should have logged the error via injected logger
            mock_logger.error.assert_called()
            # Verify the error message contains expected context
            call_args = mock_logger.error.call_args
            assert "batch fetch" in str(call_args).lower() or "pubchem" in str(call_args).lower()

    async def test_fetch_compounds_incremental_raises_in_strict_mode(self, mock_logger):
        """Test that _fetch_compounds_incremental raises exception in strict mode."""
        from bioetl.infrastructure.adapters.pubchem.client import PubChemClient

        client = PubChemClient(logger=mock_logger, strict_error_handling=True)

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
