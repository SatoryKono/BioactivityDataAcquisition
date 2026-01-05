"""Common configuration schemas for pipeline YAML files."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, model_validator

from bioetl.domain.config import DQConfig as DomainDQConfig
from bioetl.domain.configs.base import BaseClientConfig, RateLimitConfig
from bioetl.domain.resilience import CircuitBreakerConfig as DomainCircuitBreakerConfig

if TYPE_CHECKING:
    from bioetl.domain.filtering.input_config import (
        InputFilterConfig as DomainInputFilterConfig,
    )


class DQConfig(BaseModel):
    """Data Quality configuration."""

    soft_fail_threshold: float = Field(default=0.05)
    hard_fail_threshold: float = Field(default=0.20)
    strict_validation: bool = Field(default=False)

    @model_validator(mode="after")
    def validate_thresholds(self) -> DQConfig:
        """Validate that soft threshold is less than hard threshold.

        Delegates to domain DQConfig for threshold validation per §4.1.
        Raises ValueError if soft_fail_threshold >= hard_fail_threshold.

        Returns:
            Self after validation.

        Raises:
            ValueError: If threshold invariant is violated.
        """
        DomainDQConfig.validate_thresholds(
            soft_fail_threshold=self.soft_fail_threshold,
            hard_fail_threshold=self.hard_fail_threshold,
        )
        return self

    def to_domain(self) -> DomainDQConfig:
        """Convert Pydantic schema to domain DQConfig object.

        Returns:
            Domain-layer DQConfig with validated thresholds.
        """
        return DomainDQConfig(
            soft_fail_threshold=self.soft_fail_threshold,
            hard_fail_threshold=self.hard_fail_threshold,
            strict_validation=self.strict_validation,
        )


class CircuitBreakerConfig(BaseModel):
    """Circuit Breaker configuration."""

    failure_threshold: int = Field(default=5, ge=1)
    recovery_timeout: int = Field(default=300, ge=60)

    def to_domain(self) -> DomainCircuitBreakerConfig:
        """Convert Pydantic schema to domain CircuitBreakerConfig.

        Creates domain configuration for circuit breaker per §3.1.4.

        Returns:
            Domain-layer CircuitBreakerConfig with failure threshold
            and recovery timeout settings.
        """
        return DomainCircuitBreakerConfig(
            failure_threshold=self.failure_threshold,
            recovery_timeout=self.recovery_timeout,
        )


class CsvExportConfig(BaseModel):
    """Configuration for CSV export."""

    enabled: bool = False
    path: str | None = None
    delimiter: str = ","
    header: bool = True
    encoding: str = "utf-8"


class InputFilterConfig(BaseModel):
    """Configuration for input ID filtering from CSV."""

    enabled: bool = False
    source_path: str | None = Field(default=None)
    column_name: str = Field(default="id")
    filter_field: str = Field(default="molecule_chembl_id")
    batch_size: int = Field(default=100, ge=1, le=1000)

    def to_domain(self) -> DomainInputFilterConfig:
        """Convert Pydantic schema to domain InputFilterConfig.

        Creates domain configuration for CSV-based input filtering.
        When disabled, column_name and filter_field are set to None.

        Returns:
            Domain-layer InputFilterConfig for selective record processing.
        """
        from bioetl.domain.filtering.input_config import (
            InputFilterConfig as DomainInputFilterConfigImpl,
        )

        return DomainInputFilterConfigImpl(
            enabled=self.enabled,
            source_path=self.source_path,
            column_name=self.column_name if self.enabled else None,
            filter_field=self.filter_field if self.enabled else None,
            batch_size=self.batch_size,
        )


class MaintenanceConfig(BaseModel):
    """Configuration for automated maintenance operations."""

    auto_vacuum: bool = Field(default=False)
    vacuum_retention_days: int = Field(default=7, ge=1, le=365)


class ApiConfig(BaseModel):
    """Configuration for API connection details."""

    base_url: str | None = None
    rate_limit: float | None = None
    timeout: int | None = None

    def to_domain(self) -> BaseClientConfig:
        """Convert Pydantic schema to domain BaseClientConfig.

        Creates domain configuration for API client with defaults:
        - timeout: 30 seconds if not specified
        - rate_limit: 5.0 requests/second if not specified

        Returns:
            Domain-layer BaseClientConfig for HTTP client initialization.
        """
        return BaseClientConfig(
            base_url=self.base_url,
            timeout=self.timeout or 30,
            rate_limit=RateLimitConfig(
                requests_per_second=self.rate_limit or 5.0,
            ),
        )
