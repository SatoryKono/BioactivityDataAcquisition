"""Pydantic models representing raw ChEMBL payloads before normalization."""

from typing import Any

from pydantic import BaseModel, ConfigDict, model_serializer


def _flatten_value(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, dict):
        dict_parts = [
            f"{key}:{_scalar_to_str(val)}"
            for key, val in value.items()
            if val not in (None, "")
        ]
        return "|".join(dict_parts) if dict_parts else None

    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            flattened = _flatten_value(item)
            if flattened not in (None, ""):
                parts.append(str(flattened))
        return "|".join(parts) if parts else None

    return value


def _scalar_to_str(value: Any) -> str:
    if isinstance(value, (dict, list)):
        nested = _flatten_value(value)
        return "" if nested is None else str(nested)
    return str(value)


class ChemblRecordModel(BaseModel):
    """Base Pydantic model for raw ChEMBL payloads with flattening serializer."""

    model_config = ConfigDict(extra="allow")
    # Контейнерные поля, которые нельзя сплющивать: их сериализует нормализатор
    _BYPASS_FLATTEN_FIELDS: set[str] = {
        "assay_classifications",
        "assay_parameters",
        "atc_classifications",
        "target_components",
        "cross_references",
        "molecule_structures",
        "molecule_properties",
        "molecule_hierarchy",
        "molecule_synonyms",
        "activity_properties",
        "ligand_efficiency",
    }

    @model_serializer(mode="wrap")
    def serialize(self, handler: Any) -> dict[str, Any]:
        """Flatten nested structures into string-friendly values."""
        data = handler(self)
        serialized: dict[str, Any] = {}
        for key, value in data.items():
            if key in self._BYPASS_FLATTEN_FIELDS and isinstance(
                value, (list, dict)
            ):
                serialized[key] = value
            else:
                serialized[key] = _flatten_value(value)
        return serialized


class RawActivityPayload(ChemblRecordModel):
    """Container for raw ChEMBL activity records before normalization."""

    activity_properties: list[Any] | dict[str, Any] | None = None
    ligand_efficiency: dict[str, Any] | None = None


class RawAssayPayload(ChemblRecordModel):
    """Container for raw assay payloads coming from ChEMBL."""

    assay_classifications: list[Any] | None = None
    assay_parameters: list[Any] | None = None


class RawMoleculePayload(ChemblRecordModel):
    """Container for raw molecule payloads originating from ChEMBL."""

    atc_classifications: list[Any] | None = None
    cross_references: list[Any] | None = None
    molecule_hierarchy: dict[str, Any] | None = None
    molecule_properties: dict[str, Any] | None = None
    molecule_structures: dict[str, Any] | None = None
    molecule_synonyms: list[Any] | None = None
