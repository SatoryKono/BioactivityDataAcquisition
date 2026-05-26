#!/usr/bin/env python3
"""Inventory of silver_filters → gold_filters migration plan (ADR-048).

Scans all entity configs under `configs/entities/` and produces a per-rule
migration plan for the silver_filters → gold_filters consolidation described
in ADR-048 (docs/filters/ADR-048-silver-filters-structural-scope.md).

For each entity it classifies every rule in `silver_filters` as one of:

* keep_in_silver  - structural integrity (required_fields, exclude_if_present)
* move_to_gold    - semantic rule absent from gold_filters
* duplicate       - semantic rule fully covered by an identical gold_filters rule
* conflict        - semantic rule partially overlaps with a gold_filters rule
                    (different values for the same field)

Outputs (under docs/filters/):

* inventory-baseline.csv  - machine readable per-rule plan
* inventory-baseline.md   - human readable summary + per-entity tables

Usage:
    python scripts/data_quality/inventory_silver_filters_migration.py

Notes:
    Read-only script. Does not modify configs.
"""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENTITIES_DIR = PROJECT_ROOT / "configs" / "entities"
OUTPUT_DIR = PROJECT_ROOT / "docs" / "filters"
CSV_OUT = OUTPUT_DIR / "inventory-baseline.csv"
MD_OUT = OUTPUT_DIR / "inventory-baseline.md"
JSON_OUT = OUTPUT_DIR / "inventory-baseline.json"

STRUCTURAL_KEYS: frozenset[str] = frozenset({"required_fields", "exclude_if_present"})
SEMANTIC_KEYS: frozenset[str] = frozenset(
    {"columns", "ranges", "list_lengths", "list_contains"}
)
ALL_RULE_KEYS: frozenset[str] = STRUCTURAL_KEYS | SEMANTIC_KEYS

ACTION_KEEP = "keep_in_silver"
ACTION_MOVE = "move_to_gold"
ACTION_DUPLICATE = "duplicate"
ACTION_CONFLICT = "conflict"


@dataclass(frozen=True, slots=True)
class RulePlan:
    """One row of the migration plan."""

    provider: str
    entity: str
    rule_type: str  # required_fields | exclude_if_present | columns | ranges | list_lengths | list_contains
    field_name: str  # for required_fields/exclude_if_present this is the field listed; for dict rules - the key
    silver_value: str
    gold_value: str
    action: str
    notes: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "provider": self.provider,
            "entity": self.entity,
            "rule_type": self.rule_type,
            "field": self.field_name,
            "silver_value": self.silver_value,
            "gold_value": self.gold_value,
            "action": self.action,
            "notes": self.notes,
        }


@dataclass(slots=True)
class EntityPlan:
    """Aggregated migration plan for one entity."""

    provider: str
    entity: str
    path: Path
    rules: list[RulePlan] = field(default_factory=list)
    has_silver: bool = False
    has_gold: bool = False
    silver_raw: dict[str, Any] = field(default_factory=dict)
    gold_raw: dict[str, Any] = field(default_factory=dict)

    @property
    def counts_by_action(self) -> dict[str, int]:
        counters: dict[str, int] = {
            ACTION_KEEP: 0,
            ACTION_MOVE: 0,
            ACTION_DUPLICATE: 0,
            ACTION_CONFLICT: 0,
        }
        for rule in self.rules:
            counters[rule.action] = counters.get(rule.action, 0) + 1
        return counters


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        return {}
    return loaded


def _extract_filters(raw_config: dict[str, Any]) -> dict[str, Any]:
    """Return the `filters` block (preferred) or empty dict."""
    filters_block = raw_config.get("filters")
    if isinstance(filters_block, dict):
        return filters_block
    return {}


def _normalize_value(value: Any) -> str:
    """Return a stable string form for value comparison and reporting."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        # Stable sort for set-like comparison via canonical form.
        try:
            return json.dumps(
                sorted(value, key=lambda v: (str(type(v).__name__), str(v))),
                ensure_ascii=False,
            )
        except TypeError:
            return json.dumps(list(value), ensure_ascii=False)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    return json.dumps(value, ensure_ascii=False)


def _compare_values(silver_value: Any, gold_value: Any) -> str:
    """Compare two rule values and return one of ACTION_* constants.

    For lists, treat as sets when checking equality and subset relationships.
    """
    if gold_value is None:
        return ACTION_MOVE

    if isinstance(silver_value, list) and isinstance(gold_value, list):
        silver_set = {
            json.dumps(v, sort_keys=True, ensure_ascii=False) for v in silver_value
        }
        gold_set = {
            json.dumps(v, sort_keys=True, ensure_ascii=False) for v in gold_value
        }
        if silver_set == gold_set:
            return ACTION_DUPLICATE
        return ACTION_CONFLICT

    if isinstance(silver_value, dict) and isinstance(gold_value, dict):
        if silver_value == gold_value:
            return ACTION_DUPLICATE
        return ACTION_CONFLICT

    if silver_value == gold_value:
        return ACTION_DUPLICATE
    return ACTION_CONFLICT


def _plan_list_rule(
    rule_type: str,
    silver_items: list[Any],
    gold_items: list[Any],
    provider: str,
    entity: str,
) -> list[RulePlan]:
    """Plan migration for list-shaped rules (required_fields, exclude_if_present)."""
    plans: list[RulePlan] = []
    gold_set = {json.dumps(v, sort_keys=True, ensure_ascii=False) for v in gold_items}
    for item in silver_items:
        item_repr = json.dumps(item, sort_keys=True, ensure_ascii=False)
        in_gold = item_repr in gold_set
        plans.append(
            RulePlan(
                provider=provider,
                entity=entity,
                rule_type=rule_type,
                field_name=str(item),
                silver_value=_normalize_value(item),
                gold_value=_normalize_value(item) if in_gold else "",
                action=ACTION_KEEP,  # structural rules ALWAYS keep in silver per ADR-048
                notes=(
                    "also present in gold_filters (informational)"
                    if in_gold
                    else "structural rule stays in silver_filters"
                ),
            )
        )
    return plans


def _plan_dict_rule(
    rule_type: str,
    silver_dict: dict[str, Any],
    gold_dict: dict[str, Any],
    provider: str,
    entity: str,
) -> list[RulePlan]:
    """Plan migration for dict-shaped semantic rules (columns, ranges, list_*)."""
    plans: list[RulePlan] = []
    for field_name, silver_value in silver_dict.items():
        gold_value = gold_dict.get(field_name)
        if gold_value is None:
            action = ACTION_MOVE
            notes = "no rule in gold_filters - move from silver"
        else:
            comparison = _compare_values(silver_value, gold_value)
            if comparison == ACTION_DUPLICATE:
                action = ACTION_DUPLICATE
                notes = "identical rule in gold_filters - drop from silver"
            elif comparison == ACTION_CONFLICT:
                action = ACTION_CONFLICT
                notes = (
                    "different values for same field in silver vs gold - "
                    "manual review needed"
                )
            else:
                action = ACTION_MOVE
                notes = "move from silver to gold"
        plans.append(
            RulePlan(
                provider=provider,
                entity=entity,
                rule_type=rule_type,
                field_name=field_name,
                silver_value=_normalize_value(silver_value),
                gold_value=_normalize_value(gold_value),
                action=action,
                notes=notes,
            )
        )
    return plans


def build_entity_plan(provider: str, entity: str, path: Path) -> EntityPlan:
    """Build a per-entity migration plan from a YAML config."""
    raw = _load_yaml(path)
    filters_block = _extract_filters(raw)
    silver = filters_block.get("silver_filters") or {}
    gold = filters_block.get("gold_filters") or {}

    plan = EntityPlan(
        provider=provider,
        entity=entity,
        path=path,
        has_silver=bool(silver),
        has_gold=bool(gold),
        silver_raw=silver,
        gold_raw=gold,
    )

    if not isinstance(silver, dict):
        return plan

    if isinstance(gold, dict):
        gold_dict: dict[str, Any] = gold
    else:
        gold_dict = {}

    # Structural list-shaped rules
    for rule_type in ("required_fields", "exclude_if_present"):
        silver_items = silver.get(rule_type) or []
        gold_items = gold_dict.get(rule_type) or []
        if not isinstance(silver_items, list):
            continue
        if not isinstance(gold_items, list):
            gold_items = []
        plan.rules.extend(
            _plan_list_rule(rule_type, silver_items, gold_items, provider, entity)
        )

    # Semantic dict-shaped rules
    for rule_type in ("columns", "ranges", "list_lengths", "list_contains"):
        silver_dict = silver.get(rule_type) or {}
        gold_dict_rule = gold_dict.get(rule_type) or {}
        if not isinstance(silver_dict, dict):
            continue
        if not isinstance(gold_dict_rule, dict):
            gold_dict_rule = {}
        plan.rules.extend(
            _plan_dict_rule(rule_type, silver_dict, gold_dict_rule, provider, entity)
        )

    return plan


def discover_entity_configs() -> list[tuple[str, str, Path]]:
    """Return list of (provider, entity, path) tuples for all entity configs."""
    discovered: list[tuple[str, str, Path]] = []
    for provider_dir in sorted(ENTITIES_DIR.iterdir()):
        if not provider_dir.is_dir():
            continue
        for entity_file in sorted(provider_dir.glob("*.yaml")):
            entity = entity_file.stem
            discovered.append((provider_dir.name, entity, entity_file))
    return discovered


def write_csv(plans: list[EntityPlan], path: Path) -> None:
    """Write the per-rule CSV report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "provider",
                "entity",
                "rule_type",
                "field",
                "silver_value",
                "gold_value",
                "action",
                "notes",
            ],
        )
        writer.writeheader()
        for plan in plans:
            for rule in plan.rules:
                writer.writerow(rule.as_dict())


def write_json(plans: list[EntityPlan], path: Path) -> None:
    """Write a machine-readable JSON aggregate."""
    summary: dict[str, Any] = {
        "schema_version": "1.0.0",
        "generated_by": "scripts/data_quality/inventory_silver_filters_migration.py",
        "totals": _aggregate_totals(plans),
        "entities": [],
    }
    for plan in plans:
        summary["entities"].append(
            {
                "provider": plan.provider,
                "entity": plan.entity,
                "path": str(plan.path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "has_silver_filters": plan.has_silver,
                "has_gold_filters": plan.has_gold,
                "counts_by_action": plan.counts_by_action,
                "rules": [rule.as_dict() for rule in plan.rules],
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def _aggregate_totals(plans: list[EntityPlan]) -> dict[str, int]:
    totals: dict[str, int] = {
        "entities_total": len(plans),
        "entities_with_silver_filters": sum(1 for p in plans if p.has_silver),
        "entities_with_gold_filters": sum(1 for p in plans if p.has_gold),
        "rules_total": 0,
        ACTION_KEEP: 0,
        ACTION_MOVE: 0,
        ACTION_DUPLICATE: 0,
        ACTION_CONFLICT: 0,
    }
    for plan in plans:
        for rule in plan.rules:
            totals["rules_total"] += 1
            totals[rule.action] = totals.get(rule.action, 0) + 1
    return totals


def _render_md_entity_section(plan: EntityPlan) -> str:
    if not plan.rules:
        return ""

    buf = StringIO()
    rel_path = plan.path.relative_to(PROJECT_ROOT).as_posix()
    buf.write(f"### `{plan.provider}.{plan.entity}`\n\n")
    buf.write(f"Source: `{rel_path}`\n\n")
    counts = plan.counts_by_action
    buf.write(
        f"- keep_in_silver: **{counts[ACTION_KEEP]}**, "
        f"move_to_gold: **{counts[ACTION_MOVE]}**, "
        f"duplicate: **{counts[ACTION_DUPLICATE]}**, "
        f"conflict: **{counts[ACTION_CONFLICT]}**\n\n"
    )
    buf.write("| Rule type | Field | Silver value | Gold value | Action | Notes |\n")
    buf.write("| --- | --- | --- | --- | --- | --- |\n")
    for rule in plan.rules:
        # truncate long values for readability
        silver_repr = (rule.silver_value or "").replace("|", "\\|")
        gold_repr = (rule.gold_value or "").replace("|", "\\|")
        if len(silver_repr) > 80:
            silver_repr = silver_repr[:77] + "..."
        if len(gold_repr) > 80:
            gold_repr = gold_repr[:77] + "..."
        buf.write(
            f"| {rule.rule_type} | `{rule.field_name}` | `{silver_repr}` | "
            f"`{gold_repr}` | **{rule.action}** | {rule.notes} |\n"
        )
    buf.write("\n")
    return buf.getvalue()


def write_markdown(plans: list[EntityPlan], path: Path) -> None:
    """Write a human-readable Markdown report."""
    totals = _aggregate_totals(plans)
    buf = StringIO()
    buf.write("# Silver Filters Migration Inventory Baseline\n\n")
    buf.write(
        "Generated by `scripts/data_quality/inventory_silver_filters_migration.py` "
        "per ADR-048 (variant D: hybrid migration).\n\n"
    )
    buf.write("## Summary\n\n")
    buf.write(f"- **Entities scanned**: {totals['entities_total']}\n")
    buf.write(
        f"- **Entities with `silver_filters`**: "
        f"{totals['entities_with_silver_filters']}\n"
    )
    buf.write(
        f"- **Entities with `gold_filters`**: {totals['entities_with_gold_filters']}\n"
    )
    buf.write(f"- **Total rules planned**: {totals['rules_total']}\n")
    buf.write(f"  - keep_in_silver: **{totals[ACTION_KEEP]}**\n")
    buf.write(f"  - move_to_gold: **{totals[ACTION_MOVE]}**\n")
    buf.write(f"  - duplicate (drop from silver): **{totals[ACTION_DUPLICATE]}**\n")
    buf.write(f"  - conflict (manual review): **{totals[ACTION_CONFLICT]}**\n\n")
    buf.write("## Action legend\n\n")
    buf.write(
        "- **keep_in_silver** - structural rule (`required_fields` / "
        "`exclude_if_present`), stays in `silver_filters`.\n"
    )
    buf.write(
        "- **move_to_gold** - semantic rule absent from `gold_filters`, "
        "move from silver to gold.\n"
    )
    buf.write(
        "- **duplicate** - semantic rule already present in `gold_filters` with "
        "identical value; drop from silver.\n"
    )
    buf.write(
        "- **conflict** - semantic rule present in `gold_filters` with different "
        "value; needs manual review.\n\n"
    )
    buf.write("## Per-entity plan\n\n")
    for plan in plans:
        if plan.has_silver:
            section = _render_md_entity_section(plan)
            buf.write(section)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(buf.getvalue(), encoding="utf-8")


def main() -> int:
    discovered = discover_entity_configs()
    if not discovered:
        print(f"No entity configs found under {ENTITIES_DIR}", file=sys.stderr)
        return 1

    plans: list[EntityPlan] = []
    for provider, entity, path in discovered:
        plans.append(build_entity_plan(provider, entity, path))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(plans, CSV_OUT)
    write_json(plans, JSON_OUT)
    write_markdown(plans, MD_OUT)

    totals = _aggregate_totals(plans)
    print(
        f"Scanned {totals['entities_total']} entities "
        f"({totals['entities_with_silver_filters']} with silver_filters, "
        f"{totals['entities_with_gold_filters']} with gold_filters). "
        f"Rules total: {totals['rules_total']} "
        f"(keep={totals[ACTION_KEEP]}, move={totals[ACTION_MOVE]}, "
        f"duplicate={totals[ACTION_DUPLICATE]}, "
        f"conflict={totals[ACTION_CONFLICT]})."
    )
    print(f"Wrote: {CSV_OUT.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {MD_OUT.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {JSON_OUT.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
