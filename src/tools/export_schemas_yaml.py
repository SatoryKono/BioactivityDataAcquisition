#!/usr/bin/env python
"""Export Pandera schemas to YAML format.

This script extracts schema definitions from Pandera DataFrameModel classes
and exports them to YAML for documentation, validation, and interoperability.

Usage:
    python -m tools.export_schemas_yaml [--output-dir OUTPUT_DIR] [--entity ENTITY]

Examples:
    # Export all schemas to configs/schemas/
    python -m tools.export_schemas_yaml

    # Export specific entity schema
    python -m tools.export_schemas_yaml --entity activity

    # Export to custom directory
    python -m tools.export_schemas_yaml --output-dir /tmp/schemas
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import importlib
from pathlib import Path
import sys
from typing import Any

import yaml

# Schema module mappings
SCHEMA_MODULES = {
    "activity": "bioetl.infrastructure.validation.schemas.chembl.activity",
    "assay": "bioetl.infrastructure.validation.schemas.chembl.assay",
    "cell": "bioetl.infrastructure.validation.schemas.chembl.cell",
    "molecule": "bioetl.infrastructure.validation.schemas.chembl.molecule",
    "publication": "bioetl.infrastructure.validation.schemas.chembl.publication",
    "target": "bioetl.infrastructure.validation.schemas.chembl.target",
    "tissue": "bioetl.infrastructure.validation.schemas.chembl.tissue",
}

SCHEMA_CLASSES = {
    "activity": "ActivityTableSchema",
    "assay": "AssayTableSchema",
    "cell": "CellTableSchema",
    "molecule": "MoleculeTableSchema",
    "publication": "PublicationTableSchema",
    "target": "TargetTableSchema",
    "tissue": "TissueTableSchema",
}


@dataclass
class FieldSpec:
    """Specification for a single schema field."""

    name: str
    dtype: str
    nullable: bool
    description: str | None
    constraints: dict[str, Any]


@dataclass
class SchemaSpec:
    """Specification for a complete schema."""

    name: str
    entity: str
    provider: str
    fields: list[FieldSpec]
    column_order: list[str]
    config: dict[str, Any]


def extract_field_spec(name: str, field_info: Any) -> FieldSpec:
    """Extract field specification from Pandera Field object.

    Args:
        name: Field name
        field_info: Pandera Field annotation

    Returns:
        FieldSpec with extracted information
    """
    constraints: dict[str, Any] = {}

    # Extract dtype from annotation
    dtype = "object"
    if hasattr(field_info, "annotation"):
        annotation = field_info.annotation
        if hasattr(annotation, "__args__"):
            dtype_arg = annotation.__args__[0] if annotation.__args__ else "object"
            dtype = getattr(dtype_arg, "__name__", str(dtype_arg))

    # Extract field constraints
    field_obj = None
    if hasattr(field_info, "default"):
        field_obj = field_info.default

    nullable = True
    description = None

    if field_obj is not None:
        nullable = getattr(field_obj, "nullable", True)
        description = getattr(field_obj, "description", None)

        # Extract validation constraints
        if hasattr(field_obj, "ge") and field_obj.ge is not None:
            constraints["ge"] = field_obj.ge
        if hasattr(field_obj, "le") and field_obj.le is not None:
            constraints["le"] = field_obj.le
        if hasattr(field_obj, "gt") and field_obj.gt is not None:
            constraints["gt"] = field_obj.gt
        if hasattr(field_obj, "lt") and field_obj.lt is not None:
            constraints["lt"] = field_obj.lt
        if hasattr(field_obj, "isin") and field_obj.isin is not None:
            constraints["allowed_values"] = list(field_obj.isin)
        if hasattr(field_obj, "str_matches") and field_obj.str_matches is not None:
            constraints["pattern"] = field_obj.str_matches

    return FieldSpec(
        name=name,
        dtype=dtype,
        nullable=nullable,
        description=description,
        constraints=constraints,
    )


def extract_schema_spec(entity: str) -> SchemaSpec:
    """Extract schema specification from Pandera schema class.

    Args:
        entity: Entity name (activity, assay, etc.)

    Returns:
        SchemaSpec with extracted schema information
    """
    module_path = SCHEMA_MODULES.get(entity)
    class_name = SCHEMA_CLASSES.get(entity)

    if not module_path or not class_name:
        raise ValueError(f"Unknown entity: {entity}")

    module = importlib.import_module(module_path)
    schema_class = getattr(module, class_name)

    # Extract column order if available
    column_order: list[str] = []
    if hasattr(module, "OUTPUT_COLUMN_ORDER"):
        column_order = list(module.OUTPUT_COLUMN_ORDER)

    # Extract fields from class annotations
    fields: list[FieldSpec] = []
    annotations = getattr(schema_class, "__annotations__", {})

    for field_name in column_order or annotations.keys():
        if field_name.startswith("_"):
            continue

        if hasattr(schema_class, "__fields__"):
            field_info = schema_class.__fields__.get(field_name)
            if field_info:
                fields.append(extract_field_spec(field_name, field_info))
        elif field_name in annotations:
            # Fallback for simpler extraction
            fields.append(
                FieldSpec(
                    name=field_name,
                    dtype="object",
                    nullable=True,
                    description=None,
                    constraints={},
                )
            )

    # Extract config
    config: dict[str, Any] = {}
    if hasattr(schema_class, "Config"):
        config_class = schema_class.Config
        config["strict"] = getattr(config_class, "strict", False)
        config["coerce"] = getattr(config_class, "coerce", False)
        config["ordered"] = getattr(config_class, "ordered", False)

    return SchemaSpec(
        name=class_name,
        entity=entity,
        provider="chembl",
        fields=fields,
        column_order=column_order,
        config=config,
    )


def schema_spec_to_dict(spec: SchemaSpec) -> dict[str, Any]:
    """Convert SchemaSpec to dictionary for YAML export.

    Args:
        spec: Schema specification

    Returns:
        Dictionary representation
    """
    return {
        "schema": {
            "name": spec.name,
            "entity": spec.entity,
            "provider": spec.provider,
            "version": "1.0",
        },
        "config": spec.config,
        "column_order": spec.column_order,
        "fields": {
            field.name: {
                k: v
                for k, v in {
                    "dtype": field.dtype,
                    "nullable": field.nullable,
                    "description": field.description,
                    **field.constraints,
                }.items()
                if v is not None and v != {}
            }
            for field in spec.fields
        },
    }


def export_schema_yaml(entity: str, output_dir: Path) -> Path:
    """Export a single schema to YAML file.

    Args:
        entity: Entity name
        output_dir: Output directory

    Returns:
        Path to created YAML file
    """
    spec = extract_schema_spec(entity)
    data = schema_spec_to_dict(spec)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{entity}_schema.yaml"

    with output_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            data,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )

    return output_path


def export_all_schemas(output_dir: Path) -> list[Path]:
    """Export all schemas to YAML files.

    Args:
        output_dir: Output directory

    Returns:
        List of created file paths
    """
    paths: list[Path] = []
    for entity in SCHEMA_MODULES:
        path = export_schema_yaml(entity, output_dir)
        paths.append(path)
        print(f"Exported: {path}")
    return paths


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Export Pandera schemas to YAML format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("configs/schemas"),
        help="Output directory for YAML files (default: configs/schemas)",
    )
    parser.add_argument(
        "--entity",
        choices=list(SCHEMA_MODULES.keys()),
        help="Export only specific entity schema",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_entities",
        help="List available entities and exit",
    )

    args = parser.parse_args()

    if args.list_entities:
        print("Available entities:")
        for entity in SCHEMA_MODULES:
            print(f"  - {entity}")
        return 0

    try:
        if args.entity:
            path = export_schema_yaml(args.entity, args.output_dir)
            print(f"Exported: {path}")
        else:
            paths = export_all_schemas(args.output_dir)
            print(f"\nExported {len(paths)} schemas to {args.output_dir}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
