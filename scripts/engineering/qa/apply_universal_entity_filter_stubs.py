#!/usr/bin/env python3
"""Apply safe universal gold/silver filter stubs shared across entity configs."""

from __future__ import annotations

import copy
import io
import os
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parents[3]
ENTITIES = ROOT / "configs" / "entities"

PUBLICATION_YEAR_RANGE = {"min": 1950, "max": 2050}


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


def _ensure_pub_year(ranges: dict[str, Any]) -> bool:
    if "publication_year" in ranges:
        return False
    ranges["publication_year"] = copy.deepcopy(PUBLICATION_YEAR_RANGE)
    return True


def _apply_gold_stubs(gold: dict[str, Any], *, reset_list_contains: bool) -> bool:
    changed = False
    if reset_list_contains and gold.get("list_contains"):
        gold["list_contains"] = {}
        changed = True
    if "list_contains" not in gold:
        gold["list_contains"] = {}
        changed = True
    if "list_lengths" not in gold:
        gold["list_lengths"] = {}
        changed = True
    ranges = gold.get("ranges")
    if not isinstance(ranges, dict):
        gold["ranges"] = copy.deepcopy({"publication_year": PUBLICATION_YEAR_RANGE})
        return True
    if _ensure_pub_year(ranges):
        changed = True
    return changed


def _apply_silver_stubs(silver: dict[str, Any]) -> bool:
    changed = False
    ranges = silver.get("ranges")
    if not isinstance(ranges, dict):
        silver["ranges"] = {"publication_year": copy.deepcopy(PUBLICATION_YEAR_RANGE)}
        return True
    if _ensure_pub_year(ranges):
        changed = True
    return changed


def main() -> None:
    yaml = _yaml_rt()
    touched = 0
    for path in sorted(ENTITIES.glob("*/*.yaml")):
        data = yaml.load(path)
        if not isinstance(data, dict):
            continue
        filters = data.get("filters")
        if not isinstance(filters, dict):
            continue
        changed = False
        gold = filters.get("gold_filters")
        if isinstance(gold, dict):
            reset_lc = path.stem in {"activity", "protein"} and path.parent.name in {
                "chembl",
                "uniprot",
            }
            if _apply_gold_stubs(gold, reset_list_contains=reset_lc):
                changed = True
        silver = filters.get("silver_filters")
        if isinstance(silver, dict) and _apply_silver_stubs(silver):
            changed = True
        if changed:
            _atomic_write(path, yaml, data)
            touched += 1
            print(f"stubs {path.relative_to(ROOT)}")
    print(f"touched={touched}")


if __name__ == "__main__":
    main()
