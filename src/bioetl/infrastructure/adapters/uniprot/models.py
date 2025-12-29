"""Pydantic models for UniProt API responses.

These models provide type-safe parsing and validation for UniProt REST API responses.
They are infrastructure-layer models (not domain models) for raw API data.

Documentation: https://www.uniprot.org/help/api

See RULES.md §8.2 for JSON response modeling guidelines.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# === Shared Models ===


class UniProtOrganism(BaseModel):
    """Organism information from UniProt."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    scientific_name: str = Field(
        alias="scientificName", description="Scientific name"
    )
    common_name: str | None = Field(
        default=None, alias="commonName", description="Common name"
    )
    taxon_id: int = Field(alias="taxonId", description="NCBI Taxonomy ID")
    lineage: list[str] | None = Field(
        default_factory=list, description="Taxonomic lineage"
    )


class UniProtName(BaseModel):
    """Name value container."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    value: str = Field(description="Name value")


class UniProtFullName(BaseModel):
    """Full name with optional short names."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    full_name: UniProtName | None = Field(
        default=None, alias="fullName", description="Full name"
    )
    short_names: list[UniProtName] | None = Field(
        default_factory=list, alias="shortNames", description="Short names"
    )


class UniProtRecommendedName(BaseModel):
    """Recommended protein name."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    full_name: UniProtName | None = Field(
        default=None, alias="fullName", description="Full recommended name"
    )
    short_names: list[UniProtName] | None = Field(
        default_factory=list, alias="shortNames", description="Short names"
    )


class UniProtProteinDescription(BaseModel):
    """Protein description with recommended and alternative names."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    recommended_name: UniProtRecommendedName | None = Field(
        default=None, alias="recommendedName", description="Recommended name"
    )
    alternative_names: list[UniProtFullName] | None = Field(
        default_factory=list, alias="alternativeNames", description="Alternative names"
    )
    submitted_name: list[UniProtFullName] | None = Field(
        default_factory=list, alias="submittedName", description="Submitted names"
    )


class UniProtGene(BaseModel):
    """Gene information."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    gene_name: UniProtName | None = Field(
        default=None, alias="geneName", description="Primary gene name"
    )
    synonyms: list[UniProtName] | None = Field(
        default_factory=list, description="Gene name synonyms"
    )
    ordered_locus_names: list[UniProtName] | None = Field(
        default_factory=list, alias="orderedLocusNames", description="Locus names"
    )
    orf_names: list[UniProtName] | None = Field(
        default_factory=list, alias="orfNames", description="ORF names"
    )


class UniProtEvidence(BaseModel):
    """Evidence for a feature or annotation."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    evidence_code: str = Field(alias="evidenceCode", description="ECO evidence code")
    source: str | None = Field(default=None, description="Evidence source")
    id: str | None = Field(default=None, description="Source ID")


class UniProtText(BaseModel):
    """Text with evidence."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    value: str = Field(description="Text value")
    evidences: list[UniProtEvidence] | None = Field(
        default_factory=list, description="Supporting evidence"
    )


class UniProtComment(BaseModel):
    """Protein comment/annotation."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    comment_type: str = Field(alias="commentType", description="Comment type")
    texts: list[UniProtText] | None = Field(
        default_factory=list, description="Comment text entries"
    )
    molecule: str | None = Field(default=None, description="Molecule name")


class UniProtFeatureLocation(BaseModel):
    """Location of a feature."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    start: dict[str, Any] | None = Field(default=None, description="Start position")
    end: dict[str, Any] | None = Field(default=None, description="End position")


class UniProtFeature(BaseModel):
    """Protein feature (domain, site, etc.)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    type: str = Field(description="Feature type")
    location: UniProtFeatureLocation | None = Field(
        default=None, description="Feature location"
    )
    description: str | None = Field(default=None, description="Feature description")
    evidences: list[UniProtEvidence] | None = Field(
        default_factory=list, description="Supporting evidence"
    )
    feature_id: str | None = Field(
        default=None, alias="featureId", description="Feature ID"
    )


class UniProtCrossReference(BaseModel):
    """Cross-reference to external database."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    database: str = Field(description="Database name")
    id: str = Field(description="External ID")
    properties: list[dict[str, str]] | None = Field(
        default_factory=list, description="Additional properties"
    )


class UniProtSequence(BaseModel):
    """Protein sequence information."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    value: str = Field(description="Amino acid sequence")
    length: int = Field(description="Sequence length")
    mol_weight: int = Field(alias="molWeight", description="Molecular weight in Da")
    crc64: str | None = Field(default=None, description="CRC64 checksum")
    md5: str | None = Field(default=None, description="MD5 checksum")


class UniProtExtraAttributes(BaseModel):
    """Extra attributes for the entry."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    uni_parc_id: str | None = Field(
        default=None, alias="uniParcId", description="UniParc ID"
    )


# === Main Protein Record ===


class UniProtProteinRecord(BaseModel):
    """Individual protein record from UniProt API.

    Represents a single UniProtKB entry from the /uniprotkb/search endpoint.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # Entry Type
    entry_type: str = Field(
        alias="entryType",
        description="Entry type (UniProtKB reviewed/unreviewed)"
    )

    # Primary Identifiers
    primary_accession: str = Field(
        alias="primaryAccession", description="Primary accession number"
    )
    uniprot_kb_id: str | None = Field(
        default=None, alias="uniProtkbId", description="UniProtKB ID (entry name)"
    )

    # Organism
    organism: UniProtOrganism | None = Field(
        default=None, description="Source organism"
    )

    # Protein Names
    protein_description: UniProtProteinDescription | None = Field(
        default=None, alias="proteinDescription", description="Protein names"
    )

    # Genes
    genes: list[UniProtGene] | None = Field(
        default_factory=list, description="Gene information"
    )

    # Annotations
    comments: list[UniProtComment] | None = Field(
        default_factory=list, description="Protein annotations/comments"
    )

    # Features
    features: list[UniProtFeature] | None = Field(
        default_factory=list, description="Sequence features"
    )

    # Cross-References
    uniprot_kb_cross_references: list[UniProtCrossReference] | None = Field(
        default_factory=list,
        alias="uniProtKBCrossReferences",
        description="External database cross-references"
    )

    # Sequence
    sequence: UniProtSequence | None = Field(
        default=None, description="Protein sequence"
    )

    # Extra Attributes
    extra_attributes: UniProtExtraAttributes | None = Field(
        default=None, alias="extraAttributes", description="Extra attributes"
    )

    # Secondary Accessions
    secondary_accessions: list[str] | None = Field(
        default_factory=list, alias="secondaryAccessions", description="Secondary accessions"
    )


class UniProtSearchResponse(BaseModel):
    """Complete UniProt search API response."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    results: list[UniProtProteinRecord] = Field(
        default_factory=list, description="List of protein records"
    )
    # Note: pagination is handled via cursor in Link header, not in JSON body


# === Feature Record (simplified for feature endpoint) ===


class UniProtFeatureRecord(BaseModel):
    """Simplified feature record from UniProt."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    accession: str = Field(description="Protein accession")
    type: str | None = Field(default=None, description="Feature type")
    location: dict[str, Any] | None = Field(
        default=None, description="Feature location"
    )
    description: str | None = Field(default=None, description="Feature description")


# === Sequence Record (from FASTA parsing) ===


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


# === Record Type Mapping ===

UNIPROT_RECORD_MODELS: dict[str, type[BaseModel]] = {
    "protein": UniProtProteinRecord,
    "feature": UniProtFeatureRecord,
    "sequence": UniProtSequenceRecord,
}
