#!/usr/bin/env python3
"""Migrate file_size_limits exemption keys from basename to module path.

The migration keeps values/metadata intact and rewrites keys to canonical
repository-relative module paths: ``src/bioetl/.../*.py``.

Ambiguous basename keys are resolved conservatively:
- if one matching file exceeds its layer default limit, map to that file;
- if multiple files exceed limits, split one entry into multiple path keys;
- if no match exceeds limits, map to the largest matching file and report it.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from bioetl.infrastructure.quality.exemptions_registry import (
    build_module_path_key,
    load_exemptions_registry,
)

LAYER_LIMITS = {
    "domain": 305,
    "application": 500,
    "composition": 400,
    "infrastructure": 650,
    "interfaces": 400,
}
_MIGRATION_KEEP_UNMATCHED = False


@dataclass(frozen=True)
class ModuleInfo:
    path: Path
    loc: int
    default_limit: int


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate architecture_metric_exemptions file_size_limits keys to module paths."
    )
    parser.add_argument(
        "--registry",
        default="configs/quality/architecture_metric_exemptions.yaml",
        help="Path to registry YAML.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write migration result back to registry file.",
    )
    parser.add_argument(
        "--keep-unmatched",
        action="store_true",
        help="Keep unmatched legacy keys instead of dropping them.",
    )
    return parser.parse_args()


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _discover_modules() -> tuple[dict[str, list[ModuleInfo]], dict[str, ModuleInfo]]:
    src_root = _project_root() / "src"
    by_basename: dict[str, list[ModuleInfo]] = defaultdict(list)
    by_key: dict[str, ModuleInfo] = {}

    for py_file in (src_root / "bioetl").rglob("*.py"):
        if py_file.name.startswith("__"):
            continue
        rel_key = build_module_path_key(py_file, src_root=src_root)
        rel_parts = Path(rel_key).parts
        layer = rel_parts[2] if len(rel_parts) >= 3 else ""
        default_limit = LAYER_LIMITS.get(layer, 500)
        loc = len(py_file.read_text(encoding="utf-8").splitlines())
        info = ModuleInfo(path=py_file, loc=loc, default_limit=default_limit)
        by_basename[py_file.name].append(info)
        by_key[rel_key] = info

    return by_basename, by_key


def _is_canonical_file_key(key: str) -> bool:
    normalized = key.replace("\\", "/")
    return normalized.startswith("src/bioetl/") and normalized.endswith(".py")


def _resolve_targets_for_legacy_key(
    legacy_key: str,
    *,
    by_basename: dict[str, list[ModuleInfo]],
) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    matches = by_basename.get(legacy_key, [])
    if not matches:
        warnings.append(f"{legacy_key}: no matching module found")
        return [], warnings

    if len(matches) == 1:
        return [build_module_path_key(matches[0].path)], warnings

    exceeded = [m for m in matches if m.loc > m.default_limit]
    if len(exceeded) == 1:
        return [build_module_path_key(exceeded[0].path)], warnings

    if len(exceeded) > 1:
        warnings.append(
            f"{legacy_key}: split into {len(exceeded)} path keys (multiple modules exceed default limits)"
        )
        return sorted(build_module_path_key(item.path) for item in exceeded), warnings

    chosen = max(matches, key=lambda item: item.loc)
    warnings.append(
        f"{legacy_key}: no module exceeds default limit; mapped to largest candidate "
        f"{build_module_path_key(chosen.path)}"
    )
    return [build_module_path_key(chosen.path)], warnings


def _merge_entries(
    existing: dict[str, Any],  # Any: registry value payload is heterogeneous
    incoming: dict[str, Any],  # Any: registry value payload is heterogeneous
) -> dict[str, Any]:  # Any: registry value payload is heterogeneous
    if not existing:
        return dict(incoming)
    merged = dict(existing)
    existing_value = existing.get("value")
    incoming_value = incoming.get("value")
    if isinstance(existing_value, (int, float)) and isinstance(
        incoming_value, (int, float)
    ):
        merged["value"] = max(existing_value, incoming_value)
    return merged


def _validated_file_size_entry(
    key: object,
    entry: object,
) -> tuple[str | None, dict[str, Any] | None, list[str]]:
    warnings: list[str] = []
    if not isinstance(key, str):
        warnings.append(f"{key!r}: non-string key skipped")
        return None, None, warnings
    if not isinstance(entry, dict):
        warnings.append(f"{key}: non-mapping entry skipped")
        return key, None, warnings
    return key, entry, warnings


def _targets_for_registry_key(
    key: str,
    *,
    by_basename: dict[str, list[ModuleInfo]],
    keep_unmatched: bool,
) -> tuple[list[str], list[str]]:
    if _is_canonical_file_key(key):
        return [key.replace("\\", "/")], []

    targets, warnings = _resolve_targets_for_legacy_key(
        key,
        by_basename=by_basename,
    )
    if targets or not keep_unmatched:
        return targets, warnings

    warnings.append(f"{key}: preserved unmatched legacy key (--keep-unmatched)")
    return [key], warnings


def migrate_registry_keys(
    raw: dict[str, Any],  # Any: registry payload is heterogeneous
) -> tuple[dict[str, Any], list[str]]:  # Any: registry payload is heterogeneous
    warnings: list[str] = []
    registries = raw.get("registries", {})
    if not isinstance(registries, dict):
        raise ValueError("registries section must be a mapping")
    file_size = registries.get("file_size_limits", {})
    if not isinstance(file_size, dict):
        raise ValueError("registries.file_size_limits must be a mapping")

    by_basename, _ = _discover_modules()

    migrated: dict[str, Any] = {}
    for key, entry in file_size.items():
        valid_key, valid_entry, entry_warnings = _validated_file_size_entry(key, entry)
        warnings.extend(entry_warnings)
        if valid_key is None or valid_entry is None:
            continue

        targets, key_warnings = _targets_for_registry_key(
            valid_key,
            by_basename=by_basename,
            keep_unmatched=_MIGRATION_KEEP_UNMATCHED,
        )
        warnings.extend(key_warnings)

        for target in targets:
            migrated[target] = _merge_entries(migrated.get(target, {}), valid_entry)

    new_raw = dict(raw)
    new_registries = dict(registries)
    new_registries["file_size_limits"] = dict(sorted(migrated.items()))
    new_raw["registries"] = new_registries
    return new_raw, warnings


def main() -> int:
    args = _parse_args()
    registry_path = Path(args.registry)
    raw = load_exemptions_registry(registry_path)
    global _MIGRATION_KEEP_UNMATCHED
    _MIGRATION_KEEP_UNMATCHED = bool(args.keep_unmatched)
    migrated, warnings = migrate_registry_keys(raw)

    old_entries = raw["registries"]["file_size_limits"]
    new_entries = migrated["registries"]["file_size_limits"]
    print(
        "file_size_limits migration summary: "
        f"{len(old_entries)} -> {len(new_entries)} entries"
    )
    for item in warnings:
        print(f"[warn] {item}")

    if args.write:
        registry_path.write_text(
            yaml.safe_dump(migrated, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        print(f"[write] updated {registry_path}")
    else:
        print("[dry-run] use --write to apply migration")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
