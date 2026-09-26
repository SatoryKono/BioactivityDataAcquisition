# mypy: disable-error-code="misc"
"""Reference ChEMBL entity DTO models (publication/cell/component/protein class)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from bioetl.domain.immutability import freeze_fields


class ChemblPublicationRecord(BaseModel):
    """Scientific publication DTO from ChEMBL.

    Represents a publication from ChEMBL API (/document endpoint).
    Required field: publication_id.

    Note: Previously named DocumentRecord. The ChEMBL API uses 'document'
    as the endpoint name, but we use 'Publication' for Ubiquitous Language
    alignment per ADR-024.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Primary identifier (REQUIRED)
    publication_id: str = Field(description="Unique document ChEMBL ID")

    # Publication identifiers
    pubmed_id: str | None = Field(
        default=None, description="PubMed ID (numeric string)"
    )
    doi: str | None = Field(default=None, description="Digital Object Identifier")
    patent_id: str | None = Field(default=None, description="Patent ID")

    # Core metadata
    title: str | None = Field(default=None, description="Document title")
    authors: str | None = Field(default=None, description="Combined authors string")
    abstract: str | None = Field(default=None, description="Document abstract")
    doc_type: str | None = Field(
        default=None, description="Type (PUBLICATION, PATENT, etc.)"
    )

    # Journal information
    journal: str | None = Field(default=None, description="Journal name")
    year: int | None = Field(default=None, description="Publication year")
    volume: str | None = Field(default=None, description="Volume number")
    issue: str | None = Field(default=None, description="Issue number")
    first_page: str | None = Field(default=None, description="First page")
    last_page: str | None = Field(default=None, description="Last page")

    # Source information
    src_id: int | None = Field(default=None, description="Data source ID")

    # ChEMBL release metadata
    chembl_release: str | None = Field(
        default=None, description="ChEMBL release version (e.g., CHEMBL_1)"
    )
    creation_date: str | None = Field(
        default=None, description="Record creation date in ChEMBL (YYYY-MM-DD)"
    )


class ChemblPublicationTermRecord(BaseModel):
    """Publication term DTO from ChEMBL.

    Represents a term (MeSH heading, qualifier, or keyword) associated with
    a ChEMBL publication. This is a derived entity extracted from Publication
    records by flattening the 1:M relationship.

    Required fields: publication_id, term, term_type.

    Note: Previously named DocumentTermRecord per ADR-024.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # === Composite Key Fields (REQUIRED) ===
    publication_id: str = Field(description="FK → Document ChEMBL ID")
    term: str = Field(min_length=1, description="Term text (e.g., 'Aspirin')")
    term_type: str = Field(
        description="Term type: MESH_HEADING, MESH_QUALIFIER, KEYWORD"
    )

    # === MeSH-specific Fields ===
    mesh_id: str | None = Field(
        default=None, description="MeSH identifier (e.g., 'D001241')"
    )
    qualifier: str | None = Field(
        default=None, description="MeSH qualifier (e.g., 'pharmacology')"
    )


class CellLineRecord(BaseModel):
    """Cell line DTO from ChEMBL.

    Represents a cell line from ChEMBL API.
    Required fields: cell_id, cell_name.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Primary identifier (REQUIRED)
    cell_id: str = Field(description="Unique cell line ChEMBL ID")

    # Core metadata (REQUIRED)
    cell_name: str = Field(description="Cell line name")

    # Optional metadata
    cell_description: str | None = Field(
        default=None, description="Cell line description"
    )

    # Source information
    cell_source_tissue: str | None = Field(default=None, description="Source tissue")
    cell_source_organism: str | None = Field(
        default=None, description="Source organism"
    )
    cell_source_tax_id: int | None = Field(
        default=None,
        description=(
            "Source organism taxonomy ID (mirrors ChEMBL cell_source_tax_id; "
            "NCBI Taxonomy identifier)"
        ),
    )

    # External identifiers
    cellosaurus_id: str | None = Field(default=None, description="Cellosaurus ID")
    cl_lincs_id: str | None = Field(default=None, description="LINCS cell line ID")
    efo_id: str | None = Field(default=None, description="EFO ontology ID")


class TargetComponentRecord(BaseModel):
    """Target component DTO from ChEMBL.

    Represents a target component from ChEMBL API.
    Required field: component_id.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Primary identifier (REQUIRED)
    component_id: int = Field(description="Unique component ID")

    # Core metadata
    accession: str | None = Field(default=None, description="UniProt accession")
    component_type: str | None = Field(default=None, description="Component type")
    description: str | None = Field(default=None, description="Component description")
    organism: str | None = Field(default=None, description="Organism name")
    tax_id: int | None = Field(
        default=None,
        description=(
            "NCBI Taxonomy ID (mirrors ChEMBL tax_id field on target_component)"
        ),
    )

    # Flattened fields
    protein_classification_ids: list[int] | None = Field(
        default=None, description="Protein classification IDs"
    )

    # Complex fields (JSON serialized)
    target_component_synonyms: str | None = Field(
        default=None, description="Synonyms as JSON"
    )
    target_component_xrefs: str | None = Field(
        default=None, description="Cross references as JSON"
    )
    protein_classifications: str | None = Field(
        default=None, description="Protein classifications as JSON"
    )

    def model_post_init(self, _context: object, /) -> None:
        """Detach and freeze nested classification identifiers."""
        freeze_fields(self, ("protein_classification_ids",))


class ProteinClassRecord(BaseModel):
    """Protein classification DTO from ChEMBL.

    Represents a protein classification hierarchy node from ChEMBL API.
    Required field: protein_class_id.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Primary identifier (REQUIRED)
    protein_class_id: int = Field(description="Unique protein class ID")

    # Hierarchy
    parent_id: int | None = Field(default=None, description="Parent class ID")
    class_level: int | None = Field(default=None, description="Hierarchy level (1-8)")

    # Classification data
    pref_name: str | None = Field(default=None, description="Preferred name")
    short_name: str | None = Field(default=None, description="Short name")
    protein_class_desc: str | None = Field(default=None, description="Full description")
    definition: str | None = Field(
        default=None, description="Classification definition"
    )

    # Additional metadata
    sort_order: int | None = Field(default=None, description="Sort order")
    replaced_by: int | None = Field(
        default=None, description="ID of replacement class if deprecated"
    )
    downgraded: int | None = Field(
        default=None, description="Deprecation flag (0 or 1)"
    )


__all__ = [
    "CellLineRecord",
    "ChemblPublicationRecord",
    "ChemblPublicationTermRecord",
    "ProteinClassRecord",
    "TargetComponentRecord",
]
