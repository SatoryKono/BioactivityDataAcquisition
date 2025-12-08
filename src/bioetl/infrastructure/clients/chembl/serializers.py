"""Helpers to deterministically flatten ChEMBL payloads for serialization."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping, Set

# Container fields that should not be flattened; they are handled later by normalizers.
DEFAULT_BYPASS_FIELDS: Set[str] = {
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


def _flatten_value(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, Mapping):
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
    if isinstance(value, (Mapping, list)):
        nested = _flatten_value(value)
        return "" if nested is None else str(nested)
    return str(value)


def serialize_chembl_payload(
    payload: MutableMapping[str, Any],
    bypass_fields: Set[str] | frozenset[str] = DEFAULT_BYPASS_FIELDS,
) -> dict[str, Any]:
    """
    Flatten nested payload fields into string-friendly values.

    Nested mappings/lists are collapsed using pipe-delimited strings, while fields
    listed in bypass_fields are kept as-is for downstream normalization.
    """
    serialized: dict[str, Any] = {}
    for key, value in payload.items():
        if key in bypass_fields and isinstance(value, (list, Mapping)):
            serialized[key] = value
        else:
            serialized[key] = _flatten_value(value)
    return serialized


def flatten_chembl_payload(
    payload: MutableMapping[str, Any],
    bypass_fields: Set[str] | frozenset[str] = DEFAULT_BYPASS_FIELDS,
) -> dict[str, Any]:
    """
    Backwards-compatible alias for serialize_chembl_payload.

    Tests and docs refer to this helper as flatten_chembl_payload.
    """

    return serialize_chembl_payload(payload, bypass_fields=bypass_fields)


__all__ = [
    "DEFAULT_BYPASS_FIELDS",
    "serialize_chembl_payload",
    "flatten_chembl_payload",
]

