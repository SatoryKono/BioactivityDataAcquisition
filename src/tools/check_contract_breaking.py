#!/usr/bin/env python3
"""
Tool to check for breaking changes in Data Contracts.

Compares current runtime Pandera schemas (Gold) against published JSON schemas
in docs/contracts/ to detect:
- Field removals (Breaking)
- Type changes (Breaking)
- Nullability tightening (Optional -> Required) (Breaking)
- New mandatory fields (Breaking)

Usage:
    python src/tools/check_contract_breaking.py
"""
import sys
import json
import logging
from pathlib import Path
from typing import Any, Dict

from bioetl.infrastructure.schemas import gold as gold_schemas

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

CONTRACTS_DIR = Path("docs/contracts/gold")


def load_json_schema(entity_name: str) -> Dict[str, Any] | None:
    """Load published JSON schema for an entity."""
    path = CONTRACTS_DIR / f"{entity_name}.json"
    if not path.exists():
        return None
    with path.open() as f:
        return json.load(f)


def get_pandera_schema(schema_cls: Any) -> Dict[str, Any]:
    """Convert Pandera schema class to JSON Schema dict."""
    # Pandera models have a .to_json_schema() method
    return schema_cls.to_json_schema()


def compare_schemas(current: Dict[str, Any], published: Dict[str, Any]) -> list[str]:
    """Compare schemas and return list of breaking changes."""
    errors = []

    current_props = current.get("properties", {})
    published_props = published.get("properties", {})

    current_required = set(current.get("required", []))
    published_required = set(published.get("required", []))

    # 1. Check for removed fields
    for field in published_props:
        if field not in current_props:
            errors.append(f"Field '{field}' removed (Breaking)")

    # 2. Check for type changes
    for field, pub_def in published_props.items():
        if field in current_props:
            curr_def = current_props[field]
            # Simple type check (can be expanded)
            if pub_def.get("type") != curr_def.get("type"):
                errors.append(
                    f"Field '{field}' type changed: {pub_def.get('type')} -> {curr_def.get('type')} (Breaking)"
                )

    # 3. Check for new mandatory fields
    for field in current_required:
        if field not in published_required:
            # If it's a new field, it must be optional.
            # If it was existing optional and became required, it's breaking.
            if field not in published_props:
                 errors.append(f"New mandatory field '{field}' added (Breaking)")
            else:
                 errors.append(f"Field '{field}' became mandatory (Breaking)")

    return errors


def main() -> int:
    """Main execution."""
    if not CONTRACTS_DIR.exists():
        logger.warning(f"Contracts directory {CONTRACTS_DIR} not found. Skipping check.")
        return 0

    violations = []

    # Iterate over classes in gold_schemas module
    for name, obj in vars(gold_schemas).items():
        # Check if it's a Pandera model (has to_json_schema)
        if hasattr(obj, "to_json_schema") and isinstance(obj, type):
            # Infer entity name from class name (e.g. ActivitySchema -> activity)
            entity_name = name.lower().replace("schema", "")

            published = load_json_schema(entity_name)
            if not published:
                logger.info(f"No published contract for {name} ({entity_name}). Skipping.")
                continue

            current = get_pandera_schema(obj)
            errors = compare_schemas(current, published)

            if errors:
                violations.append(f"Contract violation for {name}:")
                violations.extend([f"  - {e}" for e in errors])
            else:
                logger.info(f"Contract valid: {name}")

    if violations:
        logger.error("Breaking changes detected in Data Contracts:")
        for v in violations:
            logger.error(v)
        return 1

    logger.info("All contracts valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
