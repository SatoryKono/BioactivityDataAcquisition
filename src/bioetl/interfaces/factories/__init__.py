"""Pipeline factories for the interfaces layer.

Note: Factories have been moved to bioetl.composition.factories.
This module re-exports them for backward compatibility.

New architecture (recommended):
- GenericPipelineFactory: Generic factory class
- *_factory instances: Pre-configured GenericPipelineFactory instances

Legacy classes (deprecated):
- *PipelineFactory classes: Will emit deprecation warnings
"""

# New factory infrastructure
from bioetl.composition.factories import (
    GenericPipelineFactory,
    create_pipeline_factory,
    DataSourceRegistry,
    # Factory instances
    chembl_activity_factory,
    pubchem_compound_factory,
    uniprot_protein_factory,
    pubmed_publications_factory,
)

# Deprecated classes for backwards compatibility
from bioetl.composition.factories.chembl_activity import ChEMBLActivityPipelineFactory
from bioetl.composition.factories.pubchem_compound import PubChemCompoundPipelineFactory
from bioetl.composition.factories.uniprot_protein import UniProtProteinPipelineFactory
from bioetl.composition.factories.pubmed_publications import PubMedPublicationsPipelineFactory

__all__ = [
    # New architecture
    "GenericPipelineFactory",
    "create_pipeline_factory",
    "DataSourceRegistry",
    # Factory instances
    "chembl_activity_factory",
    "pubchem_compound_factory",
    "uniprot_protein_factory",
    "pubmed_publications_factory",
    # Deprecated classes (for backwards compatibility)
    "ChEMBLActivityPipelineFactory",
    "PubChemCompoundPipelineFactory",
    "UniProtProteinPipelineFactory",
    "PubMedPublicationsPipelineFactory",
]
