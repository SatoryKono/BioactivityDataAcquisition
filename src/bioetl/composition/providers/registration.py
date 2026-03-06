"""Explicit provider registration for Composition layer.

Loads config from configs/providers/*.yaml. HttpConfig serves as fallback.
Config helpers extracted to _config_helpers.py per audit-package-structure-2026-02-07.
Creator functions extracted to registration_bio.py and registration_biblio.py.
ProviderConfig building delegated to sibling modules (Wave 3 simplification).
"""

from __future__ import annotations

from bioetl.composition.providers.provider_registry import (
    ProviderConfig,
    ProviderRegistry,
)
from bioetl.composition.providers.registration_biblio import (
    _get_biblio_provider_configs,
)
from bioetl.composition.providers.registration_bio import (
    _get_bio_provider_configs,
)

__all__ = [
    "register_all_providers",
]


def register_all_providers() -> None:
    """Explicitly register all data source providers.

    This function MUST be called from bootstrap before using ProviderRegistry.
    Idempotent - safe to call multiple times.

    Configuration Priority:
    1. configs/providers/{provider}.yaml - PRIMARY (rate limits, circuit breaker, batch_size)
    2. HttpConfig in ProviderConfig - FALLBACK only

    Each provider includes a data_source_creator for unified registry access.
    """
    for provider_name, config in _build_provider_configs().items():
        if ProviderRegistry.is_registered(provider_name):
            continue
        ProviderRegistry.register(provider_name, config)


def _build_provider_configs() -> dict[str, ProviderConfig]:
    """Build provider registry configs from YAML-backed rate limits."""
    return {**_get_bio_provider_configs(), **_get_biblio_provider_configs()}
