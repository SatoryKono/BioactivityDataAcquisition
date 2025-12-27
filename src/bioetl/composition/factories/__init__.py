# src/bioetl/composition/factories/__init__.py
"""Pipeline factories module.

Provides the GenericPipelineFactory for creating pipeline instances declaratively.

Usage:
    >>> from bioetl.composition.factories import GenericPipelineFactory
    >>> factory = GenericPipelineFactory(...)

All pipeline factories are auto-registered when this module is imported.

Structure after consolidation (v5.2):
- pipeline_factory.py: GenericPipelineFactory, runner assembly, runner services
- services_factory.py: BaseServicesFactory, ServicesBuilder
- data_source_factory.py: DataSourceFactory, DataSourceRegistry
- storage.py: StorageAdapter, StorageContext, StorageFactory
- http_client_factory.py: HttpClientFactory
- transformer_factory.py: TransformerFactory functions
- pipeline_factories.py: Pipeline definitions and registration
"""

# Core factory infrastructure - from consolidated modules
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
from bioetl.composition.factories.pipeline_factory import (
    GenericPipelineFactory,
    RunnerServices,
    assemble_runner,
    build_pipeline_services,
    build_runner_services,
    create_pipeline_factory,
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
    "DataSourceCreator",
    "DataSourceFactory",
    "DataSourceRegistry",
    "GenericPipelineFactory",
    "RunnerServices",
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
