#!/usr/bin/env python3
"""Generate comparison matrix for unified entity/composite configs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from dataclasses import dataclass
from datetime import date
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from scripts.engineering.qa.config_surface_governance import is_sanctioned_partial_key

DEFAULT_BASELINE_JSON = Path("reports/quality/config-discrepancy-baseline.json")
SANCTIONED_DEFAULT_SCALAR = "<sanctioned-default>"
DICT_SHAPE_MARKER = "(dict)"
CONFIG_PARAMETER_TAXONOMY_OWNER = "BioETL Team"
YAML_GLOB = "*.yaml"
_DEFAULT_TAXONOMY_GROUP = "domain_entity_contract"
_CONFIG_PARAMETER_FAMILY_OWNERS: dict[str, dict[str, str]] = {
    "compatibility_legacy": {
        "owner": "config-governance",
        "change_policy": "explicit_registry_entry_required",
        "rationale": (
            "Compatibility-preserving config aliases and migrations must be "
            "registered before they are accepted."
        ),
    },
    "domain_entity_contract": {
        "owner": "contract-governance",
        "change_policy": "contract_registry_or_schema_review_required",
        "rationale": (
            "Entity and composite contract parameters define runtime data shape "
            "and must evolve through contract ownership."
        ),
    },
    "dq_validation": {
        "owner": "data-quality-governance",
        "change_policy": "dq_contract_review_required",
        "rationale": "DQ and schema validation parameters own acceptance criteria.",
    },
    "medallion_write_policy": {
        "owner": "storage-platform",
        "change_policy": "storage_contract_review_required",
        "rationale": "Bronze/Silver/Gold write settings affect persisted layout.",
    },
    "observability": {
        "owner": "observability-governance",
        "change_policy": "telemetry_contract_review_required",
        "rationale": "Metric, logging, tracing, and health knobs affect telemetry contracts.",
    },
    "provider_source_access": {
        "owner": "provider-adapter-governance",
        "change_policy": "provider_contract_review_required",
        "rationale": "Provider request, pagination, and rate-limit settings own API access.",
    },
    "replay_provenance": {
        "owner": "control-plane-replay-governance",
        "change_policy": "replay_contract_review_required",
        "rationale": "Manifest, ledger, lineage, and snapshot parameters affect replay evidence.",
    },
    "runtime_control_plane": {
        "owner": "runtime-orchestration",
        "change_policy": "runtime_control_plane_review_required",
        "rationale": "Execution, checkpoint, lock, and scheduling knobs govern runtime behavior.",
    },
}
_CONFIG_EVOLUTION_POLICY = {
    "compatibility_preserving_changes": "registered_alias_or_migration_entry_required",
    "alias_registry": "configs/quality/config_compatibility_registry.yaml",
    "contract_registry_diagnostics": "reports/quality/contract-registry-diagnostics.json",
    "blocking_issue_budget": 0,
}
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
    "filters.gold_filters.columns.organism_class",
)


@dataclass(frozen=True)
class ConfigDiscrepancyEvidence:
    """Immutable, byte-stable evidence shared by generator checks in one worker."""

    fingerprint: str
    matrix_content: str
    report_content: str
    parameter_count: int
    config_count: int
    raw_partial_count: int
    actionable_count: int
    sanctioned_count: int
    baseline_metrics_json: str
    family_metrics_json: str
    parameter_taxonomy_json: str

    def baseline_metrics(self) -> dict[str, int]:
        return dict(json.loads(self.baseline_metrics_json))

    def family_metrics(self) -> dict[str, dict[str, int]]:
        return dict(json.loads(self.family_metrics_json))

    def parameter_taxonomy(self) -> dict[str, Any]:
        return dict(json.loads(self.parameter_taxonomy_json))


def flatten_dict(d: dict[str, Any], parent_key: str = "") -> dict[str, Any]:
    """Flatten nested dict to dot-notation keys."""
    items: dict[str, Any] = {}
    for key, value in d.items():
        new_key = f"{parent_key}.{key}" if parent_key else key
        if isinstance(value, dict):
            items[new_key] = DICT_SHAPE_MARKER
            items.update(flatten_dict(value, new_key))
        elif isinstance(value, list):
            items[new_key] = json.dumps(value, ensure_ascii=False) if value else "[]"
        else:
            items[new_key] = str(value) if value is not None else "null"
    return items


def _exclude_derived_entity_parameters(
    flattened: dict[str, Any],
) -> dict[str, Any]:
    """Drop deterministic mirror fields from config-surface debt metrics.

    These fields remain explicit in entity YAML for runtime validation/filtering,
    but they are derived from other governed sources (`provider`, `entity`,
    `hash_policy.contract.version`, normalization profiles) and should not inflate
    discrepancy-budget parameter counts.
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


def _load_effective_filters(
    *,
    provider: str,
    entity: str,
) -> dict[str, Any]:
    # Lazy import: FilterConfigLoader pulls domain/schema stacks that dominate
    # cold-start cost of ``python -m scripts.schema generate-config-matrix``.
    from bioetl.infrastructure.config.filter_config_loader import FilterConfigLoader

    return FilterConfigLoader(Path("configs")).load_as_dict(provider, entity)


def _entity_config_effective(path: Path) -> dict[str, Any]:
    """Return entity YAML with runtime-applied defaults merged for governance."""
    from bioetl.infrastructure.config.entity_filter_metadata_registry import (
        apply_shared_filter_metadata,
    )

    raw = apply_shared_filter_metadata(
        configs_root=Path("configs"),
        config_path=path,
        payload=load_config(path),
    )
    effective = dict(raw)
    provider = str(raw.get("provider", "")).strip()
    entity = str(raw.get("entity", "")).strip()
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
    if provider and entity:
        effective_filters = _load_effective_filters(provider=provider, entity=entity)
        if effective_filters:
            effective["filters"] = effective_filters
    return effective


def _partial_keys(configs: dict[str, dict[str, Any]]) -> list[str]:
    all_keys = sorted({key for values in configs.values() for key in values})
    if not configs:
        return []
    common = set.intersection(*(set(values.keys()) for values in configs.values()))
    return [key for key in all_keys if key not in common]


def _sanctioned_placeholder(values: list[Any]) -> Any:
    """Preserve coarse shape while collapsing sanctioned missing-vs-empty variance."""
    if DICT_SHAPE_MARKER in values:
        return DICT_SHAPE_MARKER
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
        "group_owner_map": {
            group_name: _CONFIG_PARAMETER_FAMILY_OWNERS[group_name]
            for group_name in sorted(groups)
        },
        "examples": {key: examples[key] for key in sorted(examples)},
        "unclassified_parameter_count": 0,
        "unclassified_parameters": [],
    }


def build_config_parameter_taxonomy_payload(
    families: dict[str, dict[str, dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Return family-scoped config parameter ownership/taxonomy metadata."""
    active_families = _collect_family_configs() if families is None else families
    return {
        "owner": CONFIG_PARAMETER_TAXONOMY_OWNER,
        "classification_mode": "derived_from_flattened_config_parameter_paths",
        "default_group": _DEFAULT_TAXONOMY_GROUP,
        "evolution_policy": _CONFIG_EVOLUTION_POLICY,
        "group_owner_map": {
            group_name: _CONFIG_PARAMETER_FAMILY_OWNERS[group_name]
            for group_name, _needles in _TAXONOMY_RULES
        }
        | {
            _DEFAULT_TAXONOMY_GROUP: _CONFIG_PARAMETER_FAMILY_OWNERS[
                _DEFAULT_TAXONOMY_GROUP
            ]
        },
        "families": {
            family_name: _family_parameter_taxonomy(family_configs)
            for family_name, family_configs in active_families.items()
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
    for yaml_file in sorted(entities_dir.rglob(YAML_GLOB)):
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
    for yaml_file in sorted(composites_dir.glob(YAML_GLOB)):
        if yaml_file.name.startswith("_"):
            continue
        name = f"composite/{yaml_file.stem}"
        configs[name] = flatten_dict(load_config(yaml_file))

    return configs


def _collect_family_configs(
    all_configs: dict[str, dict[str, Any]] | None = None,
) -> dict[str, dict[str, dict[str, Any]]]:
    active_configs = _collect_configs() if all_configs is None else all_configs
    families: dict[str, dict[str, dict[str, Any]]] = {
        "entity_effective": {},
        "composite_runtime": {},
    }
    for name, payload in active_configs.items():
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


def _family_partial_breakdowns(
    family_configs: dict[str, dict[str, dict[str, Any]]],
) -> list[tuple[str, dict[str, dict[str, Any]], list[str], list[str]]]:
    breakdowns: list[
        tuple[str, dict[str, dict[str, Any]], list[str], list[str]]
    ] = []
    for family_name, family_payload in family_configs.items():
        family_partial = _partial_keys(family_payload)
        actionable_partial, sanctioned_partial = _partition_partial_keys(family_partial)
        breakdowns.append(
            (family_name, family_payload, actionable_partial, sanctioned_partial)
        )
    return breakdowns


def _render_parameter_matrix(
    *,
    active_configs: dict[str, dict[str, Any]],
    all_keys: list[str],
    config_names: list[str],
) -> str:
    matrix_handle = io.StringIO(newline="")
    writer = csv.writer(matrix_handle)
    writer.writerow(["Parameter Path", *config_names])
    for key in all_keys:
        row = [key]
        for cfg_name in config_names:
            row.append(active_configs[cfg_name].get(key, "—"))
        writer.writerow(row)
    return matrix_handle.getvalue()


def _append_partial_parameter_sections(
    report_lines: list[str],
    *,
    family_breakdowns: list[
        tuple[str, dict[str, dict[str, Any]], list[str], list[str]]
    ],
    partial_index: int,
    empty_message: str,
) -> None:
    count = sum(len(item[partial_index]) for item in family_breakdowns)
    if not count:
        report_lines.append(empty_message)
        return
    for family_name, family_payload, actionable_partial, sanctioned_partial in (
        family_breakdowns
    ):
        keys = actionable_partial if partial_index == 2 else sanctioned_partial
        if not keys:
            continue
        report_lines.extend(["", f"### {family_name}", ""])
        for key in keys:
            report_lines.append(
                _parameter_presence_line(
                    key,
                    configs=family_payload,
                    total_configs=len(family_payload),
                )
            )


def _append_taxonomy_sections(
    report_lines: list[str],
    taxonomy_payload: dict[str, Any],
) -> None:
    taxonomy_families = taxonomy_payload["families"]
    for family_name in sorted(taxonomy_families):
        family_taxonomy = taxonomy_families[family_name]
        report_lines.extend(["", f"### {family_name}", ""])
        report_lines.append(f"Owner: {family_taxonomy['owner']}")
        report_lines.append(f"Parameters: {family_taxonomy['parameter_count']}")
        report_lines.append("")
        for group_name, count in family_taxonomy["groups"].items():
            report_lines.append(f"- `{group_name}`: {count}")


def _build_discrepancy_report(
    *,
    active_configs: dict[str, dict[str, Any]],
    all_keys: list[str],
    family_breakdowns: list[
        tuple[str, dict[str, dict[str, Any]], list[str], list[str]]
    ],
    actionable_count: int,
    sanctioned_count: int,
    family_raw_count: int,
    taxonomy_payload: dict[str, Any],
) -> str:
    report_lines = [
        "# Config Discrepancies Report",
        "",
        f"Total configs: {len(active_configs)}",
        f"Total unique parameters: {len(all_keys)}",
        f"Actionable inconsistent parameters: {actionable_count}",
        f"Sanctioned partial variance parameters: {sanctioned_count}",
        f"Raw partial parameter count: {family_raw_count}",
        "",
        "## Actionable Drift Parameters",
        "",
    ]
    _append_partial_parameter_sections(
        report_lines,
        family_breakdowns=family_breakdowns,
        partial_index=2,
        empty_message="No unsanctioned config drift detected.",
    )
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
    _append_partial_parameter_sections(
        report_lines,
        family_breakdowns=family_breakdowns,
        partial_index=3,
        empty_message="No sanctioned partial variance detected.",
    )
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
    _append_taxonomy_sections(report_lines, taxonomy_payload)
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
    return "\n".join(report_lines)


def _build_artifact_state(
    configs: dict[str, dict[str, Any]] | None = None,
) -> tuple[
    str,
    str,
    int,
    int,
    int,
    int,
    int,
    dict[str, dict[str, dict[str, Any]]],
    dict[str, Any],
]:
    """Build matrix/report contents plus reused family/taxonomy state."""
    active_configs = _collect_configs() if configs is None else configs
    family_configs = _collect_family_configs(active_configs)
    all_keys = sorted(
        {key for values in active_configs.values() for key in values}, key=_sort_key
    )
    config_names = sorted(active_configs.keys())
    family_breakdowns = _family_partial_breakdowns(family_configs)
    actionable_count = sum(len(item[2]) for item in family_breakdowns)
    sanctioned_count = sum(len(item[3]) for item in family_breakdowns)
    family_raw_count = actionable_count + sanctioned_count
    matrix_content = _render_parameter_matrix(
        active_configs=active_configs,
        all_keys=all_keys,
        config_names=config_names,
    )
    taxonomy_payload = build_config_parameter_taxonomy_payload(family_configs)
    report_content = _build_discrepancy_report(
        active_configs=active_configs,
        all_keys=all_keys,
        family_breakdowns=family_breakdowns,
        actionable_count=actionable_count,
        sanctioned_count=sanctioned_count,
        family_raw_count=family_raw_count,
        taxonomy_payload=taxonomy_payload,
    )
    return (
        matrix_content,
        report_content,
        len(all_keys),
        len(active_configs),
        family_raw_count,
        actionable_count,
        sanctioned_count,
        family_configs,
        taxonomy_payload,
    )


def _config_evidence_fingerprint() -> str:
    """Fingerprint generator sources and all governed YAML inputs."""
    paths = [
        Path(__file__),
        Path("scripts/engineering/qa/config_surface_governance.py"),
    ]
    paths.extend(sorted(Path("configs/entities").rglob(YAML_GLOB)))
    paths.extend(sorted(Path("configs/composites").glob(YAML_GLOB)))
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


@cache
def _build_config_discrepancy_evidence_cached(
    fingerprint: str,
) -> ConfigDiscrepancyEvidence:
    configs = _collect_configs()
    (
        matrix_content,
        report_content,
        parameter_count,
        config_count,
        raw_partial_count,
        actionable_count,
        sanctioned_count,
        family_configs,
        parameter_taxonomy,
    ) = _build_artifact_state(configs)
    baseline_metrics = _live_baseline_metrics(
        config_count=config_count,
        unique_parameter_count=parameter_count,
        _cross_family_raw_inconsistent=raw_partial_count,
        family_config_map=family_configs,
    )
    family_metrics = {
        family_name: _family_metrics(family_config)
        for family_name, family_config in family_configs.items()
    }

    def canonical(payload: dict[str, Any]) -> str:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    return ConfigDiscrepancyEvidence(
        fingerprint=fingerprint,
        matrix_content=matrix_content,
        report_content=report_content,
        parameter_count=parameter_count,
        config_count=config_count,
        raw_partial_count=raw_partial_count,
        actionable_count=actionable_count,
        sanctioned_count=sanctioned_count,
        baseline_metrics_json=canonical(baseline_metrics),
        family_metrics_json=canonical(family_metrics),
        parameter_taxonomy_json=canonical(parameter_taxonomy),
    )


def build_config_discrepancy_evidence() -> ConfigDiscrepancyEvidence:
    """Return one immutable evidence payload per source/config fingerprint."""
    return _build_config_discrepancy_evidence_cached(_config_evidence_fingerprint())


def _build_artifact_contents() -> tuple[str, str, int, int, int, int, int]:
    """Build matrix/report contents without writing files."""
    evidence = build_config_discrepancy_evidence()
    return (
        evidence.matrix_content,
        evidence.report_content,
        evidence.parameter_count,
        evidence.config_count,
        evidence.raw_partial_count,
        evidence.actionable_count,
        evidence.sanctioned_count,
    )


def _write_artifacts(
    *,
    matrix_path: Path,
    report_path: Path,
    matrix_content: str,
    report_content: str,
    root: Path | None = None,
) -> None:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    base = root if root is not None else REPO_ROOT
    matrix_path = resolve_output_path(matrix_path, root=base)
    report_path = resolve_output_path(report_path, root=base)
    matrix_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    matrix_path.write_text(  # NOSONAR - path confined by resolve_output_path
        matrix_content, encoding="utf-8", newline=""
    )
    report_path.write_text(  # NOSONAR - path confined by resolve_output_path
        report_content, encoding="utf-8", newline=""
    )


def _artifact_matches(path: Path, expected: str, *, root: Path | None = None) -> bool:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=root if root is not None else REPO_ROOT)
    if not path.exists():
        print(f"[drift] missing: {path}")
        return False
    with path.open(
        encoding="utf-8", newline=""
    ) as handle:  # NOSONAR - path confined by resolve_output_path
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
    family_config_map: dict[str, dict[str, dict[str, Any]]] | None = None,
) -> dict[str, int]:
    """Return ratchet metrics; inconsistent count is family-scoped actionable sum."""
    active_family_config_map = (
        _collect_family_configs() if family_config_map is None else family_config_map
    )
    family_actionable = sum(
        _family_metrics(family_payload)["inconsistent_parameter_count"]
        for family_payload in active_family_config_map.values()
    )
    family_sanctioned = sum(
        _family_metrics(family_payload)["sanctioned_partial_parameter_count"]
        for family_payload in active_family_config_map.values()
    )
    family_raw = sum(
        _family_metrics(family_payload)["raw_inconsistent_parameter_count"]
        for family_payload in active_family_config_map.values()
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


def _write_baseline_json(
    path: Path, payload: dict[str, Any], *, root: Path | None = None
) -> None:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=root if root is not None else REPO_ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = _canonical_baseline_json(payload)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")  # NOSONAR - confined under resolved path
    os.replace(tmp, path)


def _baseline_metrics_match(
    path: Path, expected_metrics: dict[str, int], *, root: Path | None = None
) -> bool:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=root if root is not None else REPO_ROOT)
    if not path.exists():
        print(f"[drift] missing: {path}")
        return False
    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )  # NOSONAR - path confined by resolve_output_path
    )
    metrics = payload.get("metrics")
    if metrics == expected_metrics:
        return True
    print(f"[drift] mismatch: {path}")
    return False


def _baseline_families_match(
    path: Path,
    expected_families: dict[str, dict[str, int]],
    *,
    root: Path | None = None,
) -> bool:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=root if root is not None else REPO_ROOT)
    if not path.exists():
        print(f"[drift] missing: {path}")
        return False
    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )  # NOSONAR - path confined by resolve_output_path
    )
    families = payload.get("families")
    if families == expected_families:
        return True
    print(f"[drift] mismatch families: {path}")
    return False


def _baseline_taxonomy_match(
    path: Path,
    expected_taxonomy: dict[str, Any],
    *,
    root: Path | None = None,
) -> bool:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=root if root is not None else REPO_ROOT)
    if not path.exists():
        print(f"[drift] missing: {path}")
        return False
    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )  # NOSONAR - path confined by resolve_output_path
    )
    if payload.get("parameter_taxonomy") == expected_taxonomy:
        return True
    print(f"[drift] mismatch parameter taxonomy: {path}")
    return False


def main(argv: list[str] | None = None) -> int:
    """Generate or check CSV and Markdown comparison outputs."""
    from scripts.engineering.common.repo_paths import REPO_ROOT

    args = _parse_args(argv)
    root = REPO_ROOT
    evidence = build_config_discrepancy_evidence()
    baseline_metrics = evidence.baseline_metrics()
    family_payload = evidence.family_metrics()
    parameter_taxonomy = evidence.parameter_taxonomy()
    if args.check:
        ok = _artifact_matches(
            args.matrix_output,
            evidence.matrix_content,
            root=root,
        ) and _artifact_matches(args.report_output, evidence.report_content, root=root)
        ok = ok and _baseline_metrics_match(
            args.baseline_json_out, baseline_metrics, root=root
        )
        ok = ok and _baseline_families_match(
            args.baseline_json_out, family_payload, root=root
        )
        ok = ok and _baseline_taxonomy_match(
            args.baseline_json_out, parameter_taxonomy, root=root
        )
        if ok:
            print("[ok] config matrix artifacts are up to date")
            return 0
        print("[hint] run: python -m scripts.schema generate-config-matrix --update")
        return 1

    _write_artifacts(
        matrix_path=args.matrix_output,
        report_path=args.report_output,
        matrix_content=evidence.matrix_content,
        report_content=evidence.report_content,
        root=root,
    )
    _write_baseline_json(
        args.baseline_json_out,
        _build_baseline_payload(
            snapshot_date=date.today().isoformat(),
            metrics=baseline_metrics,
            families=family_payload,
            parameter_taxonomy=parameter_taxonomy,
        ),
        root=root,
    )
    print(f"Matrix saved to {args.matrix_output}")
    print(f"Total parameters: {evidence.parameter_count}")
    print(f"Total configs: {evidence.config_count}")
    print("\n" + "=" * 80)
    print("PARAMETER PRESENCE SUMMARY")
    print("=" * 80)
    print(f"Actionable inconsistent parameters: {evidence.actionable_count}")
    print(f"Sanctioned partial variance parameters: {evidence.sanctioned_count}")
    print(f"Raw partial parameter count: {evidence.raw_partial_count}")
    print(f"Discrepancy report saved to {args.report_output}")
    print(f"Config-surface baseline saved to {args.baseline_json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
