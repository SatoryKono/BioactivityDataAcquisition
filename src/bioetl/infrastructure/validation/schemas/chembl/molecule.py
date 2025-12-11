"""Pandera schema for normalized ChEMBL molecule table.

This schema validates the structure and content of molecule data
after normalization.
"""

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.field_specs import CHEMBL_ID_PATTERN
from bioetl.infrastructure.validation.schemas.pandera_base import (
    BaseGeneratedColumnsSchema,
    build_output_column_order,
)

__all__ = ["MoleculeTableSchema", "OUTPUT_COLUMN_ORDER"]

_MOLECULE_BUSINESS_COLUMNS: list[str] = [
    "atc_classifications",
    "availability_type",
    "black_box_warning",
    "chemical_probe",
    "chirality",
    "cross_references",
    "dosed_ingredient",
    "first_approval",
    "first_in_class",
    "helm_notation",
    "inorganic_flag",
    "max_phase",
    "molecule_chembl_id",
    "molecule_hierarchy",
    "molecule_properties",
    "molecule_structures",
    "molecule_synonyms",
    "molecule_type",
    "natural_product",
    "oral",
    "orphan",
    "parenteral",
    "polymer_flag",
    "pref_name",
    "prodrug",
    "structure_type",
    "therapeutic_flag",
    "topical",
    "usan_stem",
    "usan_stem_definition",
    "usan_substem",
    "usan_year",
    "veterinary",
    "withdrawn_flag",
]

OUTPUT_COLUMN_ORDER: list[str] = build_output_column_order(_MOLECULE_BUSINESS_COLUMNS)


class MoleculeTableSchema(BaseGeneratedColumnsSchema):
    """Pandera schema describing normalized molecule data.

    Validates ChEMBL molecule records including:
    - Chemical identifiers and structures
    - Drug development phases
    - Administration routes
    - Regulatory flags
    """

    atc_classifications: Series[str] = pa.Field(
        nullable=True, description="ATC codes and descriptions"
    )
    availability_type: Series[float] = pa.Field(
        nullable=True, description="Availability type (0/1/2)"
    )
    black_box_warning: Series[float] = pa.Field(
        nullable=True, description="Black box warning flag"
    )
    chemical_probe: Series[float] = pa.Field(
        nullable=True, description="Chemical probe flag"
    )
    chirality: Series[float] = pa.Field(nullable=True, description="Chirality code")
    cross_references: Series[str] = pa.Field(
        nullable=True, description="External cross-references"
    )
    dosed_ingredient: Series[bool] = pa.Field(
        nullable=True, description="Used as dosed ingredient"
    )
    first_approval: Series[float] = pa.Field(
        nullable=True, description="Year of first approval"
    )
    first_in_class: Series[float] = pa.Field(
        nullable=True, description="First in class flag"
    )
    helm_notation: Series[str] = pa.Field(nullable=True, description="HELM notation")
    inorganic_flag: Series[float] = pa.Field(
        nullable=True, description="Inorganic compound flag"
    )
    max_phase: Series[float] = pa.Field(
        nullable=True,
        ge=0,
        le=4,
        description="Maximum clinical trial phase",
    )
    molecule_chembl_id: Series[str] = pa.Field(
        str_matches=CHEMBL_ID_PATTERN, description="ChEMBL molecule identifier"
    )
    molecule_hierarchy: Series[str] = pa.Field(
        nullable=True, description="Molecule hierarchy (JSON)"
    )
    molecule_properties: Series[str] = pa.Field(
        nullable=True, description="Physicochemical properties (JSON)"
    )
    molecule_structures: Series[str] = pa.Field(
        nullable=True, description="Structural representations (JSON)"
    )
    molecule_synonyms: Series[str] = pa.Field(
        nullable=True, description="Molecule synonyms (JSON)"
    )
    molecule_type: Series[str] = pa.Field(
        nullable=True, description="Molecule type (Small molecule, Protein, etc.)"
    )
    natural_product: Series[float] = pa.Field(
        nullable=True, description="Natural product flag"
    )
    oral: Series[bool] = pa.Field(nullable=True, description="Oral administration")
    orphan: Series[float] = pa.Field(nullable=True, description="Orphan drug status")
    parenteral: Series[bool] = pa.Field(
        nullable=True, description="Parenteral administration"
    )
    polymer_flag: Series[float] = pa.Field(nullable=True, description="Polymer flag")
    pref_name: Series[str] = pa.Field(
        nullable=True, description="Preferred molecule name"
    )
    prodrug: Series[float] = pa.Field(nullable=True, description="Prodrug flag")
    structure_type: Series[str] = pa.Field(
        nullable=True, description="Structure representation type"
    )
    therapeutic_flag: Series[bool] = pa.Field(
        nullable=True, description="Therapeutic agent flag"
    )
    topical: Series[bool] = pa.Field(
        nullable=True, description="Topical administration"
    )
    usan_stem: Series[str] = pa.Field(nullable=True, description="USAN stem")
    usan_stem_definition: Series[str] = pa.Field(
        nullable=True, description="USAN stem definition"
    )
    usan_substem: Series[str] = pa.Field(nullable=True, description="USAN substem")
    usan_year: Series[float] = pa.Field(
        nullable=True, description="USAN assignment year"
    )
    veterinary: Series[float] = pa.Field(
        nullable=True, description="Veterinary use flag"
    )
    withdrawn_flag: Series[bool] = pa.Field(
        nullable=True, description="Withdrawn from market flag"
    )
