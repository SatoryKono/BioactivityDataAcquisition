#!/usr/bin/env python3
"""Generate deterministic per-field transformation specs for Bronze→Silver→Gold."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

import yaml

from scripts.schema.analysis.generate_field_level_diagnostics import (
    build_field_level_rows,
)
from scripts.schema.analysis.generate_unified_schema_map import (
    build_unified_schema_rows,
)

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[3]
DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "quality" / "field_transformation_spec.csv"

CSV_COLUMNS: tuple[str, ...] = (
    "provider",
    "entity",
    "field",
    "layer_transition",
    "current_type",
    "target_type",
    "casting_rules_json",
    "cleaning_rules_json",
    "formatting_rules_json",
    "validation_rules_json",
    "rules_json",
    "deterministic",
    "affects_hash",
)


def _json_dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _parse_json_list(value: str) -> list[str]:
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed if isinstance(item, (str, bool, int, float))]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _canonical_type(values: list[str]) -> str:
    normalized = sorted({value for value in values if value})
    if not normalized:
        return "unknown"
    if len(normalized) == 1:
        return normalized[0]
    return f"mixed[{','.join(normalized)}]"


def _silver_type(row: dict[str, str]) -> str:
    return _canonical_type(
        _parse_json_list(row["silver_pyarrow_types_json"])
        + _parse_json_list(row["silver_pandera_types_json"])
    )


def _gold_type(row: dict[str, str]) -> str:
    return _canonical_type(_parse_json_list(row["gold_types_json"]))


def _is_json_field(row: dict[str, str]) -> bool:
    return row["json_usage"] in {"object", "canonical_string"}


def _is_doi_field(field_name: str) -> bool:
    lowered = field_name.lower()
    return lowered == "doi" or lowered.endswith("_doi") or "doi_" in lowered


def _is_pmid_field(field_name: str) -> bool:
    lowered = field_name.lower()
    return lowered == "pmid" or lowered.endswith("_pmid") or "pmid_" in lowered


def _is_date_field(field_name: str) -> bool:
    lowered = field_name.lower()
    return bool(
        re.search(
            r"(^|_)(date|datetime|timestamp|published|updated|created|ingestion_ts|ts)($|_)",
            lowered,
        )
    )


def _normalized_target_type(
    field_name: str, base_type: str, row: dict[str, str]
) -> str:
    if _is_json_field(row):
        return "string"
    if (
        _is_doi_field(field_name)
        or _is_pmid_field(field_name)
        or _is_date_field(field_name)
    ):
        return "string"
    return base_type


def _cast_rule_for_type(target_type: str) -> str | None:
    if target_type == "string":
        return "cast_to_string"
    if target_type == "integer":
        return "cast_to_integer"
    if target_type == "number":
        return "cast_to_number"
    if target_type == "boolean":
        return "cast_to_boolean"
    if target_type == "object":
        return "cast_to_object"
    return None


def _build_rules(
    field_name: str,
    row: dict[str, str],
    current_type: str,
    target_type: str,
) -> dict[str, list[str]]:
    casting: list[str] = []
    cleaning: list[str] = ["trim"]
    formatting: list[str] = ["normalize_casing"]
    validation: list[str] = ["conforms_to_target_type"]

    cast_rule = _cast_rule_for_type(target_type)
    if cast_rule and current_type != target_type:
        casting.append(cast_rule)

    if _is_json_field(row):
        casting.append("json_to_canonical_json_string")
        formatting.append("canonical_json_string")
        validation.extend(["json_serializable", "json_roundtrip_safe"])

    if _is_doi_field(field_name):
        cleaning.append("remove_doi_prefix")
        formatting.append("lowercase")
        validation.append("doi_normalized")

    if _is_pmid_field(field_name):
        cleaning.append("digits_only")
        validation.append("pmid_digits_only")

    if _is_date_field(field_name):
        formatting.append("iso_8601")
        validation.append("valid_iso_8601")

    return {
        "casting": _dedupe(casting),
        "cleaning": _dedupe(cleaning),
        "formatting": _dedupe(formatting),
        "validation": _dedupe(validation),
    }


def _load_entity_configs() -> dict[tuple[str, str], dict[str, Any]]:
    configs: dict[tuple[str, str], dict[str, Any]] = {}
    for row in build_unified_schema_rows():
        provider = row["provider"]
        entity = row["entity"]
        config_path = PROJECT_ROOT / row["config_path"]
        configs[(provider, entity)] = yaml.safe_load(
            config_path.read_text(encoding="utf-8")
        )
    return configs


def _hash_sets(config: dict[str, Any]) -> dict[str, set[str]]:
    pipeline = config.get("pipeline", {})
    schema = config.get("schema", {})
    contracts = config.get("contracts", {})
    hash_policy_root = config.get("hash_policy", {})
    hash_policy = (
        hash_policy_root.get("hash_policy", {})
        if isinstance(hash_policy_root, dict)
        else {}
    )
    content_hash = schema.get("content_hash", {}) if isinstance(schema, dict) else {}

    def as_set(value: object) -> set[str]:
        if not isinstance(value, list):
            return set()
        return {str(item) for item in value if isinstance(item, str)}

    return {
        "explicit_include": as_set(hash_policy.get("include_fields")),
        "explicit_exclude": as_set(hash_policy.get("exclude_fields")),
        "contract_include": as_set(contracts.get("hash_include")),
        "contract_exclude": as_set(contracts.get("hash_exclude")),
        "content_include": as_set(content_hash.get("include")),
        "content_exclude": as_set(content_hash.get("exclude")),
        "key_fields": (
            as_set(pipeline.get("business_primary_keys"))
            | as_set(contracts.get("primary_key"))
            | as_set(contracts.get("merge_keys"))
        ),
    }


def _actual_field_names(row: dict[str, str]) -> set[str]:
    names: set[str] = set()
    for column in (
        "bronze_field_names_json",
        "silver_pyarrow_field_names_json",
        "silver_pandera_field_names_json",
        "gold_field_names_json",
    ):
        names.update(_parse_json_list(row[column]))
    return names


def _affects_hash(row: dict[str, str], config: dict[str, Any]) -> bool:
    names = _actual_field_names(row)
    if not names:
        return False

    sets = _hash_sets(config)

    if sets["explicit_include"]:
        return bool(names & sets["explicit_include"])
    if sets["contract_include"]:
        return bool(names & sets["contract_include"])
    if sets["content_include"]:
        return bool(names & sets["content_include"])

    if names & (
        sets["explicit_exclude"] | sets["contract_exclude"] | sets["content_exclude"]
    ):
        return False

    return bool(names & sets["key_fields"])


def _spec_row(
    provider: str,
    entity: str,
    field_name: str,
    layer_transition: str,
    current_type: str,
    target_type: str,
    affects_hash: bool,
    source_row: dict[str, str],
) -> dict[str, str]:
    rules = _build_rules(field_name, source_row, current_type, target_type)
    return {
        "provider": provider,
        "entity": entity,
        "field": field_name,
        "layer_transition": layer_transition,
        "current_type": current_type,
        "target_type": target_type,
        "casting_rules_json": _json_dump(rules["casting"]),
        "cleaning_rules_json": _json_dump(rules["cleaning"]),
        "formatting_rules_json": _json_dump(rules["formatting"]),
        "validation_rules_json": _json_dump(rules["validation"]),
        "rules_json": _json_dump(rules),
        "deterministic": "true",
        "affects_hash": str(affects_hash).lower(),
    }


def build_field_transformation_rows() -> list[dict[str, str]]:
    configs = _load_entity_configs()
    rows: list[dict[str, str]] = []

    for field_row in build_field_level_rows():
        provider = field_row["provider"]
        entity = field_row["entity"]
        field_name = field_row["field"]
        config = configs[(provider, entity)]
        affects_hash = _affects_hash(field_row, config)

        silver_type = _silver_type(field_row)
        gold_type = _gold_type(field_row)

        bronze_to_silver_target = _normalized_target_type(
            field_name, silver_type, field_row
        )
        silver_to_gold_target = _normalized_target_type(
            field_name, gold_type, field_row
        )

        rows.append(
            _spec_row(
                provider=provider,
                entity=entity,
                field_name=field_name,
                layer_transition="bronze_to_silver",
                current_type="bronze_untyped",
                target_type=bronze_to_silver_target,
                affects_hash=affects_hash,
                source_row=field_row,
            )
        )
        rows.append(
            _spec_row(
                provider=provider,
                entity=entity,
                field_name=field_name,
                layer_transition="silver_to_gold",
                current_type=silver_type,
                target_type=silver_to_gold_target,
                affects_hash=affects_hash,
                source_row=field_row,
            )
        )

    rows.sort(
        key=lambda row: (
            row["provider"],
            row["entity"],
            row["field"],
            row["layer_transition"],
        )
    )
    return rows


def write_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    output_path = resolve_output_path(output_path, root=REPO_ROOT)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CSV_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate deterministic field transformation specs for Bronze→Silver→Gold."
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

    rows = build_field_transformation_rows()
    write_csv(rows, output_path)
    print(
        f"Generated {output_path.relative_to(PROJECT_ROOT)} with {len(rows)} field transformation specs."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
