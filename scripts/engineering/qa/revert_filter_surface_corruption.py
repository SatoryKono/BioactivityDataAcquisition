#!/usr/bin/env python3
"""Remove filter-column stubs copied across entity configs by auto burn-down."""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parents[3]
ENTITIES = ROOT / "configs/entities"

GOLD_COLUMNS_ALLOWLIST: dict[str, frozenset[str]] = {
    "chembl/activity": frozenset(
        {"standard_type", "standard_units", "standard_relation", "assay_type", "potential_duplicate"}
    ),
    "chembl/assay": frozenset({"assay_type", "confidence_score", "downgraded", "reviewed"}),
    "chembl/molecule": frozenset({"inorganic_flag", "molecule_type", "structure_type", "potential_duplicate"}),
    "chembl/publication": frozenset({"publication_type"}),
    "chembl/target": frozenset({"target_type"}),
    "chembl/target_component": frozenset({"component_type"}),
    "uniprot/protein": frozenset({"reviewed"}),
}

SILVER_COLUMNS_ALLOWLIST: dict[str, frozenset[str]] = {
    "chembl/activity": frozenset({"assay_type", "potential_duplicate", "standard_relation", "standard_type", "standard_units"}),
    "chembl/assay": frozenset({"assay_type", "relationship_type", "src_id"}),
    "chembl/molecule": frozenset({"inorganic_flag", "molecule_type", "structure_type", "potential_duplicate"}),
    "chembl/publication": frozenset({"publication_type"}),
    "chembl/target": frozenset({"target_type"}),
}

SILVER_RANGES_ALLOWLIST: dict[str, frozenset[str]] = {
    "chembl/activity": frozenset({"activity_id", "pchembl_value", "standard_value", "publication_year"}),
    "chembl/assay": frozenset({"confidence_score", "publication_year"}),
    "chembl/molecule": frozenset({"publication_year"}),
    "chembl/publication": frozenset({"publication_year"}),
    "chembl/target": frozenset({"publication_year"}),
}

GOLD_RANGES_ALLOWLIST: dict[str, frozenset[str]] = {
    "chembl/activity": frozenset({"standard_value", "publication_year"}),
    "chembl/assay": frozenset(),
    "chembl/molecule": frozenset({"publication_year"}),
    "chembl/publication": frozenset({"publication_year"}),
    "chembl/publication_similarity": frozenset({"max_tani", "publication_year"}),
    "chembl/target": frozenset({"publication_year"}),
    "chembl/target_component": frozenset({"publication_year"}),
}

GOLD_LIST_LENGTHS_ALLOWLIST: dict[str, frozenset[str]] = {
    "chembl/target": frozenset({"component_accessions", "component_ids"}),
    "chembl/target_component": frozenset({"component_accessions", "component_ids"}),
}

GOLD_LIST_CONTAINS_ALLOWLIST: dict[str, frozenset[str]] = {
    "chembl/target": frozenset({"component_types"}),
    "chembl/target_component": frozenset({"component_types"}),
}


def _yaml_rt() -> YAML:
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False
    yaml.width = 120
    return yaml


def _atomic_write(path: Path, yaml: YAML, data: dict[str, Any]) -> None:
    buffer = io.StringIO()
    yaml.dump(data, buffer)
    payload = buffer.getvalue()
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    tmp.write_text(payload, encoding="utf-8")
    try:
        os.replace(tmp, path)
    except OSError:
        path.write_text(payload, encoding="utf-8")
        tmp.unlink(missing_ok=True)


def _prune_mapping(block: dict[str, Any] | None, allowed: frozenset[str]) -> bool:
    if not isinstance(block, dict):
        return False
    changed = False
    for key in list(block.keys()):
        if key not in allowed:
            del block[key]
            changed = True
    return changed


def _clean_filters(data: dict[str, Any], rel_key: str) -> bool:
    filters = data.get("filters")
    if not isinstance(filters, dict):
        return False
    changed = False

    gold = filters.get("gold_filters")
    if isinstance(gold, dict):
        allowed = GOLD_COLUMNS_ALLOWLIST.get(rel_key, frozenset())
        columns = gold.get("columns")
        if isinstance(columns, dict):
            if _prune_mapping(columns, allowed):
                changed = True
            if not columns:
                gold["columns"] = {}
        ranges = gold.get("ranges")
        if isinstance(ranges, dict):
            allowed_ranges = GOLD_RANGES_ALLOWLIST.get(rel_key, frozenset({"publication_year"}))
            if _prune_mapping(ranges, allowed_ranges):
                changed = True
        list_lengths = gold.get("list_lengths")
        if isinstance(list_lengths, dict):
            allowed_lengths = GOLD_LIST_LENGTHS_ALLOWLIST.get(rel_key, frozenset())
            if _prune_mapping(list_lengths, allowed_lengths):
                changed = True
            if not list_lengths and "list_lengths" in gold:
                gold["list_lengths"] = {}
        list_contains = gold.get("list_contains")
        if isinstance(list_contains, dict):
            allowed_contains = GOLD_LIST_CONTAINS_ALLOWLIST.get(rel_key, frozenset())
            if _prune_mapping(list_contains, allowed_contains):
                changed = True
            if not list_contains and "list_contains" in gold:
                gold["list_contains"] = {}

    silver = filters.get("silver_filters")
    if isinstance(silver, dict):
        allowed_cols = SILVER_COLUMNS_ALLOWLIST.get(rel_key, frozenset())
        columns = silver.get("columns")
        if isinstance(columns, dict):
            if _prune_mapping(columns, allowed_cols):
                changed = True
            if not columns and "columns" in silver:
                silver["columns"] = {}
        ranges = silver.get("ranges")
        if isinstance(ranges, dict):
            allowed_ranges = SILVER_RANGES_ALLOWLIST.get(rel_key, frozenset({"publication_year"}))
            if _prune_mapping(ranges, allowed_ranges):
                changed = True

    quality = data.get("quality")
    if isinstance(quality, dict) and rel_key != "uniprot/idmapping" and "thresholds" in quality:
        del quality["thresholds"]
        changed = True

    return changed


def main() -> None:
    yaml = _yaml_rt()
    touched = 0
    for path in sorted(ENTITIES.glob("*/*.yaml")):
        rel_key = f"{path.parent.name}/{path.stem}"
        data = yaml.load(path)
        if not isinstance(data, dict):
            continue
        if _clean_filters(data, rel_key):
            _atomic_write(path, yaml, data)
            touched += 1
            print(f"cleaned filters {rel_key}")
    print(f"touched={touched}")


if __name__ == "__main__":
    main()
