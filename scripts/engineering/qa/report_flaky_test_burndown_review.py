#!/usr/bin/env python3
"""Generate the deterministic tracked flaky-test burndown review."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INVENTORY = Path("configs/quality/flaky_test_inventory.yaml")
DEFAULT_TEST_GOVERNANCE = Path("reports/quality/test-governance-current.json")
DEFAULT_JSON_OUTPUT = Path("reports/quality/flaky-test-burndown-review.json")
DEFAULT_EMPIRICAL_OUTPUT = Path("reports/test-telemetry/flaky-test-empirical.json")

DIMENSION_SPECS = (
    ("by_layer", "layer", "layers"),
    ("by_category", "category", "categories"),
    ("by_severity", "severity", "severities"),
    ("by_triage", "triage_status", "triage_statuses"),
    ("by_alert_level", "alert_level", "alert_levels"),
)
ENTRY_TEXT_FIELDS = ("nodeid", "owner", "cause", "remediation")


def _resolve_path(repo_root: Path, path: Path) -> Path:
    from scripts.engineering.common.repo_paths import resolve_output_path

    return resolve_output_path(path, root=repo_root)


def _load_yaml_mapping(path: Path, *, root: Path | None = None) -> dict[str, Any]:
    if root is not None:
        from scripts.engineering.common.repo_paths import ensure_path_within_root

        path = ensure_path_within_root(path, root)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected YAML object: {path}")
    return payload


def _load_json_mapping(path: Path, *, root: Path | None = None) -> dict[str, Any]:
    if root is not None:
        from scripts.engineering.common.repo_paths import ensure_path_within_root

        path = ensure_path_within_root(path, root)
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


def _file_tree_sha256(paths: list[Path], *, root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.as_posix()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def compute_replay_tree_sha256(repo_root: Path) -> str:
    """Return the current deterministic VCR replay-tree fingerprint."""
    resolved_root = repo_root.resolve()
    replay_files = list((resolved_root / "tests/fixtures/vcr").rglob("*.yaml"))
    return _file_tree_sha256(replay_files, root=resolved_root)


def _sha256_digest(value: object, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"Invalid SHA-256 at {label}")
    return value


def _junit_outcomes(path: Path) -> dict[str, str]:
    root = ET.parse(path).getroot()
    outcomes: dict[str, str] = {}
    for case in root.iter("testcase"):
        nodeid = f"{case.get('classname', 'unknown')}::{case.get('name', 'unknown')}"
        if case.find("failure") is not None:
            status = "failed"
        elif case.find("error") is not None:
            status = "error"
        elif case.find("skipped") is not None:
            status = "skipped"
        else:
            status = "passed"
        outcomes[nodeid] = status
    return dict(sorted(outcomes.items()))


def _validate_identical_node_coverage(
    node_sets: list[tuple[str, frozenset[str]]],
) -> None:
    reference_run_id, reference_nodes = node_sets[0]
    deltas: list[str] = []
    for run_id, nodes in node_sets[1:]:
        missing = sorted(reference_nodes - nodes)
        extra = sorted(nodes - reference_nodes)
        if missing or extra:
            deltas.append(f"{run_id}: missing={missing!r}, extra={extra!r}")
    if deltas:
        details = "; ".join(deltas)
        raise ValueError(
            "Empirical runs must execute an identical set of test nodes; "
            f"reference={reference_run_id}; {details}"
        )


def _require_empirical_run_fields(
    metadata: dict[str, object],
    metadata_path: Path,
) -> tuple[str, int, str]:
    run_id = metadata.get("run_id")
    seed = metadata.get("seed")
    source_sha = metadata.get("source_sha")
    if not isinstance(run_id, str) or not run_id:
        raise ValueError(f"Invalid run_id in {metadata_path}")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError(f"Invalid seed in {metadata_path}")
    if not isinstance(source_sha, str) or not source_sha:
        raise ValueError(f"Invalid source_sha in {metadata_path}")
    return run_id, seed, source_sha


def _load_empirical_outcomes(
    *,
    run_id: str,
    resolved_run_dir: Path,
) -> dict[str, str]:
    junit_path = resolved_run_dir / f"junit-{run_id}.xml"
    if not junit_path.exists():
        raise ValueError(f"Missing JUnit for {run_id}: {junit_path}")
    outcomes = _junit_outcomes(junit_path)
    if not outcomes:
        raise ValueError(f"Empirical run executed zero tests: {run_id}")
    return outcomes


def _load_empirical_run(
    metadata_path: Path,
    *,
    resolved_run_dir: Path,
    outcomes_by_node: dict[str, set[str]],
    node_sets: list[tuple[str, frozenset[str]]],
    replay_fingerprints: set[str],
    source_shas: set[str],
) -> dict[str, object]:
    metadata = _load_json_mapping(metadata_path)
    run_id, seed, source_sha = _require_empirical_run_fields(metadata, metadata_path)
    replay_fingerprint = _sha256_digest(
        metadata.get("replay_tree_sha256"),
        label=f"{metadata_path}.replay_tree_sha256",
    )
    outcomes = _load_empirical_outcomes(
        run_id=run_id, resolved_run_dir=resolved_run_dir
    )
    node_sets.append((run_id, frozenset(outcomes)))
    for nodeid, status in outcomes.items():
        outcomes_by_node.setdefault(nodeid, set()).add(status)
    outcome_sha = _semantic_sha256(outcomes)
    replay_fingerprints.add(replay_fingerprint)
    source_shas.add(source_sha)
    return {
        "run_id": run_id,
        "seed": seed,
        "order_mode": metadata.get("order_mode", "seeded-random"),
        "shard_id": metadata.get("shard_id", "determinism-critical"),
        "source_sha": source_sha,
        "executed_count": len(outcomes),
        "outcomes": outcomes,
        "artifact_hashes": {
            "node_outcomes_sha256": outcome_sha,
            "replay_tree_sha256": replay_fingerprint,
        },
    }


def build_empirical_payload(
    repo_root: Path,
    *,
    run_dir: Path,
    inventory_path: Path = DEFAULT_INVENTORY,
) -> dict[str, object]:
    """Build empirical repeated/order-randomized telemetry from JUnit runs."""
    repo_root = repo_root.resolve()
    resolved_run_dir = _resolve_path(repo_root, run_dir)
    inventory = _load_yaml_mapping(_resolve_path(repo_root, inventory_path))
    reviewed = {
        str(entry["nodeid"]): entry
        for entry in inventory.get("reviewed_flaky_tests", [])
        if isinstance(entry, dict) and isinstance(entry.get("nodeid"), str)
    }
    runs: list[dict[str, object]] = []
    outcomes_by_node: dict[str, set[str]] = {}
    node_sets: list[tuple[str, frozenset[str]]] = []
    replay_fingerprints: set[str] = set()
    source_shas: set[str] = set()
    for metadata_path in sorted(resolved_run_dir.glob("run-*.json")):
        runs.append(
            _load_empirical_run(
                metadata_path,
                resolved_run_dir=resolved_run_dir,
                outcomes_by_node=outcomes_by_node,
                node_sets=node_sets,
                replay_fingerprints=replay_fingerprints,
                source_shas=source_shas,
            )
        )
    if len(runs) < 3:
        raise ValueError("Empirical flaky telemetry requires at least three runs")
    if len(source_shas) != 1:
        raise ValueError("Empirical runs must use one source SHA")
    _validate_identical_node_coverage(node_sets)

    unstable = {
        nodeid: sorted(statuses)
        for nodeid, statuses in sorted(outcomes_by_node.items())
        if len(statuses) > 1
    }
    untriaged = sorted(set(unstable) - set(reviewed))
    quarantined = [
        {
            "nodeid": nodeid,
            "owner": entry.get("owner"),
            "cause": entry.get("cause"),
            "status": entry.get("triage_status"),
            "removal_criteria": entry.get("remediation"),
        }
        for nodeid, entry in sorted(reviewed.items())
    ]
    return {
        "schema_version": "flaky-test-empirical-v1",
        "generated_by": "scripts.engineering.qa.report_flaky_test_burndown_review",
        "source_sha": next(iter(source_shas)),
        "run_count": len(runs),
        "runs": runs,
        "comparison": {
            "unstable_node_count": len(unstable),
            "unstable_nodes": unstable,
            "untriaged_unstable_nodes": untriaged,
            "replay_fingerprint_stable": len(replay_fingerprints) == 1,
        },
        "curated_inventory_reconciliation": {
            "inventory_sha256": _semantic_sha256(inventory),
            "quarantine": quarantined,
            "untriaged_count": len(untriaged),
        },
    }


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


def _write_text_atomically(
    path: Path, content: str, *, root: Path | None = None
) -> None:
    if root is not None:
        from scripts.engineering.common.repo_paths import ensure_path_within_root

        path = ensure_path_within_root(path, root)
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
    parser.add_argument("--empirical-run-dir", type=Path)
    parser.add_argument(
        "--empirical-json-out", type=Path, default=DEFAULT_EMPIRICAL_OUTPUT
    )
    parser.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = args.repo_root.resolve()
    try:
        if args.empirical_run_dir is not None:
            payload = build_empirical_payload(
                repo_root,
                run_dir=args.empirical_run_dir,
                inventory_path=args.inventory,
            )
            output_path = _resolve_path(repo_root, args.empirical_json_out)
            _write_text_atomically(
                output_path, _canonical_json(payload), root=repo_root
            )
            reconciliation = payload["curated_inventory_reconciliation"]
            comparison = payload["comparison"]
            if not isinstance(reconciliation, dict) or not isinstance(comparison, dict):
                raise ValueError("empirical payload summary sections must be mappings")
            untriaged = reconciliation["untriaged_count"]
            replay_stable = comparison["replay_fingerprint_stable"]
            print(f"[flaky-test-empirical] wrote {output_path}")
            return 1 if untriaged or not replay_stable else 0
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

    _write_text_atomically(output_path, expected, root=repo_root)
    print(f"[flaky-test-burndown-review] wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
