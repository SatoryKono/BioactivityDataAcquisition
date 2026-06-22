#!/usr/bin/env python3
"""Generate comparison matrix for unified entity/composite configs."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from scripts.engineering.qa.config_surface_governance import is_sanctioned_partial_key

DEFAULT_BASELINE_JSON = Path("reports/quality/config-discrepancy-baseline.json")
SANCTIONED_DEFAULT_SCALAR = "<sanctioned-default>"
CONFIG_PARAMETER_TAXONOMY_OWNER = "BioETL Team"
_DEFAULT_TAXONOMY_GROUP = "domain_entity_contract"
_TAXONOMY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "compatibility_legacy",
        ("compat", "legacy", "deprecated", "alias"),
    ),
    (
        "replay_provenance",
        (
            "manifest",
            "ledger",
            "lineage",
            "provenance",
            "replay",
            "snapshot",
            "fingerprint",
            "content_hash",
        ),
    ),
    (
        "observability",
        ("observability", "metrics", "tracing", "logging", "health", "telemetry"),
    ),
    (
        "dq_validation",
        ("quality", "dq", "validation", "schema", "contract", "rule", "quarantine"),
    ),
    (
        "medallion_write_policy",
        ("sink", "storage", "bronze", "silver", "gold", "delta", "write", "partition"),
    ),
    (
        "provider_source_access",
        (
            "source",
            "api",
            "adapter",
            "endpoint",
            "request",
            "query",
            "rate_limit",
            "pagination",
            "extraction_params",
        ),
    ),
    (
        "runtime_control_plane",
        (
            "pipeline",
            "runtime",
            "execution",
            "checkpoint",
            "lock",
            "batch",
            "incremental",
            "schedule",
        ),
    ),
)
_DERIVED_ENTITY_PARAMETER_PREFIXES: tuple[str, ...] = (
    "contracts.contract_ref",
    "contracts.active_version",
    "contracts.rollout",
)


def flatten_dict(d: dict[str, Any], parent_key: str = "") -> dict[str, Any]:
    """Flatten nested dict to dot-notation keys."""
    items: dict[str, Any] = {}
    for key, value in d.items():
        new_key = f"{parent_key}.{key}" if parent_key else key
        if isinstance(value, dict):
            items[new_key] = "(dict)"
            items.update(flatten_dict(value, new_key))
        elif isinstance(value, list):
            items[new_key] = json.dumps(value, ensure_ascii=False) if value else "[]"
        else:
            items[new_key] = str(value) if value is not None else "null"
    return items


def _exclude_derived_entity_parameters(
    flattened: dict[str, Any],
) -> dict[str, Any]:
    """Drop deterministic contract mirror fields from config-surface debt metrics.

    These fields remain explicit in entity YAML for runtime identity validation, but
    they are derived from other governed sources (`provider`, `entity`,
    `hash_policy.contract.version`) and should not inflate discrepancy-budget
    parameter counts.
    """
    return {
        key: value
        for key, value in flattened.items()
        if not any(
            key == prefix or key.startswith(f"{prefix}.")
            for prefix in _DERIVED_ENTITY_PARAMETER_PREFIXES
        )
    }


def load_config(path: Path) -> dict[str, Any]:
    """Load a YAML config file as a mapping."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else {}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_pipeline_defaults() -> dict[str, Any]:
    defaults_path = Path("configs/base/pipeline.yaml")
    if not defaults_path.exists():
        return {}
    payload = load_config(defaults_path)
    payload.pop("schema_version", None)
    return payload


def _load_quality_defaults() -> dict[str, Any]:
    defaults_path = Path("configs/base/quality.yaml")
    if not defaults_path.exists():
        return {}
    payload = load_config(defaults_path)
    payload.pop("version", None)
    return payload


def _entity_config_effective(path: Path) -> dict[str, Any]:
    """Return entity YAML with runtime-applied defaults merged for governance."""
    raw = load_config(path)
    effective = dict(raw)
    pipeline = raw.get("pipeline")
    if isinstance(pipeline, dict):
        effective["pipeline"] = _deep_merge(_load_pipeline_defaults(), pipeline)

    quality = raw.get("quality")
    quality_defaults = _load_quality_defaults()
    if quality_defaults:
        effective["quality"] = _deep_merge(
            quality_defaults,
            quality if isinstance(quality, dict) else {},
        )
    return effective


def _partial_keys(configs: dict[str, dict[str, Any]]) -> list[str]:
    all_keys = sorted({key for values in configs.values() for key in values})
    if not configs:
        return []
    common = set.intersection(*(set(values.keys()) for values in configs.values()))
    return [key for key in all_keys if key not in common]


def _sanctioned_placeholder(values: list[Any]) -> Any:
    """Preserve coarse shape while collapsing sanctioned missing-vs-empty variance."""
    if "(dict)" in values:
        return "(dict)"
    if "[]" in values:
        return "[]"
    if "null" in values:
        return "null"
    return SANCTIONED_DEFAULT_SCALAR


def _normalize_sanctioned_family_presence(
    configs: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Treat sanctioned optional shapes as present across a governed family.

    This projection is for governance metrics only. It collapses structural
    missing-vs-empty variance for keys already documented as sanctioned without
    mutating the raw config comparison matrix.
    """
    sanctioned_keys = sorted(
        {
            key
            for values in configs.values()
            for key in values
            if is_sanctioned_partial_key(key)
        },
        key=_sort_key,
    )
    placeholders = {
        key: _sanctioned_placeholder(
            [values[key] for values in configs.values() if key in values]
        )
        for key in sanctioned_keys
    }

    normalized: dict[str, dict[str, Any]] = {}
    for name, payload in configs.items():
        projected = dict(payload)
        for key in sanctioned_keys:
            projected.setdefault(key, placeholders[key])
        normalized[name] = projected
    return normalized


def _family_metrics(configs: dict[str, dict[str, Any]]) -> dict[str, int]:
    partial = _partial_keys(configs)
    actionable_partial = [key for key in partial if not is_sanctioned_partial_key(key)]
    all_keys = sorted({key for values in configs.values() for key in values})
    return {
        "config_count": len(configs),
        "unique_parameter_count": len(all_keys),
        "inconsistent_parameter_count": len(actionable_partial),
        "sanctioned_partial_parameter_count": len(partial) - len(actionable_partial),
        "raw_inconsistent_parameter_count": len(partial),
    }


def _classify_parameter_key(key: str) -> str:
    normalized = key.lower().replace("-", "_")
    for group_name, needles in _TAXONOMY_RULES:
        if any(needle in normalized for needle in needles):
            return group_name
    return _DEFAULT_TAXONOMY_GROUP


def _family_parameter_taxonomy(configs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    all_keys = sorted({key for values in configs.values() for key in values})
    groups: dict[str, int] = {}
    examples: dict[str, list[str]] = {}
    for key in all_keys:
        group_name = _classify_parameter_key(key)
        groups[group_name] = groups.get(group_name, 0) + 1
        examples.setdefault(group_name, [])
        if len(examples[group_name]) < 5:
            examples[group_name].append(key)
    return {
        "owner": CONFIG_PARAMETER_TAXONOMY_OWNER,
        "parameter_count": len(all_keys),
        "groups": dict(sorted(groups.items())),
        "examples": {key: examples[key] for key in sorted(examples)},
        "unclassified_parameter_count": 0,
        "unclassified_parameters": [],
    }


def build_config_parameter_taxonomy_payload() -> dict[str, Any]:
    """Return family-scoped config parameter ownership/taxonomy metadata."""
    families = _collect_family_configs()
    return {
        "owner": CONFIG_PARAMETER_TAXONOMY_OWNER,
        "classification_mode": "derived_from_flattened_config_parameter_paths",
        "default_group": _DEFAULT_TAXONOMY_GROUP,
        "families": {
            family_name: _family_parameter_taxonomy(family_configs)
            for family_name, family_configs in families.items()
        },
    }


def _partition_partial_keys(partial: list[str]) -> tuple[list[str], list[str]]:
    actionable = [key for key in partial if not is_sanctioned_partial_key(key)]
    sanctioned = [key for key in partial if is_sanctioned_partial_key(key)]
    return actionable, sanctioned


def _parameter_presence_line(
    key: str,
    *,
    configs: dict[str, dict[str, Any]],
    total_configs: int,
) -> str:
    present_in = [cfg for cfg, data in configs.items() if key in data]
    return f"- `{key}` ({len(present_in)}/{total_configs}): {', '.join(present_in)}"


def _collect_configs() -> dict[str, dict[str, Any]]:
    configs: dict[str, dict[str, Any]] = {}

    entities_dir = Path("configs/entities")
    for yaml_file in sorted(entities_dir.rglob("*.yaml")):
        if yaml_file.name.startswith("_"):
            continue
        provider = yaml_file.relative_to(entities_dir).parts[0]
        if provider == "composite":
            # Composite runtime is governed by configs/composites/*.yaml; legacy
            # configs/entities/composite/*.yaml stubs are out of scope here.
            continue
        rel = yaml_file.relative_to(entities_dir)
        name = f"entity/{rel.parent.name}/{rel.stem}"
        configs[name] = _exclude_derived_entity_parameters(
            flatten_dict(_entity_config_effective(yaml_file))
        )

    composites_dir = Path("configs/composites")
    for yaml_file in sorted(composites_dir.glob("*.yaml")):
        if yaml_file.name.startswith("_"):
            continue
        name = f"composite/{yaml_file.stem}"
        configs[name] = flatten_dict(load_config(yaml_file))

    return configs


def _collect_family_configs() -> dict[str, dict[str, dict[str, Any]]]:
    all_configs = _collect_configs()
    families: dict[str, dict[str, dict[str, Any]]] = {
        "entity_effective": {},
        "composite_runtime": {},
    }
    for name, payload in all_configs.items():
        if name.startswith("entity/"):
            families["entity_effective"][name] = payload
        elif name.startswith("composite/"):
            families["composite_runtime"][name] = payload
    return {
        family_name: _normalize_sanctioned_family_presence(family_payload)
        for family_name, family_payload in families.items()
    }


def _sort_key(path: str) -> tuple[int, list[str]]:
    parts = path.split(".")
    return (len(parts), parts)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="Fail if committed config matrix/report artifacts are stale.",
    )
    mode.add_argument(
        "--update",
        action="store_true",
        help="Write generated config matrix/report artifacts (default).",
    )
    parser.add_argument(
        "--matrix-output",
        type=Path,
        default=Path("docs/04-reference/config_comparison_matrix.csv"),
        help="CSV matrix output path.",
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=Path("docs/config-discrepancies-report.md"),
        help="Markdown discrepancy report output path.",
    )
    parser.add_argument(
        "--baseline-json-out",
        type=Path,
        default=DEFAULT_BASELINE_JSON,
        help="JSON baseline output path for config-surface ratchet metrics.",
    )
    return parser.parse_args(argv)


def _build_artifact_contents() -> tuple[str, str, int, int, int, int, int]:
    """Build matrix/report contents without writing files."""
    configs = _collect_configs()
    family_configs = _collect_family_configs()
    all_keys = sorted(
        {key for values in configs.values() for key in values}, key=_sort_key
    )
    config_names = sorted(configs.keys())

    if configs:
        common = set.intersection(*(set(values.keys()) for values in configs.values()))
    else:
        common = set()

    family_breakdowns: list[
        tuple[str, dict[str, dict[str, Any]], list[str], list[str]]
    ] = []
    for family_name, family_payload in family_configs.items():
        family_partial = _partial_keys(family_payload)
        actionable_partial, sanctioned_partial = _partition_partial_keys(family_partial)
        family_breakdowns.append(
            (
                family_name,
                family_payload,
                actionable_partial,
                sanctioned_partial,
            )
        )
    actionable_count = sum(len(item[2]) for item in family_breakdowns)
    sanctioned_count = sum(len(item[3]) for item in family_breakdowns)
    family_raw_count = actionable_count + sanctioned_count
    matrix_handle = io.StringIO(newline="")
    writer = csv.writer(matrix_handle)
    writer.writerow(["Parameter Path", *config_names])
    for key in all_keys:
        row = [key]
        for cfg_name in config_names:
            row.append(configs[cfg_name].get(key, "—"))
        writer.writerow(row)

    report_lines = [
        "# Config Discrepancies Report",
        "",
        f"Total configs: {len(configs)}",
        f"Total unique parameters: {len(all_keys)}",
        f"Actionable inconsistent parameters: {actionable_count}",
        f"Sanctioned partial variance parameters: {sanctioned_count}",
        f"Raw partial parameter count: {family_raw_count}",
        "",
        "## Actionable Drift Parameters",
        "",
    ]
    if actionable_count:
        for family_name, family_payload, actionable_partial, _ in family_breakdowns:
            if not actionable_partial:
                continue
            report_lines.extend(["", f"### {family_name}", ""])
            for key in actionable_partial:
                report_lines.append(
                    _parameter_presence_line(
                        key,
                        configs=family_payload,
                        total_configs=len(family_payload),
                    )
                )
    else:
        report_lines.append("No unsanctioned config drift detected.")

    report_lines.extend(
        [
            "",
            "## Sanctioned Partial Variance Parameters",
            "",
            "These parameters are intentionally partial across governed config "
            "families and remain tracked as sanctioned variance rather than "
            "actionable drift.",
            "",
        ]
    )
    if sanctioned_count:
        for family_name, family_payload, _, sanctioned_partial in family_breakdowns:
            if not sanctioned_partial:
                continue
            report_lines.extend(["", f"### {family_name}", ""])
            for key in sanctioned_partial:
                report_lines.append(
                    _parameter_presence_line(
                        key,
                        configs=family_payload,
                        total_configs=len(family_payload),
                    )
                )
    else:
        report_lines.append("No sanctioned partial variance detected.")
    report_lines.extend(
        [
            "",
            "## Parameter Ownership Taxonomy",
            "",
            "Parameter ownership taxonomy is derived from flattened config "
            "parameter paths. It is a governance/reporting projection, not a "
            "second config source of truth.",
            "",
        ]
    )
    taxonomy_payload = build_config_parameter_taxonomy_payload()
    taxonomy_families = taxonomy_payload["families"]
    for family_name in sorted(taxonomy_families):
        family_taxonomy = taxonomy_families[family_name]
        report_lines.extend(["", f"### {family_name}", ""])
        report_lines.append(f"Owner: {family_taxonomy['owner']}")
        report_lines.append(f"Parameters: {family_taxonomy['parameter_count']}")
        report_lines.append("")
        for group_name, count in family_taxonomy["groups"].items():
            report_lines.append(f"- `{group_name}`: {count}")

    report_lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- CI should fail on actionable drift.",
            "- Sanctioned partial variance remains inventory debt, not a merge blocker, "
            "while its governance contract stays current.",
        ]
    )
    return (
        matrix_handle.getvalue(),
        "\n".join(report_lines),
        len(all_keys),
        len(configs),
        family_raw_count,
        actionable_count,
        sanctioned_count,
    )


def _write_artifacts(
    *,
    matrix_path: Path,
    report_path: Path,
    matrix_content: str,
    report_content: str,
) -> None:
    matrix_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    matrix_path.write_text(matrix_content, encoding="utf-8", newline="")
    report_path.write_text(report_content, encoding="utf-8", newline="")


def _artifact_matches(path: Path, expected: str) -> bool:
    if not path.exists():
        print(f"[drift] missing: {path}")
        return False
    with path.open(encoding="utf-8", newline="") as handle:
        actual = handle.read()
    if actual == expected:
        return True
    print(f"[drift] mismatch: {path}")
    return False


def _live_baseline_metrics(
    *,
    config_count: int,
    unique_parameter_count: int,
    _cross_family_raw_inconsistent: int,
) -> dict[str, int]:
    """Return ratchet metrics; inconsistent count is family-scoped actionable sum."""
    families = _collect_family_configs()
    family_actionable = sum(
        _family_metrics(family_configs)["inconsistent_parameter_count"]
        for family_configs in families.values()
    )
    family_sanctioned = sum(
        _family_metrics(family_configs)["sanctioned_partial_parameter_count"]
        for family_configs in families.values()
    )
    family_raw = sum(
        _family_metrics(family_configs)["raw_inconsistent_parameter_count"]
        for family_configs in families.values()
    )
    return {
        "config_count": config_count,
        "unique_parameter_count": unique_parameter_count,
        "inconsistent_parameter_count": family_actionable,
        "sanctioned_partial_parameter_count": family_sanctioned,
        "raw_inconsistent_parameter_count": family_raw,
    }


def _build_baseline_payload(
    *,
    snapshot_date: str,
    metrics: dict[str, int],
    families: dict[str, dict[str, int]],
    parameter_taxonomy: dict[str, Any],
) -> dict[str, Any]:
    return {
        "snapshot_date": snapshot_date,
        "metrics": metrics,
        "families": families,
        "parameter_taxonomy": parameter_taxonomy,
    }


def _canonical_baseline_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _write_baseline_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = _canonical_baseline_json(payload)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def _baseline_metrics_match(path: Path, expected_metrics: dict[str, int]) -> bool:
    if not path.exists():
        print(f"[drift] missing: {path}")
        return False
    payload = json.loads(path.read_text(encoding="utf-8"))
    metrics = payload.get("metrics")
    if metrics == expected_metrics:
        return True
    print(f"[drift] mismatch: {path}")
    return False


def _baseline_families_match(
    path: Path,
    expected_families: dict[str, dict[str, int]],
) -> bool:
    if not path.exists():
        print(f"[drift] missing: {path}")
        return False
    payload = json.loads(path.read_text(encoding="utf-8"))
    families = payload.get("families")
    if families == expected_families:
        return True
    print(f"[drift] mismatch families: {path}")
    return False


def _baseline_taxonomy_match(
    path: Path,
    expected_taxonomy: dict[str, Any],
) -> bool:
    if not path.exists():
        print(f"[drift] missing: {path}")
        return False
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("parameter_taxonomy") == expected_taxonomy:
        return True
    print(f"[drift] mismatch parameter taxonomy: {path}")
    return False


def main(argv: list[str] | None = None) -> int:
    """Generate or check CSV and Markdown comparison outputs."""
    args = _parse_args(argv)
    (
        matrix_content,
        report_content,
        parameter_count,
        config_count,
        partial_count,
        actionable_count,
        sanctioned_count,
    ) = _build_artifact_contents()
    baseline_metrics = _live_baseline_metrics(
        config_count=config_count,
        unique_parameter_count=parameter_count,
        _cross_family_raw_inconsistent=partial_count,
    )
    family_payload = {
        family_name: _family_metrics(family_configs)
        for family_name, family_configs in _collect_family_configs().items()
    }
    parameter_taxonomy = build_config_parameter_taxonomy_payload()
    if args.check:
        ok = _artifact_matches(
            args.matrix_output,
            matrix_content,
        ) and _artifact_matches(args.report_output, report_content)
        ok = ok and _baseline_metrics_match(args.baseline_json_out, baseline_metrics)
        ok = ok and _baseline_families_match(args.baseline_json_out, family_payload)
        ok = ok and _baseline_taxonomy_match(
            args.baseline_json_out, parameter_taxonomy
        )
        if ok:
            print("[ok] config matrix artifacts are up to date")
            return 0
        print("[hint] run: python -m scripts.schema generate-config-matrix --update")
        return 1

    _write_artifacts(
        matrix_path=args.matrix_output,
        report_path=args.report_output,
        matrix_content=matrix_content,
        report_content=report_content,
    )
    _write_baseline_json(
        args.baseline_json_out,
        _build_baseline_payload(
            snapshot_date=date.today().isoformat(),
            metrics=baseline_metrics,
            families=family_payload,
            parameter_taxonomy=parameter_taxonomy,
        ),
    )
    print(f"Matrix saved to {args.matrix_output}")
    print(f"Total parameters: {parameter_count}")
    print(f"Total configs: {config_count}")
    print("\n" + "=" * 80)
    print("PARAMETER PRESENCE SUMMARY")
    print("=" * 80)
    print(f"Actionable inconsistent parameters: {actionable_count}")
    print(f"Sanctioned partial variance parameters: {sanctioned_count}")
    print(f"Raw partial parameter count: {partial_count}")
    print(f"Discrepancy report saved to {args.report_output}")
    print(f"Config-surface baseline saved to {args.baseline_json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
