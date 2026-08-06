# mypy: disable-error-code="misc"
"""Common/shared ChEMBL Pydantic models used across endpoint-specific modules."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.adapters.chembl._models_common_extra import (
    ChemblCellLineRecord,
    ChemblCellLineResponse,
    ChemblTargetComponentRecord,
    ChemblTargetComponentResponse,
)
from bioetl.infrastructure.adapters.chembl._models_common_page import ChemblPageMeta

__all__ = [
    "ChemblAssayRecord",
    "ChemblAssayResponse",
    "ChemblCellLineRecord",
    "ChemblCellLineResponse",
    "ChemblPageMeta",
    "ChemblPublicationApiRecord",
    "ChemblPublicationResponse",
    "ChemblReleaseInfo",
    "ChemblTargetComponentRecord",
    "ChemblTargetComponentResponse",
    "ChemblTargetRecord",
    "ChemblTargetResponse",
]

_PAGINATION_METADATA_DESCRIPTION = "Pagination metadata"


class ChemblAssayRecord(BaseModel):
    """Individual assay record from ChEMBL API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    assay_chembl_id: str = Field(description="ChEMBL ID of the assay")
    assay_type: str | None = Field(default=None, description="Assay type code")
    assay_type_description: str | None = Field(
        default=None, description="Assay type description"
    )
    description: str | None = Field(default=None, description="Assay description")
    assay_test_type: str | None = Field(default=None, description="Test type")
    assay_category: str | None = Field(default=None, description="Assay category")
    assay_cell_type: str | None = Field(default=None, description="Cell type used")
    assay_organism: str | None = Field(
        default=None, description="Organism in the assay"
    )
    assay_strain: str | None = Field(default=None, description="Strain used")
    assay_subcellular_fraction: str | None = Field(
        default=None, description="Subcellular fraction"
    )
    assay_tissue: str | None = Field(default=None, description="Tissue type")
    document_chembl_id: str | None = Field(
        default=None, description="Source document ChEMBL ID"
    )
    target_chembl_id: str | None = Field(default=None, description="Target ChEMBL ID")
    cell_chembl_id: str | None = Field(default=None, description="Cell line ChEMBL ID")
    tissue_chembl_id: str | None = Field(default=None, description="Tissue ChEMBL ID")
    bao_format: str | None = Field(default=None, description="BAO format ID")
    bao_label: str | None = Field(default=None, description="BAO label")
    confidence_score: int | None = Field(
        default=None, description="Target confidence score"
    )
    confidence_description: str | None = Field(
        default=None, description="Confidence description"
    )
    src_id: int | None = Field(default=None, description="Source ID")
    src_assay_id: str | None = Field(default=None, description="Source assay ID")
    variant_sequence: str | None = Field(default=None, description="Variant sequence")
    assay_parameters: (
        list[JsonDict] | None  # Any: untyped API JSON record
    ) = (  # Any: nested API JSON has heterogeneous values
        Field(  # Any: nested ChEMBL JSON with provider-specific schema
            default_factory=list, description="Assay parameters"
        )
    )


class ChemblAssayResponse(BaseModel):
    """Complete ChEMBL Assay API response."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    assays: list[ChemblAssayRecord] = Field(
        default_factory=list, description="List of assay records"
    )
    page_meta: ChemblPageMeta | None = Field(
        default=None, description=_PAGINATION_METADATA_DESCRIPTION
    )


class ChemblTargetRecord(BaseModel):
    """Individual target record from ChEMBL API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    target_chembl_id: str = Field(description="ChEMBL ID of the target")
    pref_name: str | None = Field(default=None, description="Preferred name")
    target_type: str | None = Field(default=None, description="Target type")
    organism: str | None = Field(default=None, description="Target organism")
    tax_id: int | None = Field(default=None, description="Taxonomy ID")
    species_group_flag: int | None = Field(default=None)
    target_components: list[JsonDict] | None = (  # Any: untyped API JSON record
        Field(  # Any: nested API JSON has heterogeneous values
            default_factory=list
        )
    )  # Any: nested ChEMBL JSON with provider-specific schema
    cross_references: list[JsonDict] | None = (  # Any: untyped API JSON record
        Field(  # Any: nested API JSON has heterogeneous values
            default_factory=list
        )
    )  # Any: nested ChEMBL JSON with provider-specific schema


class ChemblTargetResponse(BaseModel):
    """Complete ChEMBL Target API response."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    targets: list[ChemblTargetRecord] = Field(
        default_factory=list, description="List of target records"
    )
    page_meta: ChemblPageMeta | None = Field(
        default=None, description=_PAGINATION_METADATA_DESCRIPTION
    )


class ChemblReleaseInfo(BaseModel):
    """Nested chembl_release object from ChEMBL API."""

    model_config = ConfigDict(extra="ignore")

    chembl_release: str | None = Field(
        default=None, description="ChEMBL release version (e.g., CHEMBL_1)"
    )
    creation_date: str | None = Field(
        default=None, description="Record creation date in ChEMBL (YYYY-MM-DD)"
    )


class ChemblPublicationApiRecord(BaseModel):
    """Individual publication record from ChEMBL API (infrastructure model)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    document_chembl_id: str = Field(description="ChEMBL ID of the publication")
    doc_type: str | None = Field(default=None, description="Document type")
    title: str | None = Field(default=None, description="Document title")
    abstract: str | None = Field(default=None, description="Document abstract")
    authors: str | None = Field(default=None, description="Authors")
    journal: str | None = Field(default=None, description="Journal name")
    volume: str | None = Field(default=None)
    issue: str | None = Field(default=None)
    first_page: str | None = Field(default=None)
    last_page: str | None = Field(default=None)
    year: int | None = Field(default=None, description="Publication year")
    doi: str | None = Field(default=None, description="Digital Object Identifier")
    pubmed_id: str | None = Field(
        default=None, description="PubMed ID (numeric string)"
    )
    patent_id: str | None = Field(default=None, description="Patent ID")
    src_id: int | None = Field(default=None, description="Source ID")
    chembl_release: ChemblReleaseInfo | None = Field(
        default=None, description="ChEMBL release metadata"
    )

    @field_validator("pubmed_id", mode="before")
    @classmethod
    def _normalize_pubmed_id(cls, value: object) -> object:
        """Normalize live API PMID payloads that may arrive as integers."""
        if value is None:
            return None
        if isinstance(value, int):
            return str(value)
        return value


class ChemblPublicationResponse(BaseModel):
    """Complete ChEMBL Publication API response."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    documents: list[ChemblPublicationApiRecord] = Field(
        default_factory=list, description="List of publication records"
    )
    page_meta: ChemblPageMeta | None = Field(
        default=None, description=_PAGINATION_METADATA_DESCRIPTION
    )
