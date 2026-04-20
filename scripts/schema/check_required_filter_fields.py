#!/usr/bin/env python3
"""Validate that silver filter required_fields cover explicitly required YAML fields.

Checks:
  INV-CFG-007  Every field already marked as required/not-null in quality config
               must be listed in filters.silver_filters.required_fields.

Usage:
    python scripts/schema/check_required_filter_fields.py [--verbose]

Exit codes:
    0 - All configs pass
    1 - Violations found
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIGS_DIR = PROJECT_ROOT / "configs"
ENTITIES_DIR = CONFIGS_DIR / "entities"

EXCLUDED_FIELDS: frozenset[str] = frozenset(
    {
        "entity_id",
        "content_hash",
        "_run_id",
        "_run_type",
        "_source_batch_id",
        "_ingestion_ts",
        "_index",
        "_dq_warn",
        "_dq_error",
        "_state",
    }
)


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _entity_configs() -> list[Path]:
    return sorted(
        path for path in ENTITIES_DIR.rglob("*.yaml") if not path.name.startswith("_")
    )


def _rel(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT))


def _included_field_name(field: object) -> str | None:
    if not isinstance(field, str) or field in EXCLUDED_FIELDS:
        return None
    return field


def _validation_requires_field(item: dict[str, Any]) -> bool:
    return item.get("type") in {"required", "not_null"} or item.get("nullable") is False


def _required_field_from_validation(item: object) -> str | None:
    if not isinstance(item, dict):
        return None
    field = _included_field_name(item.get("field"))
    if field is None or not _validation_requires_field(item):
        return None
    return field


def _required_field_from_key_nullability(item: object) -> str | None:
    if not isinstance(item, dict):
        return None
    field = _included_field_name(item.get("field"))
    if field is None or item.get("nullable") is not False:
        return None
    return field


def extract_expected_required_fields(config: dict[str, Any]) -> set[str]:
    """Collect explicit required fields already declared in the YAML config."""
    quality = config.get("quality")
    if not isinstance(quality, dict):
        return set()

    expected: set[str] = set()

    for item in quality.get("entity_field_validations") or []:
        if field := _required_field_from_validation(item):
            expected.add(field)

    for item in quality.get("key_nullability") or []:
        if field := _required_field_from_key_nullability(item):
            expected.add(field)

    return expected


def extract_silver_required_fields(config: dict[str, Any]) -> set[str]:
    """Collect filters.silver_filters.required_fields from YAML config."""
    filters = config.get("filters")
    if not isinstance(filters, dict):
        return set()
    silver_filters = filters.get("silver_filters")
    if not isinstance(silver_filters, dict):
        return set()
    required_fields = silver_filters.get("required_fields") or []
    return {
        field
        for field in required_fields
        if isinstance(field, str) and field not in EXCLUDED_FIELDS
    }


def collect_required_field_coverage_violations(
    config_paths: list[Path] | None = None,
) -> list[str]:
    """Return invariant violations for missing silver required fields."""
    violations: list[str] = []
    paths = config_paths if config_paths is not None else _entity_configs()

    for path in paths:
        config = _load_yaml(path)
        expected = extract_expected_required_fields(config)
        configured = extract_silver_required_fields(config)
        missing = sorted(expected - configured)
        if missing:
            violations.append(
                f"INV-CFG-007 {_rel(path)}: silver_filters.required_fields missing "
                f"{missing}; expected coverage for {sorted(expected)}"
            )

    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate that all explicit quality/key-nullability required fields "
            "are covered by filters.silver_filters.required_fields."
        )
    )
    parser.add_argument("--verbose", action="store_true", help="Print PASS summary")
    args = parser.parse_args(argv)

    violations = collect_required_field_coverage_violations()
    if violations:
        for violation in violations:
            print(violation, file=sys.stderr)
        return 1

    if args.verbose:
        print(
            "INV-CFG-007: PASS (silver required_fields cover explicit YAML requiredness)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
