"""Compatibility wrapper for provider domain types."""

from bioetl.core.providers import ProviderComponents, ProviderDefinition, ProviderId
from bioetl.schemas.provider_config_schema import BaseProviderConfig

__all__ = [
    "BaseProviderConfig",
    "ProviderComponents",
    "ProviderDefinition",
    "ProviderId",
]
