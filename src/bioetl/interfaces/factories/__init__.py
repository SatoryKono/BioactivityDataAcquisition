"""Re-exports pipeline factories for external use.

This module provides a clean public API for accessing pipeline factories
from the interfaces layer. The actual factory implementations reside in
the composition layer.
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
