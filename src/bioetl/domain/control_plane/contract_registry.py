"""Facade exports for contract registry domain APIs."""

from __future__ import annotations

from .contract_registry_service import (
    ContractRegistry,
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
    "RegistryValidationError",
    "RegistryValidationIssue",
    "RegistryValidationResult",
    "RegistryValidationSeverity",
]
