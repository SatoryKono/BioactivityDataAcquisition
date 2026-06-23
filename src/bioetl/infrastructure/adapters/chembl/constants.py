"""Constants and mappings for ChEMBL adapter."""

from __future__ import annotations

__all__ = ["CHEMBL_API_BASE", "CHEMBL_STATUS_URL"]


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic import BaseModel

from bioetl.domain.entities.chembl import (
    ActivityRecord,
    AssayRecord,
    CellLineRecord,
    ChemblPublicationRecord,
    CompoundLinkRecord,
    MoleculeRecord,
    ProteinClassRecord,
    PublicationSimilarityRecord,
    TargetComponentRecord,
    TargetRecord,
    TissueRecord,
)

# ChEMBL API base URL
# Note: ChEMBL API no longer supports .json extension - use format=json parameter instead
CHEMBL_API_BASE = "https://www.ebi.ac.uk/chembl/api/data"
CHEMBL_STATUS_URL = f"{CHEMBL_API_BASE}/status"

# Mapping from entity_type to DTO model class
CHEMBL_DTO_MODELS: dict[str, type[BaseModel]] = {
    "activity": ActivityRecord,
    "assay": AssayRecord,
    "molecule": MoleculeRecord,
    "compound": MoleculeRecord,  # Alias for molecule
    "target": TargetRecord,
    "target_component": TargetComponentRecord,
    "publication": ChemblPublicationRecord,
    "document": ChemblPublicationRecord,
    "cell_line": CellLineRecord,
    "protein_class": ProteinClassRecord,
    "protein_classification": ProteinClassRecord,
    "tissue": TissueRecord,
    "compound_record": CompoundLinkRecord,
    "publication_similarity": PublicationSimilarityRecord,
    "document_similarity": PublicationSimilarityRecord,
}

# Entity types that don't support limit/offset pagination
# These endpoints return all records in a single response.
_NO_PAGINATION_ENTITIES: frozenset[str] = frozenset(
    {
        "target_component",
        "protein_class",
    }
)

# Silver canonical name → ChEMBL API field name.
# ChEMBL API silently ignores unknown filter params and returns ALL records,
# so correct mapping is critical for filtering to work.
_SILVER_TO_CHEMBL_API_FIELD: dict[str, str] = {
    "molecule_id": "molecule_chembl_id",
    "publication_id": "document_chembl_id",
    "assay_id": "assay_chembl_id",
    "target_id": "target_chembl_id",
    "cell_id": "cell_chembl_id",
    "tissue_id": "tissue_chembl_id",
}
