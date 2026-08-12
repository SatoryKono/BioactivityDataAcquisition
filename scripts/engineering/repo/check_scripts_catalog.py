#!/usr/bin/env python3
"""Validate scripts catalog governance policy.

Checks:
- scripts/engineering/repo/catalog.yaml structure and required policy sections
- scripts/ root wrapper-only policy (except explicit allowlist)
- lifecycle registry coverage for non-active scripts from manifest
- required metadata for deprecated lifecycle decisions
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Final

import yaml

SCRIPT_EXTENSIONS: Final[tuple[str, ...]] = (".py", ".sh", ".ps1", ".cmd", ".bat")
WRAPPER_MARKER: Final[str] = "Compatibility wrapper"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_yaml(path: Path) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f"Catalog not found: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Catalog must be a YAML mapping: {path}")
    return payload


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list_of_str(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str):
            result.append(item)
    return result


def _parse_iso_date(raw: str) -> bool:
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", raw))


def _check_canonical_roots(
    *,
    root: Path,
    canonical_roots: list[str],
    violations: list[str],
) -> None:
    if not canonical_roots:
        violations.append("catalog canonical_roots must be a non-empty list[str]")
        return
    for rel in canonical_roots:
        path = root / rel
        if not path.exists() or not path.is_dir():
            violations.append(f"canonical root does not exist: {rel}")


def _check_group_entry(
    *,
    root: Path,
    group_name: object,
    group_payload: object,
    violations: list[str],
) -> None:
    if not isinstance(group_payload, dict):
        violations.append(f"groups.{group_name} must be a mapping")
        return

    group_path = group_payload.get("path")
    purpose = group_payload.get("purpose")
    if not isinstance(group_path, str) or not group_path.strip():
        violations.append(f"groups.{group_name}.path must be a non-empty string")
        return
    if not isinstance(purpose, str) or not purpose.strip():
        violations.append(f"groups.{group_name}.purpose must be a non-empty string")
    absolute = root / group_path
    if not absolute.exists() or not absolute.is_dir():
        violations.append(f"groups.{group_name}.path does not exist: {group_path}")


def _check_catalog_structure(
    *,
    root: Path,
    catalog: dict[str, object],
    violations: list[str],
) -> None:
    required_top_level = {"schema_version", "canonical_roots", "policies", "groups"}
    missing = sorted(required_top_level - set(catalog))
    if missing:
        violations.append(f"catalog missing keys: {missing}")
        return

    canonical_roots = _as_list_of_str(catalog.get("canonical_roots"))
    _check_canonical_roots(
        root=root,
        canonical_roots=canonical_roots,
        violations=violations,
    )

    groups = _as_dict(catalog.get("groups"))
    if not groups:
        violations.append("catalog groups must be a non-empty mapping")
    for group_name, group_payload in sorted(groups.items()):
        _check_group_entry(
            root=root,
            group_name=group_name,
            group_payload=group_payload,
            violations=violations,
        )


def _check_root_wrappers(
    *,
    root: Path,
    catalog: dict[str, object],
    violations: list[str],
) -> None:
    policies = _as_dict(catalog.get("policies"))
    root_wrappers_only = bool(policies.get("root_wrappers_only", True))
    if not root_wrappers_only:
        return

    allowlist = set(_as_list_of_str(policies.get("root_allowlist")))
    if not allowlist:
        allowlist = {"run.py"}

    scripts_root = root / "scripts"
    for path in sorted(scripts_root.glob("*")):
        if not path.is_file():
            continue
        if path.name == "__init__.py":
            continue
        if path.suffix not in SCRIPT_EXTENSIONS:
            continue
        if path.name in allowlist:
            continue

        text = path.read_text(encoding="utf-8")
        if WRAPPER_MARKER not in text:
            rel = path.relative_to(root).as_posix()
            violations.append(f"root script is not a wrapper: {rel}")


def _lifecycle_manifest_and_registry_paths(
    *, root: Path, lifecycle: dict[str, object], violations: list[str]
) -> tuple[Path, Path, str, str] | None:
    manifest_rel = lifecycle.get(
        "manifest_path", "configs/quality/scripts_inventory_manifest.json"
    )
    registry_rel = lifecycle.get(
        "registry_path", "configs/quality/scripts_lifecycle_registry.json"
    )
    if not isinstance(manifest_rel, str) or not manifest_rel:
        violations.append("lifecycle.manifest_path must be a non-empty string")
        return None
    if not isinstance(registry_rel, str) or not registry_rel:
        violations.append("lifecycle.registry_path must be a non-empty string")
        return None

    manifest_path = root / manifest_rel
    registry_path = root / registry_rel
    if not manifest_path.exists():
        violations.append(f"manifest not found: {manifest_rel}")
        return None
    if not registry_path.exists():
        violations.append(f"registry not found: {registry_rel}")
        return None
    return manifest_path, registry_path, manifest_rel, registry_rel


def _load_lifecycle_payloads(
    *,
    manifest_path: Path,
    registry_path: Path,
    manifest_rel: str,
    registry_rel: str,
    violations: list[str],
) -> tuple[dict[str, object], dict[str, object]] | None:
    manifest_payload = _load_json_object_with_retry(manifest_path)
    registry_payload = _load_json_object_with_retry(registry_path)
    if manifest_payload is None:
        violations.append(f"manifest JSON is invalid: {manifest_rel}")
        return None
    if registry_payload is None:
        violations.append(f"registry JSON is invalid: {registry_rel}")
        return None
    return manifest_payload, registry_payload


def _check_deprecated_lifecycle_fields(
    *,
    path: str,
    entry: dict[str, object],
    deprecated_required_fields: list[str],
    violations: list[str],
) -> None:
    for field in deprecated_required_fields:
        raw = entry.get(field)
        if not isinstance(raw, str) or not raw.strip():
            violations.append(f"{path}: deprecated entry missing field '{field}'")

    replacement = entry.get("replacement")
    if isinstance(replacement, str) and replacement.strip() == path:
        violations.append(
            f"{path}: replacement must differ from deprecated script path"
        )

    sunset_date = entry.get("sunset_date")
    if isinstance(sunset_date, str) and sunset_date.strip():
        if not _parse_iso_date(sunset_date.strip()):
            violations.append(
                f"{path}: sunset_date must be YYYY-MM-DD, got {sunset_date!r}"
            )


def _check_non_active_script_entry(
    *,
    path: str,
    entry: dict[str, object] | None,
    required_registry_fields: list[str],
    deprecated_decisions: set[str],
    deprecated_required_fields: list[str],
    violations: list[str],
) -> None:
    if not isinstance(entry, dict):
        violations.append(f"missing lifecycle entry for non-active script: {path}")
        return

    for field in required_registry_fields:
        raw = entry.get(field)
        if not isinstance(raw, str) or not raw.strip():
            violations.append(f"{path}: missing lifecycle field '{field}'")

    decision_raw = entry.get("decision")
    decision = decision_raw.strip() if isinstance(decision_raw, str) else ""
    if decision in deprecated_decisions:
        _check_deprecated_lifecycle_fields(
            path=path,
            entry=entry,
            deprecated_required_fields=deprecated_required_fields,
            violations=violations,
        )


def _check_registry_entry_coverage(
    *,
    scripts: list[object],
    entries: dict[str, object],
    non_active_statuses: set[str],
    required_registry_fields: list[str],
    deprecated_decisions: set[str],
    deprecated_required_fields: list[str],
    violations: list[str],
) -> set[str]:
    manifest_paths = {
        item.get("path")
        for item in scripts
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }

    for item in scripts:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        status = item.get("status")
        if not isinstance(path, str) or not isinstance(status, str):
            continue
        if status not in non_active_statuses:
            continue

        raw_entry = entries.get(path) if isinstance(entries, dict) else None
        entry = raw_entry if isinstance(raw_entry, dict) else None
        _check_non_active_script_entry(
            path=path,
            entry=entry,
            required_registry_fields=required_registry_fields,
            deprecated_decisions=deprecated_decisions,
            deprecated_required_fields=deprecated_required_fields,
            violations=violations,
        )

    return {path for path in manifest_paths if isinstance(path, str)}


def _lifecycle_policy_values(
    lifecycle: dict[str, object],
) -> tuple[set[str], list[str], set[str], list[str]]:
    non_active_statuses = set(
        _as_list_of_str(lifecycle.get("non_active_statuses"))
        or ["unknown", "orphan", "legacy"]
    )
    required_registry_fields = _as_list_of_str(
        lifecycle.get("required_registry_fields")
    ) or ["owner", "decision", "next_step", "review_by"]
    deprecated_decisions = set(
        _as_list_of_str(lifecycle.get("deprecated_decisions")) or ["deprecate"]
    )
    deprecated_required_fields = _as_list_of_str(
        lifecycle.get("deprecated_required_fields")
    ) or ["replacement", "sunset_date"]
    return (
        non_active_statuses,
        required_registry_fields,
        deprecated_decisions,
        deprecated_required_fields,
    )


def _check_stale_registry_entries(
    *,
    lifecycle: dict[str, object],
    entries: dict[str, object],
    manifest_paths: set[str],
    violations: list[str],
) -> None:
    if not bool(lifecycle.get("enforce_known_registry_paths", True)):
        return
    for path in sorted(entries):
        if path not in manifest_paths:
            violations.append(f"stale lifecycle entry not found in manifest: {path}")


def _recompute_script_status_counts(
    scripts: list[object], *, manifest_rel: str, violations: list[str]
) -> Counter[str]:
    recomputed_status_counts: Counter[str] = Counter()
    for index, item in enumerate(scripts):
        if not isinstance(item, dict):
            violations.append(
                f"manifest script row malformed at index {index}: {manifest_rel}"
            )
            continue
        status = item.get("status")
        if not isinstance(status, str) or not status.strip():
            violations.append(
                f"manifest script status missing or malformed at index {index}: {manifest_rel}"
            )
            continue
        recomputed_status_counts[status] += 1
    return recomputed_status_counts


def _normalized_summary_status_counts(
    status_counts: dict[str, object], *, manifest_rel: str, violations: list[str]
) -> dict[str, int] | None:
    normalized_summary_counts: dict[str, int] = {}
    for key, value in status_counts.items():
        if isinstance(key, str) and isinstance(value, int):
            normalized_summary_counts[key] = value
            continue
        violations.append(
            f"manifest summary status_counts entry malformed: {manifest_rel}"
        )
        return None
    return normalized_summary_counts


def _check_active_script_count_budget(
    *,
    lifecycle: dict[str, object],
    manifest_payload: dict[str, object],
    manifest_rel: str,
    violations: list[str],
) -> None:
    scripts = manifest_payload.get("scripts")
    if not isinstance(scripts, list):
        violations.append(f"manifest scripts payload malformed: {manifest_rel}")
        return

    summary = _as_dict(manifest_payload.get("summary"))
    summary_total = summary.get("total_scripts")
    if not isinstance(summary_total, int):
        violations.append(
            f"manifest summary total missing or malformed: {manifest_rel}"
        )
    elif summary_total != len(scripts):
        violations.append(
            f"manifest summary total does not match scripts list: {manifest_rel} "
            f"({summary_total} != {len(scripts)})"
        )

    recomputed_status_counts = _recompute_script_status_counts(
        scripts, manifest_rel=manifest_rel, violations=violations
    )
    normalized_summary_counts = _normalized_summary_status_counts(
        _as_dict(summary.get("status_counts")),
        manifest_rel=manifest_rel,
        violations=violations,
    )
    if normalized_summary_counts is None:
        return
    if normalized_summary_counts != dict(sorted(recomputed_status_counts.items())):
        violations.append(
            "manifest summary status_counts does not match scripts list: "
            f"{manifest_rel}"
        )

    budget = lifecycle.get("active_script_count_max")
    if budget is None:
        return
    if not isinstance(budget, int) or budget < 0:
        violations.append(
            "lifecycle.active_script_count_max must be a non-negative int"
        )
        return
    active_count = recomputed_status_counts.get("active", 0)
    if active_count > budget:
        violations.append(
            "active script count exceeds lifecycle.active_script_count_max "
            f"({active_count} > {budget})"
        )


def _check_entrypoint_surfaces(
    *,
    root: Path,
    catalog: dict[str, object],
    violations: list[str],
) -> None:
    entrypoints = _as_dict(catalog.get("entrypoints"))
    if not entrypoints:
        violations.append("catalog missing entrypoints policy section")
        return

    path_maps = (
        _as_dict(entrypoints.get("package_console_scripts")),
        _as_dict(entrypoints.get("script_routers")),
    )
    for mapping in path_maps:
        for name, rel_path in sorted(mapping.items()):
            if not isinstance(rel_path, str) or not rel_path.strip():
                violations.append(f"entrypoints.{name} must map to a non-empty path")
                continue
            if not (root / rel_path).is_file():
                violations.append(
                    f"entrypoint target does not exist: {name} -> {rel_path}"
                )

    for rel_path in _as_list_of_str(entrypoints.get("workflow_surfaces")):
        if not (root / rel_path).is_file():
            violations.append(f"entrypoint workflow surface does not exist: {rel_path}")


def _check_lifecycle_coverage(
    *,
    root: Path,
    catalog: dict[str, object],
    violations: list[str],
) -> None:
    lifecycle = _as_dict(catalog.get("lifecycle"))
    if not lifecycle:
        violations.append("catalog missing lifecycle policy section")
        return

    lifecycle_paths = _lifecycle_manifest_and_registry_paths(
        root=root, lifecycle=lifecycle, violations=violations
    )
    if lifecycle_paths is None:
        return
    manifest_path, registry_path, manifest_rel, registry_rel = lifecycle_paths

    payloads = _load_lifecycle_payloads(
        manifest_path=manifest_path,
        registry_path=registry_path,
        manifest_rel=manifest_rel,
        registry_rel=registry_rel,
        violations=violations,
    )
    if payloads is None:
        return
    manifest_payload, registry_payload = payloads
    _check_active_script_count_budget(
        lifecycle=lifecycle,
        manifest_payload=manifest_payload,
        manifest_rel=manifest_rel,
        violations=violations,
    )
    scripts = manifest_payload.get("scripts", [])
    entries = _as_dict(registry_payload.get("entries"))
    if not isinstance(scripts, list):
        violations.append(f"manifest scripts payload malformed: {manifest_rel}")
        return
    if not isinstance(registry_payload.get("entries"), dict):
        violations.append(f"registry entries payload malformed: {registry_rel}")
        return

    (
        non_active_statuses,
        required_registry_fields,
        deprecated_decisions,
        deprecated_required_fields,
    ) = _lifecycle_policy_values(lifecycle)

    manifest_paths = _check_registry_entry_coverage(
        scripts=scripts,
        entries=entries,
        non_active_statuses=non_active_statuses,
        required_registry_fields=required_registry_fields,
        deprecated_decisions=deprecated_decisions,
        deprecated_required_fields=deprecated_required_fields,
        violations=violations,
    )
    _check_stale_registry_entries(
        lifecycle=lifecycle,
        entries=entries,
        manifest_paths=manifest_paths,
        violations=violations,
    )


def _load_json_object_with_retry(
    path: Path,
    *,
    attempts: int = 3,
    delay_seconds: float = 0.05,
) -> dict[str, object] | None:
    """Load a JSON object, retrying briefly for concurrent writers."""

    for index in range(attempts):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            if index < attempts - 1:
                time.sleep(delay_seconds)
            continue
        if isinstance(payload, dict):
            return payload
        return None
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate scripts catalog governance")
    parser.add_argument(
        "--catalog",
        default="scripts/engineering/repo/catalog.yaml",
        help="Path to scripts catalog YAML.",
    )
    args = parser.parse_args(argv)

    root = _project_root()
    catalog_path = root / args.catalog

    violations: list[str] = []
    try:
        catalog = _load_yaml(catalog_path)
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        print(f"[FAIL] {exc}")
        return 1

    _check_catalog_structure(root=root, catalog=catalog, violations=violations)
    _check_entrypoint_surfaces(root=root, catalog=catalog, violations=violations)
    _check_root_wrappers(root=root, catalog=catalog, violations=violations)
    _check_lifecycle_coverage(root=root, catalog=catalog, violations=violations)

    if violations:
        print("[FAIL] Scripts catalog governance violations:")
        for item in violations:
            print(f"  - {item}")
        return 1

    print(f"[OK] Scripts catalog governance is valid: {args.catalog}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
