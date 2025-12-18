"""Pipeline factories for the interfaces layer.

Note: Factories have been moved to bioetl.composition.factories.
This module re-exports them for backward compatibility.
"""

from bioetl.composition.factories.chembl_activity import ChEMBLActivityPipelineFactory
from bioetl.composition.factories.pubchem_compound import PubChemCompoundPipelineFactory
from bioetl.composition.factories.uniprot_protein import UniProtProteinPipelineFactory

__all__ = [
    "ChEMBLActivityPipelineFactory",
    "PubChemCompoundPipelineFactory",
    "UniProtProteinPipelineFactory",
]
