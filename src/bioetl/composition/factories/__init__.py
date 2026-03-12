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
- storage: StorageAdapter, StorageContext, StorageFactory
- dq_services_factory: DQServicesFactory for DQ report components
"""
from __future__ import annotations

from typing import TYPE_CHECKING

# Data source factory and registry
from bioetl.composition.factories.datasource.data_source_factory import (
    DataSourceCreatorProtocol,
    DataSourceFactory,
    DataSourceRegistry,
)

# DQ services factory
from bioetl.composition.factories.dq.dq_services_factory import DQServicesFactory

# Pipeline factory and runner assembly
from bioetl.composition.factories.pipeline import (
    GenericPipelineFactory,
    assemble_runner,
    build_pipeline_services,
    create_pipeline_factory,
)

# Services factory (DI for PipelineRunner)
from bioetl.composition.factories.services.factory import (
    BaseServicesFactory,
    ServicesBuilder,
    create_data_normalization_service,
)

# Storage factory
from bioetl.composition.factories.storage import (
    StorageAdapter,
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

if TYPE_CHECKING:
    # For static analyzers only; runtime uses lazy __getattr__ below.
    from bioetl.composition.factories.pipeline.registry import (
        chembl_activity_factory,
        pubchem_compound_factory,
        pubmed_publication_factory,
        uniprot_protein_factory,
    )

_PIPELINE_FACTORY_EXPORTS = frozenset(
    {
        "chembl_activity_factory",
        "pubchem_compound_factory",
        "pubmed_publication_factory",
        "uniprot_protein_factory",
    }
)

DataSourceCreatorPort = DataSourceCreatorProtocol


def __getattr__(name: str) -> object:
    """Lazily expose heavy pipeline factory singletons to avoid import cycles."""
    if name not in _PIPELINE_FACTORY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from bioetl.composition.factories.pipeline import registry as _registry

    return getattr(_registry, name)


__all__ = [
    "BaseServicesFactory",
    "DQServicesFactory",
    "DataSourceCreatorProtocol",
    "DataSourceFactory",
    "DataSourceRegistry",
    "GenericPipelineFactory",
    "ServicesBuilder",
    "StorageAdapter",
    "StorageContext",
    "StorageFactory",
    "assemble_runner",
    "build_pipeline_services",
    "chembl_activity_factory",
    "create_data_normalization_service",
    "create_pipeline_factory",
    "create_transformer",
    "get_transformer_class",
    "pubchem_compound_factory",
    "pubmed_publication_factory",
    "register_all_transformers",
    "register_transformer",
    "uniprot_protein_factory",
]
