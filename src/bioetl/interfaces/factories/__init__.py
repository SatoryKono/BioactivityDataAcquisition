"""Pipeline factories for the interfaces layer.

Note: Factories have been moved to bioetl.composition.factories.
This module re-exports them for backward compatibility.
"""

from bioetl.composition.factories.pipeline_factories import (
    chembl_activity_factory,
    pubchem_compound_factory,
    pubmed_publications_factory,
    uniprot_protein_factory,
)

__all__ = [
    "chembl_activity_factory",
    "pubchem_compound_factory",
    "pubmed_publications_factory",
    "uniprot_protein_factory",
]
