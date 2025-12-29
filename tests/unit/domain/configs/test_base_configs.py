"""Unit tests for consolidated base configuration classes.

Tests for the base configuration classes that consolidate duplicate DTOs
per RULES.md §12.1.6.
"""

from __future__ import annotations

import pytest

from bioetl.domain.configs import (
    BaseClientConfig,
    BaseProviderConfig,
    RateLimitConfig,
)


class TestRateLimitConfig:
    """Tests for RateLimitConfig."""

    def test_default_values(self) -> None:
        """Test default values are applied correctly."""
        config = RateLimitConfig()
        assert config.requests_per_second == 5.0
        assert config.burst == 10

    def test_custom_values(self) -> None:
        """Test custom values are applied correctly."""
        config = RateLimitConfig(requests_per_second=10.0, burst=20)
        assert config.requests_per_second == 10.0
        assert config.burst == 20

    def test_validation_requests_per_second_positive(self) -> None:
        """Test that requests_per_second must be positive."""
        with pytest.raises(ValueError, match="requests_per_second must be positive"):
            RateLimitConfig(requests_per_second=0)

        with pytest.raises(ValueError, match="requests_per_second must be positive"):
            RateLimitConfig(requests_per_second=-1.0)

    def test_validation_burst_minimum(self) -> None:
        """Test that burst must be at least 1."""
        with pytest.raises(ValueError, match="burst must be at least 1"):
            RateLimitConfig(burst=0)

        with pytest.raises(ValueError, match="burst must be at least 1"):
            RateLimitConfig(burst=-5)

    def test_immutability(self) -> None:
        """Test that config is frozen (immutable)."""
        config = RateLimitConfig()
        with pytest.raises(AttributeError):
            config.requests_per_second = 100.0  # type: ignore[misc]


class TestBaseClientConfig:
    """Tests for BaseClientConfig."""

    def test_default_values(self) -> None:
        """Test default values are applied correctly."""
        config = BaseClientConfig()
        assert config.base_url is None
        assert config.timeout == 30
        assert config.rate_limit.requests_per_second == 5.0
        assert config.rate_limit.burst == 10

    def test_custom_values(self) -> None:
        """Test custom values are applied correctly."""
        rate_limit = RateLimitConfig(requests_per_second=10.0, burst=5)
        config = BaseClientConfig(
            base_url="https://api.example.com",
            timeout=60,
            rate_limit=rate_limit,
        )
        assert config.base_url == "https://api.example.com"
        assert config.timeout == 60
        assert config.rate_limit.requests_per_second == 10.0

    def test_validation_timeout_positive(self) -> None:
        """Test that timeout must be positive."""
        with pytest.raises(ValueError, match="timeout must be positive"):
            BaseClientConfig(timeout=0)

        with pytest.raises(ValueError, match="timeout must be positive"):
            BaseClientConfig(timeout=-10)

    def test_immutability(self) -> None:
        """Test that config is frozen (immutable)."""
        config = BaseClientConfig()
        with pytest.raises(AttributeError):
            config.timeout = 100  # type: ignore[misc]


class TestBaseProviderConfig:
    """Tests for BaseProviderConfig."""

    def test_default_values(self) -> None:
        """Test default values are applied correctly."""
        config = BaseProviderConfig()
        # Inherited from BaseClientConfig
        assert config.base_url is None
        assert config.timeout == 30
        assert config.rate_limit.requests_per_second == 5.0
        # Provider-specific
        assert config.batch_size == 100
        assert config.api_key is None

    def test_custom_values(self) -> None:
        """Test custom values are applied correctly."""
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
        assert config.rate_limit.requests_per_second == 20.0
        assert config.batch_size == 1000
        assert config.api_key == "secret-key"

    def test_validation_batch_size_positive(self) -> None:
        """Test that batch_size must be positive."""
        with pytest.raises(ValueError, match="batch_size must be positive"):
            BaseProviderConfig(batch_size=0)

        with pytest.raises(ValueError, match="batch_size must be positive"):
            BaseProviderConfig(batch_size=-10)

    def test_inherits_parent_validation(self) -> None:
        """Test that parent validation (timeout) still applies."""
        with pytest.raises(ValueError, match="timeout must be positive"):
            BaseProviderConfig(timeout=0)

    def test_immutability(self) -> None:
        """Test that config is frozen (immutable)."""
        config = BaseProviderConfig()
        with pytest.raises(AttributeError):
            config.batch_size = 500  # type: ignore[misc]


class TestConsolidationPattern:
    """Tests for the consolidation pattern (to_domain methods)."""

    def test_dqconfig_to_domain(self) -> None:
        """Test DQConfig Pydantic model to domain conversion."""
        from bioetl.infrastructure.schemas.pipeline_config import (
            DQConfig as PydanticDQConfig,
        )

        pydantic_config = PydanticDQConfig(
            soft_fail_threshold=0.10,
            hard_fail_threshold=0.30,
            strict_validation=True,
        )
        domain_config = pydantic_config.to_domain()

        assert domain_config.soft_fail_threshold == 0.10
        assert domain_config.hard_fail_threshold == 0.30
        assert domain_config.strict_validation is True

    def test_circuit_breaker_to_domain(self) -> None:
        """Test CircuitBreakerConfig Pydantic model to domain conversion."""
        from bioetl.infrastructure.schemas.pipeline_config import (
            CircuitBreakerConfig as PydanticCBConfig,
        )

        pydantic_config = PydanticCBConfig(
            failure_threshold=3,
            recovery_timeout=60,
        )
        domain_config = pydantic_config.to_domain()

        assert domain_config.failure_threshold == 3
        assert domain_config.recovery_timeout == 60

    def test_api_config_to_domain(self) -> None:
        """Test ApiConfig Pydantic model to domain conversion."""
        from bioetl.infrastructure.schemas.pipeline_config import (
            ApiConfig as PydanticApiConfig,
        )

        pydantic_config = PydanticApiConfig(
            base_url="https://api.example.com",
            rate_limit=15.0,
            timeout=45,
        )
        domain_config = pydantic_config.to_domain()

        assert domain_config.base_url == "https://api.example.com"
        assert domain_config.timeout == 45
        assert domain_config.rate_limit.requests_per_second == 15.0

    def test_api_config_to_domain_defaults(self) -> None:
        """Test ApiConfig with None values uses sensible defaults."""
        from bioetl.infrastructure.schemas.pipeline_config import (
            ApiConfig as PydanticApiConfig,
        )

        pydantic_config = PydanticApiConfig()
        domain_config = pydantic_config.to_domain()

        assert domain_config.base_url is None
        assert domain_config.timeout == 30  # default
        assert domain_config.rate_limit.requests_per_second == 5.0  # default

    def test_input_filter_config_to_domain_disabled(self) -> None:
        """Test InputFilterConfig to domain conversion when disabled."""
        from bioetl.infrastructure.schemas.pipeline_config import (
            InputFilterConfig as PydanticIFConfig,
        )

        pydantic_config = PydanticIFConfig(enabled=False)
        domain_config = pydantic_config.to_domain()

        assert domain_config.enabled is False
        assert domain_config.column_name is None
        assert domain_config.filter_field is None

    def test_input_filter_config_to_domain_enabled(self) -> None:
        """Test InputFilterConfig to domain conversion when enabled."""
        from bioetl.infrastructure.schemas.pipeline_config import (
            InputFilterConfig as PydanticIFConfig,
        )

        pydantic_config = PydanticIFConfig(
            enabled=True,
            source_path="/path/to/file.csv",
            column_name="chembl_id",
            filter_field="molecule_chembl_id",
            batch_size=50,
        )
        domain_config = pydantic_config.to_domain()

        assert domain_config.enabled is True
        assert domain_config.source_path == "/path/to/file.csv"
        assert domain_config.column_name == "chembl_id"
        assert domain_config.filter_field == "molecule_chembl_id"
        assert domain_config.batch_size == 50
