# src/bioetl/composition/factories/__init__.py
"""Pipeline factories module.

Provides the GenericPipelineFactory for creating pipeline instances declaratively.

Usage:
    >>> from bioetl.composition.factories import GenericPipelineFactory
    >>> factory = GenericPipelineFactory(...)

All pipeline factories are auto-registered when this module is imported.
"""

# Core factory infrastructure
from bioetl.composition.factories.data_source_registry import (
    DataSourceCreator,
    DataSourceRegistry,
)
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

__all__ = [
    "DataSourceCreator",
    "DataSourceRegistry",
    "GenericPipelineFactory",
    "chembl_activity_factory",
    "create_pipeline_factory",
    "pubchem_compound_factory",
    "pubmed_publications_factory",
    "uniprot_protein_factory",
]
