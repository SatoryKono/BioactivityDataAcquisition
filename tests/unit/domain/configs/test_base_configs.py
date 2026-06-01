"""Unit tests for consolidated base configuration classes.

Domain-pure tests for base config value objects.
"""

from __future__ import annotations

import pytest

from bioetl.domain.config import (
    BaseClientConfig,
    BaseProviderConfig,
    RateLimitConfig,
)


pytestmark = pytest.mark.unit

class TestRateLimitConfig:
    """Tests for RateLimitConfig."""

    def test_rate_limit_config__default_values__d2343cf4(self) -> None:
        config = RateLimitConfig()
        assert config.requests_per_second == pytest.approx(5.0)
        assert config.burst == 10

    def test_rate_limit_config__custom_values__517305cc(self) -> None:
        config = RateLimitConfig(requests_per_second=10.0, burst=20)
        assert config.requests_per_second == pytest.approx(10.0)
        assert config.burst == 20

    def test_validation_requests_per_second_positive(self) -> None:
        with pytest.raises(ValueError, match="requests_per_second must be positive"):
            RateLimitConfig(requests_per_second=0)
        with pytest.raises(ValueError, match="requests_per_second must be positive"):
            RateLimitConfig(requests_per_second=-1.0)

    def test_validation_burst_minimum(self) -> None:
        with pytest.raises(ValueError, match="burst must be at least 1"):
            RateLimitConfig(burst=0)
        with pytest.raises(ValueError, match="burst must be at least 1"):
            RateLimitConfig(burst=-5)

    def test_rate_limit_config__immutability__9ec137ae(self) -> None:
        config = RateLimitConfig()
        with pytest.raises(AttributeError):
            config.requests_per_second = 100.0  # type: ignore[misc]


class TestBaseClientConfig:
    """Tests for BaseClientConfig."""

    def test_base_client_config__default_values__6e736983(self) -> None:
        config = BaseClientConfig()
        assert config.base_url is None
        assert config.timeout == 30
        assert config.rate_limit.requests_per_second == pytest.approx(5.0)
        assert config.rate_limit.burst == 10

    def test_base_client_config__custom_values__465b4cf3(self) -> None:
        rate_limit = RateLimitConfig(requests_per_second=10.0, burst=5)
        config = BaseClientConfig(
            base_url="https://api.example.com",
            timeout=60,
            rate_limit=rate_limit,
        )
        assert config.base_url == "https://api.example.com"
        assert config.timeout == 60
        assert config.rate_limit.requests_per_second == pytest.approx(10.0)

    def test_validation_timeout_positive(self) -> None:
        with pytest.raises(ValueError, match="timeout must be positive"):
            BaseClientConfig(timeout=0)
        with pytest.raises(ValueError, match="timeout must be positive"):
            BaseClientConfig(timeout=-10)

    def test_base_client_config__immutability__4739c841(self) -> None:
        config = BaseClientConfig()
        with pytest.raises(AttributeError):
            config.timeout = 100  # type: ignore[misc]


class TestBaseProviderConfig:
    """Tests for BaseProviderConfig."""

    def test_base_provider_config__default_values__0e5082dd(self) -> None:
        config = BaseProviderConfig()
        assert config.base_url is None
        assert config.timeout == 30
        assert config.rate_limit.requests_per_second == pytest.approx(5.0)
        assert config.batch_size == 100
        assert config.api_key is None

    def test_base_provider_config__custom_values__f0fca59e(self) -> None:
        rate_limit = RateLimitConfig(requests_per_second=20.0, burst=50)
        config = BaseProviderConfig(
            base_url="https://www.ebi.ac.uk/chembl/api/data",
            timeout=120,
            rate_limit=rate_limit,
            batch_size=1000,
            api_key="secret-key",
        )
        assert config.base_url == "https://www.ebi.ac.uk/chembl/api/data"
        assert config.timeout == 120
        assert config.rate_limit.requests_per_second == pytest.approx(20.0)
        assert config.batch_size == 1000
        assert config.api_key == "secret-key"

    def test_validation_batch_size_positive(self) -> None:
        with pytest.raises(ValueError, match="batch_size must be positive"):
            BaseProviderConfig(batch_size=0)
        with pytest.raises(ValueError, match="batch_size must be positive"):
            BaseProviderConfig(batch_size=-10)

    def test_inherits_parent_validation(self) -> None:
        with pytest.raises(ValueError, match="timeout must be positive"):
            BaseProviderConfig(timeout=0)

    def test_base_provider_config__immutability__811f72c7(self) -> None:
        config = BaseProviderConfig()
        with pytest.raises(AttributeError):
            config.batch_size = 500  # type: ignore[misc]
