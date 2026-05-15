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
    ChemblCompoundRecordApiRecord,
    ChemblCompoundRecordResponse,
    ChemblMoleculeRecord,
    ChemblMoleculeResponse,
    ChemblPageMeta,
    ChemblProteinClassApiRecord,
    ChemblProteinClassResponse,
    ChemblPublicationApiRecord,
    ChemblPublicationResponse,
    ChemblPublicationSimilarityApiRecord,
    ChemblPublicationSimilarityResponse,
    ChemblTargetComponentRecord,
    ChemblTargetComponentResponse,
    ChemblTargetRecord,
    ChemblTargetResponse,
    ChemblTissueApiRecord,
    ChemblTissueResponse,
)

__all__ = [
    "CHEMBL_RECORD_MODELS",
    "CHEMBL_RESPONSE_MODELS",
    "ChemblActivityRecord",
    "ChemblActivityResponse",
    "ChemblAdapter",
    "ChemblAssayRecord",
    "ChemblAssayResponse",
    "ChemblCompoundRecordApiRecord",
    "ChemblCompoundRecordResponse",
    "ChemblMoleculeRecord",
    "ChemblMoleculeResponse",
    "ChemblPageMeta",
    "ChemblProteinClassApiRecord",
    "ChemblProteinClassResponse",
    "ChemblPublicationApiRecord",
    "ChemblPublicationResponse",
    "ChemblPublicationSimilarityApiRecord",
    "ChemblPublicationSimilarityResponse",
    "ChemblTargetComponentRecord",
    "ChemblTargetComponentResponse",
    "ChemblTargetRecord",
    "ChemblTargetResponse",
    "ChemblTissueApiRecord",
    "ChemblTissueResponse",
]
