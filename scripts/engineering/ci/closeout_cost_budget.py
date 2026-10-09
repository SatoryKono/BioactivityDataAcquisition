"""Fail closed when coverage closeout exceeds its fixed CI topology budget."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, cast

import yaml

from scripts.engineering.qa.run_local_coverage_verify import SHARDS

ROOT = Path(__file__).resolve().parents[3]
BUDGET_PATH = Path("configs/quality/ci_closeout_cost_budget.yaml")
CIRCLECI_PATH = Path(".circleci/config.yml")
WORKFLOWS = ("pr-gate", "main-coverage-closeout", "migration-coverage-closeout")
MEASURED_JOBS = (
    "arch-tests",
    "proof-coverage",
    "proof-governance",
    "proof-debt",
    "proof-quality",
    "proof-closeout",
    "proof-docs",
    "docs-governance",
    "proof-coverage-shard",
)


@dataclass(frozen=True)
class CoverageMeasurement:
    """Derived coverage topology and duration measurements."""

    job_count: int
    expected_groups: list[str]
    group_seconds: dict[str, float]
    total_seconds: float
    critical_seconds: float


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


def _validate_budget_identity(
    budget: dict[str, Any], telemetry: dict[str, Any], errors: list[str]
) -> tuple[dict[str, Any], dict[str, Any]]:
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
    return baseline, limits


def _measure_coverage_group(
    catalog: dict[str, Any],
    name: str,
    expected_shards: set[str],
    lane_seconds: dict[str, Any],
    errors: list[str],
) -> tuple[list[str], float | None]:
    spec = catalog["checks"].get(name)
    if not isinstance(spec, dict):
        errors.append(f"missing_group:{name}")
        return [], None

    args = spec["argv"]
    shards = [args[index + 1] for index, arg in enumerate(args) if arg == "--shard"]
    unknown = sorted(set(shards) - expected_shards)
    if unknown:
        errors.append(f"unknown_shards:{name}:{','.join(unknown)}")
        return shards, None
    duration = round(sum(float(lane_seconds[item]) for item in shards), 2)
    return shards, duration


def _coverage_measurement(
    catalog: dict[str, Any],
    telemetry: dict[str, Any],
    limits: dict[str, Any],
    errors: list[str],
) -> CoverageMeasurement:
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
        shards, duration = _measure_coverage_group(
            catalog, name, expected_shards, lane_seconds, errors
        )
        selected.extend(shards)
        if duration is not None:
            group_seconds[group] = duration

    if len(selected) != len(set(selected)):
        errors.append("duplicate_shard_assignment")
    if set(selected) != expected_shards:
        errors.append("incomplete_shard_assignment")

    total_seconds = round(sum(group_seconds.values()), 2)
    return CoverageMeasurement(
        job_count=job_count,
        expected_groups=expected_groups,
        group_seconds=group_seconds,
        total_seconds=total_seconds,
        critical_seconds=max(group_seconds.values(), default=0.0),
    )


def _validate_cost_limits(
    baseline: dict[str, Any],
    limits: dict[str, Any],
    measurement: CoverageMeasurement,
    errors: list[str],
) -> None:
    if measurement.total_seconds > float(limits["total_lane_seconds"]):
        errors.append("total_lane_budget_exceeded")
    if measurement.critical_seconds > float(limits["critical_path_seconds"]):
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


def _validate_runtime_measurement(
    budget: dict[str, Any], circleci: dict[str, Any], errors: list[str]
) -> None:
    runtime_measurement = budget["runtime_measurement"]
    start_command = runtime_measurement["start_command"]
    if runtime_measurement["additional_telemetry_jobs"] != 0:
        errors.append("additional_telemetry_jobs_allowed")
    if start_command not in circleci["commands"]:
        errors.append("missing_runtime_measurement_command")
    for job_name in MEASURED_JOBS:
        if circleci["jobs"][job_name]["steps"][0] != start_command:
            errors.append(f"runtime_measurement_not_first:{job_name}")


def _validate_circleci_topology(
    circleci: dict[str, Any],
    limits: dict[str, Any],
    expected_groups: list[str],
    errors: list[str],
) -> str:
    expected_resource = limits["coverage_resource_class"]
    actual_resource = cast(
        str, circleci["jobs"]["proof-coverage-shard"]["resource_class"]
    )
    if actual_resource != expected_resource:
        errors.append("coverage_resource_class_changed")
    for workflow in WORKFLOWS:
        if _matrix_groups(circleci, workflow) != expected_groups:
            errors.append(f"coverage_matrix_changed:{workflow}")
    return actual_resource


def evaluate_closeout_cost_budget(root: Path = ROOT) -> dict[str, Any]:
    """Evaluate the static topology and telemetry-backed closeout cost limits."""
    budget = _yaml(root, BUDGET_PATH)
    catalog = _yaml(root, budget["catalog_source"])
    telemetry = _yaml(root, budget["telemetry_source"])
    circleci = _yaml(root, CIRCLECI_PATH)
    errors: list[str] = []
    baseline, limits = _validate_budget_identity(budget, telemetry, errors)
    measurement = _coverage_measurement(catalog, telemetry, limits, errors)
    _validate_cost_limits(baseline, limits, measurement, errors)
    _validate_runtime_measurement(budget, circleci, errors)
    actual_resource = _validate_circleci_topology(
        circleci, limits, measurement.expected_groups, errors
    )

    return {
        "schema_version": 1,
        "outcome": "STOP" if errors else "PASS",
        "errors": errors,
        "measurements": {
            "coverage_job_count": measurement.job_count,
            "coverage_resource_class": actual_resource,
            "group_seconds": measurement.group_seconds,
            "total_lane_seconds": measurement.total_seconds,
            "critical_path_seconds": measurement.critical_seconds,
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
