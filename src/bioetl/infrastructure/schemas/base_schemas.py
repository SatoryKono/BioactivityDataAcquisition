"""Facade module for shared base schema components.

This module preserves stable import paths while implementations live in
provider-split modules.
"""

from __future__ import annotations

from bioetl.infrastructure.schemas.base_schemas_chembl import (
    BaseApiConfig,
    BaseCircuitBreakerConfig,
    BaseCsvExportConfig,
    BaseDQConfig,
    BaseDQThresholds,
    BaseMaintenanceConfig,
    BaseRateLimitConfig,
    HttpClientConfig,
)
from bioetl.infrastructure.schemas.base_schemas_pubchem import (
    BaseFilterColumnSchema,
    BaseGoldColumnFilterConfig,
    BaseGoldFiltersConfig,
    BaseGoldListContainsFilterConfig,
    BaseGoldListLengthFilterConfig,
    BaseGoldRangeFilterConfig,
    BaseInputFilterConfig,
)

__all__ = [
    "BaseApiConfig",
    "BaseCircuitBreakerConfig",
    "BaseCsvExportConfig",
    "BaseDQConfig",
    "BaseDQThresholds",
    "BaseFilterColumnSchema",
    "BaseGoldColumnFilterConfig",
    "BaseGoldFiltersConfig",
    "BaseGoldListContainsFilterConfig",
    "BaseGoldListLengthFilterConfig",
    "BaseGoldRangeFilterConfig",
    "BaseInputFilterConfig",
    "BaseMaintenanceConfig",
    "BaseRateLimitConfig",
    "HttpClientConfig",
]
