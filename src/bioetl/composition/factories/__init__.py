# src/bioetl/composition/factories/__init__.py

# Import all pipeline factories to ensure they are registered in the PipelineRegistry.
# The registration happens at import time when the @register decorator is processed.

from . import chembl_activity
from . import pubchem_compound
from . import uniprot_protein
from . import pubmed_publications

__all__ = [
    "chembl_activity",
    "pubchem_compound",
    "uniprot_protein",
    "pubmed_publications",
]
