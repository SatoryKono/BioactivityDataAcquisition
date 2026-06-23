"""Tests for API client error handling paths.

Tests that silent failures have been replaced with proper logging
and configurable error handling based on BIOETL_STRICT_ERROR_HANDLING.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from bioetl.domain.exceptions import ExternalServiceError
from tests.helpers.adapter_runtime import build_http_adapter_runtime_kwargs


pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def reset_settings_cache():
    """Reset settings cache before each test."""
    from bioetl.infrastructure.config._base import get_settings

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
        from bioetl.infrastructure.config._base import get_settings

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
        from bioetl.infrastructure.config._base import get_settings

        get_settings.cache_clear()
        yield get_settings()
        get_settings.cache_clear()


class TestUniProtAdapterErrorPaths:
    """Tests for UniProt adapter error handling."""

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
        from bioetl.infrastructure.adapters.http.circuit_breaker import (
            CircuitBreakerGuard,
        )

        cb = MagicMock(spec=CircuitBreakerGuard)
        cb.call = AsyncMock(side_effect=ConnectionError("Network error"))
        return cb

    async def test_fetch_proteins_logs_error_on_failure(
        self, mock_http_client, mock_logger
    ):
        """Test that _fetch_proteins logs error when fetch fails."""
        from bioetl.infrastructure.adapters.uniprot import UniProtAdapter

        with patch.dict(
            os.environ,
            {"BIOETL_STRICT_ERROR_HANDLING": "false", "BIOETL_ENV": "staging"},
        ):
            # Make http_client.get raise an exception
            mock_http_client.get = AsyncMock(
                side_effect=ConnectionError("Network error")
            )
            adapter = UniProtAdapter(
                http_client=mock_http_client,
                logger=mock_logger,
                **build_http_adapter_runtime_kwargs(
                    "uniprot",
                    logger=mock_logger,
                    include_fallback_service=True,
                ),
            )

            results = [
                r async for r in adapter._fetch_proteins(query="test", limit=100)
            ]

            # Should return empty results on failure
            assert results == []

            # Should have logged the error via injected logger
            mock_logger.error.assert_called()
            # Verify the error message contains expected context
            call_args = mock_logger.error.call_args
            assert (
                "protein fetch" in str(call_args).lower()
                or "network error" in str(call_args).lower()
            )

    async def test_fetch_proteins_raises_in_strict_mode(
        self, mock_http_client, mock_logger
    ):
        """Test that _fetch_proteins raises exception in strict mode.

        With unified error handling, exceptions are wrapped in ExternalServiceError.
        """
        from bioetl.infrastructure.adapters.uniprot import UniProtAdapter

        # Make http_client.get raise an exception
        mock_http_client.get = AsyncMock(side_effect=ConnectionError("Network error"))
        adapter = UniProtAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            strict_error_handling=True,
            **build_http_adapter_runtime_kwargs(
                "uniprot",
                logger=mock_logger,
                include_fallback_service=True,
            ),
        )

        with pytest.raises(ExternalServiceError):
            _ = [r async for r in adapter._fetch_proteins(query="test", limit=100)]

    async def test_fetch_features_logs_error_on_failure(
        self, mock_http_client, mock_logger
    ):
        """Test that _fetch_features logs error when fetch fails."""
        from bioetl.infrastructure.adapters.uniprot import UniProtAdapter

        with patch.dict(
            os.environ,
            {"BIOETL_STRICT_ERROR_HANDLING": "false", "BIOETL_ENV": "staging"},
        ):
            from bioetl.infrastructure.config._base import get_settings

            get_settings.cache_clear()

            # Make http_client.get raise an exception
            mock_http_client.get = AsyncMock(
                side_effect=TimeoutError("Request timeout")
            )
            adapter = UniProtAdapter(
                http_client=mock_http_client,
                logger=mock_logger,
                **build_http_adapter_runtime_kwargs(
                    "uniprot",
                    logger=mock_logger,
                    include_fallback_service=True,
                ),
            )

            results = [r async for r in adapter._fetch_features("P12345", limit=10)]

            # Should return empty results on failure
            assert results == []

            # Should have logged the error via injected logger
            mock_logger.error.assert_called()
            # Verify the error message contains expected context
            call_args = mock_logger.error.call_args
            assert (
                "feature fetch" in str(call_args).lower()
                or "timeout" in str(call_args).lower()
            )

    async def test_fetch_features_raises_in_strict_mode(
        self, mock_http_client, mock_logger
    ):
        """Test that _fetch_features raises exception in strict mode.

        With unified error handling, exceptions are wrapped in ExternalServiceError.
        """
        from bioetl.infrastructure.adapters.uniprot import UniProtAdapter

        # Make http_client.get raise an exception
        mock_http_client.get = AsyncMock(side_effect=TimeoutError("Request timeout"))
        adapter = UniProtAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            strict_error_handling=True,
            **build_http_adapter_runtime_kwargs(
                "uniprot",
                logger=mock_logger,
                include_fallback_service=True,
            ),
        )

        with pytest.raises(ExternalServiceError):
            _ = [r async for r in adapter._fetch_features("P12345", limit=10)]

    async def test_fetch_sequences_logs_error_on_failure(
        self, mock_http_client, mock_logger
    ):
        """Test that _fetch_sequences logs error when fetch fails."""
        from bioetl.infrastructure.adapters.uniprot import UniProtAdapter

        with patch.dict(
            os.environ,
            {"BIOETL_STRICT_ERROR_HANDLING": "false", "BIOETL_ENV": "staging"},
        ):
            from bioetl.infrastructure.config._base import get_settings

            get_settings.cache_clear()

            # Make http_client.get raise an exception
            mock_http_client.get = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Server error",
                    request=MagicMock(),
                    response=MagicMock(status_code=500),
                )
            )
            adapter = UniProtAdapter(
                http_client=mock_http_client,
                logger=mock_logger,
                **build_http_adapter_runtime_kwargs(
                    "uniprot",
                    logger=mock_logger,
                    include_fallback_service=True,
                ),
            )

            results = [r async for r in adapter._fetch_sequences("gene:TP53", limit=10)]

            # Should return empty results on failure
            assert results == []

            # Should have logged the error via injected logger
            mock_logger.error.assert_called()
            # Verify the error message contains expected context
            call_args = mock_logger.error.call_args
            assert (
                "sequence fetch" in str(call_args).lower()
                or "server error" in str(call_args).lower()
            )

    async def test_fetch_sequences_raises_in_strict_mode(
        self, mock_http_client, mock_logger
    ):
        """Test that _fetch_sequences raises exception in strict mode.

        With unified error handling, exceptions are wrapped in ExternalServiceError.
        """
        from bioetl.infrastructure.adapters.uniprot import UniProtAdapter

        # Make http_client.get raise an exception
        error = httpx.HTTPStatusError(
            "Server error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )
        mock_http_client.get = AsyncMock(side_effect=error)
        adapter = UniProtAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            strict_error_handling=True,
            **build_http_adapter_runtime_kwargs(
                "uniprot",
                logger=mock_logger,
                include_fallback_service=True,
            ),
        )

        with pytest.raises(ExternalServiceError):
            _ = [r async for r in adapter._fetch_sequences("gene:TP53", limit=10)]


class TestStrictErrorHandlingConfig:
    """Tests for the strict_error_handling configuration."""

    def test_default_is_false(self):
        """Test that strict_error_handling defaults to False."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear any existing env vars that might affect the test
            os.environ.pop("BIOETL_STRICT_ERROR_HANDLING", None)

            from bioetl.infrastructure.config._base import Settings

            settings = Settings(test_mode=True)
            assert settings.strict_error_handling is False

    def test_can_be_enabled_via_env_var(self):
        """Test that strict_error_handling can be enabled via env var."""
        with patch.dict(
            os.environ,
            {"BIOETL_STRICT_ERROR_HANDLING": "true", "BIOETL_ENV": "staging"},
            clear=True,
        ):
            from bioetl.infrastructure.config._base import Settings

            settings = Settings(test_mode=True)
            assert settings.strict_error_handling is True

    def test_env_var_case_insensitive(self):
        """Test that env var values are case-insensitive."""
        with patch.dict(
            os.environ,
            {"BIOETL_STRICT_ERROR_HANDLING": "True", "BIOETL_ENV": "staging"},
            clear=True,
        ):
            from bioetl.infrastructure.config._base import Settings

            settings = Settings(test_mode=True)
            assert settings.strict_error_handling is True

        with patch.dict(
            os.environ,
            {"BIOETL_STRICT_ERROR_HANDLING": "TRUE", "BIOETL_ENV": "staging"},
            clear=True,
        ):
            from bioetl.infrastructure.config._base import Settings

            settings = Settings(test_mode=True)
            assert settings.strict_error_handling is True
