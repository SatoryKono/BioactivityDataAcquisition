"""Core ChEMBL structure entities."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.entities.base import BaseEntity
from bioetl.domain.entities.publication_base import PublicationEntityBase
from bioetl.domain.immutability import freeze_fields

_VALID_TARGET_PROTEIN_CLASSIFICATION_STATUSES = frozenset(
    {"resolved", "missing_classification", "quarantined"}
)


@dataclass(frozen=True, kw_only=True)
class ChemblPublication(PublicationEntityBase):
    """Represents a scientific document/publication (ChEMBL Document)."""

    publication_id: str
    volume: str | None = None
    issue: str | None = None
    src_id: int | None = None
    chembl_release: str | None = None
    creation_date: str | None = None

    def _validate_invariants(self) -> None:
        super()._validate_invariants()
        if not self.publication_id:
            raise ValueError("ChemblPublication publication_id is required")


@dataclass(frozen=True, kw_only=True)
class ChemblPublicationTerm(BaseEntity):
    """Represents a term associated with a ChEMBL document."""

    publication_id: str
    term: str
    term_type: str
    mesh_id: str | None = None
    qualifier: str | None = None

    def _validate_invariants(self) -> None:
        if not self.publication_id:
            raise ValueError("Document ChEMBL ID is required")
        if not self.term:
            raise ValueError("Term text is required")
        if not self.term_type:
            raise ValueError("Term type is required")
        self._validate_term_type()

    def _validate_term_type(self) -> None:
        """Validate controlled vocabulary membership for term_type."""
        valid_term_types = {"MESH_HEADING", "MESH_QUALIFIER", "KEYWORD"}
        if self.term_type not in valid_term_types:
            raise ValueError(
                f"term_type must be one of {valid_term_types}, got {self.term_type}"
            )


@dataclass(frozen=True, kw_only=True)
class Target(BaseEntity):
    """Represents a biological target (ChEMBL Target)."""

    target_id: str
    pref_name: str | None = None
    target_type: str | None = None
    organism: str | None = None
    taxonomy_id: int | None = None
    organism_class: str | None = None
    species_group_flag: bool | None = None
    target_description: str | None = None
    target_components: str | None = None
    target_component_synonyms: str | None = None
    target_protein_synonyms: str | None = None
    target_gene_synonyms: str | None = None
    target_ec_numbers: str | None = None
    target_xref_pdb_ids: str | None = None
    target_xref_go_component: str | None = None
    target_xref_go_function: str | None = None
    target_xref_go_process: str | None = None
    target_xref_hgnc_ids: str | None = None
    target_xref_reactome_ids: str | None = None
    target_xref_uniprot_ids: str | None = None
    cross_references: str | None = None
    component_accessions: list[str] | None = None
    primary_component_id: int | None = None
    component_ids: list[int] | None = None
    component_types: list[str] | None = None
    component_relationships: list[str] | None = None
    component_descriptions: list[str] | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        freeze_fields(
            self,
            (
                "component_accessions",
                "component_ids",
                "component_types",
                "component_relationships",
                "component_descriptions",
            ),
        )

    def _validate_invariants(self) -> None:
        if not self.target_id:
            raise ValueError("Target ChEMBL ID is required")


@dataclass(frozen=True, kw_only=True)
class TargetComponent(BaseEntity):
    """Represents a target component (ChEMBL Target Component)."""

    component_id: int
    accession: str | None = None
    component_type: str | None = None
    description: str | None = None
    organism: str | None = None
    taxonomy_id: int | None = None
    target_component_synonyms: str | None = None
    target_component_xrefs: str | None = None
    protein_classifications: str | None = None
    protein_classification_id: int | None = None
    protein_classification_ids: list[int] | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        freeze_fields(self, ("protein_classification_ids",))

    def _validate_invariants(self) -> None:
        if not self.component_id:
            raise ValueError("Component ID is required")


@dataclass(frozen=True, kw_only=True)
class TargetProteinClassification(BaseEntity):
    """Represents a derived target-to-protein-classification relation row."""

    target_id: str
    classification_status: str = "resolved"
    component_id: int | None = None
    leaf_id: int | None = None
    path_ids: str | None = None
    path_names: str | None = None
    path_labels: str | None = None
    depth: int | None = None
    root_id: int | None = None
    is_leaf: bool | None = None
    l1_id: int | None = None
    l1_name: str | None = None
    l1_desc: str | None = None
    l2_id: int | None = None
    l2_name: str | None = None
    l2_desc: str | None = None
    l3_id: int | None = None
    l3_name: str | None = None
    l3_desc: str | None = None
    l4_id: int | None = None
    l4_name: str | None = None
    l4_desc: str | None = None
    l5_id: int | None = None
    l5_name: str | None = None
    l5_desc: str | None = None
    canonical_l1: str | None = None
    l1_counts_for_target_type: bool | None = None
    l1_mapping_version: str | None = None
    target_type_rule_version: str | None = None
    l1_normalization_status: str | None = None
    l1_normalization_notes: str | None = None
    dataset_version: str | None = None
    source_url: str | None = None
    chembl_release: str | None = None
    chembl_api_version: str | None = None
    source_manifest_status: str | None = None
    source_snapshot_fingerprint: str | None = None
    target_snapshot_row_count: int | None = None
    target_component_snapshot_row_count: int | None = None
    protein_class_snapshot_row_count: int | None = None

    def _validate_invariants(self) -> None:
        if not self.target_id:
            raise ValueError("Target ChEMBL ID is required")
        _validate_target_protein_classification_status(self.classification_status)
        _validate_target_protein_classification_resolution(
            classification_status=self.classification_status,
            component_id=self.component_id,
            leaf_id=self.leaf_id,
        )


@dataclass(frozen=True, kw_only=True)
class CellLine(BaseEntity):
    """Represents a cell line (ChEMBL Cell Line)."""

    cell_id: str
    cell_name: str
    cell_description: str | None = None
    cell_source_tissue: str | None = None
    cell_source_organism: str | None = None
    cell_source_taxonomy_id: int | None = None
    cell_type: str | None = None
    cellosaurus_id: str | None = None
    clo_id: str | None = None
    clo_iri: str | None = None
    clo_mapping_status: str | None = None
    clo_ontology_version: str | None = None
    cl_lincs_id: str | None = None
    efo_id: str | None = None
    efo_iri: str | None = None
    efo_mapping_status: str | None = None
    efo_ontology_version: str | None = None

    def _validate_invariants(self) -> None:
        if not self.cell_id:
            raise ValueError("Cell ChEMBL ID is required")
        if not self.cell_name:
            raise ValueError("Cell name is required")
        self._validate_taxonomy_id()

    def _validate_taxonomy_id(self) -> None:
        """Validate taxonomy id semantics when source organism is present."""
        if (
            self.cell_source_taxonomy_id is not None
            and self.cell_source_taxonomy_id < 1
        ):
            raise ValueError(
                f"cell_source_taxonomy_id must be >= 1, got {self.cell_source_taxonomy_id}"
            )


__all__ = [
    "CellLine",
    "ChemblPublication",
    "ChemblPublicationTerm",
    "Target",
    "TargetComponent",
]


def _validate_target_protein_classification_status(classification_status: str) -> None:
    if classification_status not in _VALID_TARGET_PROTEIN_CLASSIFICATION_STATUSES:
        raise ValueError("Invalid protein classification status")


def _validate_target_protein_classification_resolution(
    *,
    classification_status: str,
    component_id: int | None,
    leaf_id: int | None,
) -> None:
    if classification_status != "resolved":
        return
    if component_id is not None and leaf_id is not None:
        return
    raise ValueError(
        "Resolved target protein classification rows require component_id and leaf_id"
    )
