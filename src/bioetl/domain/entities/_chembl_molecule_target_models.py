# mypy: disable-error-code="misc"
"""ChEMBL molecule/target DTO models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from bioetl.domain.immutability import freeze_fields


class MoleculeRecord(BaseModel):
    """Chemical compound DTO from ChEMBL.

    Represents a molecule/compound from ChEMBL API.
    Required field: molecule_id.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Primary identifier (REQUIRED)
    molecule_id: str = Field(description="Unique molecule ChEMBL ID")

    # Core metadata
    pref_name: str | None = Field(default=None, description="Preferred molecule name")
    molecule_type: str | None = Field(
        default=None, description="Type (Small molecule, Protein, Antibody, etc.)"
    )
    structure_type: str | None = Field(
        default=None, description="Structure type (MOL, NONE, SEQ, BOTH)"
    )
    max_phase: int | float | None = Field(
        default=None,
        description="Maximum clinical phase quasi-enum (-1, 0, 0.5, 1, 2, 3, 4)",
    )
    first_approval: int | None = Field(
        default=None, description="Year of first approval"
    )

    # Flags
    oral: bool | None = Field(default=None, description="Oral administration flag")
    parenteral: bool | None = Field(
        default=None, description="Parenteral administration flag"
    )
    topical: bool | None = Field(
        default=None, description="Topical administration flag"
    )
    black_box_warning: int | None = Field(
        default=None, description="Black box warning flag"
    )
    natural_product: int | None = Field(
        default=None, description="Natural product flag"
    )
    first_in_class: int | None = Field(default=None, description="First in class flag")
    prodrug: int | None = Field(default=None, description="Prodrug flag")
    therapeutic_flag: bool | None = Field(
        default=None, description="Therapeutic use flag"
    )
    withdrawn_flag: bool | None = Field(default=None, description="Withdrawn drug flag")
    inorganic_flag: int | None = Field(
        default=None, description="Inorganic compound flag"
    )
    polymer_flag: int | None = Field(default=None, description="Polymer flag")
    chirality: int | None = Field(
        default=None,
        description="Chirality (-1 single, 0 achiral, 1 racemic, 2 mixture)",
    )
    dosed_ingredient: int | None = Field(
        default=None, description="Dosed ingredient flag"
    )
    availability_type: int | None = Field(
        default=None, description="Availability type (-2 to 2)"
    )

    # USAN naming
    usan_stem: str | None = Field(default=None, description="USAN stem")
    usan_stem_definition: str | None = Field(
        default=None, description="USAN stem definition"
    )
    usan_substem: str | None = Field(default=None, description="USAN substem")
    usan_year: int | None = Field(default=None, description="USAN year")

    # Other metadata
    helm_notation: str | None = Field(
        default=None, description="HELM notation for biopolymers"
    )
    molecule_species: str | None = Field(
        default=None, description="Species (ACID, BASE, NEUTRAL, ZWITTERION)"
    )

    # Flattened hierarchy
    hierarchy_parent_chembl_id: str | None = Field(
        default=None, description="Parent molecule ChEMBL ID"
    )
    hierarchy_active_chembl_id: str | None = Field(
        default=None, description="Active form ChEMBL ID"
    )
    hierarchy_child_chembl_id: str | None = Field(
        default=None, description="Child molecule ChEMBL ID"
    )

    # Flattened properties (canonical alias names, unified for Gold)
    logp: float | None = Field(
        default=None, description="Partition coefficient (ALogP)"
    )
    logp_method: str | None = Field(default=None, description="Source method for logp")
    mw_freebase: float | None = Field(
        default=None, description="Molecular weight (freebase)"
    )
    molecular_weight: float | None = Field(
        default=None, description="Full molecular weight"
    )
    hba_count: int | None = Field(default=None, description="H-bond acceptor count")
    hbd_count: int | None = Field(default=None, description="H-bond donor count")
    polar_surface_area: float | None = Field(
        default=None, description="Polar surface area"
    )
    rotatable_bond_count: int | None = Field(
        default=None, description="Rotatable bond count"
    )
    ro5_violation_count: int | None = Field(
        default=None, description="Rule of 5 violations"
    )
    heavy_atom_count: int | None = Field(default=None, description="Heavy atom count")
    aromatic_ring_count: int | None = Field(
        default=None, description="Aromatic ring count"
    )
    qed_score: float | None = Field(default=None, description="QED weighted score")
    molecular_formula: str | None = Field(
        default=None, description="Full molecular formula"
    )
    ro3_pass: str | None = Field(default=None, description="Rule of 3 pass (Y/N)")

    # Flattened structures (unified naming without structure_ prefix)
    canonical_smiles: str | None = Field(
        default=None, description="Canonical SMILES representation"
    )
    standard_inchi: str | None = Field(
        default=None, description="Standard InChI representation"
    )
    inchi_key: str | None = Field(default=None, description="Standard InChI Key")

    # Complex fields (JSON serialized)
    molecule_hierarchy: str | None = Field(
        default=None, description="Molecule hierarchy as JSON"
    )
    molecule_properties: str | None = Field(
        default=None, description="Molecule properties as JSON"
    )
    molecule_structures: str | None = Field(
        default=None, description="Molecule structures as JSON"
    )
    molecule_synonyms: str | None = Field(
        default=None, description="Molecule synonyms as JSON"
    )
    cross_references: str | None = Field(
        default=None, description="Cross references as JSON"
    )
    atc_classifications: str | None = Field(
        default=None, description="ATC classifications as JSON"
    )


class TargetRecord(BaseModel):
    """Biological target DTO from ChEMBL.

    Represents a drug target from ChEMBL API.
    Required field: target_id.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Primary identifier (REQUIRED)
    target_id: str = Field(description="Unique target ChEMBL ID")

    # Core metadata
    pref_name: str | None = Field(default=None, description="Preferred target name")
    target_type: str | None = Field(
        default=None,
        description="Type (SINGLE PROTEIN, PROTEIN COMPLEX, ORGANISM, etc.)",
    )
    organism: str | None = Field(default=None, description="Target organism")
    tax_id: int | None = Field(default=None, description="NCBI Taxonomy ID")
    species_group_flag: bool | None = Field(
        default=None, description="Species group flag"
    )
    description: str | None = Field(default=None, description="Target description")
    downgraded: bool | None = Field(
        default=None, description="Deprecated/downgraded flag"
    )

    # Optional fields
    pipeline_stages: str | None = Field(
        default=None, description="Pipeline stages JSON"
    )

    # Flattened component fields
    component_accessions: list[str] | None = Field(
        default=None, description="Component UniProt accessions"
    )
    component_ids: list[int] | None = Field(default=None, description="Component IDs")
    component_types: list[str] | None = Field(
        default=None, description="Component types"
    )
    component_relationships: list[str] | None = Field(
        default=None, description="Component relationships"
    )
    component_descriptions: list[str] | None = Field(
        default=None, description="Component descriptions"
    )

    # Complex fields (JSON serialized)
    target_components: str | None = Field(
        default=None, description="Target components as JSON"
    )
    target_component_synonyms: str | None = Field(
        default=None, description="Component synonyms as JSON"
    )
    cross_references: str | None = Field(
        default=None, description="Cross references as JSON"
    )

    def model_post_init(self, _context: object, /) -> None:
        """Detach and freeze nested component collections after validation."""
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


__all__ = [
    "MoleculeRecord",
    "TargetRecord",
]
