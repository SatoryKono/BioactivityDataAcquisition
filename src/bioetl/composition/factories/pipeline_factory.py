"""Pipeline Factory - backward-compatibility re-export facade.

All implementation has been extracted to:
- pipeline_assembler.py: GenericPipelineFactory, assemble_runner, create_pipeline_factory
- service_bundle_factory.py: build_pipeline_services, create_pipeline_with_services
- dq_context_resolver.py: DQ config extraction helpers
"""

from __future__ import annotations

import warnings

from bioetl.composition.factories.dq_context_resolver import (
    extract_dq_configs as _extract_dq_configs,
)
from bioetl.composition.factories.dq_context_resolver import (
    extract_dq_output_paths as _extract_dq_output_paths,
)
from bioetl.composition.factories.dq_context_resolver import (
    extract_single_dq_config as _extract_single_dq_config,
)
from bioetl.composition.factories.dq_context_resolver import (
    get_layer_path as _get_layer_path,
)
from bioetl.composition.factories.dq_context_resolver import (
    has_flat_structure as _has_flat_structure,
)
from bioetl.composition.factories.pipeline_assembler import (
    GenericPipelineFactory,
    assemble_runner,
    create_pipeline_factory,
)
from bioetl.composition.factories.service_bundle_factory import (
    ServiceBundleDependencies,
    _create_cached_bronze_data_source,
    _create_data_source,
)
from bioetl.composition.factories.service_bundle_factory import (
    build_pipeline_services as _build_pipeline_services,
)
from bioetl.composition.factories.service_bundle_factory import (
    create_pipeline_with_services as _create_pipeline_with_services,
)
from bioetl.composition.factories.services_factory import BaseServicesFactory
from bioetl.composition.services.versioning import compute_config_hash
from bioetl.infrastructure.config import load_pipeline_config, yaml_config_to_domain

# Keep explicit references so static analyzers treat legacy re-exports as used.
_LEGACY_REEXPORTS = (
    _extract_dq_configs,
    _extract_dq_output_paths,
    _extract_single_dq_config,
    _get_layer_path,
    _has_flat_structure,
    _create_cached_bronze_data_source,
    _create_data_source,
)


def _compat_service_bundle_dependencies() -> ServiceBundleDependencies:
    """Build compatibility dependencies bound to pipeline_factory facade symbols."""
    return ServiceBundleDependencies(
        load_pipeline_config=load_pipeline_config,
        yaml_config_to_domain=yaml_config_to_domain,
        compute_config_hash=compute_config_hash,
        base_services_factory=BaseServicesFactory,
    )


def build_pipeline_services(*args: object, **kwargs: object) -> object:
    """Compatibility facade delegating to service_bundle_factory implementation."""
    warnings.warn(
        "Use bioetl.composition.factories.service_bundle_factory.build_pipeline_services "
        "for direct wiring. pipeline_factory facade remains for compatibility.",
        DeprecationWarning,
        stacklevel=2,
    )
    kwargs.setdefault("_deps", _compat_service_bundle_dependencies())
    return _build_pipeline_services(*args, **kwargs)


def create_pipeline_with_services(*args: object, **kwargs: object) -> object:
    """Compatibility facade delegating to service_bundle_factory implementation."""
    warnings.warn(
        "Use bioetl.composition.factories.service_bundle_factory.create_pipeline_with_services "
        "for direct wiring. pipeline_factory facade remains for compatibility.",
        DeprecationWarning,
        stacklevel=2,
    )
    kwargs.setdefault("_deps", _compat_service_bundle_dependencies())
    return _create_pipeline_with_services(*args, **kwargs)


__all__ = [
    "BaseServicesFactory",
    "GenericPipelineFactory",
    "_create_cached_bronze_data_source",
    "_create_data_source",
    "_extract_dq_configs",
    "_extract_dq_output_paths",
    "_extract_single_dq_config",
    "_get_layer_path",
    "_has_flat_structure",
    "assemble_runner",
    "build_pipeline_services",
    "compute_config_hash",
    "create_pipeline_factory",
    "create_pipeline_with_services",
    "load_pipeline_config",
    "yaml_config_to_domain",
]
