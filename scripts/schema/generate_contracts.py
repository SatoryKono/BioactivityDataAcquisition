#!/usr/bin/env python3
"""Generate Gold JSON contracts from Pandera DataFrameModel schemas.

Usage:
    python -m scripts.schema generate-contracts
"""

from __future__ import annotations

import inspect
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlunsplit

from bioetl.domain.contracts import gold as gold_contracts
from bioetl.domain.normalization.profiles import (
    resolve_normalization_profile_identity,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT_VERSION = "1.0.0"
ENTITY_CONTRACT_VERSIONS: dict[str, str] = {
    "chembl_target": "3.0.0",
    "chembl_target_protein_classification": "2.0.0",
}
JSON_SCHEMA_DRAFT7_URI = urlunsplit(
    ("http", "json-schema.org", "/draft-07/schema", "", "")
)
CONTRACTS_DIR = PROJECT_ROOT / "docs" / "04-reference" / "contracts" / "gold"
DIFF_REPORT_PATH = (
    PROJECT_ROOT
    / "docs"
    / "05-operations"
    / "verification"
    / "gold-contracts-export-diff-2026-02-17.json"
)

ENTITY_NAME_OVERRIDES: dict[str, str] = {
    "chembl_document": "chembl_publication",
    "chembl_document_similarity": "chembl_publication_similarity",
    "chembl_document_term": "chembl_publication_term",
}
LEGACY_CONTRACT_FILENAMES: tuple[str, ...] = (
    "chembl_document_v1.0.json",
    "chembl_document_similarity_v1.0.json",
    "chembl_document_term_v1.0.json",
)


def _camel_to_snake(name: str) -> str:
    first_pass = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", first_pass).lower()


def _class_to_entity(schema_name: str) -> str:
    base = schema_name.removesuffix("GoldSchema")
    normalized = (
        base.replace("ChEMBL", "Chembl")
        .replace("PubChem", "Pubchem")
        .replace("PubMed", "Pubmed")
        .replace("UniProt", "Uniprot")
        .replace("IDMapping", "Idmapping")
        .replace("OpenAlex", "Openalex")
        .replace("CrossRef", "Crossref")
        .replace("SemanticScholar", "Semanticscholar")
    )
    entity = _camel_to_snake(normalized)
    return ENTITY_NAME_OVERRIDES.get(entity, entity)


def _filename_from_version(entity: str, version: str) -> str:
    major_minor = ".".join(version.split(".")[:2])
    return f"{entity}_v{major_minor}.json"


def _contract_version_for_entity(entity: str) -> str:
    return ENTITY_CONTRACT_VERSIONS.get(entity, DEFAULT_CONTRACT_VERSION)


def _normalize_export_field_name(column_name: str) -> str:
    if column_name.endswith("_chembl_id"):
        return column_name.replace("_chembl_id", "_id")
    return column_name


def _map_dtype_to_json_type(dtype_value: Any) -> str:
    dtype_str = str(dtype_value).lower()
    if dtype_str == "str":
        return "string"
    if dtype_str == "float64":
        return "number"
    if dtype_str == "int64":
        return "integer"
    if dtype_str == "bool":
        return "boolean"
    return "object"


def _build_property_schema(
    column: Any, json_schema_property: dict[str, Any]
) -> dict[str, Any]:
    base_type = _map_dtype_to_json_type(column.dtype)
    json_type: str | list[str]
    if column.nullable:
        json_type = [base_type, "null"]
    else:
        json_type = base_type

    return {
        "type": json_type,
        "nullable": bool(column.nullable),
        "description": column.description
        or json_schema_property.get("description")
        or "",
    }


def _build_contract(
    schema_cls: type[Any],
    entity: str,
    version: str,
) -> dict[str, Any]:
    schema = schema_cls.to_schema()
    json_schema = schema_cls.to_json_schema()

    properties: dict[str, dict[str, Any]] = {}
    required: list[str] = []

    for column_name, column in schema.columns.items():
        property_from_json_schema = json_schema.get("properties", {}).get(
            column_name, {}
        )
        export_name = _normalize_export_field_name(column_name)
        properties[export_name] = _build_property_schema(
            column, property_from_json_schema
        )
        if not column.nullable:
            required.append(export_name)

    provider, entity_type = entity.split("_", maxsplit=1)
    profile_identity = resolve_normalization_profile_identity(provider, entity_type)
    contract_payload = {
        "$schema": f"{JSON_SCHEMA_DRAFT7_URI}#",
        "$version": version,
        "title": f"{schema_cls.__name__} Contract",
        "description": (
            f"Gold layer data contract for {entity}. "
            f"Auto-generated from Pandera schema {schema_cls.__name__}."
        ),
        "type": "object",
        "properties": properties,
        "required": sorted(required),
    }
    if profile_identity is not None:
        contract_payload["normalization_profile"] = {
            "ref": profile_identity.profile_name,
            "version": profile_identity.profile_version,
            "hash": profile_identity.profile_hash,
        }
    return contract_payload


def _load_previous_contract(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file_obj:
        loaded_contract = json.load(file_obj)
    if isinstance(loaded_contract, dict):
        return loaded_contract
    return {}


def _compute_diff(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    prev_props = previous.get("properties", {})
    curr_props = current.get("properties", {})

    prev_names = set(prev_props)
    curr_names = set(curr_props)

    changed = []
    for prop_name in sorted(prev_names & curr_names):
        if prev_props[prop_name] != curr_props[prop_name]:
            changed.append(
                {
                    "property": prop_name,
                    "before": prev_props[prop_name],
                    "after": curr_props[prop_name],
                }
            )

    return {
        "added_properties": sorted(curr_names - prev_names),
        "removed_properties": sorted(prev_names - curr_names),
        "changed_properties": changed,
        "required_changed": previous.get("required", []) != current.get("required", []),
    }


def _remove_legacy_contracts() -> None:
    for legacy_filename in LEGACY_CONTRACT_FILENAMES:
        legacy_path = CONTRACTS_DIR / legacy_filename
        if legacy_path.exists():
            legacy_path.unlink()
            print(f"Removed legacy contract {legacy_path}")


def generate_contracts() -> None:
    CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)
    DIFF_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _remove_legacy_contracts()

    schema_classes: list[type[Any]] = []
    for export_name in gold_contracts.__all__:
        export_obj = getattr(gold_contracts, export_name)
        if inspect.isclass(export_obj) and export_name.endswith("GoldSchema"):
            schema_classes.append(export_obj)

    schema_classes.sort(key=lambda cls: cls.__name__)

    diff_report: dict[str, Any] = {
        "generated_at": "2026-02-17",
        "version": DEFAULT_CONTRACT_VERSION,
        "entities": {},
    }

    for schema_cls in schema_classes:
        entity = _class_to_entity(schema_cls.__name__)
        contract_version = _contract_version_for_entity(entity)
        filename = _filename_from_version(entity, contract_version)
        output_path = CONTRACTS_DIR / filename

        previous_contract = _load_previous_contract(output_path)
        current_contract = _build_contract(schema_cls, entity, contract_version)

        with output_path.open("w", encoding="utf-8") as file_obj:
            json.dump(current_contract, file_obj, indent=2, ensure_ascii=False)
            file_obj.write("\n")

        diff_report["entities"][entity] = {
            "file": output_path.relative_to(PROJECT_ROOT).as_posix(),
            "contract_version": contract_version,
            "status": "created" if not previous_contract else "updated",
            "diff": _compute_diff(previous_contract, current_contract),
        }
        print(f"Generated {output_path}")

    with DIFF_REPORT_PATH.open("w", encoding="utf-8") as file_obj:
        json.dump(diff_report, file_obj, indent=2, ensure_ascii=False)
        file_obj.write("\n")

    print(f"Diff report written to {DIFF_REPORT_PATH}")


def main() -> int:
    """CLI entrypoint for schema router compatibility."""
    generate_contracts()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
