#!/usr/bin/env python3
"""Generate the deterministic tracked flaky-test burndown review."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INVENTORY = Path("configs/quality/flaky_test_inventory.yaml")
DEFAULT_TEST_GOVERNANCE = Path("reports/quality/test-governance-current.json")
DEFAULT_JSON_OUTPUT = Path("reports/quality/flaky-test-burndown-review.json")

DIMENSION_SPECS = (
    ("by_layer", "layer", "layers"),
    ("by_category", "category", "categories"),
    ("by_severity", "severity", "severities"),
    ("by_triage", "triage_status", "triage_statuses"),
    ("by_alert_level", "alert_level", "alert_levels"),
)
ENTRY_TEXT_FIELDS = ("nodeid", "owner", "cause", "remediation")


def _resolve_path(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected YAML object: {path}")
    return payload


def _load_json_mapping(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def _mapping(value: object, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Expected object at {label}")
    return value


def _string_list(value: object, *, label: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(item, str) and item.strip() for item in value)
    ):
        raise ValueError(f"Expected non-empty string list at {label}")
    result = [item.strip() for item in value]
    if len(result) != len(set(result)):
        raise ValueError(f"Duplicate values at {label}")
    return result


def _nonnegative_int(value: object, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"Expected non-negative integer at {label}")
    return value


def _semantic_sha256(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _dimension_values(inventory: dict[str, Any]) -> dict[str, list[str]]:
    dimensions = _mapping(inventory.get("dimensions"), label="dimensions")
    return {
        config_key: _string_list(
            dimensions.get(config_key),
            label=f"dimensions.{config_key}",
        )
        for _, _, config_key in DIMENSION_SPECS
    }


def _reviewed_entries(
    inventory: dict[str, Any],
    *,
    dimensions: dict[str, list[str]],
) -> list[dict[str, Any]]:
    raw_entries = inventory.get("reviewed_flaky_tests")
    if not isinstance(raw_entries, list):
        raise ValueError("Expected list at reviewed_flaky_tests")

    entries: list[dict[str, Any]] = []
    for index, raw_entry in enumerate(raw_entries):
        entry = _mapping(raw_entry, label=f"reviewed_flaky_tests[{index}]")
        for field in ENTRY_TEXT_FIELDS:
            value = entry.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"Expected non-empty string at reviewed_flaky_tests[{index}].{field}"
                )
        for _, entry_field, config_key in DIMENSION_SPECS:
            if entry.get(entry_field) not in dimensions[config_key]:
                raise ValueError(
                    f"Unsupported {entry_field} at reviewed_flaky_tests[{index}]"
                )
        entries.append(dict(entry))

    entries.sort(key=lambda item: str(item["nodeid"]))
    nodeids = [str(entry["nodeid"]) for entry in entries]
    if len(nodeids) != len(set(nodeids)):
        raise ValueError("Duplicate nodeid in reviewed_flaky_tests")
    return entries


def _dimension_counts(
    entries: list[dict[str, Any]],
    *,
    field: str,
    values: list[str],
) -> dict[str, int]:
    counts = dict.fromkeys(values, 0)
    for entry in entries:
        counts[str(entry[field])] += 1
    return counts


def _test_governance_summary(payload: dict[str, Any]) -> dict[str, object]:
    report = _mapping(payload.get("report"), label="test_governance.report")
    source_tree_sha256 = payload.get("source_tree_sha256")
    if not isinstance(source_tree_sha256, str) or len(source_tree_sha256) != 64:
        raise ValueError("Invalid test_governance.source_tree_sha256")
    budget_violations = payload.get("budget_violations")
    if not isinstance(budget_violations, list):
        raise ValueError("Expected list at test_governance.budget_violations")
    return {
        "total_tests_analyzed": _nonnegative_int(
            report.get("total_test_functions"),
            label="test_governance.report.total_test_functions",
        ),
        "total_test_files": _nonnegative_int(
            report.get("total_test_files"),
            label="test_governance.report.total_test_files",
        ),
        "test_governance_budget_violation_count": len(budget_violations),
        "test_governance_source_tree_sha256": source_tree_sha256,
    }


def build_payload(
    repo_root: Path = PROJECT_ROOT,
    *,
    inventory_path: Path = DEFAULT_INVENTORY,
    test_governance_path: Path = DEFAULT_TEST_GOVERNANCE,
) -> dict[str, object]:
    """Build a deterministic review from curated rows and current static evidence."""
    repo_root = repo_root.resolve()
    inventory = _load_yaml_mapping(_resolve_path(repo_root, inventory_path))
    test_governance = _load_json_mapping(_resolve_path(repo_root, test_governance_path))
    if inventory.get("schema_version") != 1:
        raise ValueError("Unsupported flaky_test_inventory schema_version")

    dimensions = _dimension_values(inventory)
    entries = _reviewed_entries(inventory, dimensions=dimensions)
    linked_issues = inventory.get("linked_issues")
    if not isinstance(linked_issues, list) or not all(
        isinstance(issue, int) and not isinstance(issue, bool) and issue > 0
        for issue in linked_issues
    ):
        raise ValueError("Expected positive integer list at linked_issues")
    if len(linked_issues) != len(set(linked_issues)):
        raise ValueError("Duplicate values at linked_issues")
    rendered_issues = [f"#{issue}" for issue in sorted(linked_issues)]
    if not rendered_issues:
        raise ValueError("linked_issues must not be empty")

    summary: dict[str, object] = {
        **_test_governance_summary(test_governance),
        "total_flaky": len(entries),
    }
    for output_key, entry_field, config_key in DIMENSION_SPECS:
        summary[output_key] = _dimension_counts(
            entries,
            field=entry_field,
            values=dimensions[config_key],
        )

    reviewed_on = inventory.get("reviewed_on")
    evidence_scope = inventory.get("evidence_scope")
    if not isinstance(reviewed_on, str) or not reviewed_on.strip():
        raise ValueError("Expected reviewed_on string")
    try:
        date.fromisoformat(reviewed_on.strip())
    except ValueError as exc:
        raise ValueError("Expected ISO date at reviewed_on") from exc
    if not isinstance(evidence_scope, str) or not evidence_scope.strip():
        raise ValueError("Expected evidence_scope string")

    return {
        "schema_version": "flaky-test-burndown-review-v2",
        "generated_by": "scripts.engineering.qa.report_flaky_test_burndown_review",
        "linked_issue": rendered_issues[0],
        "linked_issues": rendered_issues,
        "reviewed_on": reviewed_on.strip(),
        "decision": "reviewed_inventory_clear"
        if not entries
        else "remediation_required",
        "evidence_scope": evidence_scope.strip(),
        "policy": {
            "flaky_test_definition": _string_list(
                inventory.get("flaky_test_definition"),
                label="flaky_test_definition",
            ),
            "no_growth_gate": (
                "reports/quality/debt-governance-gates.json::flaky_test_total_count"
            ),
            "untriaged_gate": (
                "reports/quality/debt-governance-gates.json::flaky_test_untriaged_count"
            ),
            "remediation_workflow": _string_list(
                inventory.get("remediation_workflow"),
                label="remediation_workflow",
            ),
        },
        "source_artifacts": [
            DEFAULT_INVENTORY.as_posix(),
            DEFAULT_TEST_GOVERNANCE.as_posix(),
        ],
        "source_fingerprints": {
            "curated_inventory_sha256": _semantic_sha256(inventory),
            "test_governance_source_tree_sha256": summary[
                "test_governance_source_tree_sha256"
            ],
        },
        "summary": summary,
        "reviewed_flaky_tests": entries,
        "review_notes": _string_list(
            inventory.get("review_notes"),
            label="review_notes",
        ),
    }


def _canonical_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _write_text_atomically(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        text=True,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument(
        "--test-governance",
        type=Path,
        default=DEFAULT_TEST_GOVERNANCE,
    )
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = args.repo_root.resolve()
    try:
        payload = build_payload(
            repo_root,
            inventory_path=args.inventory,
            test_governance_path=args.test_governance,
        )
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"[flaky-test-burndown-review] input error: {exc}", file=sys.stderr)
        return 2

    output_path = _resolve_path(repo_root, args.json_out)
    expected = _canonical_json(payload)
    if args.check:
        if not output_path.exists():
            print(
                f"[flaky-test-burndown-review] missing artifact: {output_path}",
                file=sys.stderr,
            )
            return 1
        if output_path.read_text(encoding="utf-8") != expected:
            print(
                f"[flaky-test-burndown-review] stale artifact: {output_path}",
                file=sys.stderr,
            )
            return 1
        print("[flaky-test-burndown-review] artifact is current")
        return 0

    _write_text_atomically(output_path, expected)
    print(f"[flaky-test-burndown-review] wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
