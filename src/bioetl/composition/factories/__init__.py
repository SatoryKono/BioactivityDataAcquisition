# src/bioetl/composition/factories/__init__.py
"""Pipeline factories for BioETL.

This module provides factory classes and instances for creating pipeline objects.

New architecture (recommended):
- GenericPipelineFactory: Generic factory class for all pipelines
- DataSourceRegistry: Centralized registry for data source creators
- *_factory instances: Pre-configured GenericPipelineFactory instances

Legacy architecture (deprecated):
- *PipelineFactory classes: Will be removed in future versions
"""

# Import all pipeline factories to ensure they are registered in the PipelineRegistry.
# The registration happens at import time.
from . import chembl_activity, pubchem_compound, pubmed_publications, uniprot_protein

# Export factory instances for direct use
from .chembl_activity import chembl_activity_factory

# New factory infrastructure
from .data_source_registry import (
    DataSourceCreator,
    DataSourceRegistry,
    create_chembl_data_source,
    create_pubchem_data_source,
    create_pubmed_data_source,
    create_uniprot_data_source,
)
from .generic_pipeline_factory import (
    GenericPipelineFactory,
    create_pipeline_factory,
)
from .pubchem_compound import pubchem_compound_factory
from .pubmed_publications import pubmed_publications_factory
from .uniprot_protein import uniprot_protein_factory

__all__ = [
    "DataSourceCreator",
    "DataSourceRegistry",
    "GenericPipelineFactory",
    "chembl_activity",
    "chembl_activity_factory",
    "create_chembl_data_source",
    "create_pipeline_factory",
    "create_pubchem_data_source",
    "create_pubmed_data_source",
    "create_uniprot_data_source",
    "pubchem_compound",
    "pubchem_compound_factory",
    "pubmed_publications",
    "pubmed_publications_factory",
    "uniprot_protein",
    "uniprot_protein_factory",
]
