"""Facade exports for contract registry domain APIs."""

from __future__ import annotations

from .contract_registry_service import (
    ContractRegistry,
    RegistryLoadError,
    create_contract_registry,
)
from .contract_registry_types import (
    ContractRegistryEntry,
    RegistryValidationError,
    RegistryValidationIssue,
    RegistryValidationResult,
    RegistryValidationSeverity,
)

__all__ = [
    "ContractRegistry",
    "ContractRegistryEntry",
    "RegistryLoadError",
    "RegistryValidationError",
    "RegistryValidationIssue",
    "RegistryValidationResult",
    "RegistryValidationSeverity",
    "create_contract_registry",
]
