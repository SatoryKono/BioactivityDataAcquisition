# src/bioetl/composition/factories/__init__.py
"""Pipeline factories module.

Provides the GenericPipelineFactory for creating pipeline instances declaratively.

Usage:
    >>> from bioetl.composition.factories import GenericPipelineFactory
    >>> factory = GenericPipelineFactory(...)

All pipeline factories are auto-registered when this module is imported.

Consolidated modules (v5.2):
- pipeline_factory: GenericPipelineFactory, runner assembly
- services_factory: BaseServicesFactory, ServicesBuilder, RunnerServices
- data_source_factory: DataSourceFactory, DataSourceRegistry
- storage: StorageAdapter, StorageContext, StorageFactory
"""

# Data source factory and registry
from bioetl.composition.factories.data_source_factory import (
    DataSourceCreator,
    DataSourceFactory,
    DataSourceRegistry,
)

# Import to trigger pipeline registration
from bioetl.composition.factories.pipeline_factories import (
    chembl_activity_factory,
    pubchem_compound_factory,
    pubmed_publications_factory,
    uniprot_protein_factory,
)

# Pipeline factory and runner assembly
from bioetl.composition.factories.pipeline_factory import (
    GenericPipelineFactory,
    assemble_runner,
    build_pipeline_services,
    create_pipeline_factory,
)

# Services factory (DI for PipelineRunner)
from bioetl.composition.factories.services_factory import (
    BaseServicesFactory,
    RunnerServices,
    ServicesBuilder,
    build_runner_services,
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

__all__ = [
    "BaseServicesFactory",
    "DataSourceCreator",
    "DataSourceFactory",
    "DataSourceRegistry",
    "GenericPipelineFactory",
    "RunnerServices",
    "ServicesBuilder",
    "StorageAdapter",
    "StorageContext",
    "StorageFactory",
    "assemble_runner",
    "build_pipeline_services",
    "build_runner_services",
    "chembl_activity_factory",
    "create_pipeline_factory",
    "create_transformer",
    "get_transformer_class",
    "pubchem_compound_factory",
    "pubmed_publications_factory",
    "register_all_transformers",
    "register_transformer",
    "uniprot_protein_factory",
]
