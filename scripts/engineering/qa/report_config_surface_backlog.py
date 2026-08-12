#!/usr/bin/env python3
"""Categorize remaining entity config-surface drift for Stream B burn-down."""

from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.engineering.qa.config_surface_governance import (
    is_sanctioned_partial_key,
)
from scripts.schema.analysis.generate_config_matrix import (
    _collect_family_configs,
    _family_metrics,
)

BACKLOG_PATH = ROOT / "reports/quality/config-surface-backlog.json"
DUPLICATION_SURFACE_ROOT = ROOT / "configs"
DUPLICATION_EXCLUDED_GENERATED_ROOTS = (DUPLICATION_SURFACE_ROOT / "_schema",)
DUPLICATION_FILE_SUFFIXES = (".yaml", ".yml", ".json")
GENERATED_DUPLICATION_SURFACE_DIRS = (ROOT / "configs" / "_schema",)
GENERATED_DUPLICATION_SURFACE_FILES = (
    ROOT / "configs" / "quality" / "test_telemetry_baseline.yaml",
)
JSCPD_IGNORED_PATTERNS = ("**/configs/**", "**/*.yaml", "**/*.yml", "**/*.json")
MIN_DUPLICATE_BLOCK_BYTES = 200
MAX_DUPLICATION_BLOCK_DEPTH = 2
MAX_REPORTED_DUPLICATION_CLUSTERS = 25

# Ownership / issue identities shared across backlog governance (python:S1192).
OWNER_BIOETL_CONFIG = "@bioetl-config"
OWNER_BIOETL_DQ = "@bioetl-dq"
OWNER_BIOETL_CONTRACTS = "@bioetl-contracts"
OWNER_BIOETL_ARCHITECTURE = "@bioetl-architecture"
OWNER_BIOETL_COMPOSITE = "@bioetl-composite"
LINKED_ISSUE_5568 = "#5568"

CATEGORY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("hash_policy_chembl_only", ("hash_policy.",)),
    ("extraction_params_entity_specific", ("filters.extraction_params.",)),
    ("filter_metadata_entity_specific", ("filters.metadata", "filters.metadata.")),
    ("gold_filter_entity_specific", ("filters.gold_filters.",)),
    ("silver_filter_entity_specific", ("filters.silver_filters.",)),
    ("quality_metadata_entity_specific", ("quality.metadata", "quality.metadata.")),
    ("schema_field_aliases_entity_specific", ("schema.field_aliases.",)),
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

CATEGORY_GOVERNANCE: dict[str, dict[str, str]] = {
    "extraction_params_entity_specific": {
        "owner": OWNER_BIOETL_CONFIG,
        "decision": "retain_entity_specific",
        "rationale": "Extraction filters encode provider/entity source API semantics.",
    },
    "filter_metadata_entity_specific": {
        "owner": OWNER_BIOETL_CONFIG,
        "decision": "retain_entity_specific",
        "rationale": "Filter metadata documents entity-specific extraction policy.",
    },
    "gold_filter_entity_specific": {
        "owner": OWNER_BIOETL_CONTRACTS,
        "decision": "retain_contract_specific",
        "rationale": "Gold filters track entity contract and DQ semantics.",
    },
    "pipeline_overrides": {
        "owner": "@bioetl-application",
        "decision": "retain_pipeline_specific",
        "rationale": "Pipeline overrides represent runtime behavior differences.",
    },
    "quality_metadata_entity_specific": {
        "owner": OWNER_BIOETL_DQ,
        "decision": "retain_entity_specific",
        "rationale": "Quality metadata varies by entity data-quality posture.",
    },
    "quality_thresholds": {
        "owner": OWNER_BIOETL_DQ,
        "decision": "retain_entity_specific",
        "rationale": "DQ thresholds are entity-specific validation policy.",
    },
    "schema_field_aliases_entity_specific": {
        "owner": OWNER_BIOETL_CONTRACTS,
        "decision": "retain_contract_specific",
        "rationale": "Field aliases map provider-specific source names into contracts.",
    },
    "silver_filter_entity_specific": {
        "owner": OWNER_BIOETL_CONTRACTS,
        "decision": "retain_contract_specific",
        "rationale": "Silver filters track entity contract normalization semantics.",
    },
}

DUPLICATION_CLUSTER_GOVERNANCE: tuple[tuple[str, dict[str, str]], ...] = (
    (
        "pipelines",
        {
            "owner": OWNER_BIOETL_DQ,
            "decision": "retain_shared_quality_shadow_analysis_policy",
            "linked_issue": LINKED_ISSUE_5568,
            "review_date": "2026-09-30",
            "rationale": (
                "Quality-registry shadow-analysis blocks intentionally share "
                "provider-family boundary policy; retained duplication stays "
                "visible in the config backlog and must not grow without review."
            ),
        },
    ),
    (
        "$defs.FieldValidationConfig",
        {
            "owner": OWNER_BIOETL_CONTRACTS,
            "decision": "retain_generated_schema_contract",
            "linked_issue": LINKED_ISSUE_5568,
            "review_date": "2026-09-30",
            "rationale": (
                "Field validation definitions are duplicated by generated schema "
                "artifacts; retention is contract-owned rather than unresolved "
                "review-required debt."
            ),
        },
    ),
    (
        "$defs.CrossFieldValidationConfig",
        {
            "owner": OWNER_BIOETL_CONTRACTS,
            "decision": "retain_generated_schema_contract",
            "linked_issue": LINKED_ISSUE_5568,
            "review_date": "2026-09-30",
            "rationale": (
                "Cross-field validation definitions are generated schema "
                "contract mirrors and remain explicit contract-owned duplication."
            ),
        },
    ),
    (
        "$defs.ConditionalValidationConfig",
        {
            "owner": OWNER_BIOETL_CONTRACTS,
            "decision": "retain_generated_schema_contract",
            "linked_issue": LINKED_ISSUE_5568,
            "review_date": "2026-09-30",
            "rationale": (
                "Conditional validation definitions are generated schema "
                "contract mirrors and remain explicit contract-owned duplication."
            ),
        },
    ),
    (
        "$defs.DQReportYamlConfig",
        {
            "owner": OWNER_BIOETL_DQ,
            "decision": "retain_generated_dq_schema_contract",
            "linked_issue": LINKED_ISSUE_5568,
            "review_date": "2026-09-30",
            "rationale": (
                "DQ report YAML schema definitions are duplicated by generated "
                "contract artifacts and remain DQ-owned until schema generation "
                "is consolidated."
            ),
        },
    ),
    (
        "$defs.ColumnGroupSchema",
        {
            "owner": OWNER_BIOETL_CONTRACTS,
            "decision": "retain_generated_schema_contract",
            "linked_issue": LINKED_ISSUE_5568,
            "review_date": "2026-09-30",
            "rationale": (
                "Column-group schema definitions are generated contract mirrors; "
                "the backlog keeps them visible without leaving them review-free."
            ),
        },
    ),
    (
        "$defs.GoldFiltersConfig",
        {
            "owner": OWNER_BIOETL_CONTRACTS,
            "decision": "retain_generated_gold_filter_schema_contract",
            "linked_issue": LINKED_ISSUE_5568,
            "review_date": "2026-09-30",
            "rationale": (
                "Gold filter schema properties are generated contract surfaces "
                "and stay contract-owned until the generated definitions collapse."
            ),
        },
    ),
    (
        "pipeline.sink.gold",
        {
            "owner": OWNER_BIOETL_CONFIG,
            "decision": "retain_shared_entity_gold_sink_policy",
            "linked_issue": LINKED_ISSUE_5568,
            "review_date": "2026-09-30",
            "rationale": (
                "Gold sink settings are shared intentionally across matching "
                "entity configs to preserve deterministic sink layout policy."
            ),
        },
    ),
    (
        "entries.scripts/",
        {
            "owner": OWNER_BIOETL_ARCHITECTURE,
            "decision": "retain_shared_lifecycle_registry_entry",
            "linked_issue": LINKED_ISSUE_5568,
            "review_date": "2026-09-30",
            "rationale": (
                "Duplicated script-inventory lifecycle rows are quality-registry "
                "mirrors for sibling tooling entrypoints and stay explicitly "
                "architecture-owned rather than unresolved review debt."
            ),
        },
    ),
    (
        "aliases.S7-architecture-fast-boundary",
        {
            "owner": "@bioetl-test-platform",
            "decision": "retain_shared_test_shard_alias",
            "linked_issue": LINKED_ISSUE_5568,
            "review_date": "2026-09-30",
            "rationale": (
                "The S7 architecture shard alias is intentionally mirrored "
                "between quality registries so local and CI shard routing stay "
                "deterministic."
            ),
        },
    ),
    (
        "composite.merge.field_priorities",
        {
            "owner": OWNER_BIOETL_COMPOSITE,
            "decision": "retain_shared_composite_policy",
            "linked_issue": LINKED_ISSUE_5568,
            "review_date": "2026-09-30",
            "rationale": (
                "Composite field-priority blocks intentionally share conflict "
                "resolution policy across the five composite runtime configs."
            ),
        },
    ),
    (
        "composite.normalized_anchor_policy",
        {
            "owner": OWNER_BIOETL_COMPOSITE,
            "decision": "retain_shared_composite_policy",
            "linked_issue": LINKED_ISSUE_5568,
            "review_date": "2026-09-30",
            "rationale": (
                "Composite normalized-anchor policy is shared to keep join-key "
                "normalization deterministic across composite entities."
            ),
        },
    ),
    (
        "composite.lineage.provider_lookup_fields",
        {
            "owner": "@bioetl-lineage",
            "decision": "retain_shared_lineage_policy",
            "linked_issue": LINKED_ISSUE_5568,
            "review_date": "2026-09-30",
            "rationale": (
                "Provider lookup fields are duplicated intentionally while "
                "composite lineage policy remains entity-config-local."
            ),
        },
    ),
    (
        "composite.merge.field_mappings",
        {
            "owner": OWNER_BIOETL_COMPOSITE,
            "decision": "retain_shared_composite_policy",
            "linked_issue": LINKED_ISSUE_5568,
            "review_date": "2026-09-30",
            "rationale": (
                "Composite field mappings stay colocated with each composite "
                "runtime config until a schema-owned shared policy object exists."
            ),
        },
    ),
    (
        "composite.merge.column_groups",
        {
            "owner": OWNER_BIOETL_COMPOSITE,
            "decision": "retain_shared_composite_policy",
            "linked_issue": LINKED_ISSUE_5568,
            "review_date": "2026-09-30",
            "rationale": (
                "Composite column_groups are intentionally mirrored between "
                "runtime composite configs and entity contract surfaces so "
                "merge field sets stay deterministic across providers."
            ),
        },
    ),
    (
        "schema.gold.include_groups",
        {
            "owner": OWNER_BIOETL_COMPOSITE,
            "decision": "retain_entity_specific",
            "linked_issue": LINKED_ISSUE_5568,
            "review_date": "2026-09-30",
            "rationale": (
                "Gold include_groups blocks are entity-local contract copies "
                "retained until a shared gold projection schema object exists."
            ),
        },
    ),
)

DEFAULT_DUPLICATION_CLUSTER_GOVERNANCE: dict[str, str] = {
    "owner": OWNER_BIOETL_ARCHITECTURE,
    "decision": "review_required",
    "linked_issue": LINKED_ISSUE_5568,
    "review_date": "2026-09-30",
    "rationale": (
        "Exact structured config duplication is measured and requires explicit "
        "owner review before it can be retained or removed."
    ),
}


def _duplication_surface_kind(path: Path) -> str:
    relative = path.relative_to(ROOT).as_posix()
    if relative.startswith("configs/quality/"):
        return "quality_registry"
    if relative.startswith("configs/entities/"):
        return "entity_config"
    if relative.startswith("configs/composites/"):
        return "composite_config"
    if relative.startswith("configs/base/"):
        return "base_config"
    if relative.startswith("configs/enums/"):
        return "enum_registry"
    return "other_config"


def _load_structured_config(path: Path) -> Any:
    if path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _duplication_cluster_governance(block_path: str) -> dict[str, str]:
    for prefix, governance in DUPLICATION_CLUSTER_GOVERNANCE:
        if block_path == prefix or block_path.startswith(f"{prefix}."):
            return dict(governance)
    return dict(DEFAULT_DUPLICATION_CLUSTER_GOVERNANCE)


def _canonical_json_text(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


def _iter_duplication_surface_files() -> list[Path]:
    files = [
        path
        for path in DUPLICATION_SURFACE_ROOT.rglob("*")
        if path.is_file()
        and path.suffix in DUPLICATION_FILE_SUFFIXES
        and not any(
            path.is_relative_to(generated_root)
            for generated_root in GENERATED_DUPLICATION_SURFACE_DIRS
        )
        and path not in GENERATED_DUPLICATION_SURFACE_FILES
    ]
    return sorted(files)


def _iter_structured_blocks(
    payload: Any,
    *,
    path: tuple[str, ...] = (),
    depth: int = 0,
) -> list[tuple[tuple[str, ...], Any]]:
    blocks: list[tuple[tuple[str, ...], Any]] = []
    if not isinstance(payload, dict):
        return blocks
    for key, value in sorted(payload.items()):
        block_path = (*path, str(key))
        if isinstance(value, (dict, list)):
            rendered = _canonical_json_text(value)
            if len(rendered) >= MIN_DUPLICATE_BLOCK_BYTES:
                blocks.append((block_path, value))
        if depth < MAX_DUPLICATION_BLOCK_DEPTH and isinstance(value, dict):
            blocks.extend(
                _iter_structured_blocks(value, path=block_path, depth=depth + 1)
            )
    return blocks


def _is_child_of_reported_parent(block_path: str, paths: set[str]) -> bool:
    """True when a nested suffix path is covered by an already-reported parent."""
    if block_path.endswith(".properties"):
        parent = block_path[: -len(".properties")]
        if parent in paths:
            return True
    if block_path.endswith(".expands_to"):
        parent = block_path[: -len(".expands_to")]
        if parent in paths:
            return True
    if (
        block_path.startswith("composite.normalized_anchor_policy.")
        and "composite.normalized_anchor_policy" in paths
    ):
        return True
    return False


def _is_shadow_analysis_cluster(cluster: dict[str, Any]) -> bool:
    """True when the cluster represents shared shadow_analysis policy debt."""
    block_path = str(cluster["block_path"])
    decision = str((cluster.get("governance") or {}).get("decision") or "")
    return (
        decision == "retain_shared_quality_shadow_analysis_policy"
        or block_path.endswith(".shadow_analysis")
    )


def _collapse_shadow_analysis_clusters(
    clusters: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Keep one representative cluster for shared shadow_analysis decisions."""
    shadow_seen = False
    collapsed: list[dict[str, Any]] = []
    for cluster in clusters:
        if _is_shadow_analysis_cluster(cluster):
            if shadow_seen:
                continue
            shadow_seen = True
            cluster = dict(cluster)
            cluster["block_path"] = "pipelines.*.shadow_analysis"
        collapsed.append(cluster)
    return collapsed


def _collapse_nested_duplication_clusters(
    clusters: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Drop child subtree clusters when a parent block_path is already reported.

    Generated JSON Schema often duplicates both ``$defs.Foo`` and
    ``$defs.Foo.properties`` as separate exact-match clusters. Those child
    property bags are not independent governance debt once the parent contract
    cluster is retained. The same applies to alias ``expands_to`` children and
    specialized composite policy suffixes under a shared root key.
    """
    paths = {str(cluster["block_path"]) for cluster in clusters}
    kept = [
        cluster
        for cluster in clusters
        if not _is_child_of_reported_parent(str(cluster["block_path"]), paths)
    ]
    return _collapse_shadow_analysis_clusters(kept)


def _record_block_occurrence(
    clusters: dict[str, dict[str, Any]],
    *,
    block_path: tuple[str, ...],
    block: object,
    relative_path: str,
    surface_kind: str,
) -> None:
    """Accumulate one structured block occurrence into fingerprint clusters."""
    rendered = _canonical_json_text(block)
    if len(rendered) < MIN_DUPLICATE_BLOCK_BYTES:
        return
    fingerprint = sha256(rendered.encode("utf-8")).hexdigest()
    cluster = clusters.setdefault(
        fingerprint,
        {
            "fingerprint": fingerprint[:12],
            "serialized_bytes": len(rendered),
            "block_path": ".".join(block_path),
            "occurrences": [],
        },
    )
    cluster["occurrences"].append(
        {
            "path": relative_path,
            "surface_kind": surface_kind,
            "block_path": ".".join(block_path),
        }
    )


def _is_ignored_single_file_cluster(
    cluster: dict[str, Any],
    *,
    unique_paths: set[str],
) -> bool:
    """True for intentional same-file mirrors that are not multi-surface debt."""
    if len(unique_paths) != 1:
        return False
    block_path = str(cluster["block_path"])
    if block_path.startswith("contracts.hash_"):
        return True
    if block_path.startswith("entries.scripts/"):
        return True
    return False


def _duplicate_cluster_payload(cluster: dict[str, Any]) -> dict[str, Any]:
    """Build the published duplicate-cluster row for one fingerprint group."""
    occurrences = cluster["occurrences"]
    by_kind = Counter(entry["surface_kind"] for entry in occurrences)
    return {
        "fingerprint": cluster["fingerprint"],
        "serialized_bytes": cluster["serialized_bytes"],
        "block_path": cluster["block_path"],
        "occurrence_count": len(occurrences),
        "governance": _duplication_cluster_governance(str(cluster["block_path"])),
        "surface_kind_counts": {kind: by_kind[kind] for kind in sorted(by_kind)},
        "occurrences": sorted(
            occurrences,
            key=lambda entry: (
                str(entry["path"]),
                str(entry["block_path"]),
                str(entry["surface_kind"]),
            ),
        ),
    }


def _select_duplicate_clusters(
    clusters: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], set[str]]:
    """Filter fingerprint groups into multi-location duplicate clusters."""
    duplicate_clusters: list[dict[str, Any]] = []
    affected_files: set[str] = set()
    for cluster in clusters.values():
        occurrences = cluster["occurrences"]
        unique_paths = {entry["path"] for entry in occurrences}
        unique_locations = {
            (entry["path"], entry["block_path"]) for entry in occurrences
        }
        if len(unique_locations) < 2:
            continue
        if _is_ignored_single_file_cluster(cluster, unique_paths=unique_paths):
            continue
        affected_files.update(entry["path"] for entry in occurrences)
        duplicate_clusters.append(_duplicate_cluster_payload(cluster))
    return duplicate_clusters, affected_files


def _build_duplication_audit() -> dict[str, Any]:
    clusters: dict[str, dict[str, Any]] = {}
    surface_files = _iter_duplication_surface_files()

    for path in surface_files:
        payload = _load_structured_config(path)
        if not isinstance(payload, dict):
            continue
        relative_path = path.relative_to(ROOT).as_posix()
        surface_kind = _duplication_surface_kind(path)
        for block_path, block in _iter_structured_blocks(payload):
            _record_block_occurrence(
                clusters,
                block_path=block_path,
                block=block,
                relative_path=relative_path,
                surface_kind=surface_kind,
            )

    duplicate_clusters, affected_files = _select_duplicate_clusters(clusters)

    duplicate_clusters = _collapse_nested_duplication_clusters(duplicate_clusters)
    duplicate_clusters.sort(
        key=lambda cluster: (
            -int(cluster["occurrence_count"]),
            -int(cluster["serialized_bytes"]),
            str(cluster["block_path"]),
        )
    )
    trimmed_clusters = duplicate_clusters[:MAX_REPORTED_DUPLICATION_CLUSTERS]

    return {
        "scope": {
            "root": DUPLICATION_SURFACE_ROOT.relative_to(ROOT).as_posix(),
            "file_suffixes": list(DUPLICATION_FILE_SUFFIXES),
            "files_scanned": len(surface_files),
            "excluded_generated_roots": [
                path.relative_to(ROOT).as_posix()
                for path in GENERATED_DUPLICATION_SURFACE_DIRS
            ],
            "excluded_generated_files": [
                path.relative_to(ROOT).as_posix()
                for path in GENERATED_DUPLICATION_SURFACE_FILES
            ],
            "ignored_by_jscpd_patterns": list(JSCPD_IGNORED_PATTERNS),
            "excluded_generated_roots": [
                path.relative_to(ROOT).as_posix()
                for path in DUPLICATION_EXCLUDED_GENERATED_ROOTS
            ],
            "structured_block_min_bytes": MIN_DUPLICATE_BLOCK_BYTES,
            "max_traversal_depth": MAX_DUPLICATION_BLOCK_DEPTH,
        },
        "summary": {
            "duplicate_cluster_count": len(duplicate_clusters),
            "reported_cluster_count": len(trimmed_clusters),
            "duplicate_occurrence_count": sum(
                int(cluster["occurrence_count"]) for cluster in duplicate_clusters
            ),
            "affected_file_count": len(affected_files),
        },
        "clusters": trimmed_clusters,
        "notes": [
            (
                "This audit covers structured config/contract/registry surfaces "
                "under configs/** that JSCPD intentionally ignores."
            ),
            (
                "Generated JSON Schemas are excluded because their repeated $defs "
                "are materialized from shared Pydantic source models rather than "
                "independently maintained configuration debt."
            ),
            (
                "The generated test telemetry baseline is excluded because repeated "
                "duration maps are captured observations, not maintained config debt."
            ),
            (
                "Clusters report exact canonical JSON subtree duplicates only; "
                "near-duplicate prose and comment drift stay out of scope."
            ),
            (
                "Generated JSON schemas are excluded because their repeated definitions "
                "are projections of source models, not independently maintained config debt."
            ),
            (
                "The audit is report-only and exists to make YAML/JSON governance "
                "duplication reviewable in CI-visible artifacts."
            ),
            (
                "Every reported duplicate cluster carries owner/rationale metadata "
                "so retained duplication is explicit debt rather than implicit residue."
            ),
        ],
    }


def _partial_keys(family_configs: dict[str, dict[str, str]]) -> list[tuple[int, str]]:
    all_keys = sorted({key for values in family_configs.values() for key in values})
    if not family_configs:
        return []
    common = set.intersection(
        *(set(values.keys()) for values in family_configs.values())
    )
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
        "duplication_audit": _build_duplication_audit(),
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
                    **CATEGORY_GOVERNANCE.get(
                        category,
                        {
                            "owner": OWNER_BIOETL_ARCHITECTURE,
                            "decision": "review_required",
                            "rationale": "Unrecognized partial-key category.",
                        },
                    ),
                    "key_count": len(entries),
                    "keys": entries,
                }
                for category, entries in sorted(by_category.items())
            },
        },
        "notes": [
            "actionable_partial_key_count excludes keys under INTENTIONAL_PREFIXES.",
            "hash_policy is common across all 22 entity configs after Stream B design review.",
            "composite_runtime family is at zero inconsistent keys as of Stream B plateau.",
            "Residual entity drift is limited to intentional entity-specific filters, "
            "metadata policy blocks, schema field-alias surfaces, and pipeline overrides.",
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
