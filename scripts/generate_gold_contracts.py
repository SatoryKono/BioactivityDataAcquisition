#!/usr/bin/env python3
"""Generate JSON Schema contracts from Pandera Gold schemas.

This script ensures that docs/contracts/gold/*.json files are always
synchronized with the Pandera source of truth in src/bioetl/domain/contracts/gold/.

Usage:
    python scripts/generate_gold_contracts.py [--check] [--verbose]

Options:
    --check     Check if contracts are up-to-date (exit 1 if changes needed)
    --verbose   Print detailed output

Exit codes:
    0 - Contracts generated/up-to-date
    1 - Contracts need regeneration (with --check)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bioetl.domain.contracts.gold.chembl import (
    ChEMBLActivityGoldSchema,
    ChEMBLAssayGoldSchema,
    ChEMBLAssayParametersGoldSchema,
    ChEMBLCellLineGoldSchema,
    ChEMBLCompoundRecordGoldSchema,
    ChEMBLDocumentGoldSchema,
    ChEMBLDocumentSimilarityGoldSchema,
    ChEMBLDocumentTermGoldSchema,
    ChEMBLMoleculeGoldSchema,
    ChEMBLProteinClassGoldSchema,
    ChEMBLTargetComponentGoldSchema,
    ChEMBLTargetGoldSchema,
)
from bioetl.domain.contracts.gold.pubchem import PubChemCompoundGoldSchema
from bioetl.domain.contracts.gold.publications import (
    CrossRefPublicationGoldSchema,
    OpenAlexPublicationGoldSchema,
    PubMedPublicationGoldSchema,
    SemanticScholarPublicationGoldSchema,
)
from bioetl.domain.contracts.gold.uniprot import (
    UniProtIDMappingGoldSchema,
    UniProtProteinGoldSchema,
)

# Mapping from Pandera schema class to output filename
SCHEMA_MAPPING = {
    # ChEMBL schemas
    ChEMBLActivityGoldSchema: "chembl_activity_v1.0.json",
    ChEMBLAssayGoldSchema: "chembl_assay_v1.0.json",
    ChEMBLAssayParametersGoldSchema: "chembl_assay_parameters_v1.0.json",
    ChEMBLCellLineGoldSchema: "chembl_cell_line_v1.0.json",
    ChEMBLCompoundRecordGoldSchema: "chembl_compound_record_v1.0.json",
    ChEMBLDocumentGoldSchema: "chembl_document_v1.0.json",
    ChEMBLDocumentSimilarityGoldSchema: "chembl_document_similarity_v1.0.json",
    ChEMBLDocumentTermGoldSchema: "chembl_document_term_v1.0.json",
    ChEMBLMoleculeGoldSchema: "chembl_molecule_v1.0.json",
    ChEMBLProteinClassGoldSchema: "chembl_protein_class_v1.0.json",
    ChEMBLTargetGoldSchema: "chembl_target_v1.0.json",
    ChEMBLTargetComponentGoldSchema: "chembl_target_component_v1.0.json",
    # Publication schemas
    CrossRefPublicationGoldSchema: "crossref_publication_v1.0.json",
    OpenAlexPublicationGoldSchema: "openalex_publication_v1.0.json",
    PubMedPublicationGoldSchema: "pubmed_publication_v1.0.json",
    SemanticScholarPublicationGoldSchema: "semanticscholar_publication_v1.0.json",
    # PubChem schemas
    PubChemCompoundGoldSchema: "pubchem_compound_v1.0.json",
    # UniProt schemas
    UniProtIDMappingGoldSchema: "uniprot_idmapping_v1.0.json",
    UniProtProteinGoldSchema: "uniprot_protein_v1.0.json",
}

# Schema name to display name mapping (handles complex cases like ChEMBL)
SCHEMA_DISPLAY_NAMES = {
    "ChEMBLActivityGoldSchema": ("ChEMBL", "Activity"),
    "ChEMBLAssayGoldSchema": ("ChEMBL", "Assay"),
    "ChEMBLAssayParametersGoldSchema": ("ChEMBL", "Assay Parameters"),
    "ChEMBLCellLineGoldSchema": ("ChEMBL", "Cell Line"),
    "ChEMBLCompoundRecordGoldSchema": ("ChEMBL", "Compound Record"),
    "ChEMBLDocumentGoldSchema": ("ChEMBL", "Document"),
    "ChEMBLDocumentSimilarityGoldSchema": ("ChEMBL", "Document Similarity"),
    "ChEMBLDocumentTermGoldSchema": ("ChEMBL", "Document Term"),
    "ChEMBLMoleculeGoldSchema": ("ChEMBL", "Molecule"),
    "ChEMBLProteinClassGoldSchema": ("ChEMBL", "Protein Class"),
    "ChEMBLTargetGoldSchema": ("ChEMBL", "Target"),
    "ChEMBLTargetComponentGoldSchema": ("ChEMBL", "Target Component"),
    "CrossRefPublicationGoldSchema": ("CrossRef", "Publication"),
    "OpenAlexPublicationGoldSchema": ("OpenAlex", "Publication"),
    "PubMedPublicationGoldSchema": ("PubMed", "Publication"),
    "SemanticScholarPublicationGoldSchema": ("Semantic Scholar", "Publication"),
    "PubChemCompoundGoldSchema": ("PubChem", "Compound"),
    "UniProtIDMappingGoldSchema": ("UniProt", "ID Mapping"),
    "UniProtProteinGoldSchema": ("UniProt", "Protein"),
}


def dtype_to_json_type(dtype: Any) -> str:
    """Convert Pandera dtype to JSON Schema type.

    Args:
        dtype: Pandera column dtype (e.g., str, float64, int64, bool)

    Returns:
        JSON Schema type string
    """
    dtype_str = str(dtype).lower()

    if dtype_str in ("str", "string", "object"):
        return "string"
    elif dtype_str in ("float64", "float32", "float", "number"):
        return "number"
    elif dtype_str in ("int64", "int32", "int", "integer"):
        return "integer"
    elif dtype_str in ("bool", "boolean"):
        return "boolean"
    else:
        # Default to string for unknown types
        return "string"


def pandera_field_to_json_schema(col_info: Any) -> dict[str, Any]:
    """Convert a Pandera column to JSON Schema property definition.

    Args:
        col_info: Pandera column from schema.columns dict

    Returns:
        JSON Schema property definition
    """
    # Get type from dtype
    json_type = dtype_to_json_type(col_info.dtype)

    prop: dict[str, Any] = {}

    # Determine if nullable
    nullable = getattr(col_info, "nullable", False)

    # Set type (with null if nullable)
    if nullable:
        prop["type"] = [json_type, "null"]
    else:
        prop["type"] = json_type

    # Handle array types (object dtype → array in JSON Schema)
    if json_type == "array":
        prop["items"] = {"type": "string"}  # Default to string items

    # Add constraints from Pandera checks
    checks = getattr(col_info, "checks", []) or []
    for check in checks:
        check_name = getattr(check, "name", "")
        stats = getattr(check, "statistics", {}) or {}

        if check_name == "greater_than_or_equal_to" and "min_value" in stats:
            prop["minimum"] = stats["min_value"]
        elif check_name == "less_than_or_equal_to" and "max_value" in stats:
            prop["maximum"] = stats["max_value"]
        elif check_name == "str_matches" and "pattern" in stats:
            prop["pattern"] = stats["pattern"]
        elif check_name == "isin" and "allowed_values" in stats:
            prop["enum"] = list(stats["allowed_values"])

    return prop


def pandera_schema_to_json_schema(schema_class: type) -> dict[str, Any]:
    """Convert a Pandera DataFrameModel to JSON Schema."""
    schema_name = schema_class.__name__

    # Get display names from mapping
    if schema_name in SCHEMA_DISPLAY_NAMES:
        provider_display, entity_display = SCHEMA_DISPLAY_NAMES[schema_name]
        title = f"{provider_display} {entity_display} Gold Contract"
    else:
        title = f"{schema_name} Gold Contract"

    json_schema: dict[str, Any] = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$version": "1.0.0",
        "title": title,
        "description": (
            f"Gold layer data contract for {title}. "
            f"Auto-generated from Pandera schema {schema_name}."
        ),
        "type": "object",
        "properties": {},
        "required": [],
    }

    # Get the actual schema to access column definitions
    # The schema.columns dict has the correct column names (including aliases)
    schema = schema_class.to_schema()
    columns = schema.columns

    for col_name, col_info in columns.items():
        # Convert to JSON Schema property
        prop = pandera_field_to_json_schema(col_info)
        json_schema["properties"][col_name] = prop

        # Add to required if not nullable
        nullable = getattr(col_info, "nullable", False)
        if not nullable:
            json_schema["required"].append(col_name)

    # Sort required for consistency
    json_schema["required"].sort()

    return json_schema


def generate_all_contracts(
    output_dir: Path,
    check_only: bool = False,
    verbose: bool = False,
) -> tuple[int, int, int]:
    """Generate all JSON Schema contracts from Pandera schemas.

    Returns:
        Tuple of (generated_count, unchanged_count, error_count)
    """
    generated = 0
    unchanged = 0
    errors = 0

    output_dir.mkdir(parents=True, exist_ok=True)

    for schema_class, filename in SCHEMA_MAPPING.items():
        output_path = output_dir / filename

        try:
            json_schema = pandera_schema_to_json_schema(schema_class)

            # Pretty-print JSON
            new_content = json.dumps(json_schema, indent=2) + "\n"

            # Check if file exists and content differs
            if output_path.exists():
                existing_content = output_path.read_text()
                if existing_content == new_content:
                    unchanged += 1
                    if verbose:
                        print(f"  [unchanged] {filename}")
                    continue

            if check_only:
                print(f"  [outdated] {filename}")
                generated += 1
            else:
                output_path.write_text(new_content)
                print(f"  [generated] {filename}")
                generated += 1

        except Exception as e:
            print(f"  [error] {filename}: {e}", file=sys.stderr)
            errors += 1

    return generated, unchanged, errors


def cleanup_obsolete_contracts(output_dir: Path, verbose: bool = False) -> list[str]:
    """Find contracts that don't correspond to any Pandera schema.

    Returns:
        List of obsolete filenames
    """
    expected_files = set(SCHEMA_MAPPING.values())
    actual_files = {f.name for f in output_dir.glob("*.json")}

    obsolete = actual_files - expected_files
    return list(obsolete)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate JSON Schema contracts from Pandera Gold schemas"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if contracts are up-to-date (exit 1 if changes needed)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed output",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Remove obsolete contract files",
    )
    args = parser.parse_args()

    output_dir = Path(__file__).parent.parent / "docs" / "contracts" / "gold"

    print(f"Gold Contract Generator")
    print(f"Output directory: {output_dir}")
    print(f"Source: src/bioetl/domain/contracts/gold/")
    print()

    if args.check:
        print("Mode: Check (dry-run)")
    else:
        print("Mode: Generate")
    print()

    # Find obsolete contracts
    obsolete = cleanup_obsolete_contracts(output_dir, args.verbose)
    if obsolete:
        print(f"Obsolete contracts found ({len(obsolete)}):")
        for f in sorted(obsolete):
            print(f"  - {f}")
        if args.cleanup and not args.check:
            for f in obsolete:
                (output_dir / f).unlink()
                print(f"  [deleted] {f}")
        print()

    # Generate/check contracts
    print(f"Processing {len(SCHEMA_MAPPING)} schemas...")
    generated, unchanged, errors = generate_all_contracts(
        output_dir,
        check_only=args.check,
        verbose=args.verbose,
    )

    print()
    print(f"Results:")
    print(f"  Generated/Updated: {generated}")
    print(f"  Unchanged: {unchanged}")
    print(f"  Errors: {errors}")

    if args.check and (generated > 0 or obsolete):
        print()
        print("Contracts are out of date. Run without --check to regenerate.")
        return 1

    if errors > 0:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
