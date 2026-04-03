# mypy: disable-error-code="misc,untyped-decorator"
"""Shared base schemas for connection, DQ, and maintenance configuration."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from bioetl.domain.config import DQConfig as DomainDQConfig
from bioetl.domain.config.base_provider import (
    BaseClientConfig as DomainBaseClientConfig,
)
from bioetl.domain.config.base_provider import RateLimitConfig
from bioetl.domain.resilience import CircuitBreakerConfig as DomainCircuitBreakerConfig


class BaseDQThresholds(BaseModel):
    """DQ threshold configuration with soft_fail < hard_fail validation."""

    model_config = ConfigDict(extra="ignore")

    soft_fail_threshold: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Warning threshold (0.0-1.0). Default: 0.05 (5%)",
    )
    hard_fail_threshold: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="Failure threshold (0.0-1.0). Default: 0.20 (20%)",
    )

    @model_validator(mode="after")
    def validate_thresholds(self) -> BaseDQThresholds:
        """Validate soft_fail < hard_fail."""
        DomainDQConfig.validate_thresholds(
            soft_fail_threshold=self.soft_fail_threshold,
            hard_fail_threshold=self.hard_fail_threshold,
        )
        return self


class BaseDQConfig(BaseDQThresholds):
    """Base class for DQ configuration."""

    strict_validation: bool = Field(
        default=False,
        description="Apply stricter validation rules (feature flag)",
    )

    def to_domain(self) -> DomainDQConfig:
        """Convert to domain DQConfig dataclass."""
        return DomainDQConfig(
            soft_fail_threshold=self.soft_fail_threshold,
            hard_fail_threshold=self.hard_fail_threshold,
            strict_validation=self.strict_validation,
        )


class BaseCircuitBreakerConfig(BaseModel):
    """Base class for Circuit Breaker configuration."""

    model_config = ConfigDict(extra="ignore")

    failure_threshold: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of consecutive failures before opening circuit",
    )
    recovery_timeout: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="Time in seconds before attempting recovery",
    )

    def to_domain(self) -> DomainCircuitBreakerConfig:
        """Convert to domain CircuitBreakerConfig dataclass."""
        return DomainCircuitBreakerConfig(
            failure_threshold=self.failure_threshold,
            recovery_timeout=self.recovery_timeout,
        )


class BaseRateLimitConfig(BaseModel):
    """Base class for Rate Limit configuration."""

    model_config = ConfigDict(extra="ignore")

    requests_per_second: float = Field(
        default=5.0,
        ge=0.1,
        le=100.0,
        description="Maximum requests per second",
    )
    burst: int = Field(
        default=10,
        ge=1,
        le=200,
        description="Maximum burst capacity (token bucket)",
    )


class HttpClientConfig(BaseModel):
    """Base HTTP client config for pipeline and source configs."""

    model_config = ConfigDict(extra="ignore")

    timeout_sec: float = Field(default=30.0, ge=1.0, le=300.0)
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_base_delay: float = Field(default=1.0, ge=0.1, le=120.0)
    retry_max_delay: float = Field(default=60.0, ge=1.0, le=600.0)
    max_connections: int = Field(default=50, ge=1, le=500)
    max_keepalive_connections: int = Field(default=10, ge=1, le=100)
    trust_env: bool = Field(
        default=True,
        description=(
            "Whether httpx should inherit HTTP(S)_PROXY and other network-related "
            "environment variables from the process environment."
        ),
    )


class BaseApiConfig(BaseModel):
    """Base class for API connection configuration."""

    model_config = ConfigDict(extra="ignore")

    base_url: str | None = Field(default=None, description="Base URL for the API")
    rate_limit: float | None = Field(
        default=None,
        description="Rate limit in requests per second",
    )
    timeout: int | None = Field(default=None, description="Request timeout in seconds")

    def to_domain(self) -> DomainBaseClientConfig:
        """Convert to domain BaseClientConfig dataclass."""
        return DomainBaseClientConfig(
            base_url=self.base_url,
            timeout=self.timeout or 30,
            rate_limit=RateLimitConfig(
                requests_per_second=self.rate_limit or 5.0,
            ),
        )


class BaseCsvExportConfig(BaseModel):
    """Base class for CSV export configuration."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = Field(default=False, description="Whether CSV export is enabled")
    path: str | None = Field(default=None, description="Output path for CSV file")
    delimiter: str = Field(default=",", description="CSV field delimiter")
    header: bool = Field(default=True, description="Whether to include header row")
    encoding: str = Field(default="utf-8", description="File encoding")


class BaseMaintenanceConfig(BaseModel):
    """Base class for maintenance configuration."""

    model_config = ConfigDict(extra="ignore")

    auto_vacuum: bool = Field(
        default=False,
        description="Enable automatic VACUUM after successful pipeline run",
    )
    vacuum_retention_days: int = Field(
        default=7,
        ge=1,
        le=365,
        description="Minimum age of files to remove during VACUUM (days)",
    )


__all__ = [
    "BaseApiConfig",
    "BaseCircuitBreakerConfig",
    "BaseCsvExportConfig",
    "BaseDQConfig",
    "BaseDQThresholds",
    "BaseMaintenanceConfig",
    "BaseRateLimitConfig",
    "HttpClientConfig",
]
