# mypy: disable-error-code="misc"
"""Annotation-related UniProt response models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "UniProtComment",
    "UniProtEcNumber",
    "UniProtEvidence",
    "UniProtFullName",
    "UniProtGene",
    "UniProtIsoform",
    "UniProtKeyword",
    "UniProtLocation",
    "UniProtName",
    "UniProtOrganism",
    "UniProtProteinDescription",
    "UniProtReaction",
    "UniProtRecommendedName",
    "UniProtSubcellularLocation",
    "UniProtText",
]

_SUPPORTING_EVIDENCE_DESCRIPTION = "Supporting evidence"


class UniProtEcNumber(BaseModel):
    """EC number entry."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    value: str = Field(description="EC number value (e.g., 2.7.11.1)")


class UniProtKeyword(BaseModel):
    """UniProt keyword entry."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str = Field(description="Keyword ID (e.g., KW-0067)")
    category: str | None = Field(default=None, description="Keyword category")
    name: str = Field(description="Keyword name")


class UniProtOrganism(BaseModel):
    """Organism information from UniProt."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    scientific_name: str = Field(alias="scientificName", description="Scientific name")
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
    ec_numbers: list[UniProtEcNumber] | None = Field(
        default_factory=list, alias="ecNumbers", description="EC numbers"
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
    flag: str | None = Field(
        default=None,
        description="Protein sequence completeness flag (Fragment/Precursor)",
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
        default_factory=list, description=_SUPPORTING_EVIDENCE_DESCRIPTION
    )


class UniProtLocation(BaseModel):
    """Location value with evidence."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    value: str = Field(description="Location name")
    evidences: list[UniProtEvidence] | None = Field(
        default_factory=list, description=_SUPPORTING_EVIDENCE_DESCRIPTION
    )


class UniProtSubcellularLocation(BaseModel):
    """Subcellular location entry."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    location: UniProtLocation | None = Field(default=None, description="Location")
    topology: UniProtLocation | None = Field(default=None, description="Topology")
    orientation: UniProtLocation | None = Field(default=None, description="Orientation")


class UniProtReaction(BaseModel):
    """Catalytic reaction entry."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    name: str | None = Field(default=None, description="Reaction name")
    ec_number: str | None = Field(
        default=None, alias="ecNumber", description="EC number"
    )
    evidences: list[UniProtEvidence] | None = Field(
        default_factory=list, description=_SUPPORTING_EVIDENCE_DESCRIPTION
    )


class UniProtIsoform(BaseModel):
    """Isoform entry for alternative products."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    isoform_ids: list[str] | None = Field(
        default_factory=list, alias="isoformIds", description="Isoform identifiers"
    )
    name: UniProtName | None = Field(default=None, description="Isoform name")
    sequence_status: str | None = Field(
        default=None, alias="sequenceStatus", description="Sequence status"
    )


class UniProtComment(BaseModel):
    """Protein comment/annotation."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    comment_type: str = Field(alias="commentType", description="Comment type")
    texts: list[UniProtText] | None = Field(
        default_factory=list, description="Comment text entries"
    )
    molecule: str | None = Field(default=None, description="Molecule name")
    reaction: UniProtReaction | None = Field(
        default=None, description="Catalytic reaction details"
    )
    subcellular_locations: list[UniProtSubcellularLocation] | None = Field(
        default_factory=list,
        alias="subcellularLocations",
        description="Subcellular location entries",
    )
    isoforms: list[UniProtIsoform] | None = Field(
        default_factory=list, description="Isoform entries"
    )
