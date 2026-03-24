"""Explicit provider registration for Composition layer.

Loads config from configs/providers/*.yaml. HttpConfig serves as fallback.
Config helpers extracted to _config_helpers.py per audit-package-structure-2026-02-07.
Creator functions extracted to registration_bio.py and registration_biblio.py.
ProviderConfig building delegated to sibling modules (Wave 3 simplification).
"""

from __future__ import annotations

from typing import cast

from bioetl.composition.providers._default_registry import (
    get_default_provider_registrar,
)
from bioetl.composition.providers._models import ProviderConfig
from bioetl.composition.providers._registration_contracts import (
    ProviderAssemblySupport,
    resolve_provider_assembly_support,
)
from bioetl.composition.providers._registry_protocols import (
    ProviderRegistrarProtocol,
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


def register_all_providers(
    registry: ProviderRegistrarProtocol | None = None,
    *,
    assembly_support: ProviderAssemblySupport | None = None,
) -> None:
    """Explicitly register all data source providers.

    This function MUST be called from bootstrap before using ProviderRegistry.
    Idempotent - safe to call multiple times.

    Configuration Priority:
    1. configs/providers/{provider}.yaml - PRIMARY (rate limits, circuit breaker, batch_size)
    2. HttpConfig in ProviderConfig - FALLBACK only

    Each provider includes a data_source_creator for unified registry access.
    """
    from bioetl.composition.providers.provider_registry import ProviderRegistry

    target_registry = _resolve_registration_registry(registry)
    provider_registry = (
        target_registry if isinstance(target_registry, ProviderRegistry) else None
    )
    support = resolve_provider_assembly_support(
        assembly_support,
        provider_registry=provider_registry,
    )
    for provider_name, config in _build_provider_configs(
        assembly_support=support
    ).items():
        if target_registry.is_registered(provider_name):
            continue
        target_registry.register(provider_name, config)


def _build_provider_configs(
    *,
    assembly_support: ProviderAssemblySupport | None = None,
) -> dict[str, ProviderConfig]:
    """Build provider registry configs from YAML-backed rate limits."""
    support = resolve_provider_assembly_support(assembly_support)
    return {
        **_get_bio_provider_configs(assembly_support=support),
        **_get_biblio_provider_configs(assembly_support=support),
    }


def _resolve_registration_registry(
    registry: ProviderRegistrarProtocol | None,
) -> ProviderRegistrarProtocol:
    """Resolve the target registry while keeping default access as a compat seam."""
    if registry is not None:
        return registry

    return get_default_provider_registrar()
