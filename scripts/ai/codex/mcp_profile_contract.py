#!/usr/bin/env python3
"""Inspect and validate profile-aware Codex MCP readiness requirements."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import setup_mcp


REPO_ROOT = Path(__file__).resolve().parents[3]


def selected_names(profile: str, repo_root: Path = REPO_ROOT) -> tuple[str, ...]:
    return tuple(sorted(setup_mcp._canonical_servers(repo_root, profile=profile)))


def profile_plan(profile: str, repo_root: Path = REPO_ROOT) -> dict[str, object]:
    selected = selected_names(profile, repo_root)
    required, optional = setup_mcp.mcp_profile_requirements(profile, selected)
    catalog_path = repo_root / "scripts/ops/runtime/mcp/shared-servers.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))["servers"]
    local = set(catalog)
    return {
        "profile": profile,
        "selected": list(selected),
        "required": list(required),
        "optional": list(optional),
        "required_local": sorted(set(required) & local),
        "optional_local": sorted(set(optional) & local),
        "remote_or_external": sorted(set(selected) - local),
    }


def _safe_plan_for_json(plan: dict[str, object]) -> dict[str, object]:
    """Return an allowlisted, non-sensitive view of profile plan data."""
    return {
        "profile": str(plan.get("profile", "")),
        "selected": list(plan.get("selected", [])),
        "required": list(plan.get("required", [])),
        "optional": list(plan.get("optional", [])),
        "required_local": list(plan.get("required_local", [])),
        "optional_local": list(plan.get("optional_local", [])),
        "remote_or_external": list(plan.get("remote_or_external", [])),
    }


def validate_profile_matrix(repo_root: Path = REPO_ROOT) -> list[str]:
    errors: list[str] = []
    for profile in setup_mcp.MCP_PROFILES:
        try:
            plan = profile_plan(profile, repo_root)
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            errors.append(f"{profile}: {exc}")
            continue
        selected = set(plan["selected"])
        required = set(plan["required"])
        optional = set(plan["optional"])
        if required & optional:
            errors.append(f"{profile}: required/optional sets overlap")
        if required | optional != selected:
            errors.append(f"{profile}: matrix does not cover selected inventory")

    stable_required = set(profile_plan("stable", repo_root)["required"])
    if set(profile_plan("shared", repo_root)["required"]) != stable_required:
        errors.append("shared: daily required set must match stable")
    if "mermaid" not in set(profile_plan("core", repo_root)["required"]):
        errors.append("core: mermaid must be required for diagram readiness")
    if "mermaid" in set(profile_plan("shared", repo_root)["required"]):
        errors.append("shared: mermaid must remain optional")
    graph_required = set(profile_plan("graph", repo_root)["required"])
    for name in ("neo4j-cypher", "neo4j-memory"):
        if name not in graph_required:
            errors.append(f"graph: {name} must be required")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile", choices=sorted(setup_mcp.MCP_PROFILES), default="stable"
    )
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true")
    output.add_argument("--required-local", action="store_true")
    output.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.check:
        errors = validate_profile_matrix()
        for error in errors:
            print(f"[FAIL] {error}")
        if errors:
            return 1
        print(f"[OK] {len(setup_mcp.MCP_PROFILES)} MCP profile matrices are valid")
        return 0

    plan = profile_plan(args.profile)
    if args.required_local:
        print("\n".join(plan["required_local"]))
    elif args.json:
        print(json.dumps(_safe_plan_for_json(plan), indent=2, sort_keys=True))
    else:
        print(f"profile={args.profile}")
        print(f"required={','.join(plan['required'])}")
        print(f"optional={','.join(plan['optional'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
