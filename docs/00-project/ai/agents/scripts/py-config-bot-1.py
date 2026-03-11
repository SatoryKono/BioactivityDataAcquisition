#!/usr/bin/env python3
"""Gap analysis for pipeline configs against ADR-014/025/027/028/029.

Checks pipeline configurations for compliance with:
- ADR-014: Deterministic Writes (sort_by requirements)
- ADR-025: Pipeline Config Unification (required/recommended fields)
- ADR-027/028: unified DQ/filter hierarchy
- ADR-029: convention-based path resolution

Usage:
    python docs/00-project/ai/agents/scripts/py-config-bot-1.py
    python docs/00-project/ai/agents/scripts/py-config-bot-1.py -o docs/audits/config_gaps.md
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml

ENTITY_CONFIGS_DIR = Path("configs/entities")
COMPOSITES_DIR = Path("configs/composites")


@dataclass
class ConfigGaps:
    """Gaps found in a single config."""

    path: Path
    is_composite: bool = False
    critical: list[str] = field(default_factory=list)
    medium: list[str] = field(default_factory=list)
    low: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.critical) + len(self.medium) + len(self.low)


def _as_dict(value: Any) -> dict[str, Any]:
    """Return value as dict if possible, else empty dict."""
    return value if isinstance(value, dict) else {}


def analyze_standard_config(
    pipeline_config: dict[str, Any],
    gaps: ConfigGaps,
    full_config: dict[str, Any] | None = None,
) -> None:
    """Analyze standard (non-composite) pipeline config.

    Supports the current unified format:
    - top-level sections: pipeline/schema/quality/filters/contracts
    - pipeline.business_primary_keys
    - optional pipeline.sink.* sections
    """
    # === ADR-025: Required pipeline fields (MUST) ===
    for fld in ("pipeline_name", "provider", "entity_type", "business_primary_keys"):
        if fld not in pipeline_config:
            gaps.critical.append(f"Missing MUST field: pipeline.{fld}")

    business_keys = pipeline_config.get("business_primary_keys")
    if not isinstance(business_keys, list) or not business_keys:
        gaps.critical.append("pipeline.business_primary_keys must be a non-empty list")

    # === ADR-025: Recommended metadata fields (SHOULD) ===
    top = full_config or {}
    if "version" not in top:
        gaps.medium.append("Missing SHOULD field: top-level version")
    if "description" not in pipeline_config:
        gaps.medium.append("Missing SHOULD field: pipeline.description")

    # === ADR-025: Version format ===
    version = top.get("version")
    if version and not re.match(r"^\d+\.\d+\.\d+$", str(version)):
        gaps.medium.append(f"Version '{version}' not semver format")

    # === Unified key consistency checks ===
    contracts = _as_dict(top.get("contracts"))
    contract_pk = contracts.get("primary_key")
    if contract_pk is None:
        gaps.critical.append("Missing MUST field: contracts.primary_key")
    elif isinstance(business_keys, list) and isinstance(contract_pk, list):
        if sorted(str(v) for v in business_keys) != sorted(str(v) for v in contract_pk):
            gaps.medium.append(
                "Mismatch between pipeline.business_primary_keys and contracts.primary_key"
            )

    # === Sink checks (keep aligned with current Pydantic schema) ===
    sink = _as_dict(pipeline_config.get("sink"))

    # === ADR-025: Hierarchical paths (SHOULD) ===
    provider = pipeline_config.get("provider", "")
    entity = pipeline_config.get("entity_type", "")
    if provider and entity and sink:
        expected_suffix = f"{provider}/{entity}"
        for layer in ("bronze", "silver", "gold"):
            layer_cfg = _as_dict(sink.get(layer))
            path = layer_cfg.get("path", "")
            if isinstance(path, str) and path and not path.endswith(expected_suffix):
                gaps.low.append(
                    f"sink.{layer}.path should end with '{expected_suffix}' (got '{path}')"
                )

    # === ADR-027: DQ rules ===
    for dq_parent_name, dq_parent in (
        ("top-level", top),
        ("pipeline", pipeline_config),
    ):
        dq = _as_dict(dq_parent.get("dq_overrides"))
        if "soft_fail_threshold" in dq or "hard_fail_threshold" in dq:
            gaps.medium.append(
                f"Inline dq_overrides thresholds in {dq_parent_name} (deprecated per ADR-027)"
            )

    # === ADR-025: gold_filters ===
    filters = _as_dict(top.get("filters"))
    gold_filters = _as_dict(filters.get("gold_filters"))
    if not gold_filters:
        gaps.low.append("Missing filters.gold_filters section")
    elif not gold_filters.get("required_fields"):
        gaps.low.append("filters.gold_filters.required_fields empty or missing")


def analyze_composite_config(config: dict[str, Any], gaps: ConfigGaps) -> None:
    """Analyze composite pipeline config (ADR-026 structure)."""
    gaps.is_composite = True

    composite = _as_dict(config.get("composite"))

    # === Required composite fields ===
    if not composite:
        gaps.critical.append("Missing 'composite' section for composite pipeline")
        return

    for fld in ["name", "version", "seed", "enrichers", "merge"]:
        if fld not in composite:
            gaps.critical.append(f"Missing composite.{fld}")

    # === Seed validation ===
    seed = _as_dict(composite.get("seed"))
    if seed:
        for fld in ["pipeline", "output_keys", "silver_table"]:
            if fld not in seed:
                gaps.medium.append(f"Missing composite.seed.{fld}")

    # === Enrichers validation ===
    enrichers = composite.get("enrichers", [])
    for i, enricher in enumerate(enrichers):
        if "pipeline" not in enricher:
            gaps.critical.append(f"Missing pipeline in enricher[{i}]")
        if "join_keys" not in enricher:
            gaps.medium.append(f"Missing join_keys in enricher[{i}]")
        if "silver_table" not in enricher:
            gaps.medium.append(f"Missing silver_table in enricher[{i}]")

    # === Merge validation ===
    merge = _as_dict(composite.get("merge"))
    if merge:
        if "strategy" not in merge:
            gaps.medium.append("Missing composite.merge.strategy")
        output = _as_dict(merge.get("output"))
        if not output.get("silver"):
            gaps.medium.append("Missing composite.merge.output.silver")
        if not output.get("gold"):
            gaps.low.append("Missing composite.merge.output.gold")

    # === ADR-027: DQ rules in composite ===
    if "dq_overrides" in config:
        dq = config["dq_overrides"]
        if "soft_fail_threshold" in dq or "hard_fail_threshold" in dq:
            gaps.medium.append(
                "Inline dq_overrides thresholds in composite (deprecated per ADR-027)"
            )

    # Note: Composite pipelines don't have standard sink structure
    # sort_by would be defined in the individual pipelines that composite references


def analyze_config(config_path: Path) -> ConfigGaps:
    """Analyze single config for ADR compliance."""
    gaps = ConfigGaps(path=config_path)

    try:
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        gaps.critical.append(f"YAML parse error: {e}")
        return gaps

    if not config:
        gaps.critical.append("Empty config file")
        return gaps

    # Detect composite vs standard config
    if "composite" in config:
        analyze_composite_config(config, gaps)
    elif isinstance(config.get("pipeline"), dict):
        pipeline_config = dict(config["pipeline"])
        pipeline_config.setdefault("provider", config.get("provider"))
        pipeline_config.setdefault("entity_type", config.get("entity"))
        analyze_standard_config(pipeline_config, gaps, config)
        for section in ("schema", "quality", "filters", "contracts"):
            if section not in config:
                gaps.critical.append(f"Missing unified section: {section}")
    else:
        analyze_standard_config(config, gaps)
        gaps.low.append("Legacy standalone pipeline format detected")

    return gaps


def generate_report(all_gaps: list[ConfigGaps]) -> str:
    """Generate markdown report."""
    standard_gaps = [g for g in all_gaps if not g.is_composite]
    composite_gaps = [g for g in all_gaps if g.is_composite]

    lines = [
        "# Config Gap Analysis Report",
        "",
        f"**Date**: {date.today()}",
        "**Baseline**: ADR-014 (Deterministic Writes), ADR-025 (Config Unification), ADR-027/028 (Unified DQ/Filter Hierarchy), ADR-029 (Convention-based Resolution)",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|--------|-------|",
        f"| Total configs analyzed | {len(all_gaps)} |",
        f"| Standard pipeline configs | {len(standard_gaps)} |",
        f"| Composite pipeline configs | {len(composite_gaps)} |",
        f"| With critical issues | {sum(1 for g in all_gaps if g.critical)} |",
        f"| With medium issues | {sum(1 for g in all_gaps if g.medium)} |",
        f"| With low issues | {sum(1 for g in all_gaps if g.low)} |",
        f"| Clean (no issues) | {sum(1 for g in all_gaps if not g.total)} |",
        "",
        "### Issue Counts by Severity",
        "",
        "| Severity | Total Issues |",
        "|----------|-------------|",
        f"| Critical (MUST fix) | {sum(len(g.critical) for g in all_gaps)} |",
        f"| Medium (SHOULD fix) | {sum(len(g.medium) for g in all_gaps)} |",
        f"| Low (MAY fix) | {sum(len(g.low) for g in all_gaps)} |",
        "",
    ]

    def _rel(path: Path) -> Path:
        for root in (ENTITY_CONFIGS_DIR, COMPOSITES_DIR):
            try:
                return path.relative_to(root)
            except ValueError:
                continue
        return path

    # Critical
    critical_gaps = [g for g in all_gaps if g.critical]
    if critical_gaps:
        lines.extend(["## Critical Issues (MUST fix)", ""])
        for g in critical_gaps:
            rel = _rel(g.path)
            config_type = " (composite)" if g.is_composite else ""
            lines.append(f"### `{rel}`{config_type}")
            for issue in g.critical:
                lines.append(f"- [CRIT] {issue}")
            lines.append("")
    else:
        lines.extend(
            ["## Critical Issues (MUST fix)", "", "No critical issues found.", ""]
        )

    # Medium
    medium_gaps = [g for g in all_gaps if g.medium]
    if medium_gaps:
        lines.extend(["## Medium Issues (SHOULD fix)", ""])
        for g in medium_gaps:
            rel = _rel(g.path)
            config_type = " (composite)" if g.is_composite else ""
            lines.append(f"### `{rel}`{config_type}")
            for issue in g.medium:
                lines.append(f"- [WARN] {issue}")
            lines.append("")

    # Low
    low_gaps = [g for g in all_gaps if g.low]
    if low_gaps:
        lines.extend(["## Low Issues (MAY fix)", ""])
        for g in low_gaps:
            rel = _rel(g.path)
            config_type = " (composite)" if g.is_composite else ""
            lines.append(f"### `{rel}`{config_type}")
            for issue in g.low:
                lines.append(f"- [INFO] {issue}")
            lines.append("")

    # Action items
    lines.extend(
        [
            "## Recommended Actions",
            "",
            "### Priority 0 (Critical - Blocks CI)",
            "1. Add missing required pipeline fields (`pipeline_name`, `provider`, `entity_type`, `business_primary_keys`)",
            "2. Ensure `contracts.primary_key` exists and is aligned with `pipeline.business_primary_keys`",
            "3. Add missing unified sections (`pipeline`, `schema`, `quality`, `filters`, `contracts`)",
            "",
            "### Priority 1 (Medium - Should Fix)",
            "1. Add `pipeline.description` and semver `version` where missing",
            "2. Migrate inline `dq_overrides` thresholds into the unified `quality` hierarchy when possible (ADR-027)",
            "3. Keep `pipeline.sink` keys aligned with `PipelineYamlConfig` schema",
            "",
            "### Priority 2 (Low - Nice to Have)",
            "1. Unify `sink.*.path` to end with `{provider}/{entity}`",
            "2. Remove legacy explicit path overrides such as `dq_config_file` / `filter_config_file` unless a compatibility case is documented",
            "3. Add `filters.gold_filters.required_fields` where missing",
            "",
            "## ADR References",
            "",
            "- [ADR-014](docs/02-architecture/decisions/ADR-014-deterministic-writes.md): Deterministic Writes",
            "- [ADR-025](docs/02-architecture/decisions/ADR-025-pipeline-config-unification.md): Pipeline Config Unification",
            "- [ADR-027](docs/02-architecture/decisions/ADR-027-dq-rules-externalization.md): DQ Rules Externalization",
            "- [ADR-028](docs/02-architecture/decisions/ADR-028-filter-rules-externalization.md): Filter Rules Externalization",
            "- [ADR-029](docs/02-architecture/decisions/ADR-029-convention-based-configuration.md): Convention-based Configuration",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Gap analysis for pipeline configs against ADR requirements"
    )
    parser.add_argument("-o", "--output", help="Output file path for markdown report")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Print detailed output"
    )
    args = parser.parse_args()

    all_gaps: list[ConfigGaps] = []
    config_files = sorted(ENTITY_CONFIGS_DIR.rglob("*.yaml")) + sorted(
        COMPOSITES_DIR.glob("*.yaml")
    )
    for cfg in config_files:
        if cfg.name.startswith("_"):
            continue
        gaps = analyze_config(cfg)
        all_gaps.append(gaps)

        if args.verbose:
            rel = cfg
            for root in (ENTITY_CONFIGS_DIR, COMPOSITES_DIR):
                try:
                    rel = cfg.relative_to(root)
                    break
                except ValueError:
                    continue
            status = (
                "[FAIL]"
                if gaps.critical
                else ("[WARN]" if gaps.medium else ("[INFO]" if gaps.low else "[OK]"))
            )
            print(
                f"{status} {rel}: {len(gaps.critical)} critical, {len(gaps.medium)} medium, {len(gaps.low)} low"
            )

    report = generate_report(all_gaps)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(report)
        print(f"Report written to: {args.output}")
    else:
        print(report)

    # Summary
    critical_count = sum(len(g.critical) for g in all_gaps)
    medium_count = sum(len(g.medium) for g in all_gaps)
    low_count = sum(len(g.low) for g in all_gaps)

    print(f"\n{'=' * 60}")
    print(
        f"Summary: {critical_count} critical, {medium_count} medium, {low_count} low issues"
    )
    print(f"{'=' * 60}")

    # Exit code based on critical issues
    return 1 if critical_count else 0


if __name__ == "__main__":
    sys.exit(main())
