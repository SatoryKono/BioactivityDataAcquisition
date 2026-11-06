#!/usr/bin/env python3
"""Inspect and validate profile-aware Codex MCP readiness requirements."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import cast

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import setup_mcp  # pyright: ignore[reportImplicitRelativeImport]


REPO_ROOT = Path(__file__).resolve().parents[3]


def selected_names(profile: str, repo_root: Path = REPO_ROOT) -> tuple[str, ...]:
    return tuple(sorted(setup_mcp._canonical_servers(repo_root, profile=profile)))


def _as_str_list(value: object) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value]
    return []


def profile_plan(profile: str, repo_root: Path = REPO_ROOT) -> dict[str, object]:
    selected = selected_names(profile, repo_root)
    required, optional = setup_mcp.mcp_profile_requirements(profile, selected)
    catalog_path = repo_root / "scripts/ops/runtime/mcp/shared-servers.json"
    catalog_raw = json.loads(catalog_path.read_text(encoding="utf-8"))["servers"]
    local = set(cast(list[str], list(catalog_raw)))
    required_list = list(required)
    optional_list = list(optional)
    selected_list = list(selected)
    return {
        "profile": profile,
        "selected": selected_list,
        "required": required_list,
        "optional": optional_list,
        "required_local": sorted(set(required_list) & local),
        "optional_local": sorted(set(optional_list) & local),
        "remote_or_external": sorted(set(selected_list) - local),
    }


def _memory_mode(repo_root: Path) -> str:
    """Read only the persistence setting, with the memory wrapper's precedence."""
    key = "BIOETL_AI_MEMORY_MODE"
    if key in os.environ:
        return (os.environ[key] or "off").lower()
    if os.environ.get("BIOETL_REPO_ENV_LOADED") == "1":
        return "off"
    source = Path(os.environ.get("BIOETL_ENV_FILE") or repo_root / ".env")
    mode = "off"
    if source.is_file():
        for raw in source.read_text(encoding="utf-8").splitlines():
            name, separator, value = raw.partition("=")
            if not separator or name.strip() != key:
                continue
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                mode = value[1:-1]
            else:
                mode = re.sub(r"\s+#.*$", "", value).rstrip()
    return (mode or "off").lower()


def effective_profile_plan(
    plan: dict[str, object], repo_root: Path = REPO_ROOT
) -> dict[str, object]:
    """Apply task persistence authority without changing the declared inventory."""
    mode = _memory_mode(repo_root)
    if mode in {"read-write", "readwrite", "rw"}:
        return {**plan, "disabled_by_mode": []}
    if mode not in {"off", "disabled", "read-only", "readonly", "ro"}:
        raise ValueError("Invalid BIOETL_AI_MEMORY_MODE")
    return {
        **plan,
        "required_local": [
            name
            for name in _as_str_list(plan.get("required_local"))
            if name != "memory"
        ],
        "optional_local": [
            name
            for name in _as_str_list(plan.get("optional_local"))
            if name != "memory"
        ],
        "disabled_by_mode": ["memory"]
        if "memory" in _as_str_list(plan.get("selected"))
        else [],
    }


def _safe_plan_for_json(plan: dict[str, object]) -> dict[str, object]:
    """Return an allowlisted, non-sensitive view of profile plan data."""
    return {
        "disabled_by_mode": _as_str_list(plan.get("disabled_by_mode")),
        "profile": str(plan.get("profile", "")),
        "selected": _as_str_list(plan.get("selected")),
        "required": _as_str_list(plan.get("required")),
        "optional": _as_str_list(plan.get("optional")),
        "required_local": _as_str_list(plan.get("required_local")),
        "optional_local": _as_str_list(plan.get("optional_local")),
        "remote_or_external": _as_str_list(plan.get("remote_or_external")),
    }


def validate_profile_matrix(repo_root: Path = REPO_ROOT) -> list[str]:
    errors: list[str] = []
    for profile in setup_mcp.MCP_PROFILES:
        try:
            plan = profile_plan(profile, repo_root)
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            errors.append(f"{profile}: {exc}")
            continue
        selected = set(_as_str_list(plan["selected"]))
        required = set(_as_str_list(plan["required"]))
        optional = set(_as_str_list(plan["optional"]))
        if required & optional:
            errors.append(f"{profile}: required/optional sets overlap")
        if required | optional != selected:
            errors.append(f"{profile}: matrix does not cover selected inventory")

    stable_required = set(_as_str_list(profile_plan("stable", repo_root)["required"]))
    stable_selected = set(_as_str_list(profile_plan("stable", repo_root)["selected"]))
    shared_selected = set(_as_str_list(profile_plan("shared", repo_root)["selected"]))
    if "deepwiki" in stable_selected:
        errors.append("stable: credentialed DeepWiki must not be selected")
    if "deepwiki" not in shared_selected:
        errors.append("shared: opt-in DeepWiki must remain available")
    if (
        set(_as_str_list(profile_plan("shared", repo_root)["required"]))
        != stable_required
    ):
        errors.append("shared: daily required set must match stable")
    if "mermaid" not in set(_as_str_list(profile_plan("core", repo_root)["required"])):
        errors.append("core: mermaid must be required for diagram readiness")
    if "mermaid" in set(_as_str_list(profile_plan("shared", repo_root)["required"])):
        errors.append("shared: mermaid must remain optional")
    graph_required = set(_as_str_list(profile_plan("graph", repo_root)["required"]))
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

    plan = effective_profile_plan(profile_plan(args.profile))
    if args.required_local:
        print("\n".join(_as_str_list(plan["required_local"])))
        return 0
    print(json.dumps(_safe_plan_for_json(plan), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
