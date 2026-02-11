"""PubChem provider adapter.

Implements RULES.md Appendix A - PubChem data source.
"""

from __future__ import annotations

from bioetl.infrastructure.adapters.pubchem.client import PubChemAdapter
from bioetl.infrastructure.adapters.pubchem.models import (
    PUBCHEM_RECORD_MODELS,
    PubChemAssayRecord,
    PubChemBioactivityRecord,
    PubchemMoleculeApiRecord,
    PubchemMoleculeDetailRecord,
    PubChemSubstanceRecord,
)

__all__ = [
    # Model Mappings
    "PUBCHEM_RECORD_MODELS",
    # Adapter
    "PubChemAdapter",
    # Record Models
    "PubChemAssayRecord",
    "PubChemBioactivityRecord",
    "PubChemSubstanceRecord",
    "PubchemMoleculeDetailRecord",
    "PubchemMoleculeApiRecord",
]
