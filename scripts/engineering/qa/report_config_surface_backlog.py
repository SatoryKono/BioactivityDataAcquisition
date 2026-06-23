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

from scripts.engineering.qa.config_surface_governance import (  # noqa: E402
    is_sanctioned_partial_key,
)
from scripts.schema.generate_config_matrix import (  # noqa: E402
    _collect_family_configs,
    _family_metrics,
)

BACKLOG_PATH = ROOT / "reports/quality/config-surface-backlog.json"
DUPLICATION_SURFACE_ROOT = ROOT / "configs"
DUPLICATION_FILE_SUFFIXES = (".yaml", ".yml", ".json")
JSCPD_IGNORED_PATTERNS = ("**/configs/**", "**/*.yaml", "**/*.yml", "**/*.json")
MIN_DUPLICATE_BLOCK_BYTES = 200
MAX_DUPLICATION_BLOCK_DEPTH = 2
MAX_REPORTED_DUPLICATION_CLUSTERS = 25

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
        "owner": "@bioetl-config",
        "decision": "retain_entity_specific",
        "rationale": "Extraction filters encode provider/entity source API semantics.",
    },
    "filter_metadata_entity_specific": {
        "owner": "@bioetl-config",
        "decision": "retain_entity_specific",
        "rationale": "Filter metadata documents entity-specific extraction policy.",
    },
    "gold_filter_entity_specific": {
        "owner": "@bioetl-contracts",
        "decision": "retain_contract_specific",
        "rationale": "Gold filters track entity contract and DQ semantics.",
    },
    "pipeline_overrides": {
        "owner": "@bioetl-application",
        "decision": "retain_pipeline_specific",
        "rationale": "Pipeline overrides represent runtime behavior differences.",
    },
    "quality_metadata_entity_specific": {
        "owner": "@bioetl-dq",
        "decision": "retain_entity_specific",
        "rationale": "Quality metadata varies by entity data-quality posture.",
    },
    "quality_thresholds": {
        "owner": "@bioetl-dq",
        "decision": "retain_entity_specific",
        "rationale": "DQ thresholds are entity-specific validation policy.",
    },
    "schema_field_aliases_entity_specific": {
        "owner": "@bioetl-contracts",
        "decision": "retain_contract_specific",
        "rationale": "Field aliases map provider-specific source names into contracts.",
    },
    "silver_filter_entity_specific": {
        "owner": "@bioetl-contracts",
        "decision": "retain_contract_specific",
        "rationale": "Silver filters track entity contract normalization semantics.",
    },
}


def _duplication_surface_kind(path: Path) -> str:
    relative = path.relative_to(ROOT).as_posix()
    if relative.startswith("configs/quality/"):
        return "quality_registry"
    if relative.startswith("configs/entities/"):
        return "entity_config"
    if relative.startswith("configs/composite/"):
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


def _canonical_json_text(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


def _iter_duplication_surface_files() -> list[Path]:
    files = [
        path
        for path in DUPLICATION_SURFACE_ROOT.rglob("*")
        if path.is_file() and path.suffix in DUPLICATION_FILE_SUFFIXES
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
            rendered = _canonical_json_text(block)
            if len(rendered) < MIN_DUPLICATE_BLOCK_BYTES:
                continue
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
        if cluster["block_path"].startswith("contracts.hash_") and len(unique_paths) == 1:
            # Ignore same-file contract/hash_policy mirrors; the audit tracks
            # reviewable config-surface duplication, not intentional hash aliases.
            continue
        by_kind = Counter(entry["surface_kind"] for entry in occurrences)
        affected_files.update(entry["path"] for entry in occurrences)
        duplicate_clusters.append(
            {
                "fingerprint": cluster["fingerprint"],
                "serialized_bytes": cluster["serialized_bytes"],
                "block_path": cluster["block_path"],
                "occurrence_count": len(occurrences),
                "surface_kind_counts": {
                    kind: by_kind[kind] for kind in sorted(by_kind)
                },
                "occurrences": sorted(
                    occurrences,
                    key=lambda entry: (
                        str(entry["path"]),
                        str(entry["block_path"]),
                        str(entry["surface_kind"]),
                    ),
                ),
            }
        )

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
            "ignored_by_jscpd_patterns": list(JSCPD_IGNORED_PATTERNS),
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
            "This audit covers structured config/contract/registry surfaces under configs/** that JSCPD intentionally ignores.",
            "Clusters report exact canonical JSON subtree duplicates only; near-duplicate prose and comment drift stay out of scope.",
            "The audit is report-only and exists to make YAML/JSON governance duplication reviewable in CI-visible artifacts.",
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
                            "owner": "@bioetl-architecture",
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
