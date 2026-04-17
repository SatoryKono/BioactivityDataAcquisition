"""Tests for base provider configuration classes.

Tests for RateLimitConfig, BaseClientConfig, BaseProviderConfig.
"""

from __future__ import annotations

import pytest

from bioetl.domain.config.base_provider import (
    BaseClientConfig,
    BaseProviderConfig,
    RateLimitConfig,
)


@pytest.mark.unit
class TestRateLimitConfig:
    """Tests for RateLimitConfig frozen dataclass."""

    def test_default_values(self) -> None:
        config = RateLimitConfig()
        assert config.requests_per_second == pytest.approx(5.0)
        assert config.burst == 10

    def test_custom_values(self) -> None:
        config = RateLimitConfig(requests_per_second=10.0, burst=20)
        assert config.requests_per_second == pytest.approx(10.0)
        assert config.burst == 20

    def test_zero_rps_raises(self) -> None:
        with pytest.raises(ValueError, match="requests_per_second must be positive"):
            RateLimitConfig(requests_per_second=0.0)

    def test_negative_rps_raises(self) -> None:
        with pytest.raises(ValueError, match="requests_per_second must be positive"):
            RateLimitConfig(requests_per_second=-1.0)

    def test_zero_burst_raises(self) -> None:
        with pytest.raises(ValueError, match="burst must be at least 1"):
            RateLimitConfig(burst=0)

    def test_frozen(self) -> None:
        config = RateLimitConfig()
        with pytest.raises(AttributeError):
            config.burst = 20  # type: ignore[misc]


@pytest.mark.unit
class TestBaseClientConfig:
    """Tests for BaseClientConfig frozen dataclass."""

    def test_default_values(self) -> None:
        config = BaseClientConfig()
        assert config.base_url is None
        assert config.timeout == 30
        assert isinstance(config.rate_limit, RateLimitConfig)

    def test_custom_url(self) -> None:
        config = BaseClientConfig(base_url="https://api.example.com")
        assert config.base_url == "https://api.example.com"

    def test_zero_timeout_raises(self) -> None:
        with pytest.raises(ValueError, match="timeout must be positive"):
            BaseClientConfig(timeout=0)

    def test_negative_timeout_raises(self) -> None:
        with pytest.raises(ValueError, match="timeout must be positive"):
            BaseClientConfig(timeout=-1)

    def test_custom_rate_limit(self) -> None:
        rl = RateLimitConfig(requests_per_second=20.0, burst=50)
        config = BaseClientConfig(rate_limit=rl)
        assert config.rate_limit.requests_per_second == pytest.approx(20.0)


@pytest.mark.unit
class TestBaseProviderConfig:
    """Tests for BaseProviderConfig frozen dataclass."""

    def test_default_values(self) -> None:
        config = BaseProviderConfig()
        assert config.batch_size == 100
        assert config.api_key is None
        assert config.timeout == 30  # inherited

    def test_custom_values(self) -> None:
        config = BaseProviderConfig(
            base_url="https://www.ebi.ac.uk/chembl/api/data",
            batch_size=1000,
            api_key="test-key",
        )
        assert config.batch_size == 1000
        assert config.api_key == "test-key"

    def test_zero_batch_size_raises(self) -> None:
        with pytest.raises(ValueError, match="batch_size must be positive"):
            BaseProviderConfig(batch_size=0)

    def test_negative_batch_size_raises(self) -> None:
        with pytest.raises(ValueError, match="batch_size must be positive"):
            BaseProviderConfig(batch_size=-1)

    def test_inherits_timeout_validation(self) -> None:
        with pytest.raises(ValueError, match="timeout must be positive"):
            BaseProviderConfig(timeout=0)
