"""Fail closed when coverage closeout exceeds its fixed CI topology budget."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from scripts.engineering.qa.run_local_coverage_verify import SHARDS

ROOT = Path(__file__).resolve().parents[3]
BUDGET_PATH = Path("configs/quality/ci_closeout_cost_budget.yaml")
CIRCLECI_PATH = Path(".circleci/config.yml")
WORKFLOWS = ("pr-gate", "main-coverage-closeout", "migration-coverage-closeout")


def _yaml(root: Path, path: str | Path) -> dict[str, Any]:
    payload = yaml.safe_load((root / path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected mapping in {path}")
    return payload


def _matrix_groups(config: dict[str, Any], workflow: str) -> list[str]:
    jobs = config["workflows"][workflow]["jobs"]
    matches = [
        item["proof-coverage-shard"]["matrix"]["parameters"]["group"]
        for item in jobs
        if isinstance(item, dict) and "proof-coverage-shard" in item
    ]
    if len(matches) != 1 or not isinstance(matches[0], list):
        raise ValueError(f"Expected one coverage matrix in workflow {workflow}")
    return [str(value) for value in matches[0]]


def evaluate_closeout_cost_budget(root: Path = ROOT) -> dict[str, Any]:
    """Evaluate the static topology and telemetry-backed closeout cost limits."""
    budget = _yaml(root, BUDGET_PATH)
    catalog = _yaml(root, budget["catalog_source"])
    telemetry = _yaml(root, budget["telemetry_source"])
    circleci = _yaml(root, CIRCLECI_PATH)
    errors: list[str] = []

    if budget.get("schema_version") != 1:
        errors.append("invalid_schema_version")
    if budget.get("budget_policy") != "shrink_only":
        errors.append("budget_is_not_shrink_only")
    baseline = budget["baseline"]
    limits = budget["limits"]
    if baseline["source_commit"] != telemetry["source_commit"]:
        errors.append("stale_telemetry_source_commit")
    if (
        baseline["test_tree_sha256"]
        != telemetry["measurement_provenance"]["test_tree_sha256"]
    ):
        errors.append("stale_telemetry_test_tree")

    job_count = limits["coverage_job_count"]
    if type(job_count) is not int or job_count != 4:
        errors.append("coverage_job_count_changed")
        job_count = 4
    expected_groups = [str(index) for index in range(job_count)]
    expected_shards = {shard.name for shard in SHARDS}
    lane_seconds = telemetry["duration_telemetry"]["execution_context"][
        "lane_wall_time_s"
    ]
    selected: list[str] = []
    group_seconds: dict[str, float] = {}
    for group in expected_groups:
        name = f"coverage-{group}"
        spec = catalog["checks"].get(name)
        if not isinstance(spec, dict):
            errors.append(f"missing_group:{name}")
            continue
        args = spec["argv"]
        shards = [args[index + 1] for index, arg in enumerate(args) if arg == "--shard"]
        selected.extend(shards)
        unknown = sorted(set(shards) - expected_shards)
        if unknown:
            errors.append(f"unknown_shards:{name}:{','.join(unknown)}")
            continue
        group_seconds[group] = round(sum(float(lane_seconds[item]) for item in shards), 2)

    if len(selected) != len(set(selected)):
        errors.append("duplicate_shard_assignment")
    if set(selected) != expected_shards:
        errors.append("incomplete_shard_assignment")

    total_seconds = round(sum(group_seconds.values()), 2)
    critical_seconds = max(group_seconds.values(), default=0.0)
    if total_seconds > float(limits["total_lane_seconds"]):
        errors.append("total_lane_budget_exceeded")
    if critical_seconds > float(limits["critical_path_seconds"]):
        errors.append("critical_path_budget_exceeded")
    if float(limits["total_lane_seconds"]) > float(baseline["total_lane_seconds"]):
        errors.append("total_lane_budget_increased")
    if float(limits["critical_path_seconds"]) >= float(
        baseline["critical_path_seconds"]
    ):
        errors.append("critical_path_budget_not_reduced")
    if limits["additional_coverage_jobs"] != 0:
        errors.append("additional_coverage_jobs_allowed")
    if limits["resource_class_increase_allowed"] is not False:
        errors.append("resource_class_increase_allowed")

    expected_resource = limits["coverage_resource_class"]
    actual_resource = circleci["jobs"]["proof-coverage-shard"]["resource_class"]
    if actual_resource != expected_resource:
        errors.append("coverage_resource_class_changed")
    for workflow in WORKFLOWS:
        if _matrix_groups(circleci, workflow) != expected_groups:
            errors.append(f"coverage_matrix_changed:{workflow}")

    return {
        "schema_version": 1,
        "outcome": "STOP" if errors else "PASS",
        "errors": errors,
        "measurements": {
            "coverage_job_count": job_count,
            "coverage_resource_class": actual_resource,
            "group_seconds": group_seconds,
            "total_lane_seconds": total_seconds,
            "critical_path_seconds": critical_seconds,
        },
        "limits": dict(limits),
        "telemetry_source_commit": telemetry["source_commit"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = evaluate_closeout_cost_budget()
    except (KeyError, OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        result = {
            "schema_version": 1,
            "outcome": "STOP",
            "errors": [str(exc)],
        }
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"closeout-cost-budget: {result['outcome']}")
        for error in result["errors"]:
            print(f"  - {error}")
    return 0 if result["outcome"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
