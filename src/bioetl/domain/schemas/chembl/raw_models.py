"""Typed raw models for ChEMBL payloads."""

from __future__ import annotations

from typing import TypeAlias

from pydantic import ConfigDict, field_validator

from bioetl.domain.record_source import RawRecord

ScalarValue: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = (
    ScalarValue
    | dict[str, ScalarValue | list[ScalarValue]]
    | list[ScalarValue | dict[str, ScalarValue]]
)
JsonObject: TypeAlias = dict[
    str, ScalarValue | list[ScalarValue] | dict[str, ScalarValue]
]


class ActivityRawModel(RawRecord):
    """Raw ChEMBL activity payload."""

    model_config = ConfigDict(extra="forbid")

    action_type: str | None = None
    activity_comment: str | None = None
    activity_id: str
    activity_properties: list[JsonObject] | None = None
    assay_chembl_id: str | None = None
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
    document_chembl_id: str | None = None
    document_journal: str | None = None
    document_year: int | None = None
    ligand_efficiency: JsonObject | None = None
    molecule_chembl_id: str | None = None
    molecule_pref_name: str | None = None
    parent_molecule_chembl_id: str | None = None
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
    target_chembl_id: str | None = None
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

    @field_validator("activity_id", mode="before")
    @classmethod
    def _stringify_activity_id(cls, value: str | int) -> str:
        return str(value)


class MoleculeRawModel(RawRecord):
    """Raw ChEMBL molecule payload."""

    model_config = ConfigDict(extra="allow")

    molecule_chembl_id: str
    pref_name: str | None = None
    molecule_type: str | None = None
    max_phase: int | None = None
    molecule_structures: JsonObject | None = None
    molecule_properties: JsonObject | None = None

    @field_validator("molecule_chembl_id", mode="before")
    @classmethod
    def _stringify_molecule_id(cls, value: str | int) -> str:
        return str(value)


class TargetRawModel(RawRecord):
    """Raw ChEMBL target payload."""

    model_config = ConfigDict(extra="allow")

    target_chembl_id: str
    pref_name: str | None = None
    organism: str | None = None
    target_type: str | None = None
    tax_id: int | None = None
    species_group_flag: bool | None = None

    @field_validator("target_chembl_id", mode="before")
    @classmethod
    def _stringify_target_id(cls, value: str | int) -> str:
        return str(value)


class AssayRawModel(RawRecord):
    """Raw ChEMBL assay payload."""

    model_config = ConfigDict(extra="allow")

    assay_chembl_id: str
    assay_type: str | None = None
    description: str | None = None
    assay_organism: str | None = None
    assay_tax_id: int | None = None
    assay_strain: str | None = None
    assay_tissue: str | None = None
    assay_cell_type: str | None = None
    assay_subcellular_fraction: str | None = None
    target_chembl_id: str | None = None
    document_chembl_id: str | None = None
    src_id: int | None = None
    bao_format: str | None = None

    @field_validator("assay_chembl_id", mode="before")
    @classmethod
    def _stringify_assay_id(cls, value: str | int) -> str:
        return str(value)


class DocumentRawModel(RawRecord):
    """Raw ChEMBL document/publication payload."""

    model_config = ConfigDict(extra="allow")

    document_chembl_id: str
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


__all__ = [
    "ActivityRawModel",
    "MoleculeRawModel",
    "TargetRawModel",
    "AssayRawModel",
    "DocumentRawModel",
    "JsonValue",
    "JsonObject",
    "ScalarValue",
]
