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
DEFAULT_GENERATED_ARTIFACTS = (
    Path("reports/quality/test-governance-current.json"),
    Path("reports/quality/config-discrepancy-baseline.json"),
)

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


def _file_tree_sha256(paths: list[Path], *, root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.as_posix()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


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


def capture_empirical_run_metadata(
    repo_root: Path,
    *,
    output_path: Path,
    run_id: str,
    seed: int,
    source_sha: str,
    shard_id: str,
    order_mode: str,
    phase: str,
    order_manifest: Path | None = None,
) -> dict[str, object]:
    """Capture per-run replay/generated hashes before and after pytest."""
    repo_root = repo_root.resolve()
    resolved_output = _resolve_path(repo_root, output_path)
    replay_files = list((repo_root / "tests/fixtures/vcr").rglob("*.yaml"))
    generated_files = [
        repo_root / path
        for path in DEFAULT_GENERATED_ARTIFACTS
        if (repo_root / path).exists()
    ]
    if not generated_files:
        raise ValueError("No governed generated artifacts available to fingerprint")
    replay_hash = _file_tree_sha256(replay_files, root=repo_root)
    generated_hash = _file_tree_sha256(generated_files, root=repo_root)
    if phase == "start":
        payload: dict[str, object] = {
            "schema_version": "flaky-run-metadata-v2",
            "run_id": run_id,
            "seed": seed,
            "source_sha": source_sha,
            "order_mode": order_mode,
            "shard_id": shard_id,
            "artifact_hashes": {
                "replay_tree_before_sha256": replay_hash,
                "generated_artifacts_before_sha256": generated_hash,
            },
        }
    elif phase == "finish":
        payload = _load_json_mapping(resolved_output)
        artifact_hashes = _mapping(
            payload.get("artifact_hashes"), label="artifact_hashes"
        )
        artifact_hashes["replay_tree_after_sha256"] = replay_hash
        artifact_hashes["generated_artifacts_after_sha256"] = generated_hash
        if order_manifest is None:
            raise ValueError("Finish capture requires an execution-order manifest")
        order_path = _resolve_path(repo_root, order_manifest)
        execution_order = json.loads(order_path.read_text(encoding="utf-8"))
        if not isinstance(execution_order, list) or not all(
            isinstance(nodeid, str) and nodeid for nodeid in execution_order
        ):
            raise ValueError("Execution-order manifest must be a node-id list")
        payload["execution_order"] = execution_order
    else:
        raise ValueError(f"Unsupported capture phase: {phase}")
    _write_text_atomically(resolved_output, _canonical_json(payload))
    return payload


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
    source_shas: set[str] = set()
    for metadata_path in sorted(resolved_run_dir.glob("run-*.json")):
        metadata = _load_json_mapping(metadata_path)
        run_id = metadata.get("run_id")
        seed = metadata.get("seed")
        source_sha = metadata.get("source_sha")
        if not isinstance(run_id, str) or not run_id:
            raise ValueError(f"Invalid run_id in {metadata_path}")
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError(f"Invalid seed in {metadata_path}")
        if not isinstance(source_sha, str) or not source_sha:
            raise ValueError(f"Invalid source_sha in {metadata_path}")
        execution_order = metadata.get("execution_order")
        if not isinstance(execution_order, list) or not all(
            isinstance(nodeid, str) and nodeid for nodeid in execution_order
        ):
            raise ValueError(f"Missing execution order in {metadata_path}")
        artifact_hashes = _mapping(
            metadata.get("artifact_hashes"),
            label=f"{metadata_path}.artifact_hashes",
        )
        required_hashes = {
            "replay_tree_before_sha256",
            "replay_tree_after_sha256",
            "generated_artifacts_before_sha256",
            "generated_artifacts_after_sha256",
        }
        if not required_hashes <= artifact_hashes.keys():
            raise ValueError(f"Incomplete per-run artifact hashes in {metadata_path}")
        junit_path = resolved_run_dir / f"junit-{run_id}.xml"
        if not junit_path.exists():
            raise ValueError(f"Missing JUnit for {run_id}: {junit_path}")
        outcomes = _junit_outcomes(junit_path)
        if not outcomes:
            raise ValueError(f"Empirical run executed zero tests: {run_id}")
        for nodeid, status in outcomes.items():
            outcomes_by_node.setdefault(nodeid, set()).add(status)
        outcome_sha = _semantic_sha256(outcomes)
        source_shas.add(source_sha)
        runs.append(
            {
                "run_id": run_id,
                "seed": seed,
                "order_mode": metadata.get("order_mode", "seeded-random"),
                "shard_id": metadata.get("shard_id", "determinism-critical"),
                "source_sha": source_sha,
                "executed_count": len(outcomes),
                "execution_order": execution_order,
                "outcomes": outcomes,
                "artifact_hashes": {
                    "node_outcomes_sha256": outcome_sha,
                    **{key: str(artifact_hashes[key]) for key in required_hashes},
                },
            }
        )
    if len(runs) < 3:
        raise ValueError("Empirical flaky telemetry requires at least three runs")
    if len(source_shas) != 1:
        raise ValueError("Empirical runs must use one source SHA")

    unstable = {
        nodeid: sorted(statuses)
        for nodeid, statuses in sorted(outcomes_by_node.items())
        if len(statuses) > 1
    }
    untriaged = sorted(set(unstable) - set(reviewed))
    replay_hashes = {
        str(run["artifact_hashes"]["replay_tree_after_sha256"])  # type: ignore[index]
        for run in runs
    }
    generated_hashes = {
        str(run["artifact_hashes"]["generated_artifacts_after_sha256"])  # type: ignore[index]
        for run in runs
    }
    replay_unchanged_within_runs = all(
        run["artifact_hashes"]["replay_tree_before_sha256"]  # type: ignore[index]
        == run["artifact_hashes"]["replay_tree_after_sha256"]  # type: ignore[index]
        for run in runs
    )
    generated_unchanged_within_runs = all(
        run["artifact_hashes"]["generated_artifacts_before_sha256"]  # type: ignore[index]
        == run["artifact_hashes"]["generated_artifacts_after_sha256"]  # type: ignore[index]
        for run in runs
    )
    execution_orders = {
        tuple(run["execution_order"])  # type: ignore[arg-type]
        for run in runs
    }
    non_passed = {
        nodeid: sorted(statuses)
        for nodeid, statuses in sorted(outcomes_by_node.items())
        if statuses != {"passed"}
    }
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
        "schema_version": "flaky-test-empirical-v2",
        "generated_by": "scripts.engineering.qa.report_flaky_test_burndown_review",
        "source_sha": next(iter(source_shas)),
        "run_count": len(runs),
        "runs": runs,
        "comparison": {
            "unstable_node_count": len(unstable),
            "unstable_nodes": unstable,
            "untriaged_unstable_nodes": untriaged,
            "replay_fingerprint_stable": (
                replay_unchanged_within_runs and len(replay_hashes) == 1
            ),
            "generated_artifact_fingerprint_stable": (
                generated_unchanged_within_runs and len(generated_hashes) == 1
            ),
            "execution_order_changed": len(execution_orders) > 1,
            "non_passed_nodes": non_passed,
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
    parser.add_argument("--empirical-run-dir", type=Path)
    parser.add_argument(
        "--empirical-json-out", type=Path, default=DEFAULT_EMPIRICAL_OUTPUT
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--capture-run-phase", choices=("start", "finish"))
    parser.add_argument("--run-metadata-out", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--source-sha")
    parser.add_argument("--shard-id", default="determinism-critical")
    parser.add_argument("--order-mode", default="seeded-random")
    parser.add_argument("--order-manifest", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = args.repo_root.resolve()
    try:
        if args.capture_run_phase is not None:
            if not all(
                value is not None
                for value in (
                    args.run_metadata_out,
                    args.run_id,
                    args.seed,
                    args.source_sha,
                )
            ):
                raise ValueError("Run metadata capture requires output/id/seed/source")
            capture_empirical_run_metadata(
                repo_root,
                output_path=args.run_metadata_out,
                run_id=args.run_id,
                seed=args.seed,
                source_sha=args.source_sha,
                shard_id=args.shard_id,
                order_mode=args.order_mode,
                phase=args.capture_run_phase,
                order_manifest=args.order_manifest,
            )
            return 0
        if args.empirical_run_dir is not None:
            payload = build_empirical_payload(
                repo_root,
                run_dir=args.empirical_run_dir,
                inventory_path=args.inventory,
            )
            output_path = _resolve_path(repo_root, args.empirical_json_out)
            _write_text_atomically(output_path, _canonical_json(payload))
            untriaged = payload["curated_inventory_reconciliation"]["untriaged_count"]  # type: ignore[index]
            print(f"[flaky-test-empirical] wrote {output_path}")
            comparison = payload["comparison"]  # type: ignore[assignment]
            invalid_evidence = bool(
                untriaged
                or comparison["non_passed_nodes"]  # type: ignore[index]
                or not comparison["replay_fingerprint_stable"]  # type: ignore[index]
                or not comparison["generated_artifact_fingerprint_stable"]  # type: ignore[index]
                or not comparison["execution_order_changed"]  # type: ignore[index]
            )
            return 1 if invalid_evidence else 0
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
