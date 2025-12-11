"""Typed raw models for ChEMBL payloads.

These models extend SourceRecordModel to provide typed validation
for ChEMBL API responses at the system boundary.
"""

from __future__ import annotations

from typing import Any, Self, TypeAlias

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

    @classmethod
    def _extract_string_from_dict(cls, value: dict[str, Any]) -> str | None:
        """Extract string value from dict using priority keys."""
        for key in ("action_type", "description", "label", "name"):
            candidate = value.get(key)
            if isinstance(candidate, str):
                return candidate
        scalar_values = [
            str(v)
            for _, v in sorted(value.items())
            if isinstance(v, (str, int, float, bool))
        ]
        return ";".join(scalar_values) if scalar_values else None

    @classmethod
    def _coerce_action_type_value(cls, value: object) -> str | None:
        """Coerce action_type to a string when API returns nested structures."""
        if value is None or value == "":
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return cls._extract_string_from_dict(value)
        if isinstance(value, list):
            items = [str(item) for item in value if item is not None]
            return ";".join(items) if items else None
        return str(value)

    @model_validator(mode="before")
    @classmethod
    def _normalize_action_type(cls, data: object) -> object:
        """Normalize action_type before field validation."""
        if not isinstance(data, dict) or "action_type" not in data:
            return data
        data = dict(data)
        data["action_type"] = cls._coerce_action_type_value(data["action_type"])
        return data

    @field_validator("pchembl_value")
    @classmethod
    def validate_pchembl_range(cls, v: float | None) -> float | None:
        """Ensure pchembl_value stays within the valid 0–20 range."""
        if v is not None and not (0 <= v <= 20):
            raise ValueError(f"pchembl_value must be 0-20, got {v}")
        return v

    @field_validator("action_type", mode="before")
    @classmethod
    def normalize_action_type(cls, value: JsonValue) -> str | None:
        """Normalize action_type values regardless of representation."""
        return cls._coerce_action_type_value(value)

    @field_validator("standard_relation")
    @classmethod
    def validate_standard_relation(cls, v: str | None) -> str | None:
        """Validate standard_relation against the allowed relation symbols."""
        valid = {"=", ">", "<", ">=", "<=", "~", None}
        if v not in valid:
            raise ValueError(f"Invalid standard_relation: {v}")
        return v

    @model_validator(mode="after")
    def validate_standard_flag_consistency(self) -> Self:
        """Validate standard_flag consistency with standard_value."""
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
    """Raw ChEMBL publication/document payload."""

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
        """Convert document ID to string."""
        return str(value)


__all__ = [
    "ActivityRawModel",
    "MoleculeRawModel",
    "TargetRawModel",
    "AssayRawModel",
    "PublicationRawModel",
    "JsonValue",
    "JsonObject",
    "ScalarValue",
]
