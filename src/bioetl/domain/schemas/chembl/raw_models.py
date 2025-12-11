"""Typed raw models for ChEMBL payloads.

These models extend SourceRecordModel to provide typed validation
for ChEMBL API responses at the system boundary.

Model naming:
    PublicationRawModel: Canonical name for ChEMBL document/publication payloads.
    DocumentRawModel: Deprecated alias for PublicationRawModel (will be removed in v3.0).
"""

from __future__ import annotations

import warnings
from typing import Self, TypeAlias

from pydantic import ConfigDict, field_validator, model_validator

from bioetl.domain.record_source import SourceRecordModel
from bioetl.domain.value_objects import ActivityId, ChemblId

ScalarValue: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = (
    ScalarValue
    | dict[str, ScalarValue | list[ScalarValue]]
    | list[ScalarValue | dict[str, ScalarValue]]
)
JsonObject: TypeAlias = dict[
    str, ScalarValue | list[ScalarValue] | dict[str, ScalarValue]
]


class ActivityRawModel(SourceRecordModel):
    """Raw ChEMBL activity payload."""

    model_config = ConfigDict(extra="forbid")

    action_type: str | None = None
    activity_comment: str | None = None
    activity_id: ActivityId
    activity_properties: list[JsonObject] | None = None
    assay_chembl_id: ChemblId | None = None
    assay_description: str | None = None
    assay_type: str | None = None
    assay_variant_accession: str | None = None
    assay_variant_mutation: str | None = None
    bao_endpoint: str | None = None
    bao_format: str | None = None
    bao_label: str | None = None
    canonical_smiles: str | None = None
    data_validity_comment: str | None = None
    data_validity_description: str | None = None
    document_chembl_id: ChemblId | None = None
    document_journal: str | None = None
    document_year: int | None = None
    ligand_efficiency: JsonObject | None = None
    molecule_chembl_id: ChemblId | None = None
    molecule_pref_name: str | None = None
    parent_molecule_chembl_id: ChemblId | None = None
    pchembl_value: float | None = None
    potential_duplicate: bool | None = None
    qudt_units: str | None = None
    record_id: int | None = None
    relation: str | None = None
    src_id: int | None = None
    standard_flag: bool
    standard_relation: str | None = None
    standard_text_value: str | None = None
    standard_type: str | None = None
    standard_units: str | None = None
    standard_upper_value: float | None = None
    standard_value: float | None = None
    target_chembl_id: ChemblId | None = None
    target_organism: str | None = None
    target_pref_name: str | None = None
    target_tax_id: int | None = None
    text_value: str | None = None
    toid: str | None = None
    type: str | None = None
    units: str | None = None
    uo_units: str | None = None
    upper_value: float | None = None
    value: float | None = None

    @field_validator("pchembl_value")
    @classmethod
    def validate_pchembl_range(cls, v: float | None) -> float | None:
        if v is not None and not (0 <= v <= 20):
            raise ValueError(f"pchembl_value must be 0-20, got {v}")
        return v

    @field_validator("standard_relation")
    @classmethod
    def validate_standard_relation(cls, v: str | None) -> str | None:
        valid = {"=", ">", "<", ">=", "<=", "~", None}
        if v not in valid:
            raise ValueError(f"Invalid standard_relation: {v}")
        return v

    @model_validator(mode="after")
    def validate_standard_flag_consistency(self) -> Self:
        if self.standard_flag and self.standard_value is None:
            raise ValueError("standard_value required when standard_flag is True")
        return self


class MoleculeRawModel(SourceRecordModel):
    """Raw ChEMBL molecule payload."""

    model_config = ConfigDict(extra="allow")

    molecule_chembl_id: ChemblId
    pref_name: str | None = None
    molecule_type: str | None = None
    max_phase: int | None = None
    molecule_structures: JsonObject | None = None
    molecule_properties: JsonObject | None = None

    @field_validator("molecule_chembl_id", mode="before")
    @classmethod
    def _stringify_molecule_id(cls, value: str | int) -> str:
        return str(value)


class TargetRawModel(SourceRecordModel):
    """Raw ChEMBL target payload."""

    model_config = ConfigDict(extra="allow")

    target_chembl_id: ChemblId
    pref_name: str | None = None
    organism: str | None = None
    target_type: str | None = None
    tax_id: int | None = None
    species_group_flag: bool | None = None

    @field_validator("target_chembl_id", mode="before")
    @classmethod
    def _stringify_target_id(cls, value: str | int) -> str:
        return str(value)


class AssayRawModel(SourceRecordModel):
    """Raw ChEMBL assay payload."""

    model_config = ConfigDict(extra="allow")

    assay_chembl_id: ChemblId
    assay_type: str | None = None
    description: str | None = None
    assay_organism: str | None = None
    assay_tax_id: int | None = None
    assay_strain: str | None = None
    assay_tissue: str | None = None
    assay_cell_type: str | None = None
    assay_subcellular_fraction: str | None = None
    target_chembl_id: ChemblId | None = None
    document_chembl_id: ChemblId | None = None
    src_id: int | None = None
    bao_format: str | None = None

    @field_validator("assay_chembl_id", mode="before")
    @classmethod
    def _stringify_assay_id(cls, value: str | int) -> str:
        return str(value)


class PublicationRawModel(SourceRecordModel):
    """Raw ChEMBL publication/document payload.

    This is the canonical model name. Previously named DocumentRawModel.
    """

    model_config = ConfigDict(extra="allow")

    document_chembl_id: ChemblId
    journal: str | None = None
    year: int | None = None
    volume: str | None = None
    issue: str | None = None
    first_page: str | None = None
    last_page: str | None = None
    pubmed_id: int | None = None
    doi: str | None = None
    title: str | None = None
    doc_type: str | None = None
    authors: str | None = None
    abstract: str | None = None

    @field_validator("document_chembl_id", mode="before")
    @classmethod
    def _stringify_document_id(cls, value: str | int) -> str:
        return str(value)


def __getattr__(name: str) -> type[PublicationRawModel]:
    """Provide deprecated alias for DocumentRawModel."""
    if name == "DocumentRawModel":
        warnings.warn(
            "DocumentRawModel is deprecated, use PublicationRawModel instead. "
            "Will be removed in v3.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        return PublicationRawModel
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Deprecated alias for backward compatibility (will be removed in v3.0)
# Note: Direct class reference for type checkers; runtime uses __getattr__
DocumentRawModel = PublicationRawModel


__all__ = [
    "ActivityRawModel",
    "MoleculeRawModel",
    "TargetRawModel",
    "AssayRawModel",
    "PublicationRawModel",
    "DocumentRawModel",  # Deprecated alias
    "JsonValue",
    "JsonObject",
    "ScalarValue",
]
