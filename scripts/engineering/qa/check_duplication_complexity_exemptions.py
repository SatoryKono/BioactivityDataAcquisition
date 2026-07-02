#!/usr/bin/env python3
"""Validate duplication/complexity workflow exemptions against a registry."""

from __future__ import annotations

import ast
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "duplication-complexity.yml"
REGISTRY_PATH = ROOT / "configs" / "quality" / "duplication_complexity_exemptions.yaml"


def _extract_literal(text: str, name: str) -> object:
    match = re.search(rf"{name}\s*=\s*(\{{.*?\n\s*\}})", text, re.DOTALL)
    if match is None:
        raise ValueError(f"Could not find {name} literal in {WORKFLOW_PATH}")
    return ast.literal_eval(match.group(1))


def _extract_xenon_excludes(text: str) -> set[str]:
    match = re.search(r'--exclude "([^"]+)" src', text)
    if match is None:
        raise ValueError(f"Could not find xenon --exclude list in {WORKFLOW_PATH}")
    return {item.strip() for item in match.group(1).split(",") if item.strip()}


def _normalize_path_pattern(path: str) -> str:
    return path.removesuffix("*")


def _load_registry() -> dict[str, object]:
    payload = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Expected mapping payload in {REGISTRY_PATH}")
    return payload


def _validate_metadata(entries: list[dict[str, object]], *, label: str) -> list[str]:
    errors: list[str] = []
    today = datetime.now(UTC).date()
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for entry in entries:
        raw_scopes = entry.get("scopes")
        scopes = tuple(sorted(str(scope) for scope in raw_scopes or []))
        key = (str(entry.get("path") or entry.get("name")), scopes)
        if key in seen:
            errors.append(f"duplicate {label} registry row: {key[0]} scopes={list(scopes)}")
        seen.add(key)

        owner = str(entry.get("owner", "")).strip()
        expiry = str(entry.get("expiry", "")).strip()
        removal_step = str(entry.get("removal_step", "")).strip()
        rationale = str(entry.get("rationale", "")).strip()
        if not owner.startswith("@bioetl-"):
            errors.append(f"{label} {key[0]} missing @bioetl-* owner")
        if not removal_step:
            errors.append(f"{label} {key[0]} missing removal_step")
        if not rationale:
            errors.append(f"{label} {key[0]} missing rationale")
        try:
            expiry_date = datetime.fromisoformat(expiry).date()
        except ValueError:
            errors.append(f"{label} {key[0]} has invalid expiry {expiry!r}")
            continue
        if expiry_date < today:
            errors.append(f"{label} {key[0]} expiry is stale: {expiry}")
    return errors


def main() -> None:
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    registry = _load_registry()

    path_entries = registry.get("path_entries")
    function_entries = registry.get("function_entries")
    if not isinstance(path_entries, list) or not isinstance(function_entries, list):
        raise SystemExit("Registry must define path_entries and function_entries lists")

    typed_path_entries = [
        entry for entry in path_entries if isinstance(entry, dict)
    ]
    typed_function_entries = [
        entry for entry in function_entries if isinstance(entry, dict)
    ]

    errors = [
        * _validate_metadata(typed_path_entries, label="path"),
        * _validate_metadata(typed_function_entries, label="function"),
    ]

    workflow_xenon_paths = _extract_xenon_excludes(workflow_text)
    workflow_critical_paths = set(_extract_literal(workflow_text, "EXEMPT_PATHS"))
    workflow_critical_functions = _extract_literal(workflow_text, "EXEMPT_FUNCTIONS")
    if not isinstance(workflow_critical_functions, dict):
        errors.append("EXEMPT_FUNCTIONS must stay a dict literal in workflow")
        workflow_critical_functions = {}

    registry_xenon_paths = {
        str(entry["path"])
        for entry in typed_path_entries
        if "xenon" in {str(scope) for scope in entry.get("scopes", [])}
    }
    registry_critical_paths = {
        str(entry["path"])
        for entry in typed_path_entries
        if "critical_check" in {str(scope) for scope in entry.get("scopes", [])}
    }
    registry_critical_functions = {
        str(entry["name"]): int(entry["max_complexity"])
        for entry in typed_function_entries
        if "critical_check" in {str(scope) for scope in entry.get("scopes", [])}
    }

    normalized_workflow_xenon = {
        _normalize_path_pattern(path) for path in workflow_xenon_paths
    }
    normalized_registry_xenon = {
        _normalize_path_pattern(path) for path in registry_xenon_paths
    }
    normalized_workflow_critical = {
        _normalize_path_pattern(path) for path in workflow_critical_paths
    }
    normalized_registry_critical = {
        _normalize_path_pattern(path) for path in registry_critical_paths
    }

    if normalized_workflow_xenon != normalized_registry_xenon:
        errors.append(
            "xenon exclude registry drifted: "
            f"workflow_only={sorted(normalized_workflow_xenon - normalized_registry_xenon)} "
            f"registry_only={sorted(normalized_registry_xenon - normalized_workflow_xenon)}"
        )
    if normalized_workflow_critical != normalized_registry_critical:
        errors.append(
            "critical-check exempt path registry drifted: "
            f"workflow_only={sorted(normalized_workflow_critical - normalized_registry_critical)} "
            f"registry_only={sorted(normalized_registry_critical - normalized_workflow_critical)}"
        )
    if workflow_critical_functions != registry_critical_functions:
        errors.append(
            "critical-check exempt function registry drifted: "
            f"workflow={workflow_critical_functions} registry={registry_critical_functions}"
        )

    if errors:
        print("Duplication/complexity exemption registry errors:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        raise SystemExit(1)

    print(
        "[OK] duplication/complexity exemptions registry matches workflow and has current metadata"
    )


if __name__ == "__main__":
    main()
