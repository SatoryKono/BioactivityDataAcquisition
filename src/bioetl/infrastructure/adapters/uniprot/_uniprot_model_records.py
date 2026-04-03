# mypy: disable-error-code="misc"
"""Top-level UniProt record models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.adapters.uniprot._uniprot_model_annotations import (
    UniProtComment,
    UniProtGene,
    UniProtKeyword,
    UniProtOrganism,
    UniProtProteinDescription,
)
from bioetl.infrastructure.adapters.uniprot._uniprot_model_structures import (
    UniProtCrossReference,
    UniProtExtraAttributes,
    UniProtFeature,
    UniProtSequence,
)

__all__ = [
    "UNIPROT_RECORD_MODELS",
    "UniProtFeatureRecord",
    "UniProtProteinRecord",
    "UniProtSearchResponse",
    "UniProtSequenceRecord",
]


class UniProtProteinRecord(BaseModel):
    """Individual protein record from UniProt API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    entry_type: str = Field(
        alias="entryType", description="Entry type (UniProtKB reviewed/unreviewed)"
    )
    primary_accession: str = Field(
        alias="primaryAccession", description="Primary accession number"
    )
    uniprot_kb_id: str | None = Field(
        default=None, alias="uniProtkbId", description="UniProtKB ID (entry name)"
    )
    secondary_accessions: list[str] | None = Field(
        default_factory=list,
        alias="secondaryAccessions",
        description="Secondary accessions",
    )
    annotation_score: int | None = Field(
        default=None, alias="annotationScore", description="Annotation quality (1-5)"
    )
    protein_existence: str | None = Field(
        default=None, alias="proteinExistence", description="Protein existence evidence"
    )
    organism: UniProtOrganism | None = Field(
        default=None, description="Source organism"
    )
    protein_description: UniProtProteinDescription | None = Field(
        default=None, alias="proteinDescription", description="Protein names"
    )
    genes: list[UniProtGene] | None = Field(
        default_factory=list, description="Gene information"
    )
    comments: list[UniProtComment] | None = Field(
        default_factory=list, description="Protein annotations/comments"
    )
    features: list[UniProtFeature] | None = Field(
        default_factory=list, description="Sequence features"
    )
    keywords: list[UniProtKeyword] | None = Field(
        default_factory=list, description="UniProt keywords"
    )
    uniprot_kb_cross_references: list[UniProtCrossReference] | None = Field(
        default_factory=list,
        alias="uniProtKBCrossReferences",
        description="External database cross-references",
    )
    sequence: UniProtSequence | None = Field(
        default=None, description="Protein sequence"
    )
    extra_attributes: UniProtExtraAttributes | None = Field(
        default=None, alias="extraAttributes", description="Extra attributes"
    )


class UniProtSearchResponse(BaseModel):
    """Complete UniProt search API response."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    results: list[UniProtProteinRecord] = Field(
        default_factory=list, description="List of protein records"
    )


class UniProtFeatureRecord(BaseModel):
    """Simplified feature record from UniProt."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    accession: str = Field(description="Protein accession")
    type: str | None = Field(default=None, description="Feature type")
    location: JsonDict | None = Field(  # Any: nested API JSON has heterogeneous values
        default=None, description="Feature location"
    )
    description: str | None = Field(default=None, description="Feature description")


class UniProtSequenceRecord(BaseModel):
    """Sequence record from FASTA parsing."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    accession: str = Field(description="Primary accession")
    entry_name: str | None = Field(default=None, description="Entry name")
    organism_name: str | None = Field(default=None, description="Organism name")
    gene_name: str | None = Field(default=None, description="Gene name")
    protein_name: str | None = Field(default=None, description="Protein name")
    sequence: str = Field(description="Amino acid sequence")
    length: int | None = Field(default=None, description="Sequence length")


UNIPROT_RECORD_MODELS: dict[str, type[BaseModel]] = {
    "protein": UniProtProteinRecord,
    "feature": UniProtFeatureRecord,
    "sequence": UniProtSequenceRecord,
}
