#!/usr/bin/env python3
"""Generate field-level cross-layer diagnostics for all entity pipelines."""

from __future__ import annotations

import argparse
import ast
import csv
import json
import re
from pathlib import Path
from typing import Any

from scripts.schema.generate_unified_schema_map import (
    build_unified_schema_rows,
)

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[2]
PUBLICATION_ALIAS_FILE = (
    PROJECT_ROOT / "src" / "bioetl" / "application" / "core" / "publication_aliases.py"
)
MOLECULE_ALIAS_FILE = (
    PROJECT_ROOT / "src" / "bioetl" / "domain" / "registry" / "field_aliases.py"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "quality" / "field_level_diagnostics.csv"

CSV_COLUMNS: tuple[str, ...] = (
    "provider",
    "entity",
    "field",
    "bronze_groups_json",
    "bronze_field_names_json",
    "silver_pyarrow_field_names_json",
    "silver_pandera_field_names_json",
    "gold_field_names_json",
    "silver_pyarrow_types_json",
    "silver_pandera_types_json",
    "gold_types_json",
    "silver_pyarrow_nullable_json",
    "silver_pandera_nullable_json",
    "gold_nullable_json",
    "type_inconsistency",
    "json_usage",
    "nullable_violation",
    "redundancy",
)


def _json_dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _normalize_pyarrow_type(type_name: str) -> str:
    lowered = type_name.lower()
    if "list_(" in lowered or "struct(" in lowered or "map_(" in lowered:
        return "object"
    if "string" in lowered:
        return "string"
    if "int" in lowered:
        return "integer"
    if "float" in lowered or "double" in lowered:
        return "number"
    if "bool" in lowered:
        return "boolean"
    return "object"


def _normalize_pandera_type(type_name: str) -> str:
    lowered = type_name.lower()
    if "list[" in lowered or "dict[" in lowered or "series[list" in lowered:
        return "object"
    if "series[str" in lowered or lowered == "str":
        return "string"
    if "int64dtype" in lowered or "series[int" in lowered or lowered.startswith("int"):
        return "integer"
    if "series[float" in lowered or lowered.startswith("float"):
        return "number"
    if "series[bool" in lowered or lowered == "bool":
        return "boolean"
    return "object"


def _normalize_gold_type(type_value: object) -> str:
    if isinstance(type_value, list):
        non_null = [item for item in type_value if item != "null"]
        if not non_null:
            return "object"
        return _normalize_gold_type(non_null[0])
    if isinstance(type_value, str):
        if type_value in {"string", "integer", "number", "boolean", "object", "array"}:
            return "object" if type_value == "array" else type_value
    return "object"


def _normalize_gold_nullable(type_value: object, nullable: object) -> bool:
    if isinstance(nullable, bool):
        return nullable
    if isinstance(type_value, list):
        return "null" in type_value
    return False


def _assignment_target(node: ast.stmt) -> tuple[str, ast.AST | None]:
    if isinstance(node, ast.Assign):
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            return node.targets[0].id, node.value
        return "", None
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id, node.value
    return "", None


def _string_dict_literal(node: ast.Dict) -> dict[str, str]:
    values: dict[str, str] = {}
    for key_node, value_node in zip(node.keys, node.values, strict=False):
        if (
            isinstance(key_node, ast.Constant)
            and isinstance(key_node.value, str)
            and isinstance(value_node, ast.Constant)
            and isinstance(value_node.value, str)
        ):
            values[key_node.value] = value_node.value
    return values


def _parse_publication_aliases() -> dict[str, str]:
    tree = ast.parse(PUBLICATION_ALIAS_FILE.read_text(encoding="utf-8"))
    for node in tree.body:
        target_name, value = _assignment_target(node)
        if target_name != "PUBLICATION_SCHEMA_FIELD_ALIASES":
            continue
        if not isinstance(value, ast.Dict):
            continue
        return _string_dict_literal(value)
    return {}


def _field_alias_payload(element: ast.AST) -> tuple[str, dict[str, str]] | None:
    if not isinstance(element, ast.Call):
        return None
    if not isinstance(element.func, ast.Name) or element.func.id != "FieldAlias":
        return None

    canonical_name = ""
    provider_aliases: dict[str, str] = {}
    for kw in element.keywords:
        if kw.arg == "canonical_name" and isinstance(kw.value, ast.Constant):
            if isinstance(kw.value.value, str):
                canonical_name = kw.value.value
        elif kw.arg == "provider_aliases" and isinstance(kw.value, ast.Dict):
            provider_aliases.update(_string_dict_literal(kw.value))

    if not canonical_name:
        return None
    return canonical_name, provider_aliases


def _record_provider_aliases(
    provider_maps: dict[str, dict[str, str]],
    *,
    canonical_name: str,
    provider_aliases: dict[str, str],
) -> None:
    for provider, provider_field in provider_aliases.items():
        if provider_field == canonical_name:
            continue
        provider_maps.setdefault(provider, {})[provider_field] = canonical_name


def _parse_molecule_aliases() -> dict[str, dict[str, str]]:
    tree = ast.parse(MOLECULE_ALIAS_FILE.read_text(encoding="utf-8"))
    provider_maps: dict[str, dict[str, str]] = {}
    for node in tree.body:
        target_name, value = _assignment_target(node)
        if target_name != "MOLECULE_FIELD_ALIASES":
            continue
        if not isinstance(value, ast.Tuple):
            continue
        for element in value.elts:
            payload = _field_alias_payload(element)
            if payload is None:
                continue
            canonical_name, provider_aliases = payload
            _record_provider_aliases(
                provider_maps,
                canonical_name=canonical_name,
                provider_aliases=provider_aliases,
            )
        break
    return provider_maps


PUBLICATION_ALIASES = _parse_publication_aliases()
MOLECULE_ALIASES = _parse_molecule_aliases()


def _alias_map(provider: str, entity: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    if entity == "publication":
        mapping.update(PUBLICATION_ALIASES)
    if entity in {"molecule", "compound"}:
        mapping.update(MOLECULE_ALIASES.get(provider, {}))
    return mapping


def _canonical_field(provider: str, entity: str, field_name: str) -> str:
    return _alias_map(provider, entity).get(field_name, field_name)


def _field_groups_for_name(
    bronze_groups: list[dict[str, Any]], field_name: str
) -> list[str]:
    matched: list[str] = []
    for group in bronze_groups:
        group_name = group.get("name")
        if not isinstance(group_name, str):
            continue
        fields = group.get("fields", [])
        if isinstance(fields, list) and field_name in fields:
            matched.append(group_name)
            continue
        pattern = group.get("pattern")
        if isinstance(pattern, str) and pattern:
            try:
                if re.search(pattern, field_name):
                    matched.append(group_name)
            except re.error:
                continue
    return matched


def _layer_row(
    provider: str,
    entity: str,
    field_name: str,
    record: dict[str, Any],
) -> dict[str, str]:
    return {
        "provider": provider,
        "entity": entity,
        "field": field_name,
        "bronze_groups_json": _json_dump(sorted(record["bronze_groups"])),
        "bronze_field_names_json": _json_dump(sorted(record["bronze_field_names"])),
        "silver_pyarrow_field_names_json": _json_dump(
            sorted(record["silver_pyarrow_field_names"])
        ),
        "silver_pandera_field_names_json": _json_dump(
            sorted(record["silver_pandera_field_names"])
        ),
        "gold_field_names_json": _json_dump(sorted(record["gold_field_names"])),
        "silver_pyarrow_types_json": _json_dump(sorted(record["silver_pyarrow_types"])),
        "silver_pandera_types_json": _json_dump(sorted(record["silver_pandera_types"])),
        "gold_types_json": _json_dump(sorted(record["gold_types"])),
        "silver_pyarrow_nullable_json": _json_dump(
            sorted(record["silver_pyarrow_nullable"])
        ),
        "silver_pandera_nullable_json": _json_dump(
            sorted(record["silver_pandera_nullable"])
        ),
        "gold_nullable_json": _json_dump(sorted(record["gold_nullable"])),
        "type_inconsistency": str(_type_inconsistency(record)).lower(),
        "json_usage": _json_usage(record),
        "nullable_violation": str(_nullable_violation(record)).lower(),
        "redundancy": str(_redundancy(record)).lower(),
    }


def _unified_row_payload(
    unified_row: dict[str, str],
) -> tuple[
    str,
    str,
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    provider = unified_row["provider"]
    entity = unified_row["entity"]
    bronze_groups = json.loads(unified_row["bronze_column_groups_json"])
    silver_pyarrow_fields = json.loads(unified_row["silver_pyarrow_fields_json"])
    silver_pandera_fields = json.loads(unified_row["silver_pandera_fields_json"])
    gold_properties = json.loads(unified_row["gold_json_contract"])["properties"]
    return (
        provider,
        entity,
        bronze_groups,
        silver_pyarrow_fields,
        silver_pandera_fields,
        gold_properties,
    )


def _ensure_diagnostic_record(
    diagnostics: dict[str, dict[str, Any]], canonical: str
) -> dict[str, Any]:
    if canonical not in diagnostics:
        diagnostics[canonical] = {
            "bronze_groups": set(),
            "bronze_field_names": set(),
            "silver_pyarrow_field_names": set(),
            "silver_pandera_field_names": set(),
            "gold_field_names": set(),
            "silver_pyarrow_types": set(),
            "silver_pandera_types": set(),
            "gold_types": set(),
            "silver_pyarrow_nullable": set(),
            "silver_pandera_nullable": set(),
            "gold_nullable": set(),
            "descriptions": [],
            "actual_names": set(),
        }
    return diagnostics[canonical]


def _add_bronze_fields(
    *,
    provider: str,
    entity: str,
    bronze_groups: list[dict[str, Any]],
    diagnostics: dict[str, dict[str, Any]],
) -> None:
    for group in bronze_groups:
        for field_name in group.get("fields", []):
            if not isinstance(field_name, str):
                continue
            canonical = _canonical_field(provider, entity, field_name)
            record = _ensure_diagnostic_record(diagnostics, canonical)
            record["bronze_field_names"].add(field_name)
            record["actual_names"].add(field_name)
            for group_name in _field_groups_for_name(bronze_groups, field_name):
                record["bronze_groups"].add(group_name)


def _add_pyarrow_fields(
    *,
    provider: str,
    entity: str,
    bronze_groups: list[dict[str, Any]],
    silver_pyarrow_fields: list[dict[str, Any]],
    diagnostics: dict[str, dict[str, Any]],
) -> None:
    for field in silver_pyarrow_fields:
        field_name = str(field.get("name", ""))
        if not field_name:
            continue
        canonical = _canonical_field(provider, entity, field_name)
        record = _ensure_diagnostic_record(diagnostics, canonical)
        record["silver_pyarrow_field_names"].add(field_name)
        record["actual_names"].add(field_name)
        record["silver_pyarrow_types"].add(
            _normalize_pyarrow_type(str(field.get("type", "")))
        )
        record["silver_pyarrow_nullable"].add(bool(field.get("nullable", True)))
        for group_name in _field_groups_for_name(bronze_groups, field_name):
            record["bronze_groups"].add(group_name)


def _add_pandera_fields(
    *,
    provider: str,
    entity: str,
    bronze_groups: list[dict[str, Any]],
    silver_pandera_fields: list[dict[str, Any]],
    diagnostics: dict[str, dict[str, Any]],
) -> None:
    for field in silver_pandera_fields:
        field_name = str(field.get("name", ""))
        if not field_name:
            continue
        canonical = _canonical_field(provider, entity, field_name)
        record = _ensure_diagnostic_record(diagnostics, canonical)
        record["silver_pandera_field_names"].add(field_name)
        record["actual_names"].add(field_name)
        record["silver_pandera_types"].add(
            _normalize_pandera_type(str(field.get("dtype", "")))
        )
        record["silver_pandera_nullable"].add(bool(field.get("nullable", False)))
        description = str(field.get("description", "")).strip()
        if description:
            record["descriptions"].append(description)
        for group_name in _field_groups_for_name(bronze_groups, field_name):
            record["bronze_groups"].add(group_name)


def _add_gold_fields(
    *,
    provider: str,
    entity: str,
    bronze_groups: list[dict[str, Any]],
    gold_properties: dict[str, dict[str, Any]],
    diagnostics: dict[str, dict[str, Any]],
) -> None:
    for field_name, prop in gold_properties.items():
        canonical = _canonical_field(provider, entity, field_name)
        record = _ensure_diagnostic_record(diagnostics, canonical)
        record["gold_field_names"].add(field_name)
        record["actual_names"].add(field_name)
        record["gold_types"].add(_normalize_gold_type(prop.get("type")))
        record["gold_nullable"].add(
            _normalize_gold_nullable(prop.get("type"), prop.get("nullable"))
        )
        description = str(prop.get("description", "")).strip()
        if description:
            record["descriptions"].append(description)
        for group_name in _field_groups_for_name(bronze_groups, field_name):
            record["bronze_groups"].add(group_name)


def _collect_layer_items(
    provider: str,
    entity: str,
    bronze_groups: list[dict[str, Any]],
    silver_pyarrow_fields: list[dict[str, Any]],
    silver_pandera_fields: list[dict[str, Any]],
    gold_properties: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    diagnostics: dict[str, dict[str, Any]] = {}
    _add_bronze_fields(
        provider=provider,
        entity=entity,
        bronze_groups=bronze_groups,
        diagnostics=diagnostics,
    )
    _add_pyarrow_fields(
        provider=provider,
        entity=entity,
        bronze_groups=bronze_groups,
        silver_pyarrow_fields=silver_pyarrow_fields,
        diagnostics=diagnostics,
    )
    _add_pandera_fields(
        provider=provider,
        entity=entity,
        bronze_groups=bronze_groups,
        silver_pandera_fields=silver_pandera_fields,
        diagnostics=diagnostics,
    )
    _add_gold_fields(
        provider=provider,
        entity=entity,
        bronze_groups=bronze_groups,
        gold_properties=gold_properties,
        diagnostics=diagnostics,
    )
    return diagnostics


def _json_usage(record: dict[str, Any]) -> str:
    all_types = (
        set(record["silver_pyarrow_types"])
        | set(record["silver_pandera_types"])
        | set(record["gold_types"])
    )
    descriptions = " ".join(record["descriptions"]).lower()
    actual_names = {str(name).lower() for name in record["actual_names"]}

    if "object" in all_types:
        return "object"
    if any(name.endswith("_json") for name in actual_names):
        return "canonical_string"
    if "json" in descriptions:
        return "canonical_string"
    return "none"


def _type_inconsistency(record: dict[str, Any]) -> bool:
    all_types = (
        set(record["silver_pyarrow_types"])
        | set(record["silver_pandera_types"])
        | set(record["gold_types"])
    )
    return len({item for item in all_types if item}) > 1


def _nullable_violation(record: dict[str, Any]) -> bool:
    all_flags = (
        set(record["silver_pyarrow_nullable"])
        | set(record["silver_pandera_nullable"])
        | set(record["gold_nullable"])
    )
    return len(all_flags) > 1


def _redundancy(record: dict[str, Any]) -> bool:
    return len(set(record["actual_names"])) > 1


def build_field_level_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for unified_row in build_unified_schema_rows():
        (
            provider,
            entity,
            bronze_groups,
            silver_pyarrow_fields,
            silver_pandera_fields,
            gold_properties,
        ) = _unified_row_payload(unified_row)

        diagnostics = _collect_layer_items(
            provider,
            entity,
            bronze_groups,
            silver_pyarrow_fields,
            silver_pandera_fields,
            gold_properties,
        )

        for field_name, record in sorted(diagnostics.items()):
            rows.append(_layer_row(provider, entity, field_name, record))

    rows.sort(key=lambda row: (row["provider"], row["entity"], row["field"]))
    return rows


def write_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    output_path = resolve_output_path(output_path, root=REPO_ROOT)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CSV_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate field-level diagnostics for Bronze→Silver→Gold schema drift."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output CSV path (default: {DEFAULT_OUTPUT.relative_to(PROJECT_ROOT)})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = args.output
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path

    rows = build_field_level_rows()
    write_csv(rows, output_path)
    print(f"Generated {_display_path(output_path)} with {len(rows)} field diagnostics.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
