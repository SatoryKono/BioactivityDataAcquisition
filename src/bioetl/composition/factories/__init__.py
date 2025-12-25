# src/bioetl/composition/factories/__init__.py
"""Pipeline factories module.

Provides the GenericPipelineFactory for creating pipeline instances declaratively.

Usage:
    >>> from bioetl.composition.factories import GenericPipelineFactory
    >>> factory = GenericPipelineFactory(...)

All pipeline factories are auto-registered when this module is imported.

New in v5.1: Client, Storage, and DataSource factories consolidated here from
infrastructure/factories/ following architectural requirements.
"""

# Core factory infrastructure
from bioetl.composition.factories.data_source_registry import (
    DataSourceCreator,
    DataSourceRegistry,
)

# Data source factory
from bioetl.composition.factories.data_sources import DataSourceFactory
from bioetl.composition.factories.generic_factory import (
    GenericPipelineFactory,
    create_pipeline_factory,
)

# Import to trigger pipeline registration
from bioetl.composition.factories.pipeline_factories import (
    chembl_activity_factory,
    pubchem_compound_factory,
    pubmed_publications_factory,
    uniprot_protein_factory,
)

# Storage factory
from bioetl.composition.factories.storage_factory import (
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
    "StorageAdapter",
    "StorageContext",
    "StorageFactory",
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
