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
COMPOSITE_SUFFIX = " (composite)"


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


def _validate_required_pipeline_fields(
    pipeline_config: dict[str, Any],
) -> tuple[list[str], list[str], list[str]]:
    """Return critical/medium/low gaps for required standard fields."""
    critical: list[str] = []
    medium: list[str] = []
    low: list[str] = []
    for field_name in (
        "pipeline_name",
        "provider",
        "entity_type",
        "business_primary_keys",
    ):
        if field_name not in pipeline_config:
            critical.append(f"Missing MUST field: pipeline.{field_name}")
    business_keys = pipeline_config.get("business_primary_keys")
    if not isinstance(business_keys, list) or not business_keys:
        critical.append("pipeline.business_primary_keys must be a non-empty list")
    return critical, medium, low


def _validate_recommended_metadata(
    pipeline_config: dict[str, Any],
    top: dict[str, Any],
) -> tuple[list[str], list[str], list[str]]:
    """Return gaps for recommended metadata and version formatting."""
    medium: list[str] = []
    if "version" not in top:
        medium.append("Missing SHOULD field: top-level version")
    if "description" not in pipeline_config:
        medium.append("Missing SHOULD field: pipeline.description")
    version = top.get("version")
    if version and not re.match(r"^\d+\.\d+\.\d+$", str(version)):
        medium.append(f"Version '{version}' not semver format")
    return [], medium, []


def _validate_contract_alignment(
    pipeline_config: dict[str, Any],
    top: dict[str, Any],
) -> tuple[list[str], list[str], list[str]]:
    """Return gaps for contract primary key alignment."""
    critical: list[str] = []
    medium: list[str] = []
    contracts = _as_dict(top.get("contracts"))
    contract_pk = contracts.get("primary_key")
    business_keys = pipeline_config.get("business_primary_keys")
    if contract_pk is None:
        critical.append("Missing MUST field: contracts.primary_key")
    elif isinstance(business_keys, list) and isinstance(contract_pk, list):
        if sorted(str(v) for v in business_keys) != sorted(str(v) for v in contract_pk):
            medium.append(
                "Mismatch between pipeline.business_primary_keys and contracts.primary_key"
            )
    return critical, medium, []


def _validate_sink_path_suffixes(
    pipeline_config: dict[str, Any],
) -> tuple[list[str], list[str], list[str]]:
    """Return low-severity sink path hierarchy gaps."""
    provider = pipeline_config.get("provider", "")
    entity = pipeline_config.get("entity_type", "")
    sink = _as_dict(pipeline_config.get("sink"))
    if not (provider and entity and sink):
        return [], [], []
    expected_suffix = f"{provider}/{entity}"
    low: list[str] = []
    for layer in ("bronze", "silver", "gold"):
        layer_cfg = _as_dict(sink.get(layer))
        path = layer_cfg.get("path", "")
        if isinstance(path, str) and path and not path.endswith(expected_suffix):
            low.append(
                f"sink.{layer}.path should end with '{expected_suffix}' (got '{path}')"
            )
    return [], [], low


def _validate_inline_dq_thresholds(
    pipeline_config: dict[str, Any],
    top: dict[str, Any],
) -> tuple[list[str], list[str], list[str]]:
    """Return deprecated inline DQ threshold findings."""
    medium: list[str] = []
    for dq_parent_name, dq_parent in (
        ("top-level", top),
        ("pipeline", pipeline_config),
    ):
        dq = _as_dict(dq_parent.get("dq_overrides"))
        if "soft_fail_threshold" in dq or "hard_fail_threshold" in dq:
            medium.append(
                f"Inline dq_overrides thresholds in {dq_parent_name} (deprecated per ADR-027)"
            )
    return [], medium, []


def _validate_gold_filters(
    top: dict[str, Any],
) -> tuple[list[str], list[str], list[str]]:
    """Return findings for missing gold filter declarations."""
    low: list[str] = []
    filters = _as_dict(top.get("filters"))
    gold_filters = _as_dict(filters.get("gold_filters"))
    if not gold_filters:
        low.append("Missing filters.gold_filters section")
    elif not gold_filters.get("required_fields"):
        low.append("filters.gold_filters.required_fields empty or missing")
    return [], [], low


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
    top = full_config or {}
    validators = (
        _validate_required_pipeline_fields,
        lambda cfg: _validate_recommended_metadata(cfg, top),
        lambda cfg: _validate_contract_alignment(cfg, top),
        _validate_sink_path_suffixes,
        lambda cfg: _validate_inline_dq_thresholds(cfg, top),
        lambda _cfg: _validate_gold_filters(top),
    )
    for validator in validators:
        critical, medium, low = validator(pipeline_config)
        gaps.critical.extend(critical)
        gaps.medium.extend(medium)
        gaps.low.extend(low)


def _validate_composite_seed(
    seed: dict[str, Any],
) -> tuple[list[str], list[str], list[str]]:
    """Return findings for composite seed configuration."""
    medium: list[str] = []
    if seed:
        for field_name in ("pipeline", "output_keys", "silver_table"):
            if field_name not in seed:
                medium.append(f"Missing composite.seed.{field_name}")
    return [], medium, []


def _validate_composite_enrichers(
    enrichers: Any,
) -> tuple[list[str], list[str], list[str]]:
    """Return findings for composite enricher declarations."""
    critical: list[str] = []
    medium: list[str] = []
    for index, enricher in enumerate(enrichers if isinstance(enrichers, list) else []):
        if "pipeline" not in enricher:
            critical.append(f"Missing pipeline in enricher[{index}]")
        if "join_keys" not in enricher:
            medium.append(f"Missing join_keys in enricher[{index}]")
        if "silver_table" not in enricher:
            medium.append(f"Missing silver_table in enricher[{index}]")
    return critical, medium, []


def _validate_composite_merge(
    merge: dict[str, Any],
) -> tuple[list[str], list[str], list[str]]:
    """Return findings for composite merge configuration."""
    medium: list[str] = []
    low: list[str] = []
    if merge:
        if "strategy" not in merge:
            medium.append("Missing composite.merge.strategy")
        output = _as_dict(merge.get("output"))
        if not output.get("silver"):
            medium.append("Missing composite.merge.output.silver")
        if not output.get("gold"):
            low.append("Missing composite.merge.output.gold")
    return [], medium, low


def _validate_composite_dq_overrides(
    config: dict[str, Any],
) -> tuple[list[str], list[str], list[str]]:
    """Return findings for deprecated composite inline DQ thresholds."""
    dq = config.get("dq_overrides")
    if not isinstance(dq, dict):
        return [], [], []
    if "soft_fail_threshold" in dq or "hard_fail_threshold" in dq:
        return (
            [],
            ["Inline dq_overrides thresholds in composite (deprecated per ADR-027)"],
            [],
        )
    return [], [], []


def analyze_composite_config(config: dict[str, Any], gaps: ConfigGaps) -> None:
    """Analyze composite pipeline config (ADR-026 structure)."""
    gaps.is_composite = True

    composite = _as_dict(config.get("composite"))

    # === Required composite fields ===
    if not composite:
        gaps.critical.append("Missing 'composite' section for composite pipeline")
        return

    for field_name in ("name", "version", "seed", "enrichers", "merge"):
        if field_name not in composite:
            gaps.critical.append(f"Missing composite.{field_name}")
    validators = (
        lambda: _validate_composite_seed(_as_dict(composite.get("seed"))),
        lambda: _validate_composite_enrichers(composite.get("enrichers", [])),
        lambda: _validate_composite_merge(_as_dict(composite.get("merge"))),
        lambda: _validate_composite_dq_overrides(config),
    )
    for validator in validators:
        critical, medium, low = validator()
        gaps.critical.extend(critical)
        gaps.medium.extend(medium)
        gaps.low.extend(low)

    # Note: Composite pipelines don't have standard sink structure
    # sort_by would be defined in the individual pipelines that composite references


def analyze_config(config_path: Path) -> ConfigGaps:
    """Analyze single config for ADR compliance."""
    gaps = ConfigGaps(path=config_path)

    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except Exception as exc:
        gaps.critical.append(f"YAML parse error: {exc}")
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


def _relative_config_path(path: Path) -> Path:
    """Return config path relative to entity/composite roots when possible."""
    for root in (ENTITY_CONFIGS_DIR, COMPOSITES_DIR):
        try:
            return path.relative_to(root)
        except ValueError:
            continue
    return path


def _config_type_suffix(gaps: ConfigGaps) -> str:
    """Return printable config type suffix."""
    return COMPOSITE_SUFFIX if gaps.is_composite else ""


def _append_gap_section(
    lines: list[str],
    *,
    heading: str,
    gaps_list: list[ConfigGaps],
    attribute: str,
    marker: str,
    empty_message: str | None = None,
) -> None:
    """Append one severity section to the report."""
    if not gaps_list and empty_message is None:
        return
    lines.extend([heading, ""])
    if not gaps_list:
        lines.extend([empty_message or "", ""])
        return
    for gaps in gaps_list:
        rel = _relative_config_path(gaps.path)
        lines.append(f"### `{rel}`{_config_type_suffix(gaps)}")
        for issue in getattr(gaps, attribute):
            lines.append(f"- {marker} {issue}")
        lines.append("")


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

    _append_gap_section(
        lines,
        heading="## Critical Issues (MUST fix)",
        gaps_list=[g for g in all_gaps if g.critical],
        attribute="critical",
        marker="[CRIT]",
        empty_message="No critical issues found.",
    )
    _append_gap_section(
        lines,
        heading="## Medium Issues (SHOULD fix)",
        gaps_list=[g for g in all_gaps if g.medium],
        attribute="medium",
        marker="[WARN]",
    )
    _append_gap_section(
        lines,
        heading="## Low Issues (MAY fix)",
        gaps_list=[g for g in all_gaps if g.low],
        attribute="low",
        marker="[INFO]",
    )

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


def _status_for_gaps(gaps: ConfigGaps) -> str:
    """Return printable status tag for one config report line."""
    if gaps.critical:
        return "[FAIL]"
    if gaps.medium:
        return "[WARN]"
    if gaps.low:
        return "[INFO]"
    return "[OK]"


def _print_verbose_config_status(cfg: Path, gaps: ConfigGaps) -> None:
    """Print one verbose config status line."""
    rel = _relative_config_path(cfg)
    status = _status_for_gaps(gaps)
    print(
        f"{status} {rel}: {len(gaps.critical)} critical, "
        f"{len(gaps.medium)} medium, {len(gaps.low)} low"
    )


def _iter_config_files() -> list[Path]:
    """Return all config files participating in the audit."""
    return sorted(ENTITY_CONFIGS_DIR.rglob("*.yaml")) + sorted(
        COMPOSITES_DIR.glob("*.yaml")
    )


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
    config_files = _iter_config_files()
    for cfg in config_files:
        if cfg.name.startswith("_"):
            continue
        gaps = analyze_config(cfg)
        all_gaps.append(gaps)
        if args.verbose:
            _print_verbose_config_status(cfg, gaps)

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
