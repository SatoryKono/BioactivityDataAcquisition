"""Pydantic models for UniProt API responses."""

from __future__ import annotations

from bioetl.infrastructure.adapters.uniprot._uniprot_model_annotations import (
    UniProtComment,
    UniProtEcNumber,
    UniProtEvidence,
    UniProtFullName,
    UniProtGene,
    UniProtIsoform,
    UniProtKeyword,
    UniProtLocation,
    UniProtName,
    UniProtOrganism,
    UniProtProteinDescription,
    UniProtReaction,
    UniProtRecommendedName,
    UniProtSubcellularLocation,
    UniProtText,
)
from bioetl.infrastructure.adapters.uniprot._uniprot_model_records import (
    UNIPROT_RECORD_MODELS,
    UniProtFeatureRecord,
    UniProtProteinRecord,
    UniProtSearchResponse,
    UniProtSequenceRecord,
)
from bioetl.infrastructure.adapters.uniprot._uniprot_model_structures import (
    UniProtCrossReference,
    UniProtExtraAttributes,
    UniProtFeature,
    UniProtFeatureLocation,
    UniProtSequence,
)

__all__ = [
    "UNIPROT_RECORD_MODELS",
    "UniProtComment",
    "UniProtCrossReference",
    "UniProtEcNumber",
    "UniProtEvidence",
    "UniProtExtraAttributes",
    "UniProtFeature",
    "UniProtFeatureLocation",
    "UniProtFeatureRecord",
    "UniProtFullName",
    "UniProtGene",
    "UniProtIsoform",
    "UniProtKeyword",
    "UniProtLocation",
    "UniProtName",
    "UniProtOrganism",
    "UniProtProteinDescription",
    "UniProtProteinRecord",
    "UniProtReaction",
    "UniProtRecommendedName",
    "UniProtSearchResponse",
    "UniProtSequence",
    "UniProtSequenceRecord",
    "UniProtSubcellularLocation",
    "UniProtText",
]
