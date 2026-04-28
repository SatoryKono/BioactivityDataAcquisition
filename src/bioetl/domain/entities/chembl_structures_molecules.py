"""Molecule and similarity ChEMBL structure entities."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.entities.base import BaseEntity
from bioetl.domain.schemas.constants import MAX_PHASE_VALUES


@dataclass(frozen=True, kw_only=True)
class Molecule(BaseEntity):
    """Represents a chemical compound (ChEMBL Molecule)."""

    molecule_id: str
    pref_name: str | None = None
    molecule_type: str | None = None
    structure_type: str | None = None
    max_phase: int | float | None = None
    first_approval: int | None = None
    oral: bool | None = None
    parenteral: bool | None = None
    topical: bool | None = None
    black_box_warning: int | None = None
    natural_product: int | None = None
    first_in_class: int | None = None
    prodrug: int | None = None
    therapeutic_flag: bool | None = None
    withdrawn_flag: bool | None = None
    inorganic_flag: int | None = None
    polymer_flag: int | None = None
    chirality: int | None = None
    dosed_ingredient: int | None = None
    availability_type: int | None = None
    usan_stem: str | None = None
    usan_stem_definition: str | None = None
    usan_substem: str | None = None
    usan_year: int | None = None
    helm_notation: str | None = None
    molecule_species: str | None = None
    molecule_hierarchy: str | None = None
    molecule_properties: str | None = None
    molecule_structures: str | None = None
    molecule_synonyms: str | None = None
    cross_references: str | None = None
    atc_classifications: str | None = None
    hierarchy_parent_chembl_id: str | None = None
    hierarchy_active_chembl_id: str | None = None
    hierarchy_child_chembl_id: str | None = None
    logp: float | None = None
    logp_method: str | None = None
    mw_freebase: float | None = None
    molecular_weight: float | None = None
    hba_count: int | None = None
    hbd_count: int | None = None
    polar_surface_area: float | None = None
    rotatable_bond_count: int | None = None
    ro5_violation_count: int | None = None
    heavy_atom_count: int | None = None
    aromatic_ring_count: int | None = None
    qed_score: float | None = None
    molecular_formula: str | None = None
    ro3_pass: str | None = None
    canonical_smiles: str | None = None
    standard_inchi: str | None = None
    inchi_key: str | None = None

    def _validate_invariants(self) -> None:
        if not self.molecule_id:
            raise ValueError("Molecule ChEMBL ID is required")
        if self.max_phase is not None and self.max_phase not in MAX_PHASE_VALUES:
            raise ValueError(
                f"max_phase must be one of {MAX_PHASE_VALUES}, got {self.max_phase}"
            )


def _validate_tanimoto(value: float | None, field_name: str) -> None:
    """Validate Tanimoto coefficient is in [0.0, 1.0] range."""
    if value is not None and not 0.0 <= value <= 1.0:
        raise ValueError(f"{field_name} must be in [0.0, 1.0], got {value}")


@dataclass(frozen=True, kw_only=True)
class ChemblPublicationSimilarity(BaseEntity):
    """Represents similarity between two ChEMBL documents."""

    sim_id: int
    doc_1: int
    doc_2: int
    pubmed_id1: str | None = None
    pubmed_id2: str | None = None
    tid_tani: float | None = None
    mol_tani: float | None = None
    avg_tani: float | None = None
    max_tani: float | None = None

    def _validate_invariants(self) -> None:
        if self.sim_id <= 0:
            raise ValueError(f"sim_id must be positive, got {self.sim_id}")
        self._validate_similarity_documents()
        _validate_tanimoto(self.tid_tani, "tid_tani")
        _validate_tanimoto(self.mol_tani, "mol_tani")
        _validate_tanimoto(self.avg_tani, "avg_tani")
        _validate_tanimoto(self.max_tani, "max_tani")

    def _validate_similarity_documents(self) -> None:
        """Validate similarity endpoints for positivity and non-identity."""
        if self.doc_1 <= 0 or self.doc_2 <= 0:
            raise ValueError("doc_1 and doc_2 must be positive")
        if self.doc_1 == self.doc_2:
            raise ValueError("Document cannot be similar to itself")


@dataclass(frozen=True, kw_only=True)
class ProteinClassification(BaseEntity):
    """Represents a protein classification hierarchy node."""

    protein_class_id: int
    parent_id: int | None = None
    class_level: int | None = None
    pref_name: str | None = None
    short_name: str | None = None
    protein_class_desc: str | None = None
    definition: str | None = None
    sort_order: int | None = None
    replaced_by: int | None = None
    downgraded: int | None = None

    def _validate_invariants(self) -> None:
        if self.protein_class_id < 1:
            raise ValueError(
                f"protein_class_id must be >= 1, got {self.protein_class_id}"
            )
        self._validate_class_level()
        self._validate_downgraded()

    def _validate_class_level(self) -> None:
        if self.class_level is not None and not 1 <= self.class_level <= 8:
            raise ValueError(f"class_level must be 1-8, got {self.class_level}")

    def _validate_downgraded(self) -> None:
        if self.downgraded is not None and self.downgraded not in (0, 1):
            raise ValueError(f"downgraded must be 0 or 1, got {self.downgraded}")

    def is_root(self) -> bool:
        """Check whether this node is a root node."""
        return self.parent_id is None

    def is_deprecated(self) -> bool:
        """Check whether this classification is deprecated."""
        return self.replaced_by is not None or self.downgraded == 1


__all__ = [
    "ChemblPublicationSimilarity",
    "Molecule",
    "ProteinClassification",
]
