#!/usr/bin/env python3
"""Inventory of silver_filters → gold_filters migration plan (ADR-050).

Scans all entity configs under `configs/entities/` and active runtime/operator
surfaces that participate in the Silver structural / Gold semantic boundary
described in ADR-050.

For each entity it classifies every rule in `silver_filters` as one of:

* keep_in_silver  - structural integrity (required_fields, exclude_if_present)
* move_to_gold    - semantic rule absent from gold_filters
* duplicate       - semantic rule fully covered by an identical gold_filters rule
* conflict        - semantic rule partially overlaps with a gold_filters rule
                    (different values for the same field)

Outputs (under docs/filters/):

* inventory-baseline.csv  - machine readable per-rule and surface inventory
* inventory-baseline.json - structured aggregate
* inventory-baseline.md   - human readable summary + per-entity/surface tables

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

SURFACE_CATEGORIES: frozenset[str] = frozenset(
    {
        "silver_config",
        "runtime_gate",
        "source_profile",
        "observability",
        "consumer_alias",
    }
)
_SURFACE_FILE_SUFFIXES: frozenset[str] = frozenset(
    {".py", ".yaml", ".yml", ".json", ".md"}
)
_IGNORED_SURFACE_SUFFIXES: tuple[str, ...] = (".bak",)


@dataclass(frozen=True, slots=True)
class SurfacePattern:
    """Literal source-scan pattern for one active migration surface."""

    category: str
    surface: str
    symbol: str
    paths: tuple[str, ...]
    role: str
    migration_relevance: str


@dataclass(frozen=True, slots=True)
class SurfaceFinding:
    """One discovered runtime/ops/source-profile migration surface."""

    category: str
    surface: str
    symbol: str
    path: str
    occurrence_count: int
    first_line: int
    role: str
    migration_relevance: str
    notes: str = ""

    def as_dict(self) -> dict[str, str | int]:
        return {
            "category": self.category,
            "surface": self.surface,
            "symbol": self.symbol,
            "path": self.path,
            "occurrence_count": self.occurrence_count,
            "first_line": self.first_line,
            "role": self.role,
            "migration_relevance": self.migration_relevance,
            "notes": self.notes,
        }


SURFACE_PATTERNS: tuple[SurfacePattern, ...] = (
    SurfacePattern(
        category="silver_config",
        surface="domain_silver_config",
        symbol="SilverFilterConfig",
        paths=("src/bioetl/domain/filtering/silver_config.py",),
        role="Domain Silver filter object",
        migration_relevance="Domain Silver config must remain structural-only after compatibility conversion.",
    ),
    SurfacePattern(
        category="silver_config",
        surface="direct_silver_config_construction",
        symbol="SilverFilterConfig(",
        paths=(
            "src/bioetl/infrastructure/config/silver_filter_migration.py",
            "src/bioetl/infrastructure/schemas/filter_config.py",
            "src/bioetl/infrastructure/schemas/pipeline_config_common_schemas.py",
        ),
        role="Direct SilverFilterConfig construction",
        migration_relevance="New direct construction sites must not bypass structural-only compatibility helpers.",
    ),
    SurfacePattern(
        category="silver_config",
        surface="compatibility_normalizer",
        symbol="SILVER_SEMANTIC_FILTER_KEYS",
        paths=("src/bioetl/infrastructure/config/silver_filter_migration.py",),
        role="Legacy semantic Silver key set",
        migration_relevance="Defines semantic keys that are promoted to Gold during the compatibility window.",
    ),
    SurfacePattern(
        category="silver_config",
        surface="compatibility_normalizer",
        symbol="normalize_silver_gold_filter_payload",
        paths=(
            "src/bioetl/infrastructure/config",
            "src/bioetl/infrastructure/schemas",
        ),
        role="Silver-to-Gold payload promotion",
        migration_relevance="Boundary hook that keeps domain Silver filters structural-only.",
    ),
    SurfacePattern(
        category="silver_config",
        surface="schema_silver_projection",
        symbol="SilverFiltersFileConfig",
        paths=("src/bioetl/infrastructure/schemas/filter_config.py",),
        role="Filter-file Silver schema",
        migration_relevance="Accepts legacy semantic keys only at the infrastructure boundary.",
    ),
    SurfacePattern(
        category="silver_config",
        surface="schema_silver_projection",
        symbol="SilverFiltersConfig",
        paths=("src/bioetl/infrastructure/schemas/pipeline_config_common_schemas.py",),
        role="Pipeline Silver schema",
        migration_relevance="Projects YAML Silver filters to structural-only domain config.",
    ),
    SurfacePattern(
        category="silver_config",
        surface="runtime_identity",
        symbol="silver_filter_compatibility_mode",
        paths=(
            "src/bioetl/application/core/lifecycle/checkpoint_identity_overrides.py",
            "src/bioetl/domain/config/runtime.py",
            "src/bioetl/infrastructure/schemas/pipeline_config.py",
        ),
        role="Execution identity compatibility mode",
        migration_relevance="Run manifest/checkpoint/effective config identity must preserve compatibility mode.",
    ),
    SurfacePattern(
        category="runtime_gate",
        surface="silver_filter_application",
        symbol="apply_silver_filter",
        paths=(
            "src/bioetl/application/core/_base_transformer_structural_support.py",
            "src/bioetl/application/core/base_transformer_execution_mixin.py",
            "src/bioetl/application/core/pre_silver_adapter_mixin.py",
            "src/bioetl/application/core/pre_silver_record.py",
            "src/bioetl/application/core/pre_silver_staging_flow.py",
            "src/bioetl/application/core/record_normalization_processor.py",
            "src/bioetl/application/pipelines/common/publication_transformer_records.py",
        ),
        role="Runtime Silver filter application callsite",
        migration_relevance="Any new runtime application gate must remain structural-only or be inventoried.",
    ),
    SurfacePattern(
        category="runtime_gate",
        surface="pre_silver_filter_adapter",
        symbol="_apply_pre_silver_filter",
        paths=("src/bioetl/application/core",),
        role="Pre-Silver adapter filter callsite",
        migration_relevance="Pre-Silver path still delegates to the structural Silver filter gate.",
    ),
    SurfacePattern(
        category="runtime_gate",
        surface="legacy_silver_write_decision",
        symbol="should_write_silver",
        paths=("src/bioetl/application/core/base_transformer/base.py",),
        role="Legacy Silver write decision helper",
        migration_relevance="Any active semantic use of should_write_silver must be explicit in this inventory.",
    ),
    SurfacePattern(
        category="runtime_gate",
        surface="silver_filter_evaluation",
        symbol="_silver_filters.evaluate",
        paths=("src/bioetl/application/core/_base_transformer_structural_support.py",),
        role="Runtime Silver filter evaluator",
        migration_relevance="Evaluator sites are migration-sensitive because they can reject records before Gold.",
    ),
    SurfacePattern(
        category="runtime_gate",
        surface="silver_filter_should_include",
        symbol="_silver_filters.should_include",
        paths=("src/bioetl/application/core/base_transformer/base.py",),
        role="Runtime Silver include predicate",
        migration_relevance="Predicate sites are migration-sensitive and must not add semantic Silver gating.",
    ),
    SurfacePattern(
        category="source_profile",
        surface="config_source_profile_policy",
        symbol="extraction_params",
        paths=(
            "src/bioetl/infrastructure/config",
            "src/bioetl/infrastructure/schemas",
            "configs/_schema/pipeline.json",
            "scripts/engineering/qa/config_surface_governance.py",
            "scripts/docs/matrix/generate_pipeline_normalization_matrix.py",
        ),
        role="Source-profile extraction policy",
        migration_relevance="extraction_params are provider request policy and must not be treated as Silver filters.",
    ),
    SurfacePattern(
        category="observability",
        surface="silver_filter_metric",
        symbol="bioetl_silver_filter_rejections_total",
        paths=(
            "src/bioetl/application/observability",
            "src/bioetl/infrastructure/observability",
            "grafana/dashboards",
            "grafana/prometheus-rules",
            "grafana/README.md",
            "docs/04-reference/observability",
            "docs/03-guides/metrics-monitoring.md",
        ),
        role="Silver filter rejection metric",
        migration_relevance="Metric semantics are narrowed to Silver structural rejects during compatibility cleanup.",
    ),
    SurfacePattern(
        category="observability",
        surface="silver_filter_reconciliation_rule",
        symbol="bioetl_silver_filter_reject_total_mismatch_15m",
        paths=("grafana/prometheus-rules", "grafana/README.md"),
        role="Silver reject accounting reconciliation",
        migration_relevance="Recording rule reconciles stage totals with bounded Silver reject breakdowns.",
    ),
    SurfacePattern(
        category="consumer_alias",
        surface="legacy_silver_error_code",
        symbol="FILTERED_OUT_SILVER",
        paths=(
            "src/bioetl/application/core/_quarantine_metrics_support.py",
            "src/bioetl/application/core/_quarantine_request_builders.py",
            "src/bioetl/application/core/_quarantine_support.py",
            "src/bioetl/infrastructure/quarantine/filtered_reads.py",
            "src/bioetl/infrastructure/quarantine/statistics_support.py",
            "src/bioetl/infrastructure/storage/workflow_foreign_key_reconciliation_quarantine.py",
            "src/bioetl/interfaces/cli/commands/diagnostics.py",
            "src/bioetl/interfaces/cli/commands/quarantine.py",
            "grafana/dashboards/bioetl-silver-reject-explorer.json",
            "docs/05-operations",
            "docs/04-reference/cli.md",
            "docs/03-guides/running-pipelines.md",
            "docs/03-guides/troubleshooting.md",
            "docs/03-guides/dashboards/dashboard-requirements-comprehensive.md",
            "docs/03-guides/dashboards/dashboard-v2-usage.md",
            "docs/plans/silver-filter-rejects-observability-plan.md",
        ),
        role="Temporary legacy Silver reject alias",
        migration_relevance="Alias remains a compatibility surface, not target semantic rejection taxonomy.",
    ),
    SurfacePattern(
        category="consumer_alias",
        surface="cli_silver_filter_shortcut",
        symbol="--silver-filter-only",
        paths=(
            "src/bioetl/interfaces/cli/commands/diagnostics.py",
            "src/bioetl/interfaces/cli/commands/quarantine.py",
            "grafana/dashboards/bioetl-silver-reject-explorer.json",
            "docs/05-operations",
            "docs/04-reference/cli.md",
            "docs/03-guides/metrics-monitoring.md",
            "docs/03-guides/running-pipelines.md",
            "docs/03-guides/troubleshooting.md",
            "docs/03-guides/dashboards/dashboard-v2-usage.md",
            "docs/03-guides/dashboards/monitoring-index.md",
        ),
        role="CLI/operator shortcut for FILTERED_OUT_SILVER",
        migration_relevance="Shortcut is a compatibility alias while operator wording moves to structural rejects.",
    ),
    SurfacePattern(
        category="consumer_alias",
        surface="silver_filter_rejects_summary_alias",
        symbol="silver_filter_rejects",
        paths=(
            "src/bioetl/application/services/_observability_workflow_quarantine_support.py",
            "src/bioetl/infrastructure/quarantine/_statistics.py",
            "src/bioetl/infrastructure/quarantine/statistics_support.py",
            "src/bioetl/interfaces/cli/commands/domains/diagnostics/rendering.py",
            "src/bioetl/interfaces/cli/commands/domains/quarantine/_run_scope_stats.py",
            "src/bioetl/interfaces/cli/commands/domains/quarantine/rendering.py",
            "grafana/prometheus-rules",
            "docs/05-operations",
            "docs/03-guides/running-pipelines.md",
            "docs/plans/silver-filter-rejects-observability-plan.md",
        ),
        role="Operator summary alias for Silver rejects",
        migration_relevance=(
            "Summary key is a compatibility alias while semantic/business rejects "
            "move to Gold taxonomy."
        ),
    ),
)


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


def _is_scannable_surface_file(path: Path) -> bool:
    """Return whether a file belongs to the active surface inventory."""
    if not path.is_file():
        return False
    if path.name.endswith(_IGNORED_SURFACE_SUFFIXES):
        return False
    return path.suffix in _SURFACE_FILE_SUFFIXES


def _iter_surface_files(path_specs: tuple[str, ...]) -> list[Path]:
    """Expand relative file/dir scan specs into deterministic active files."""
    files: dict[str, Path] = {}
    for path_spec in path_specs:
        root = PROJECT_ROOT / path_spec
        if root.is_file():
            if _is_scannable_surface_file(root):
                files[root.as_posix()] = root
            continue
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if _is_scannable_surface_file(path):
                files[path.as_posix()] = path
    return [files[key] for key in sorted(files)]


def _first_line_number(text: str, symbol: str) -> int:
    for line_number, line in enumerate(text.splitlines(), start=1):
        if symbol in line:
            return line_number
    return 0


def _rel_path(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def _scan_literal_surface_patterns() -> list[SurfaceFinding]:
    findings: list[SurfaceFinding] = []
    for pattern in SURFACE_PATTERNS:
        assert pattern.category in SURFACE_CATEGORIES, (
            f"Unsupported surface category: {pattern.category}"
        )
        for path in _iter_surface_files(pattern.paths):
            text = path.read_text(encoding="utf-8", errors="ignore")
            occurrence_count = text.count(pattern.symbol)
            if occurrence_count <= 0:
                continue
            findings.append(
                SurfaceFinding(
                    category=pattern.category,
                    surface=pattern.surface,
                    symbol=pattern.symbol,
                    path=_rel_path(path),
                    occurrence_count=occurrence_count,
                    first_line=_first_line_number(text, pattern.symbol),
                    role=pattern.role,
                    migration_relevance=pattern.migration_relevance,
                )
            )
    return findings


def _extract_entity_extraction_params_surfaces() -> list[SurfaceFinding]:
    findings: list[SurfaceFinding] = []
    for provider, entity, path in discover_entity_configs():
        raw = _load_yaml(path)
        filters_block = _extract_filters(raw)
        if "extraction_params" not in filters_block:
            continue
        extraction_params = filters_block.get("extraction_params")
        parameter_count = (
            len(extraction_params) if isinstance(extraction_params, dict) else 0
        )
        text = path.read_text(encoding="utf-8", errors="ignore")
        findings.append(
            SurfaceFinding(
                category="source_profile",
                surface="entity_config_extraction_params",
                symbol="filters.extraction_params",
                path=_rel_path(path),
                occurrence_count=1,
                first_line=_first_line_number(text, "extraction_params"),
                role=f"Entity source-profile policy for {provider}.{entity}",
                migration_relevance=(
                    "Provider API request narrowing is source-profile policy, "
                    "not Silver structural filtering."
                ),
                notes=("non_empty" if parameter_count > 0 else "empty")
                + f"; parameter_count={parameter_count}",
            )
        )
    return findings


def build_surface_inventory() -> list[SurfaceFinding]:
    """Build runtime, ops, source-profile, and compatibility surface inventory."""
    findings = [
        *_scan_literal_surface_patterns(),
        *_extract_entity_extraction_params_surfaces(),
    ]
    return sorted(
        findings,
        key=lambda finding: (
            finding.category,
            finding.surface,
            finding.path,
            finding.symbol,
        ),
    )


def _aggregate_surface_totals(findings: list[SurfaceFinding]) -> dict[str, Any]:
    by_category = dict.fromkeys(sorted(SURFACE_CATEGORIES), 0)
    by_symbol: dict[str, int] = {}
    for finding in findings:
        by_category[finding.category] = by_category.get(finding.category, 0) + 1
        by_symbol[finding.symbol] = by_symbol.get(finding.symbol, 0) + 1
    return {
        "surfaces_total": len(findings),
        "by_category": by_category,
        "by_symbol": dict(sorted(by_symbol.items())),
    }


def write_csv(
    plans: list[EntityPlan],
    surface_inventory: list[SurfaceFinding],
    path: Path,
) -> None:
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
                "record_kind",
                "category",
                "symbol",
                "surface",
                "path",
                "occurrence_count",
                "first_line",
                "role",
                "migration_relevance",
            ],
        )
        writer.writeheader()
        for plan in plans:
            for rule in plan.rules:
                row = rule.as_dict()
                row.update(
                    {
                        "record_kind": "entity_rule",
                        "category": "entity_config",
                        "symbol": "",
                        "surface": "entity_silver_filter_rule",
                        "path": _rel_path(plan.path),
                        "occurrence_count": "",
                        "first_line": "",
                        "role": "Entity Silver filter migration rule",
                        "migration_relevance": (
                            "Classifies current filters.silver_filters rule for "
                            "Silver structural / Gold semantic cleanup."
                        ),
                    }
                )
                writer.writerow(row)
        for finding in surface_inventory:
            writer.writerow(
                {
                    "provider": "",
                    "entity": "",
                    "rule_type": "",
                    "field": "",
                    "silver_value": "",
                    "gold_value": "",
                    "action": "inventory",
                    "notes": finding.notes,
                    "record_kind": "surface",
                    "category": finding.category,
                    "symbol": finding.symbol,
                    "surface": finding.surface,
                    "path": finding.path,
                    "occurrence_count": finding.occurrence_count,
                    "first_line": finding.first_line,
                    "role": finding.role,
                    "migration_relevance": finding.migration_relevance,
                }
            )


def write_json(
    plans: list[EntityPlan],
    surface_inventory: list[SurfaceFinding],
    path: Path,
) -> None:
    """Write a machine-readable JSON aggregate."""
    summary: dict[str, Any] = {
        "schema_version": "2.0.0",
        "generated_by": "scripts/data_quality/inventory_silver_filters_migration.py",
        "totals": _aggregate_totals(plans),
        "surface_totals": _aggregate_surface_totals(surface_inventory),
        "entities": [],
        "surface_inventory": [finding.as_dict() for finding in surface_inventory],
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


def _render_md_surface_section(findings: list[SurfaceFinding]) -> str:
    if not findings:
        return ""

    buf = StringIO()
    by_category: dict[str, list[SurfaceFinding]] = {}
    for finding in findings:
        by_category.setdefault(finding.category, []).append(finding)

    buf.write("## Runtime, Ops, and Source-Profile Surfaces\n\n")
    for category in sorted(by_category):
        rows = sorted(
            by_category[category],
            key=lambda finding: (finding.surface, finding.path, finding.symbol),
        )
        buf.write(f"### `{category}`\n\n")
        buf.write("| Surface | Symbol | Path | Count | First line | Notes |\n")
        buf.write("| --- | --- | --- | ---: | ---: | --- |\n")
        for finding in rows:
            notes = finding.notes or finding.role
            notes = notes.replace("|", "\\|")
            buf.write(
                f"| `{finding.surface}` | `{finding.symbol}` | `{finding.path}` | "
                f"{finding.occurrence_count} | {finding.first_line} | {notes} |\n"
            )
        buf.write("\n")
    return buf.getvalue()


def write_markdown(
    plans: list[EntityPlan],
    surface_inventory: list[SurfaceFinding],
    path: Path,
) -> None:
    """Write a human-readable Markdown report."""
    totals = _aggregate_totals(plans)
    surface_totals = _aggregate_surface_totals(surface_inventory)
    buf = StringIO()
    buf.write("# Silver Filters Migration Inventory Baseline\n\n")
    buf.write(
        "Generated by `scripts/data_quality/inventory_silver_filters_migration.py` "
        "for ADR-050 Silver structural / Gold semantic boundary governance.\n\n"
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
    buf.write(
        f"- **Runtime/ops/source-profile surfaces**: {surface_totals['surfaces_total']}\n"
    )
    for category, count in surface_totals["by_category"].items():
        buf.write(f"  - {category}: **{count}**\n")
    buf.write("\n")
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
    buf.write(_render_md_surface_section(surface_inventory))
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
    surface_inventory = build_surface_inventory()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(plans, surface_inventory, CSV_OUT)
    write_json(plans, surface_inventory, JSON_OUT)
    write_markdown(plans, surface_inventory, MD_OUT)

    totals = _aggregate_totals(plans)
    surface_totals = _aggregate_surface_totals(surface_inventory)
    print(
        f"Scanned {totals['entities_total']} entities "
        f"({totals['entities_with_silver_filters']} with silver_filters, "
        f"{totals['entities_with_gold_filters']} with gold_filters). "
        f"Rules total: {totals['rules_total']} "
        f"(keep={totals[ACTION_KEEP]}, move={totals[ACTION_MOVE]}, "
        f"duplicate={totals[ACTION_DUPLICATE]}, "
        f"conflict={totals[ACTION_CONFLICT]})."
    )
    print(
        f"Inventoried {surface_totals['surfaces_total']} runtime/ops/source-profile "
        f"surfaces across categories: {surface_totals['by_category']}."
    )
    print(f"Wrote: {CSV_OUT.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {MD_OUT.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {JSON_OUT.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
