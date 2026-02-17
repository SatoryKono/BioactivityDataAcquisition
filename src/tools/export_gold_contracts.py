"""Export Gold Pandera contracts to JSON reference files.

This tool discovers all ``pandera.DataFrameModel`` classes from
``bioetl.domain.contracts.gold`` and exports machine-readable contracts into
``docs/04-reference/contracts/gold``.
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
import logging
import pkgutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandera.pandas as pa

LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = ROOT / "docs" / "04-reference" / "contracts" / "gold"
PACKAGE_NAME = "bioetl.domain.contracts.gold"
SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class FieldSpec:
    """Canonical field definition used in contracts and parity checks."""

    name: str
    json_type: str
    nullable: bool
    description: str | None


def _to_entity_name(class_name: str) -> str:
    """Convert Gold schema class name to entity snake_case name."""
    if not class_name.endswith("GoldSchema"):
        raise ValueError(f"Unexpected schema class name: {class_name}")
    stem = class_name[: -len("GoldSchema")]

    prefixes = {
        "ChEMBL": "chembl",
        "PubChem": "pubchem",
        "UniProt": "uniprot",
        "PubMed": "pubmed",
        "OpenAlex": "openalex",
        "CrossRef": "crossref",
        "SemanticScholar": "semanticscholar",
        "Composite": "composite",
    }

    for prefix, normalized in prefixes.items():
        if stem.startswith(prefix):
            suffix = stem[len(prefix) :]
            return f"{normalized}_{_camel_to_snake(suffix)}" if suffix else normalized
    return _camel_to_snake(stem)


def _camel_to_snake(value: str) -> str:
    chars: list[str] = []
    for idx, char in enumerate(value):
        if char.isupper() and idx > 0 and not value[idx - 1].isupper():
            chars.append("_")
        chars.append(char.lower())
    return "".join(chars)


def _json_type_from_dtype(dtype_str: str) -> str:
    lowered = dtype_str.lower()
    if "int" in lowered:
        return "integer"
    if "float" in lowered or "double" in lowered or "decimal" in lowered:
        return "number"
    if "bool" in lowered:
        return "boolean"
    if "object" in lowered:
        return "array"
    return "string"


def get_gold_schema_classes() -> list[type[pa.DataFrameModel]]:
    """Discover all Gold Pandera schema classes."""
    package = importlib.import_module(PACKAGE_NAME)
    classes: list[type[pa.DataFrameModel]] = []

    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        if module_name.startswith("_"):
            continue
        module = importlib.import_module(f"{PACKAGE_NAME}.{module_name}")
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(cls, pa.DataFrameModel)
                and cls is not pa.DataFrameModel
                and cls.__module__ == module.__name__
            ):
                classes.append(cls)

    return sorted(classes, key=lambda item: item.__name__)


def extract_field_specs(schema_cls: type[pa.DataFrameModel]) -> list[FieldSpec]:
    """Extract field metadata from Pandera schema using alias-aware names."""
    schema = schema_cls.to_schema()
    specs: list[FieldSpec] = []
    for field_name, column in schema.columns.items():
        specs.append(
            FieldSpec(
                name=field_name,
                json_type=_json_type_from_dtype(str(column.dtype)),
                nullable=column.nullable,
                description=column.description,
            )
        )
    return specs


def _read_existing_field_specs(path: Path) -> dict[str, FieldSpec]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    field_entries: list[dict[str, Any]] = payload.get("fields", [])
    return {
        item["name"]: FieldSpec(
            name=item["name"],
            json_type=item["json_type"],
            nullable=item["nullable"],
            description=item.get("description"),
        )
        for item in field_entries
    }


def _build_changes(
    previous: dict[str, FieldSpec], current: list[FieldSpec]
) -> list[dict[str, Any]]:
    current_map = {item.name: item for item in current}
    changes: list[dict[str, Any]] = []

    for field_name in sorted(previous):
        if field_name not in current_map:
            changes.append(
                {
                    "field": field_name,
                    "change": "removed",
                    "breaking": True,
                    "details": "Field removed from schema.",
                }
            )

    for field_name in sorted(current_map):
        current_item = current_map[field_name]
        previous_item = previous.get(field_name)
        if previous_item is None:
            is_breaking = not current_item.nullable
            changes.append(
                {
                    "field": field_name,
                    "change": "added",
                    "breaking": is_breaking,
                    "details": "New nullable field."
                    if current_item.nullable
                    else "New required field.",
                }
            )
            continue

        if previous_item.json_type != current_item.json_type:
            changes.append(
                {
                    "field": field_name,
                    "change": "type_changed",
                    "breaking": True,
                    "details": f"Type changed from {previous_item.json_type} to {current_item.json_type}.",
                }
            )
        if previous_item.nullable and not current_item.nullable:
            changes.append(
                {
                    "field": field_name,
                    "change": "nullable_narrowed",
                    "breaking": True,
                    "details": "Nullable changed from true to false.",
                }
            )
        if (not previous_item.nullable) and current_item.nullable:
            changes.append(
                {
                    "field": field_name,
                    "change": "nullable_widened",
                    "breaking": False,
                    "details": "Nullable changed from false to true.",
                }
            )
        if (previous_item.description or "") != (current_item.description or ""):
            changes.append(
                {
                    "field": field_name,
                    "change": "description_updated",
                    "breaking": False,
                    "details": "Description metadata updated.",
                }
            )

    return changes


def build_contract_payload(
    schema_cls: type[pa.DataFrameModel],
    entity_name: str,
    fields: list[FieldSpec],
    previous_fields: dict[str, FieldSpec],
) -> dict[str, Any]:
    """Build exported JSON contract payload."""
    properties: dict[str, dict[str, Any]] = {}
    required: list[str] = []

    for field in fields:
        field_types = [field.json_type, "null"] if field.nullable else field.json_type
        properties[field.name] = {"type": field_types}
        if field.description:
            properties[field.name]["description"] = field.description
        if not field.nullable:
            required.append(field.name)

    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    changelog_changes = _build_changes(previous_fields, fields)

    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$version": SCHEMA_VERSION,
        "title": f"{schema_cls.__name__.removesuffix('GoldSchema')} Gold Contract",
        "description": (
            f"Gold layer data contract for {entity_name}. "
            f"Auto-generated from Pandera schema {schema_cls.__name__}."
        ),
        "type": "object",
        "fields": [field.__dict__ for field in fields],
        "properties": properties,
        "required": sorted(required),
        "changelog": {
            "generated_at": generated_at,
            "summary": {
                "breaking": any(item["breaking"] for item in changelog_changes),
                "non_breaking": any(not item["breaking"] for item in changelog_changes),
            },
            "changes": changelog_changes,
        },
    }


def export_contracts() -> list[Path]:
    """Generate JSON contracts for all Gold schemas."""
    CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)
    written_files: list[Path] = []

    for schema_cls in get_gold_schema_classes():
        entity_name = _to_entity_name(schema_cls.__name__)
        output_path = CONTRACTS_DIR / f"{entity_name}_v1.0.json"
        fields = extract_field_specs(schema_cls)
        previous_fields = _read_existing_field_specs(output_path)
        payload = build_contract_payload(
            schema_cls, entity_name, fields, previous_fields
        )
        output_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        written_files.append(output_path)
        LOGGER.info("Exported %s", output_path.relative_to(ROOT))

    return written_files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO, format="%(message)s"
    )
    export_contracts()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
