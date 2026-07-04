#!/usr/bin/env python3
"""Validate unified entity configs (`configs/entities/**/*.yaml`)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

REQUIRED_ENTITY_TOP_LEVEL = {
    "version",
    "provider",
    "entity",
    "pipeline",
    "schema",
    "quality",
    "filters",
    "contracts",
}
REQUIRED_PIPELINE_KEYS = {
    "pipeline_name",
    "provider",
    "entity_type",
    "business_primary_keys",
}


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else {}


def validate_entity_config(path: Path, entities_dir: Path) -> list[str]:
    """Validate unified entity config structure and return errors."""
    errors: list[str] = []
    config = _load_yaml(path)
    if not config:
        return [f"{path}: Empty or non-mapping config"]

    rel_path = path.relative_to(entities_dir)

    missing_top = REQUIRED_ENTITY_TOP_LEVEL - set(config.keys())
    if missing_top:
        errors.append(f"{rel_path}: Missing top-level keys: {sorted(missing_top)}")

    pipeline = config.get("pipeline", {})
    if not isinstance(pipeline, dict):
        errors.append(f"{rel_path}: 'pipeline' must be a mapping")
    else:
        missing_pipeline = REQUIRED_PIPELINE_KEYS - set(pipeline.keys())
        if missing_pipeline:
            errors.append(
                f"{rel_path}: Missing pipeline keys: {sorted(missing_pipeline)}"
            )
        if pipeline.get("provider") != config.get("provider"):
            errors.append(
                f"{rel_path}: provider mismatch ({config.get('provider')} != {pipeline.get('provider')})"
            )
        if pipeline.get("entity_type") != config.get("entity"):
            errors.append(
                f"{rel_path}: entity mismatch ({config.get('entity')} != {pipeline.get('entity_type')})"
            )

    contracts = config.get("contracts", {})
    if isinstance(contracts, dict):
        if "primary_key" not in contracts or "merge_keys" not in contracts:
            errors.append(
                f"{rel_path}: contracts must contain primary_key and merge_keys"
            )
    else:
        errors.append(f"{rel_path}: 'contracts' must be a mapping")

    return errors


def main() -> int:
    """Validate all unified entity configs."""
    entities_dir = Path("configs/entities")
    if not entities_dir.exists():
        print("ERROR: configs/entities not found")
        return 1

    all_errors: list[str] = []
    validated = 0

    print("=" * 80)
    print("UNIFIED CONFIG VALIDATION REPORT")
    print("=" * 80)
    print()

    for yaml_file in sorted(entities_dir.rglob("*.yaml")):
        if yaml_file.name.startswith("_"):
            continue
        errors = validate_entity_config(yaml_file, entities_dir)
        validated += 1

        rel_path = yaml_file.relative_to(entities_dir)
        if errors:
            for err in errors:
                all_errors.append(err)
                print(f"[ERROR] {err}")
        else:
            print(f"[OK] {rel_path}")

    print()
    print("=" * 80)
    print(f"Configs validated: {validated}")
    print(f"Total errors: {len(all_errors)}")
    print("=" * 80)

    if all_errors:
        print("\nValidation FAILED")
        return 1

    print("\nValidation PASSED: unified entity configs are consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
