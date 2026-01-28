#!/usr/bin/env python3
"""
Metadata Audit Script for BioETL.

Identifies all pipelines, extracts metadata schemas (Silver/Gold),
and generates a reference document.
"""

import importlib
import inspect
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

import yaml

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

import pandera
import pandera.pandas as pa

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DOCS_OUTPUT = "docs/audits/metadata_audit_2026_jan.md"

# Manual mapping for known discrepancies between entity_type and schema module
SCHEMA_MAPPING = {
    ("chembl", "document"): "bioetl.domain.schemas.chembl.publication",
    ("chembl", "document_similarity"): "bioetl.domain.schemas.chembl.publication_similarity",
    ("chembl", "document_term"): "bioetl.domain.schemas.chembl.publication_term",
    ("chembl", "protein_class"): "bioetl.domain.schemas.chembl.protein_classification",
    ("pubmed", "publication"): "bioetl.domain.schemas.pubmed.article",
}

def load_pipeline_configs(root_path: str = "configs/pipelines") -> List[Dict[str, Any]]:
    """Finds and loads all pipeline configurations."""
    pipelines = []
    root = Path(root_path)

    for path in root.rglob("*.yaml"):
        if path.name.startswith("_") or "composite" in str(path):
            continue

        try:
            with open(path, "r") as f:
                config = yaml.safe_load(f)

            if not config or "provider" not in config or "entity_type" not in config:
                continue

            pipelines.append({
                "path": str(path),
                "provider": config["provider"],
                "entity": config["entity_type"],
                "name": config.get("pipeline_name", f"{config['provider']}_{config['entity_type']}")
            })
        except Exception as e:
            logger.warning(f"Failed to load config {path}: {e}")

    return sorted(pipelines, key=lambda x: (x["provider"], x["entity"]))

def get_schema_class(provider: str, entity: str) -> Optional[Type[pa.DataFrameModel]]:
    """Dynamically loads the schema class for a provider/entity."""
    # Try mapping first
    if (provider, entity) in SCHEMA_MAPPING:
        module_name = SCHEMA_MAPPING[(provider, entity)]
    else:
        module_name = f"bioetl.domain.schemas.{provider}.{entity}"

    try:
        module = importlib.import_module(module_name)
    except ImportError:
        # Try plural/singular variations if direct import fails
        try:
             module_name_s = f"bioetl.domain.schemas.{provider}.{entity}s"
             module = importlib.import_module(module_name_s)
        except ImportError:
            logger.warning(f"Could not import module {module_name}")
            return None

    # Find schema class: ends with 'Schema' and inherits from DataFrameModel
    # We prioritize specific ones over generic ones
    candidates = []
    for name, obj in inspect.getmembers(module):
        if (inspect.isclass(obj) and
            issubclass(obj, pa.DataFrameModel) and
            name.endswith("Schema") and
            name != "ETLRecordSchema"): # Skip base class if specific one exists
            candidates.append(obj)

    if not candidates:
        return None

    # Return the one that matches EntitySchema convention best
    expected_name = f"{entity.capitalize()}Schema"
    for cand in candidates:
        if cand.__name__ == expected_name:
            return cand

    # Fallback to the first one found
    return candidates[0]

def extract_schema_fields(schema_cls: Type[pa.DataFrameModel]) -> List[Dict[str, Any]]:
    """Extracts field metadata from a Pandera schema."""
    fields = []

    # Access the underlying schema model
    try:
        # pandera 0.18+ might differ, but generally schema_model is accessible
        # We iterate over type hints or __annotations__ or use to_schema().columns

        # Using to_schema() to get the actual Schema object
        schema_obj = schema_cls.to_schema()

        for col_name, col in schema_obj.columns.items():
            field_meta = {
                "name": col_name,
                "type": str(col.dtype),
                "nullable": col.nullable,
                "description": col.description or "",
                "checks": []
            }

            # Extract checks
            for check in col.checks:
                field_meta["checks"].append(str(check))

            fields.append(field_meta)

    except Exception as e:
        logger.error(f"Error extracting fields from {schema_cls}: {e}")

    return fields

def generate_markdown(audit_data: List[Dict[str, Any]]) -> str:
    """Generates a Markdown report from the audit data."""
    md = ["# Metadata Audit: BioETL Pipelines\n"]
    from datetime import UTC, datetime
    md.append(f"Generated on: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
    md.append("## Executive Summary\n")
    md.append(f"Total Pipelines: {len(audit_data)}\n")

    # Table of Contents
    md.append("\n## Table of Contents")
    for item in audit_data:
        anchor = f"{item['provider']}-{item['entity']}".lower()
        md.append(f"- [{item['provider'].upper()} / {item['entity']}: {item['name']}](#{anchor})")

    md.append("\n---\n")

    # Details
    for item in audit_data:
        anchor = f"{item['provider']}-{item['entity']}".lower()
        md.append(f"## {item['provider'].upper()} / {item['entity']}: {item['name']} <a name='{anchor}'></a>\n")
        md.append(f"- **Config**: `{item['path']}`")

        if not item.get("schema_found"):
            md.append("\n**⚠️ Warning: No Schema Class Found**\n")
            continue

        schema_name = item['schema_class']
        md.append(f"- **Schema Class**: `{schema_name}`")

        md.append("\n### Field Specifications (Silver/Gold)\n")
        md.append("| Field | Type | Nullable | Description | Constraints |")
        md.append("|---|---|---|---|---|")

        for field in item['fields']:
            checks = "<br>".join(field['checks']) if field['checks'] else "-"
            md.append(f"| `{field['name']}` | `{field['type']}` | {field['nullable']} | {field['description']} | {checks} |")

        md.append("\n[Back to Top](#table-of-contents)\n")
        md.append("\n---\n")

    return "\n".join(md)

def main():
    pipelines = load_pipeline_configs()
    audit_data = []

    for p in pipelines:
        logger.info(f"Processing {p['provider']}/{p['entity']}...")
        schema_cls = get_schema_class(p['provider'], p['entity'])

        p_data = p.copy()
        if schema_cls:
            p_data["schema_found"] = True
            p_data["schema_class"] = schema_cls.__name__
            p_data["fields"] = extract_schema_fields(schema_cls)
        else:
            p_data["schema_found"] = False
            p_data["fields"] = []

        audit_data.append(p_data)

    md_content = generate_markdown(audit_data)

    # Ensure directory exists
    os.makedirs(os.path.dirname(DOCS_OUTPUT), exist_ok=True)

    with open(DOCS_OUTPUT, "w") as f:
        f.write(md_content)

    logger.info(f"Audit report written to {DOCS_OUTPUT}")

if __name__ == "__main__":
    main()
