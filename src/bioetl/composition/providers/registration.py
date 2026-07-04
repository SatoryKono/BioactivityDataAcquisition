"""Explicit provider registration entrypoint for the composition layer.

Wave 3 ownership classification: simplify-now closeout complete.

Canonical assembly ownership now lives in ``_registration_contracts.py``,
``_config_helpers.py``, and the family-specific manifest builders. This module
stays as a thin explicit bootstrap seam that merges family builders onto an
injected or canonically resolved registry.
"""

from __future__ import annotations

from collections.abc import Callable

from bioetl.composition.providers._models import ProviderConfig
from bioetl.composition.providers._registration_contracts import (
    ProviderAssemblySupport,
    resolve_provider_assembly_support,
)
from bioetl.composition.providers._registry_protocols import (
    ProviderRegistrarProtocol,
)
from bioetl.composition.providers._registry_resolution import (
    resolve_provider_registry,
)
from bioetl.composition.providers.registration_biblio import (
    _get_biblio_provider_configs,
)
from bioetl.composition.providers.registration_bio import (
    _get_bio_provider_configs,
)

__all__ = [
    "ProviderAssemblySupport",
    "register_all_providers",
    "resolve_provider_assembly_support",
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
    target_registry = resolve_provider_registry(registry)
    support = resolve_provider_assembly_support(
        assembly_support,
        provider_registry=target_registry,
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
    return _merge_provider_config_families(
        assembly_support=support,
    )


def _merge_provider_config_families(
    *,
    assembly_support: ProviderAssemblySupport,
) -> dict[str, ProviderConfig]:
    """Merge provider-config families through one canonical assembly path."""
    merged: dict[str, ProviderConfig] = {}
    for build_family_configs in _iter_provider_config_family_builders():
        merged.update(build_family_configs(assembly_support=assembly_support))
    return merged


def _iter_provider_config_family_builders() -> tuple[
    Callable[..., dict[str, ProviderConfig]],
    ...,
]:
    """Return ordered family builders for provider registration assembly."""
    return (
        _get_bio_provider_configs,
        _get_biblio_provider_configs,
    )
