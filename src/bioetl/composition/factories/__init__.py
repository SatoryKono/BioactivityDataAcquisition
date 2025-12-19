# src/bioetl/composition/factories/__init__.py
"""Pipeline factories module.

Provides both legacy class-based factories and new generic factory pattern.

Usage (new pattern):
    >>> from bioetl.composition.factories import GenericPipelineFactory
    >>> factory = GenericPipelineFactory(...)

Usage (legacy pattern):
    >>> from bioetl.composition.factories import chembl_activity
"""

# New unified factory system
from bioetl.composition.factories.data_source_registry import (
    DataSourceCreator,
    DataSourceRegistry,
)
from bioetl.composition.factories.generic_factory import (
    GenericPipelineFactory,
    create_pipeline_factory,
)

# Import all pipeline factories to ensure they are registered in the PipelineRegistry.
# The registration happens at import time when the module is loaded.
from . import chembl_activity, pubchem_compound, pubmed_publications, uniprot_protein

__all__ = [
    # New generic factory
    "GenericPipelineFactory",
    "create_pipeline_factory",
    "DataSourceRegistry",
    "DataSourceCreator",
    # Legacy factories (still functional)
    "chembl_activity",
    "pubchem_compound",
    "uniprot_protein",
    "pubmed_publications",
]
