#!/usr/bin/env python3
"""Generate versioned Gold JSON contracts from Pandera schemas."""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

# Ensure project root is in python path
project_root = Path(__file__).resolve().parents[3]
sys.path.append(str(project_root / "src"))

from bioetl.domain.contracts import gold as gold_contracts  # noqa: E402

CONTRACTS_DIR = project_root / "docs" / "04-reference" / "contracts" / "gold"
SCHEMA_SUFFIX = "GoldSchema"
PROVIDER_PREFIXES = (
    ("ChEMBL", "chembl"),
    ("PubChem", "pubchem"),
    ("PubMed", "pubmed"),
    ("UniProt", "uniprot"),
    ("CrossRef", "crossref"),
    ("OpenAlex", "openalex"),
    ("SemanticScholar", "semanticscholar"),
    ("Composite", "composite"),
)


def to_contract_stem(schema_name: str) -> str:
    """Convert a Gold schema class name to a contract file stem."""
    if not schema_name.endswith(SCHEMA_SUFFIX):
        raise ValueError(f"Schema class {schema_name} must end with {SCHEMA_SUFFIX}")

    base_name = schema_name.removesuffix(SCHEMA_SUFFIX)

    for class_prefix, file_prefix in PROVIDER_PREFIXES:
        if base_name.startswith(class_prefix):
            suffix = base_name.removeprefix(class_prefix)
            if not suffix:
                return file_prefix
            return f"{file_prefix}_{_camel_to_snake(suffix)}"

    raise ValueError(f"Unsupported schema class prefix in {schema_name}")


def _camel_to_snake(value: str) -> str:
    """Convert CamelCase to snake_case while preserving IDMapping as one token."""
    value = value.replace("IDMapping", "Idmapping")

    chunks: list[str] = []
    current_chunk = ""
    for char in value:
        if char.isupper() and current_chunk:
            chunks.append(current_chunk)
            current_chunk = char
        else:
            current_chunk += char

    if current_chunk:
        chunks.append(current_chunk)

    return "_".join(chunk.lower() for chunk in chunks)


def _type_to_json_type(dtype: object) -> str:
    """Map Pandera dtype to JSON schema scalar type."""
    dtype_name = str(dtype).lower()
    if "int" in dtype_name:
        return "integer"
    if "float" in dtype_name or "double" in dtype_name:
        return "number"
    if "bool" in dtype_name:
        return "boolean"
    return "string"


def _stem_to_title(stem: str) -> str:
    parts = []
    for part in stem.split("_"):
        if part == "chembl":
            parts.append("ChEMBL")
        else:
            parts.append(part.capitalize())
    return " ".join(parts)


def get_gold_schema_classes() -> dict[str, type]:
    """Discover all schema classes exported by bioetl.domain.contracts.gold."""
    schema_classes: dict[str, type] = {}

    for export_name in gold_contracts.__all__:
        exported_obj = getattr(gold_contracts, export_name)
        if inspect.isclass(exported_obj) and export_name.endswith(SCHEMA_SUFFIX):
            schema_classes[export_name] = exported_obj

    return schema_classes


def build_contract(schema_cls: type, contract_stem: str) -> dict[str, object]:
    """Build a record-level JSON contract from a Pandera DataFrameModel class."""
    pandera_schema = schema_cls.to_schema()  # type: ignore[attr-defined]

    properties: dict[str, dict[str, object]] = {}
    required: list[str] = []

    for column_name, column in pandera_schema.columns.items():
        json_type = _type_to_json_type(column.dtype)
        if column.nullable:
            properties[column_name] = {"type": [json_type, "null"]}
        else:
            properties[column_name] = {"type": json_type}
            required.append(column_name)

    title = f"{_stem_to_title(contract_stem)} Gold Contract"
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$version": "1.0.0",
        "title": title,
        "description": (
            f"Gold layer data contract for {title}. "
            f"Auto-generated from Pandera schema {schema_cls.__name__}."
        ),
        "type": "object",
        "properties": properties,
        "required": sorted(required),
    }


def generate_contracts() -> None:
    """Generate JSON contract files for every exported Gold schema class."""
    CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)

    schema_classes = get_gold_schema_classes()

    for schema_name, schema_cls in sorted(schema_classes.items()):
        contract_stem = to_contract_stem(schema_name)
        contract_name = f"{contract_stem}_v1.0.json"
        output_file = CONTRACTS_DIR / contract_name

        print(f"Generating contract for {schema_name} -> {contract_name}...")
        contract = build_contract(schema_cls, contract_stem)

        with output_file.open("w", encoding="utf-8") as handle:
            json.dump(contract, handle, indent=2)
            handle.write("\n")

    generated_contracts = sorted(CONTRACTS_DIR.glob("*.json"))
    if len(generated_contracts) != len(schema_classes):
        raise RuntimeError(
            "Gold contract completeness check failed: "
            f"generated {len(generated_contracts)} JSON files, "
            f"but found {len(schema_classes)} schema classes in "
            "bioetl.domain.contracts.gold.__all__."
        )

    print(
        f"\nGenerated {len(generated_contracts)} Gold contracts successfully "
        f"in {CONTRACTS_DIR}."
    )


if __name__ == "__main__":
    generate_contracts()
