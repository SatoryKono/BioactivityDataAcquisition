"""ChEMBL data source adapter.

Implements DataSourcePort for ChEMBL database.
See RULES.md Appendix A for rate limits and retry strategy.
"""

from __future__ import annotations

from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter
from bioetl.infrastructure.adapters.chembl.models import (
    CHEMBL_RECORD_MODELS,
    CHEMBL_RESPONSE_MODELS,
    ChemblActivityRecord,
    ChemblActivityResponse,
    ChemblAssayRecord,
    ChemblAssayResponse,
    ChemblDocumentRecord,
    ChemblDocumentResponse,
    ChemblMoleculeRecord,
    ChemblMoleculeResponse,
    ChemblPageMeta,
    ChemblTargetComponentRecord,
    ChemblTargetComponentResponse,
    ChemblTargetRecord,
    ChemblTargetResponse,
)

__all__ = [
    # Model Mappings
    "CHEMBL_RECORD_MODELS",
    "CHEMBL_RESPONSE_MODELS",
    # Record Models
    "ChemblActivityRecord",
    # Response Models
    "ChemblActivityResponse",
    # Adapter
    "ChemblAdapter",
    "ChemblAssayRecord",
    "ChemblAssayResponse",
    "ChemblDocumentRecord",
    "ChemblDocumentResponse",
    "ChemblMoleculeRecord",
    "ChemblMoleculeResponse",
    "ChemblPageMeta",
    "ChemblTargetComponentRecord",
    "ChemblTargetComponentResponse",
    "ChemblTargetRecord",
    "ChemblTargetResponse",
]
