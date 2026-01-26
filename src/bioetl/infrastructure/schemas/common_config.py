"""Common configuration schemas for pipeline YAML files.

This module provides backward-compatible re-exports of base configuration classes.
New code should import directly from `base_schemas` or `pipeline_config` instead.

Deprecated:
    This module is maintained for backward compatibility only.
    Prefer importing from:
    - `bioetl.infrastructure.schemas.base_schemas` for base classes
    - `bioetl.infrastructure.schemas.pipeline_config` for extended classes

Example:
    # Preferred (new code):
    >>> from bioetl.infrastructure.schemas.base_schemas import BaseDQConfig
    >>> from bioetl.infrastructure.schemas.pipeline_config import DQConfig

    # Deprecated (backward compatibility):
    >>> from bioetl.infrastructure.schemas.common_config import DQConfig
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.infrastructure.schemas.base_schemas import (
    BaseApiConfig,
    BaseCircuitBreakerConfig,
    BaseCsvExportConfig,
    BaseDQConfig,
    BaseInputFilterConfig,
    BaseMaintenanceConfig,
)

if TYPE_CHECKING:
    from bioetl.domain.config import DQConfig as DomainDQConfig
    from bioetl.domain.configs.base import BaseClientConfig as DomainBaseClientConfig
    from bioetl.domain.filtering.input_config import (
        InputFilterConfig as DomainInputFilterConfig,
    )
    from bioetl.domain.resilience import (
        CircuitBreakerConfig as DomainCircuitBreakerConfig,
    )


# =============================================================================
# Backward Compatibility Aliases
# =============================================================================
#
# These classes inherit from base classes without modification.
# They exist solely for backward compatibility with existing code.
# New code should import from base_schemas or pipeline_config directly.


class DQConfig(BaseDQConfig):
    """Data Quality configuration (backward compatibility alias).

    Deprecated:
        Use `BaseDQConfig` from `base_schemas` or extended `DQConfig`
        from `pipeline_config` instead.
    """

    def to_domain(self) -> DomainDQConfig:
        """Convert Pydantic schema to domain DQConfig object.

        Returns:
            Domain-layer DQConfig with validated thresholds.
        """
        return super().to_domain()


class CircuitBreakerConfig(BaseCircuitBreakerConfig):
    """Circuit Breaker configuration (backward compatibility alias).

    Deprecated:
        Use `BaseCircuitBreakerConfig` from `base_schemas` instead.
    """

    def to_domain(self) -> DomainCircuitBreakerConfig:
        """Convert Pydantic schema to domain CircuitBreakerConfig.

        Returns:
            Domain-layer CircuitBreakerConfig with failure threshold
            and recovery timeout settings.
        """
        return super().to_domain()


class CsvExportConfig(BaseCsvExportConfig):
    """Configuration for CSV export (backward compatibility alias).

    Deprecated:
        Use `BaseCsvExportConfig` from `base_schemas` instead.
    """


class InputFilterConfig(BaseInputFilterConfig):
    """Configuration for input ID filtering from CSV (backward compatibility alias).

    Note:
        This is a simplified version that supports both single-column and
        multi-column modes. The full implementation is in `pipeline_config`.

    Deprecated:
        Use `BaseInputFilterConfig` from `base_schemas` or extended
        `InputFilterConfig` from `pipeline_config` instead.
    """

    def to_domain(self) -> DomainInputFilterConfig:
        """Convert Pydantic schema to domain InputFilterConfig.

        Returns:
            Domain-layer InputFilterConfig for selective record processing.
        """
        return super().to_domain()


class MaintenanceConfig(BaseMaintenanceConfig):
    """Configuration for maintenance operations (backward compatibility alias).

    Deprecated:
        Use `BaseMaintenanceConfig` from `base_schemas` instead.
    """


class ApiConfig(BaseApiConfig):
    """Configuration for API connection details (backward compatibility alias).

    Deprecated:
        Use `BaseApiConfig` from `base_schemas` instead.
    """

    def to_domain(self) -> DomainBaseClientConfig:
        """Convert Pydantic schema to domain BaseClientConfig.

        Returns:
            Domain-layer BaseClientConfig for HTTP client initialization.
        """
        return super().to_domain()


__all__ = [
    "ApiConfig",
    "CircuitBreakerConfig",
    "CsvExportConfig",
    "DQConfig",
    "InputFilterConfig",
    "MaintenanceConfig",
]
