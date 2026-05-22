# mypy: disable-error-code="misc"
"""Additional ChEMBL API response models for non-core API-backed entities."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from bioetl.infrastructure.adapters.chembl.models_common import ChemblPageMeta

__all__ = [
    "ChemblCompoundRecordApiRecord",
    "ChemblCompoundRecordResponse",
    "ChemblProteinClassApiRecord",
    "ChemblProteinClassResponse",
    "ChemblPublicationSimilarityApiRecord",
    "ChemblPublicationSimilarityResponse",
    "ChemblTissueApiRecord",
    "ChemblTissueResponse",
]

_PAGINATION_METADATA_DESCRIPTION = "Pagination metadata"


class ChemblTissueApiRecord(BaseModel):
    """Individual tissue record from the ChEMBL API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    tissue_chembl_id: str = Field(description="ChEMBL ID of the tissue")
    pref_name: str | None = Field(default=None, description="Preferred name")
    bto_id: str | None = Field(default=None, description="BRENDA tissue ontology ID")
    caloha_id: str | None = Field(default=None, description="CALOHA tissue ID")
    efo_id: str | None = Field(default=None, description="EFO tissue ID")
    uberon_id: str | None = Field(default=None, description="UBERON tissue ID")


class ChemblTissueResponse(BaseModel):
    """Complete ChEMBL Tissue API response."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    tissues: list[ChemblTissueApiRecord] = Field(
        default_factory=list, description="List of tissue records"
    )
    page_meta: ChemblPageMeta | None = Field(
        default=None, description=_PAGINATION_METADATA_DESCRIPTION
    )


class ChemblCompoundRecordApiRecord(BaseModel):
    """Individual compound-record link from the ChEMBL API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    record_id: int = Field(description="ChEMBL compound-record identifier")
    molecule_chembl_id: str | None = Field(
        default=None, description="Linked molecule ChEMBL ID"
    )
    document_chembl_id: str | None = Field(
        default=None, description="Linked document ChEMBL ID"
    )
    compound_key: str | None = Field(default=None, description="Provider compound key")
    compound_name: str | None = Field(
        default=None, description="Provider compound name"
    )
    src_id: int | None = Field(default=None, description="Provider source ID")
    src_compound_id: str | None = Field(
        default=None, description="Provider source compound identifier"
    )


class ChemblCompoundRecordResponse(BaseModel):
    """Complete ChEMBL Compound Record API response."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    compound_records: list[ChemblCompoundRecordApiRecord] = Field(
        default_factory=list, description="List of compound-record rows"
    )
    page_meta: ChemblPageMeta | None = Field(
        default=None, description=_PAGINATION_METADATA_DESCRIPTION
    )


class ChemblProteinClassApiRecord(BaseModel):
    """Individual protein classification node from the ChEMBL API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    protein_class_id: int = Field(description="Protein class identifier")
    parent_id: int | None = Field(default=None, description="Parent class identifier")
    class_level: int | None = Field(default=None, description="Hierarchy level")
    pref_name: str | None = Field(default=None, description="Preferred name")
    short_name: str | None = Field(default=None, description="Short name")
    protein_class_desc: str | None = Field(
        default=None, description="Protein class description"
    )
    definition: str | None = Field(default=None, description="Definition")
    sort_order: int | None = Field(default=None, description="Sort order")
    replaced_by: int | None = Field(
        default=None, description="Replacement protein class identifier"
    )
    downgraded: int | None = Field(default=None, description="Downgraded flag")


class ChemblProteinClassResponse(BaseModel):
    """Complete ChEMBL Protein Classification API response."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    protein_classifications: list[ChemblProteinClassApiRecord] = Field(
        default_factory=list, description="List of protein classification rows"
    )
    page_meta: ChemblPageMeta | None = Field(
        default=None, description=_PAGINATION_METADATA_DESCRIPTION
    )


class ChemblPublicationSimilarityApiRecord(BaseModel):
    """Individual publication-similarity row from the ChEMBL API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    document_1_chembl_id: str = Field(description="Primary document ChEMBL identifier")
    document_2_chembl_id: str = Field(
        description="Secondary document ChEMBL identifier"
    )
    tid_tani: float | None = Field(
        default=None, description="Target-identifier similarity score"
    )
    mol_tani: float | None = Field(
        default=None, description="Molecule similarity score"
    )


class ChemblPublicationSimilarityResponse(BaseModel):
    """Complete ChEMBL Publication Similarity API response."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    document_similarities: list[ChemblPublicationSimilarityApiRecord] = Field(
        default_factory=list, description="List of publication-similarity rows"
    )
    page_meta: ChemblPageMeta | None = Field(
        default=None, description=_PAGINATION_METADATA_DESCRIPTION
    )
