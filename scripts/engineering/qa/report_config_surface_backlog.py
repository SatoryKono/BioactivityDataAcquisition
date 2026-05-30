#!/usr/bin/env python3
"""Categorize remaining entity config-surface drift for Stream B burn-down."""

from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.engineering.qa.config_surface_governance import (  # noqa: E402
    INTENTIONAL_PREFIXES,
    is_sanctioned_partial_key,
)
from scripts.schema.generate_config_matrix import (  # noqa: E402
    _collect_family_configs,
    _family_metrics,
)

BACKLOG_PATH = ROOT / "reports/quality/config-surface-backlog.json"

CATEGORY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("hash_policy_chembl_only", ("hash_policy.",)),
    ("extraction_params_entity_specific", ("filters.extraction_params.",)),
    ("gold_filter_entity_specific", ("filters.gold_filters.",)),
    ("silver_filter_entity_specific", ("filters.silver_filters.",)),
    (
        "pipeline_overrides",
        (
            "pipeline.page_size_override",
            "pipeline.field_policy.therapeutic_flag",
            "pipeline.source.",
        ),
    ),
    ("quality_thresholds", ("quality.thresholds",)),
    ("composite_runtime_only", ("composite.",)),
)


def _partial_keys(family_configs: dict[str, dict[str, str]]) -> list[tuple[int, str]]:
    all_keys = sorted({key for values in family_configs.values() for key in values})
    if not family_configs:
        return []
    common = set.intersection(*(set(values.keys()) for values in family_configs.values()))
    ranked: list[tuple[int, str]] = []
    for key in all_keys:
        if key in common:
            continue
        present = sum(1 for values in family_configs.values() if key in values)
        ranked.append((present, key))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return ranked


def _categorize_key(key: str) -> str:
    if key == "hash_policy" or key.startswith("hash_policy."):
        return "hash_policy_chembl_only"
    for category, prefixes in CATEGORY_RULES:
        if category == "hash_policy_chembl_only":
            continue
        if any(key == prefix or key.startswith(prefix) for prefix in prefixes):
            return category
    return "other_partial"


def _configs_with_key(
    family_configs: dict[str, dict[str, str]],
    key: str,
) -> list[str]:
    return sorted(name for name, values in family_configs.items() if key in values)


def build_backlog() -> dict[str, Any]:
    families = _collect_family_configs()
    entity = families["entity_effective"]
    entity_metrics = _family_metrics(entity)
    ranked = _partial_keys(entity)

    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    presence_histogram = Counter()
    actionable_keys: list[str] = []

    for present, key in ranked:
        category = _categorize_key(key)
        presence_histogram[present] += 1
        entry = {
            "key": key,
            "present_count": present,
            "config_count": len(entity),
            "configs": _configs_with_key(entity, key),
        }
        by_category[category].append(entry)
        if not is_sanctioned_partial_key(key):
            actionable_keys.append(key)

    return {
        "snapshot_date": date.today().isoformat(),
        "families": {
            name: _family_metrics(configs) for name, configs in families.items()
        },
        "entity_effective": {
            **entity_metrics,
            "partial_key_count": len(ranked),
            "presence_histogram": {
                str(count): presence_histogram[count]
                for count in sorted(presence_histogram)
            },
            "actionable_partial_key_count": len(actionable_keys),
            "categories": {
                category: {
                    "key_count": len(entries),
                    "keys": entries,
                }
                for category, entries in sorted(by_category.items())
            },
        },
        "notes": [
            "actionable_partial_key_count excludes keys under INTENTIONAL_PREFIXES.",
            "hash_policy is common across all 21 entity configs after Stream B design review.",
            "composite_runtime family is at zero inconsistent keys as of Stream B plateau.",
            "Residual entity drift is entity-specific filters/extraction_params/pipeline overrides only.",
        ],
    }


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    tmp.write_text(text, encoding="utf-8")
    try:
        os.replace(tmp, path)
    except OSError:
        path.write_text(text, encoding="utf-8")
        tmp.unlink(missing_ok=True)


def main() -> None:
    payload = build_backlog()
    _atomic_write(BACKLOG_PATH, payload)
    entity = payload["entity_effective"]
    families = payload["families"]
    print(f"Backlog saved to {BACKLOG_PATH.relative_to(ROOT)}")
    print(
        f"entity_effective partial={entity['partial_key_count']} "
        f"actionable={entity['actionable_partial_key_count']} "
        f"composite={families['composite_runtime']['inconsistent_parameter_count']}"
    )
    for category, block in entity["categories"].items():
        print(f"  {category}: {block['key_count']} keys")


if __name__ == "__main__":
    main()
