# src/bioetl/composition/factories/__init__.py
"""Pipeline factories module.

Provides the GenericPipelineFactory for creating pipeline instances declaratively.

Usage:
    >>> from bioetl.composition.factories import GenericPipelineFactory
    >>> factory = GenericPipelineFactory(...)

All pipeline factories are auto-registered when this module is imported.

Consolidated in v5.2:
- pipeline_factory.py: GenericPipelineFactory, runner assembly functions
- services_factory.py: BaseServicesFactory, ServicesBuilder, RunnerServices
- adapters_factory.py: HttpClientFactory, DataSourceFactory, DataSourceRegistry
- registry.py: Pipeline factory instances, transformer registry
- storage_factory.py: StorageFactory, StorageContext
- storage_adapter.py: StorageAdapter
"""

# Adapters factory (HTTP clients, data sources)
from bioetl.composition.factories.adapters_factory import (
    DataSourceCreator,
    DataSourceFactory,
    DataSourceRegistry,
    HttpClientFactory,
)

# Pipeline factory (GenericPipelineFactory, runner assembly)
from bioetl.composition.factories.pipeline_factory import (
    GenericPipelineFactory,
    assemble_runner,
    build_pipeline_services,
    create_pipeline_factory,
)

# Registry (pipeline factories, transformer registry)
from bioetl.composition.factories.registry import (
    chembl_activity_factory,
    chembl_assay_factory,
    chembl_document_factory,
    chembl_molecule_factory,
    chembl_target_component_factory,
    chembl_target_factory,
    create_transformer,
    get_transformer_class,
    pubchem_compound_factory,
    pubmed_publications_factory,
    register_all_pipelines,
    register_all_transformers,
    register_transformer,
    uniprot_protein_factory,
)

# Services factory (BaseServicesFactory, ServicesBuilder, RunnerServices)
from bioetl.composition.factories.services_factory import (
    BaseServicesFactory,
    RunnerServices,
    ServicesBuilder,
    build_runner_services,
)

# Storage factory
from bioetl.composition.factories.storage_factory import (
    StorageAdapter,
    StorageContext,
    StorageFactory,
)

__all__ = [
    "BaseServicesFactory",
    "DataSourceCreator",
    "DataSourceFactory",
    "DataSourceRegistry",
    "GenericPipelineFactory",
    "HttpClientFactory",
    "RunnerServices",
    "ServicesBuilder",
    "StorageAdapter",
    "StorageContext",
    "StorageFactory",
    "assemble_runner",
    "build_pipeline_services",
    "build_runner_services",
    "chembl_activity_factory",
    "chembl_assay_factory",
    "chembl_document_factory",
    "chembl_molecule_factory",
    "chembl_target_component_factory",
    "chembl_target_factory",
    "create_pipeline_factory",
    "create_transformer",
    "get_transformer_class",
    "pubchem_compound_factory",
    "pubmed_publications_factory",
    "register_all_pipelines",
    "register_all_transformers",
    "register_transformer",
    "uniprot_protein_factory",
]
