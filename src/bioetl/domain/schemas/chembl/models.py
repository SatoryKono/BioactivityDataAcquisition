from typing import Any

from pydantic import BaseModel, ConfigDict, model_serializer


def _flatten_value(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, dict):
        parts = [f"{key}:{_scalar_to_str(val)}" for key, val in value.items() if val not in (None, "")]
        return "|".join(parts) if parts else None

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
    model_config = ConfigDict(extra="allow")

    @model_serializer(mode="wrap")
    def serialize(self, handler: Any) -> dict[str, Any]:
        data = handler(self)
        return {key: _flatten_value(value) for key, value in data.items()}


class ActivityModel(ChemblRecordModel):
    activity_properties: list[Any] | dict[str, Any] | None = None
    ligand_efficiency: dict[str, Any] | None = None

