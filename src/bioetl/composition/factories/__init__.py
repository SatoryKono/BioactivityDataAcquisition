# src/bioetl/composition/factories/__init__.py
"""Pipeline factories module.

Provides the GenericPipelineFactory for creating pipeline instances declaratively.

Usage:
    >>> from bioetl.composition.factories import GenericPipelineFactory
    >>> factory = GenericPipelineFactory(...)

All pipeline factories are auto-registered when this module is imported.

Consolidated modules (v5.2):
- pipeline_factory: GenericPipelineFactory, runner assembly
- services_factory: BaseServicesFactory, ServicesBuilder
- data_source_factory: DataSourceFactory, DataSourceRegistry
- storage: StorageBundle, StorageContext, StorageFactory
- dq_services_factory: DQServicesFactory for DQ report components
"""

from __future__ import annotations

# Data source factory and registry
from bioetl.composition.factories.datasource.data_source_factory import (
    DataSourceCreatorProtocol,
    DataSourceFactory,
    DataSourceRegistry,
)

# DQ services factory
from bioetl.composition.factories.dq.factory import DQServicesFactory

# Services factory (DI for PipelineRunner)
from bioetl.composition.factories.services.factory import (
    BaseServicesFactory,
    ServicesBuilder,
    create_data_normalization_service,
)

# Storage factory
from bioetl.composition.factories.storage import (
    StorageBundle,
    StorageContext,
    StorageFactory,
)

# Transformer factory (DI for transformers)
from bioetl.composition.factories.transformer_factory import (
    create_transformer,
    get_transformer_class,
    register_all_transformers,
    register_transformer,
)

# Backward-compatible package alias for tests/tools that patch
# `bioetl.composition.factories.datasource.*` via string import paths.
from . import datasource as datasource

_PIPELINE_FACTORY_EXPORTS = frozenset(
    {
        "chembl_activity_factory",
        "pubchem_compound_factory",
        "pubmed_publication_factory",
        "uniprot_protein_factory",
    }
)
# Compatibility alias retained for legacy imports; new code should use
# DataSourceCreatorProtocol directly.
import warnings


class DataSourceCreatorPort(DataSourceCreatorProtocol):
    def __init__(self, *args: object, **kwargs: object) -> None:
        warnings.warn(
            "DataSourceCreatorPort is deprecated and will be removed in v2.0. "
            "Use DataSourceCreatorProtocol instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)


_PIPELINE_EXPORTS = frozenset(
    {
        "GenericPipelineFactory",
        "assemble_runner",
        "build_pipeline_services",
        "create_pipeline_factory",
    }
)


def __getattr__(name: str) -> object:
    """Lazily expose heavy pipeline exports to avoid import cycles."""
    if name in _PIPELINE_EXPORTS:
        from bioetl.composition.factories import pipeline as _pipeline

        return getattr(_pipeline, name)
    if name in _PIPELINE_FACTORY_EXPORTS:
        from bioetl.composition.factories.pipeline import registry as _registry

        return getattr(_registry, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BaseServicesFactory",
    "DQServicesFactory",
    "DataSourceCreatorProtocol",
    "DataSourceFactory",
    "DataSourceRegistry",
    "GenericPipelineFactory",
    "ServicesBuilder",
    "StorageBundle",
    "StorageContext",
    "StorageFactory",
    "assemble_runner",
    "build_pipeline_services",
    "chembl_activity_factory",
    "create_data_normalization_service",
    "create_pipeline_factory",
    "create_transformer",
    "datasource",
    "get_transformer_class",
    "pubchem_compound_factory",
    "pubmed_publication_factory",
    "register_all_transformers",
    "register_transformer",
    "uniprot_protein_factory",
]
