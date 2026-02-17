#!/usr/bin/env python3
"""Gap analysis for pipeline configs against ADR-014/025/027.

Checks pipeline configurations for compliance with:
- ADR-014: Deterministic Writes (sort_by requirements)
- ADR-025: Pipeline Config Unification (required/recommended fields)
- ADR-027: DQ Rules Externalization (inline thresholds deprecated)

Usage:
    python scripts/config_gap_analysis.py
    python scripts/config_gap_analysis.py -o docs/audits/config_gaps.md
"""

import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

CONFIGS_DIR = Path("configs/pipelines")
DQ_DIR = Path("configs/quality")


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


def analyze_standard_config(config: dict, gaps: ConfigGaps) -> None:
    """Analyze standard (non-composite) pipeline config."""
    # === ADR-025: Required fields (MUST) ===
    for fld in [
        "pipeline_name",
        "provider",
        "entity_type",
        "primary_keys",
        "silver_table",
    ]:
        if fld not in config:
            gaps.critical.append(f"Missing MUST field: {fld}")

    # === ADR-025: Recommended fields (SHOULD) ===
    for fld in ["version", "description", "gold_table"]:
        if fld not in config:
            gaps.medium.append(f"Missing SHOULD field: {fld}")

    # === ADR-025: Version format ===
    version = config.get("version", "")
    if version and not re.match(r"^\d+\.\d+\.\d+$", str(version)):
        gaps.medium.append(f"Version '{version}' not semver format")

    # === ADR-014: sort_by in sink ===
    sink = config.get("sink", {})

    # Check silver sink
    silver = sink.get("silver", {})
    if silver:
        if "sort_by" not in silver:
            gaps.critical.append("Missing sink.silver.sort_by (ADR-014)")
        if "primary_key" not in silver:
            gaps.critical.append("Missing sink.silver.primary_key (ADR-025)")
    else:
        gaps.critical.append("Missing sink.silver section")

    # Check gold sink
    gold = sink.get("gold", {})
    if gold:
        # Gold is enabled by default unless explicitly disabled
        gold_enabled = gold.get("enabled", True)
        if gold_enabled and "sort_by" not in gold:
            gaps.critical.append("Missing sink.gold.sort_by (ADR-014)")
    else:
        # Missing gold section is medium - not all pipelines need Gold
        gaps.medium.append("Missing sink.gold section")

    # Check bronze sink
    if "bronze" not in sink:
        gaps.medium.append("Missing sink.bronze section")

    # === ADR-025: Hierarchical paths (SHOULD) ===
    provider = config.get("provider", "")
    entity = config.get("entity_type", "")
    if provider and entity:
        expected_pattern = f"{provider}/{entity}"
        for layer in ["bronze", "silver", "gold"]:
            layer_cfg = sink.get(layer, {})
            path = layer_cfg.get("path", "")
            if path and expected_pattern not in path:
                gaps.low.append(
                    f"sink.{layer}.path not hierarchical ({provider}/{entity})"
                )

    # === ADR-027: DQ rules ===
    if "dq_overrides" in config:
        dq = config["dq_overrides"]
        # Check for inline thresholds (deprecated)
        if "soft_fail_threshold" in dq or "hard_fail_threshold" in dq:
            gaps.medium.append("Inline dq_overrides thresholds (deprecated per ADR-027)")

    # Check for dq_config_file reference
    if "dq_config_file" not in config:
        if provider and entity:
            expected_dq = DQ_DIR / "entities" / provider / f"{entity}.yaml"
            if expected_dq.exists():
                gaps.low.append(
                    f"DQ file exists at {expected_dq.relative_to('.')} but not referenced"
                )
            else:
                gaps.low.append(
                    f"No dq_config_file and no DQ file at entities/{provider}/{entity}.yaml"
                )

    # === ADR-025: gold_filters ===
    gf = config.get("gold_filters", {})
    if not gf:
        gaps.low.append("Missing gold_filters section")
    elif not gf.get("required_fields"):
        gaps.low.append("gold_filters.required_fields empty or missing")


def analyze_composite_config(config: dict, gaps: ConfigGaps) -> None:
    """Analyze composite pipeline config (ADR-026 structure)."""
    gaps.is_composite = True

    composite = config.get("composite", {})

    # === Required composite fields ===
    if not composite:
        gaps.critical.append("Missing 'composite' section for composite pipeline")
        return

    for fld in ["name", "version", "seed", "enrichers", "merge"]:
        if fld not in composite:
            gaps.critical.append(f"Missing composite.{fld}")

    # === Seed validation ===
    seed = composite.get("seed", {})
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
    merge = composite.get("merge", {})
    if merge:
        if "strategy" not in merge:
            gaps.medium.append("Missing composite.merge.strategy")
        output = merge.get("output", {})
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
        with open(config_path) as f:
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
    else:
        analyze_standard_config(config, gaps)

    return gaps


def generate_report(all_gaps: list[ConfigGaps]) -> str:
    """Generate markdown report."""
    standard_gaps = [g for g in all_gaps if not g.is_composite]
    composite_gaps = [g for g in all_gaps if g.is_composite]

    lines = [
        "# Config Gap Analysis Report",
        "",
        f"**Date**: {date.today()}",
        "**Baseline**: ADR-014 (Deterministic Writes), ADR-025 (Config Unification), ADR-027 (DQ Externalization)",
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

    # Critical
    critical_gaps = [g for g in all_gaps if g.critical]
    if critical_gaps:
        lines.extend(["## Critical Issues (MUST fix)", ""])
        for g in critical_gaps:
            rel = g.path.relative_to(CONFIGS_DIR)
            config_type = " (composite)" if g.is_composite else ""
            lines.append(f"### `{rel}`{config_type}")
            for issue in g.critical:
                lines.append(f"- ❌ {issue}")
            lines.append("")
    else:
        lines.extend(
            ["## Critical Issues (MUST fix)", "", "✅ No critical issues found!", ""]
        )

    # Medium
    medium_gaps = [g for g in all_gaps if g.medium]
    if medium_gaps:
        lines.extend(["## Medium Issues (SHOULD fix)", ""])
        for g in medium_gaps:
            rel = g.path.relative_to(CONFIGS_DIR)
            config_type = " (composite)" if g.is_composite else ""
            lines.append(f"### `{rel}`{config_type}")
            for issue in g.medium:
                lines.append(f"- ⚠️ {issue}")
            lines.append("")

    # Low
    low_gaps = [g for g in all_gaps if g.low]
    if low_gaps:
        lines.extend(["## Low Issues (MAY fix)", ""])
        for g in low_gaps:
            rel = g.path.relative_to(CONFIGS_DIR)
            config_type = " (composite)" if g.is_composite else ""
            lines.append(f"### `{rel}`{config_type}")
            for issue in g.low:
                lines.append(f"- ℹ️ {issue}")
            lines.append("")

    # Action items
    lines.extend(
        [
            "## Recommended Actions",
            "",
            "### Priority 0 (Critical - Blocks CI)",
            "1. Add `sort_by` to all silver sinks (ADR-014 compliance)",
            "2. Add `sort_by` to all gold sinks where gold.enabled=true (ADR-014)",
            "3. Add `primary_key` to all silver sinks (ADR-025 compliance)",
            "4. Add required fields: `pipeline_name`, `provider`, `entity_type`, `primary_keys`, `silver_table`",
            "",
            "### Priority 1 (Medium - Should Fix)",
            "1. Add `version`, `description`, `gold_table` where missing (ADR-025)",
            "2. Migrate inline `dq_overrides` thresholds to `dq_config_file` (ADR-027)",
            "3. Add missing `sink.bronze` and `sink.gold` sections",
            "",
            "### Priority 2 (Low - Nice to Have)",
            "1. Unify path patterns to `{provider}/{entity}` hierarchy",
            "2. Reference existing DQ config files via `dq_config_file`",
            "3. Add `gold_filters.required_fields` where missing",
            "",
            "## ADR References",
            "",
            "- [ADR-014](docs/02-architecture/decisions/ADR-014-deterministic-writes.md): Deterministic Writes",
            "- [ADR-025](docs/02-architecture/decisions/ADR-025-pipeline-config-unification.md): Pipeline Config Unification",
            "- [ADR-027](docs/02-architecture/decisions/ADR-027-dq-rules-externalization.md): DQ Rules Externalization",
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
    for cfg in sorted(CONFIGS_DIR.rglob("*.yaml")):
        if cfg.name.startswith("_"):
            continue
        gaps = analyze_config(cfg)
        all_gaps.append(gaps)

        if args.verbose:
            rel = cfg.relative_to(CONFIGS_DIR)
            status = (
                "❌"
                if gaps.critical
                else ("⚠️" if gaps.medium else ("ℹ️" if gaps.low else "✅"))
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
