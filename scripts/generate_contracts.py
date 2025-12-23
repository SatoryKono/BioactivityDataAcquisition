#!/usr/bin/env python3
"""
Generate JSON Schema contracts from Pandera models.
Usage: python scripts/generate_contracts.py
"""

import json
import sys
from pathlib import Path

# Ensure project root is in python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root / "src"))

try:
    from bioetl.infrastructure.schemas.gold import (
        ChEMBLActivityGoldSchema,
        PubChemCompoundGoldSchema,
        PubMedPublicationGoldSchema,
        UniProtProteinGoldSchema,
    )
except ImportError as e:
    print(f"Error importing schemas: {e}")
    sys.exit(1)

CONTRACTS_DIR = project_root / "docs" / "contracts"

ENTITY_SCHEMA_MAP = {
    "chembl_activity": ChEMBLActivityGoldSchema,
    "pubchem_compound": PubChemCompoundGoldSchema,
    "uniprot_protein": UniProtProteinGoldSchema,
    "pubmed_publication": PubMedPublicationGoldSchema,
}

def generate_contracts() -> None:
    CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)

    for entity, schema_cls in ENTITY_SCHEMA_MAP.items():
        print(f"Generating contract for {entity}...")
        try:
            # Generate JSON Schema
            json_schema = schema_cls.to_json_schema()

            # Save to file
            output_file = CONTRACTS_DIR / f"{entity}_gold.json"
            with output_file.open("w", encoding="utf-8") as f:
                json.dump(json_schema, f, indent=2)
            print(f"  -> Saved to {output_file}")

        except Exception as e:
            print(f"Failed to generate contract for {entity}: {e}")
            sys.exit(1)

    print("\nAll contracts generated successfully.")

if __name__ == "__main__":
    generate_contracts()
