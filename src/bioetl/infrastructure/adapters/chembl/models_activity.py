# mypy: disable-error-code="misc"
"""ChEMBL activity endpoint models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.adapters.chembl.models_common import ChemblPageMeta

__all__ = [
    "ActionType",
    "ChemblActivityRecord",
    "ChemblActivityResponse",
    "LigandEfficiency",
]


class LigandEfficiency(BaseModel):
    """Ligand efficiency metrics for an activity record."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    bei: str | None = Field(default=None, description="Binding Efficiency Index")
    le: str | None = Field(default=None, description="Ligand Efficiency")
    lle: str | None = Field(default=None, description="Lipophilic Ligand Efficiency")
    sei: str | None = Field(default=None, description="Surface Efficiency Index")


class ActionType(BaseModel):
    """Action type details for an activity record."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    action_type: str | None = Field(default=None, description="Action type name")
    description: str | None = Field(default=None, description="Action description")
    parent_type: str | None = Field(default=None, description="Parent action type")


class ChemblActivityRecord(BaseModel):
    """Individual activity record from ChEMBL API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    activity_id: int = Field(description="Primary activity identifier")
    assay_chembl_id: str = Field(description="ChEMBL ID of the assay")
    molecule_chembl_id: str = Field(description="ChEMBL ID of the molecule")
    target_chembl_id: str | None = Field(
        default=None, description="ChEMBL ID of the target"
    )
    document_chembl_id: str | None = Field(
        default=None, description="ChEMBL ID of the source document"
    )
    standard_relation: str | None = Field(
        default=None, description="Standardized relation operator (=, <, >, etc.)"
    )
    standard_value: str | float | None = Field(
        default=None, description="Standardized activity value"
    )
    standard_units: str | None = Field(
        default=None, description="Standardized units (nM, uM, etc.)"
    )
    standard_type: str | None = Field(
        default=None, description="Standardized measurement type (IC50, EC50, etc.)"
    )
    standard_flag: int | None = Field(
        default=None, description="Standardization flag (0 or 1)"
    )
    standard_text_value: str | None = Field(
        default=None, description="Standardized text value"
    )
    standard_upper_value: float | None = Field(
        default=None, description="Standardized upper bound"
    )
    pchembl_value: str | float | None = Field(
        default=None, description="-log10 of molar activity"
    )
    ligand_efficiency: LigandEfficiency | None = Field(
        default=None, description="Ligand efficiency metrics"
    )
    action_type: ActionType | str | None = Field(
        default=None, description="Action type details"
    )
    type: str | None = Field(default=None, description="Original measurement type")
    relation: str | None = Field(default=None, description="Original relation operator")
    value: str | float | None = Field(default=None, description="Original value")
    units: str | None = Field(default=None, description="Original units")
    text_value: str | None = Field(default=None, description="Text value")
    upper_value: float | None = Field(default=None, description="Upper bound value")
    data_validity_comment: str | None = Field(
        default=None, description="Data quality comment"
    )
    data_validity_description: str | None = Field(
        default=None, description="Data validity description"
    )
    activity_comment: str | None = Field(
        default=None, description="Activity textual comment"
    )
    potential_duplicate: int | None = Field(
        default=None, description="Duplicate flag (0 or 1)"
    )
    bao_endpoint: str | None = Field(default=None, description="BAO endpoint ID")
    bao_format: str | None = Field(default=None, description="BAO format ID")
    bao_label: str | None = Field(default=None, description="BAO label")
    uo_units: str | None = Field(default=None, description="Units Ontology ID")
    qudt_units: str | None = Field(default=None, description="QUDT unit URI")
    src_id: int | None = Field(default=None, description="Source ID")
    record_id: int | None = Field(
        default=None, description="Foreign key to compound_record"
    )
    toid: int | None = Field(default=None, description="Test Occasion ID")
    assay_description: str | None = Field(default=None, description="Assay description")
    assay_type: str | None = Field(default=None, description="Assay type code")
    assay_variant_accession: str | None = Field(
        default=None, description="Assay variant accession"
    )
    assay_variant_mutation: str | None = Field(
        default=None, description="Assay variant mutation"
    )
    canonical_smiles: str | None = Field(
        default=None, description="Canonical SMILES structure"
    )
    molecule_pref_name: str | None = Field(
        default=None, description="Molecule preferred name"
    )
    parent_molecule_chembl_id: str | None = Field(
        default=None, description="Parent molecule ChEMBL ID"
    )
    target_pref_name: str | None = Field(
        default=None, description="Target preferred name"
    )
    target_organism: str | None = Field(
        default=None, description="Target organism name"
    )
    target_tax_id: str | None = Field(default=None, description="Target taxonomy ID")
    document_journal: str | None = Field(
        default=None, description="Source journal name"
    )
    document_year: int | None = Field(default=None, description="Publication year")
    activity_properties: (
        list[JsonDict] | None  # Any: untyped API JSON record
    ) = (  # Any: nested API JSON has heterogeneous values
        Field(  # Any: nested ChEMBL JSON with provider-specific schema
            default_factory=list, description="Additional activity properties"
        )
    )


class ChemblActivityResponse(BaseModel):
    """Complete ChEMBL Activity API response."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    activities: list[ChemblActivityRecord] = Field(
        default_factory=list, description="List of activity records"
    )
    page_meta: ChemblPageMeta | None = Field(
        default=None, description="Pagination metadata"
    )
