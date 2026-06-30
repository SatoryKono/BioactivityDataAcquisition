#!/usr/bin/env python3
"""Validate root-governance docs against machine-readable enforcement surfaces."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.engineering.repo import _root_governance as root_governance


ROOT_POLICY_DOC = Path("docs/00-project/governance/03-file-policy.md")
PLANS_README = Path("docs/plans/README.md")
OPS_INDEX = Path("scripts/ops/INDEX.md")
ROOT_REVIEW_REGISTRY = Path("configs/quality/root_hygiene_review_registry.yaml")
GENERATED_ARTIFACT_ROUTING = Path("configs/quality/generated_artifact_routing.yaml")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _read_text(repo_root: Path, relative_path: Path) -> str:
    return (repo_root / relative_path).read_text(encoding="utf-8")


def _missing_machine_readable_refs(text: str) -> list[str]:
    required_refs = (
        ".github/root-allowlist.txt",
        "configs/quality/repo_structure_catalog.yaml",
        ROOT_REVIEW_REGISTRY.as_posix(),
        GENERATED_ARTIFACT_ROUTING.as_posix(),
    )
    return [ref for ref in required_refs if ref not in text]


def _missing_root_dir_mentions(
    *,
    approved_root_directories: frozenset[str],
    policy_text: str,
) -> list[str]:
    missing: list[str] = []
    for path in sorted(approved_root_directories):
        if f"`{path}`" not in policy_text:
            missing.append(path)
    return missing


def _missing_blocked_zone_mentions(
    *,
    catalog: dict[str, Any],
    policy_text: str,
) -> list[str]:
    missing: list[str] = []
    blocked_zones = catalog.get("blocked_cleanup_zones", [])
    if not isinstance(blocked_zones, list):
        return ["configs/quality/repo_structure_catalog.yaml blocked_cleanup_zones"]
    for zone in blocked_zones:
        if not isinstance(zone, dict):
            continue
        path = zone.get("path")
        if isinstance(path, str) and f"`{path}/**`" not in policy_text:
            missing.append(path)
    return missing


def _plans_readme_issues(*, catalog: dict[str, Any], readme_text: str) -> list[str]:
    issues: list[str] = []
    plans = catalog.get("plans")
    if not isinstance(plans, dict):
        return ["repo_structure_catalog.plans must be a mapping"]

    readme_path = plans.get("readme")
    if readme_path != str(PLANS_README):
        issues.append("repo_structure_catalog.plans.readme must point to docs/plans/README.md")

    if "configs/quality/repo_structure_catalog.yaml" not in readme_text:
        issues.append("docs/plans/README.md must reference repo_structure_catalog.yaml")
    if "Only one tracked plan file may hold lifecycle `active_backlog`." not in readme_text:
        issues.append("docs/plans/README.md must restate the one-active-backlog rule")

    allowed_files = plans.get("allowed_files", [])
    if not isinstance(allowed_files, list):
        return issues + ["repo_structure_catalog.plans.allowed_files must be a list"]
    active_backlog = [
        entry["path"]
        for entry in allowed_files
        if isinstance(entry, dict) and entry.get("lifecycle") == "active_backlog"
    ]
    if len(active_backlog) != 1:
        issues.append("repo_structure_catalog.plans must declare exactly one active_backlog")
    else:
        active_name = Path(active_backlog[0]).name
        if active_name not in readme_text:
            issues.append(
                f"docs/plans/README.md must link the active backlog {active_name}"
            )
    return issues


def _ops_index_issues(text: str) -> list[str]:
    issues: list[str] = []
    if "script-codex/" in text or "script-gemini/" in text:
        issues.append("scripts/ops/INDEX.md must not point to root script-codex/ or script-gemini/ surfaces")
    if "scripts/ai/codex/helper/ensure-codex-cli.sh" not in text:
        issues.append(
            "scripts/ops/INDEX.md must point helper guidance to scripts/ai/codex/helper/ensure-codex-cli.sh"
        )
    return issues


def _collect_issues(repo_root: Path) -> list[str]:
    policy = root_governance.load_root_governance_policy(repo_root)
    policy_text = _read_text(repo_root, ROOT_POLICY_DOC)
    plans_readme = _read_text(repo_root, PLANS_README)
    ops_index = _read_text(repo_root, OPS_INDEX)

    issues: list[str] = []

    missing_refs = _missing_machine_readable_refs(policy_text)
    issues.extend(
        f"{ROOT_POLICY_DOC}: missing machine-readable reference {path}"
        for path in missing_refs
    )

    missing_dirs = _missing_root_dir_mentions(
        approved_root_directories=policy.approved_root_directories,
        policy_text=policy_text,
    )
    issues.extend(
        f"{ROOT_POLICY_DOC}: missing approved tracked root directory mention `{path}`"
        for path in missing_dirs
    )

    missing_zones = _missing_blocked_zone_mentions(
        catalog=policy.catalog,
        policy_text=policy_text,
    )
    issues.extend(
        f"{ROOT_POLICY_DOC}: missing blocked cleanup zone mention `{path}/**`"
        for path in missing_zones
    )

    issues.extend(_plans_readme_issues(catalog=policy.catalog, readme_text=plans_readme))
    issues.extend(_ops_index_issues(ops_index))
    return issues


def main(argv: list[str] | None = None) -> int:
    _ = argv
    repo_root = _project_root()
    issues = _collect_issues(repo_root)
    if issues:
        print("[FAIL] Root governance docs drift detected:")
        for issue in issues:
            print(f"  - {issue}")
        return 1

    print("[PASS] Root governance docs align with machine-readable governance surfaces.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
