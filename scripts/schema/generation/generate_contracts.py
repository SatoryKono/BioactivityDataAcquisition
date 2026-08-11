#!/usr/bin/env python3
"""Generate Gold JSON contracts from Pandera DataFrameModel schemas.

Usage:
    python -m scripts.schema generate-contracts
"""

from __future__ import annotations

import argparse
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

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONTRACT_VERSION = "1.0.0"
ENTITY_CONTRACT_VERSIONS: dict[str, str] = {
    "chembl_target": "3.0.0",
    "chembl_target_protein_classification": "2.2.0",
}
JSON_SCHEMA_DRAFT7_URI = urlunsplit(
    ("http", "json-schema.org", "/draft-07/schema", "", "")
)
CONTRACTS_DIR = PROJECT_ROOT / "docs" / "04-reference" / "contracts" / "gold"
ENTITY_NAME_OVERRIDES: dict[str, str] = {
    "chembl_document": "chembl_publication",
    "chembl_document_similarity": "chembl_publication_similarity",
    "chembl_document_term": "chembl_publication_term",
}
RETAINED_LEGACY_CONTRACT_FILENAMES: frozenset[str] = frozenset()


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
    if dtype_str in {"bool", "boolean"}:
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
    contract_payload: dict[str, Any] = {
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


def _remove_stale_contracts(active_filenames: set[str]) -> None:
    retained_filenames = active_filenames | RETAINED_LEGACY_CONTRACT_FILENAMES
    for contract_path in sorted(CONTRACTS_DIR.glob("*.json")):
        if contract_path.name in retained_filenames:
            continue
        contract_path.unlink()
        print(f"Removed stale contract {contract_path}")


def _active_contract_filenames(schema_classes: list[type[Any]]) -> set[str]:
    filenames: set[str] = set()
    for schema_cls in schema_classes:
        entity = _class_to_entity(schema_cls.__name__)
        filenames.add(
            _filename_from_version(entity, _contract_version_for_entity(entity))
        )
    return filenames


def _schema_classes() -> list[type[Any]]:
    schema_classes: list[type[Any]] = []
    for export_name in gold_contracts.__all__:
        export_obj = getattr(gold_contracts, export_name)
        if inspect.isclass(export_obj) and export_name.endswith("GoldSchema"):
            schema_classes.append(export_obj)
    schema_classes.sort(key=lambda cls: cls.__name__)
    return schema_classes


def _expected_artifacts() -> dict[Path, str]:
    schema_classes = _schema_classes()
    artifacts: dict[Path, str] = {}

    for schema_cls in schema_classes:
        entity = _class_to_entity(schema_cls.__name__)
        contract_version = _contract_version_for_entity(entity)
        filename = _filename_from_version(entity, contract_version)
        output_path = CONTRACTS_DIR / filename

        current_contract = _build_contract(schema_cls, entity, contract_version)
        artifacts[output_path] = (
            json.dumps(current_contract, indent=2, ensure_ascii=False) + "\n"
        )

    return artifacts


def _stale_artifacts(expected: dict[Path, str]) -> list[Path]:
    stale = [
        path
        for path, content in expected.items()
        if not path.exists() or path.read_text(encoding="utf-8") != content
    ]
    active_contracts = {path.name for path in expected if path.parent == CONTRACTS_DIR}
    stale.extend(
        path
        for path in sorted(CONTRACTS_DIR.glob("*.json"))
        if path.name not in active_contracts
        and path.name not in RETAINED_LEGACY_CONTRACT_FILENAMES
    )
    return sorted(set(stale))


def generate_contracts(*, check: bool = False) -> int:
    expected = _expected_artifacts()
    stale = _stale_artifacts(expected)
    if check:
        if stale:
            for path in stale:
                print(f"Stale generated artifact: {path}")
            return 1
        print("Gold contract artifacts are current")
        return 0

    CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)
    _remove_stale_contracts(
        {path.name for path in expected if path.parent == CONTRACTS_DIR}
    )
    for output_path, content in expected.items():
        output_path.write_text(content, encoding="utf-8")
        print(f"Generated {output_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for schema router compatibility."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when generated contracts are stale without writing files.",
    )
    args = parser.parse_args(argv)
    return generate_contracts(check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
