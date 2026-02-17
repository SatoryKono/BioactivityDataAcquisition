#!/usr/bin/env python3
"""Verify Silver schema contract snapshots are in sync."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast


@dataclass(frozen=True)
class FieldChange:
    """Represents a field-level schema change."""

    schema_name: str
    field_name: str
    attribute: str
    expected: str
    actual: str


def _load_schema_registry() -> tuple[dict[str, Any], Callable[[Any], dict[str, Any]]]:
    """Load schema registry utilities from test contract module."""
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    module = importlib.import_module("tests.contract.silver_schemas.conftest")
    schemas = cast(dict[str, Any], module.SILVER_SCHEMAS)
    extractor = cast(Callable[[Any], dict[str, Any]], module.extract_field_metadata)
    return schemas, extractor


def _write_line(text: str) -> None:
    """Write a line to stdout."""
    sys.stdout.write(f"{text}\n")


def _canonicalize(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Normalize snapshot representation for stable comparison."""
    canonical = json.loads(json.dumps(snapshot, sort_keys=True, ensure_ascii=False))
    return cast(dict[str, Any], canonical)


def _load_snapshot(path: Path) -> dict[str, Any] | None:
    """Load an existing snapshot file, if present."""
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as handle:
        loaded = json.load(handle)
    return cast(dict[str, Any], loaded)


def _generate_snapshot(
    schema_name: str,
    schemas: dict[str, Any],
    extractor: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    """Generate snapshot metadata for a schema."""
    schema_cls = schemas[schema_name]
    return extractor(schema_cls)


def _collect_diffs(
    schema_name: str, expected: dict[str, Any], actual: dict[str, Any]
) -> dict[str, list[FieldChange] | list[str]]:
    """Collect field-level differences grouped by requested dimensions."""
    expected_fields = set(expected.keys())
    actual_fields = set(actual.keys())

    added = sorted(actual_fields - expected_fields)
    removed = sorted(expected_fields - actual_fields)

    type_changes: list[FieldChange] = []
    nullable_changes: list[FieldChange] = []
    description_changes: list[FieldChange] = []

    for field_name in sorted(expected_fields & actual_fields):
        expected_field = expected[field_name]
        actual_field = actual[field_name]

        if expected_field.get("dtype") != actual_field.get("dtype"):
            type_changes.append(
                FieldChange(
                    schema_name=schema_name,
                    field_name=field_name,
                    attribute="type",
                    expected=str(expected_field.get("dtype")),
                    actual=str(actual_field.get("dtype")),
                )
            )

        if expected_field.get("nullable") != actual_field.get("nullable"):
            nullable_changes.append(
                FieldChange(
                    schema_name=schema_name,
                    field_name=field_name,
                    attribute="nullable",
                    expected=str(expected_field.get("nullable")),
                    actual=str(actual_field.get("nullable")),
                )
            )

        if expected_field.get("description") != actual_field.get("description"):
            description_changes.append(
                FieldChange(
                    schema_name=schema_name,
                    field_name=field_name,
                    attribute="description",
                    expected=str(expected_field.get("description", "")),
                    actual=str(actual_field.get("description", "")),
                )
            )

    return {
        "name": [
            *[f"+ {field}" for field in added],
            *[f"- {field}" for field in removed],
        ],
        "type": type_changes,
        "nullable": nullable_changes,
        "description": description_changes,
    }


def _render_summary(diffs_by_schema: dict[str, dict[str, list[Any]]]) -> str:
    """Render a human-readable diff summary grouped by field attributes."""
    lines: list[str] = [
        "Silver contract snapshot diff detected.",
        "Grouped summary (name/type/nullable/description):",
    ]

    for schema_name in sorted(diffs_by_schema):
        schema_diffs = diffs_by_schema[schema_name]
        lines.append(f"\nSchema: {schema_name}")

        name_changes = schema_diffs["name"]
        lines.append("  name:")
        if name_changes:
            for item in name_changes:
                lines.append(f"    {item}")
        else:
            lines.append("    (no changes)")

        for key in ["type", "nullable", "description"]:
            raw_changes = schema_diffs[key]
            changes = [
                change for change in raw_changes if isinstance(change, FieldChange)
            ]
            lines.append(f"  {key}:")
            if changes:
                for change in changes:
                    lines.append(
                        f"    {change.field_name}: expected={change.expected!r}, actual={change.actual!r}"
                    )
            else:
                lines.append("    (no changes)")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Verify Silver schema contract snapshots are up to date."
    )
    parser.add_argument(
        "--snapshot-dir",
        default="tests/contract/silver_schemas/snapshots",
        help="Directory with tracked snapshot JSON files.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write regenerated snapshots to tracked files instead of checking only.",
    )
    return parser.parse_args()


def main() -> int:
    """Run verification/export flow."""
    args = parse_args()
    schemas, extractor = _load_schema_registry()

    snapshot_dir = Path(args.snapshot_dir)
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    diffs: dict[str, dict[str, list[Any]]] = {}

    for schema_name in sorted(schemas.keys()):
        generated = _canonicalize(_generate_snapshot(schema_name, schemas, extractor))
        snapshot_path = snapshot_dir / f"{schema_name}_schema.json"

        if args.write:
            with snapshot_path.open("w", encoding="utf-8") as handle:
                json.dump(
                    generated, handle, indent=2, sort_keys=True, ensure_ascii=False
                )
                handle.write("\n")

        tracked = _load_snapshot(snapshot_path)
        if tracked is None:
            diffs[schema_name] = {
                "name": ["snapshot file missing"],
                "type": [],
                "nullable": [],
                "description": [],
            }
            continue

        tracked_canonical = _canonicalize(tracked)
        if tracked_canonical != generated:
            diffs[schema_name] = _collect_diffs(
                schema_name=schema_name,
                expected=tracked_canonical,
                actual=generated,
            )

    if diffs:
        _write_line(_render_summary(diffs))
        _write_line(
            "\nRun `python scripts/verify_silver_contract_snapshots.py --write` and commit updates."
        )
        return 1

    _write_line("Silver contract snapshots are up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
