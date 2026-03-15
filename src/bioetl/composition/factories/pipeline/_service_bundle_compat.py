"""Internal forwarding helpers for legacy pipeline service-bundle wrappers."""

from __future__ import annotations

import warnings

from bioetl.composition.factories.services.bundle import ServiceBundleDependencies
from bioetl.composition.factories.services.factory import BaseServicesFactory
from bioetl.composition.services.versioning import compute_config_hash
from bioetl.infrastructure.config import load_pipeline_config, yaml_config_to_domain

__all__ = [
    "BaseServicesFactory",
    "ServiceBundleDependencies",
    "compute_config_hash",
    "load_pipeline_config",
    "yaml_config_to_domain",
]

_BUILD_PIPELINE_SERVICES_WARNING = (
    "Use bioetl.composition.factories.services.bundle.build_pipeline_services "
    "for direct wiring. pipeline_factory facade remains for compatibility."
)
_CREATE_PIPELINE_WITH_SERVICES_WARNING = (
    "Use bioetl.composition.factories.services.bundle.create_pipeline_with_services "
    "for direct wiring. pipeline_factory facade remains for compatibility."
)

_DEFAULT_COMPAT_SERVICE_BUNDLE_DEPENDENCIES = ServiceBundleDependencies(
    load_pipeline_config=load_pipeline_config,
    yaml_config_to_domain=yaml_config_to_domain,
    compute_config_hash=compute_config_hash,
    base_services_factory=BaseServicesFactory,
)


def _resolve_compat_service_bundle_dependencies(
    deps: ServiceBundleDependencies | None = None,
) -> ServiceBundleDependencies:
    """Resolve compatibility dependencies bound to legacy facade symbols."""
    return deps or _DEFAULT_COMPAT_SERVICE_BUNDLE_DEPENDENCIES


def _warn_compatibility(message: str) -> None:
    """Emit a deprecation warning for legacy pipeline-facade entrypoints."""
    warnings.warn(
        message,
        DeprecationWarning,
        stacklevel=3,
    )
