"""Fail-closed classifier and result evaluator for the PR gate coordinator."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
from pathlib import Path
import subprocess
from typing import Any, cast

import yaml


REQUIRED = "required"
NOT_APPLICABLE = "not_applicable"
SUCCESS = "success"
SKIPPED = "skipped"
ZERO_SHA = "0" * 40


class CatalogError(ValueError):
    """Raised when the required-check catalog is incomplete or inconsistent."""


def _as_dict(value: object, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CatalogError(f"{label} must be a mapping")
    return cast(dict[str, Any], value)


def load_catalog(path: Path) -> dict[str, Any]:
    """Load and validate the canonical required-check catalog."""
    data = _as_dict(yaml.safe_load(path.read_text(encoding="utf-8")), label="catalog")
    if data.get("schema_version") != 1:
        raise CatalogError("schema_version must be 1")
    if not isinstance(data.get("version"), int) or data["version"] < 1:
        raise CatalogError("version must be a positive integer")
    if data.get("aggregator") != "pr-gate-complete":
        raise CatalogError("aggregator must be pr-gate-complete")

    gates = data.get("gates")
    if not isinstance(gates, list) or not gates:
        raise CatalogError("gates must be a non-empty list")

    seen: set[str] = set()
    for index, raw_gate in enumerate(gates):
        gate = _as_dict(raw_gate, label=f"gates[{index}]")
        gate_id = gate.get("id")
        if not isinstance(gate_id, str) or not gate_id:
            raise CatalogError(f"gates[{index}].id must be a non-empty string")
        if gate_id in seen:
            raise CatalogError(f"duplicate gate id: {gate_id}")
        seen.add(gate_id)
        if not isinstance(gate.get("owner_workflow"), str):
            raise CatalogError(f"{gate_id}: owner_workflow is required")
        owner_jobs = gate.get("owner_jobs")
        if not isinstance(owner_jobs, list) or not owner_jobs:
            raise CatalogError(f"{gate_id}: owner_jobs must be non-empty")
        decision = gate.get("decision")
        if decision not in {"always_required", "path_scoped"}:
            raise CatalogError(f"{gate_id}: unsupported decision {decision!r}")
        allowed = gate.get("allowed_results")
        if not isinstance(allowed, list) or not allowed:
            raise CatalogError(f"{gate_id}: allowed_results must be non-empty")
        if any(item not in {SUCCESS, NOT_APPLICABLE} for item in allowed):
            raise CatalogError(f"{gate_id}: unsupported allowed result")
        na_allowed = gate.get("not_applicable_allowed") is True
        if decision == "path_scoped":
            paths = _as_dict(gate.get("paths"), label=f"{gate_id}.paths")
            include = paths.get("include")
            if not isinstance(include, list) or not include:
                raise CatalogError(f"{gate_id}: path_scoped gate needs include paths")
            if not na_allowed or NOT_APPLICABLE not in allowed:
                raise CatalogError(f"{gate_id}: path_scoped gate must allow N/A")
            if gate.get("not_applicable_reason_required") is not True:
                raise CatalogError(f"{gate_id}: N/A reason must be required")
        elif na_allowed or NOT_APPLICABLE in allowed:
            raise CatalogError(f"{gate_id}: always_required gate cannot allow N/A")
        if gate.get("sha_binding") is not True:
            raise CatalogError(f"{gate_id}: sha_binding must be true")
    return data


def _match_path_pattern(path: str, pattern: str) -> bool:
    """Match GitHub-style path globs without allowing stars to cross slashes."""
    path_parts = tuple(path.replace("\\", "/").split("/"))
    pattern_parts = tuple(pattern.replace("\\", "/").split("/"))
    memo: dict[tuple[int, int], bool] = {}

    def visit(pattern_index: int, path_index: int) -> bool:
        key = (pattern_index, path_index)
        if key in memo:
            return memo[key]
        if pattern_index == len(pattern_parts):
            matched = path_index == len(path_parts)
        elif pattern_parts[pattern_index] == "**":
            matched = visit(pattern_index + 1, path_index) or (
                path_index < len(path_parts) and visit(pattern_index, path_index + 1)
            )
        else:
            matched = (
                path_index < len(path_parts)
                and fnmatch.fnmatchcase(
                    path_parts[path_index], pattern_parts[pattern_index]
                )
                and visit(pattern_index + 1, path_index + 1)
            )
        memo[key] = matched
        return matched

    return visit(0, 0)


def _matches(path: str, patterns: list[object]) -> bool:
    for raw_pattern in patterns:
        if not isinstance(raw_pattern, str) or not raw_pattern:
            raise CatalogError("path patterns must be non-empty strings")
        if _match_path_pattern(path, raw_pattern):
            return True
    return False


def _gate_matches(gate: dict[str, Any], path: str) -> bool:
    paths = _as_dict(gate.get("paths"), label=f"{gate.get('id')}.paths")
    include = cast(list[object], paths.get("include", []))
    exclude = cast(list[object], paths.get("exclude", []))
    return _matches(path, include) and not _matches(path, exclude)


def classify_changes(
    catalog: dict[str, Any],
    changed_files: list[str],
    *,
    head_sha: str,
) -> dict[str, Any]:
    """Return a versioned decision matrix; unclassified paths fail closed."""
    normalized = sorted(
        {path.strip().replace("\\", "/") for path in changed_files if path.strip()}
    )
    gates = [cast(dict[str, Any], gate) for gate in catalog["gates"]]
    anchor_gates = [
        gate
        for gate in gates
        if gate.get("decision") == "path_scoped"
        and gate.get("unknown_path_anchor", True) is not False
    ]
    unclassified = [
        path
        for path in normalized
        if not any(_gate_matches(gate, path) for gate in anchor_gates)
    ]

    decisions: dict[str, dict[str, str]] = {}
    for gate in gates:
        gate_id = cast(str, gate["id"])
        if gate["decision"] == "always_required":
            decisions[gate_id] = {
                "decision": REQUIRED,
                "reason": "always_required",
            }
        elif not normalized:
            decisions[gate_id] = {
                "decision": REQUIRED,
                "reason": "fail_closed_empty_diff",
            }
        elif unclassified:
            decisions[gate_id] = {
                "decision": REQUIRED,
                "reason": "fail_closed_unclassified_path",
            }
        elif any(_gate_matches(gate, path) for path in normalized):
            decisions[gate_id] = {
                "decision": REQUIRED,
                "reason": "path_match",
            }
        else:
            decisions[gate_id] = {
                "decision": NOT_APPLICABLE,
                "reason": "no_path_match",
            }

    return {
        "schema_version": 1,
        "config_version": catalog["version"],
        "head_sha": head_sha,
        "decisions": decisions,
        "changed_files": normalized[:500],
        "unclassified_files": unclassified[:500],
    }


def _parse_name_status_paths(raw: bytes) -> list[str]:
    """Return every path from a NUL-delimited git name-status diff."""
    tokens = raw.split(b"\0")
    if tokens and tokens[-1] == b"":
        tokens.pop()

    paths: list[str] = []
    index = 0
    while index < len(tokens):
        status = os.fsdecode(tokens[index])
        index += 1
        if not status or status[0] not in "ACDMRTUXB":
            raise CatalogError(f"malformed git name-status record: {status!r}")

        path_count = 2 if status[0] in {"C", "R"} else 1
        if index + path_count > len(tokens):
            raise CatalogError(f"incomplete git name-status record: {status!r}")
        paths.extend(os.fsdecode(item) for item in tokens[index : index + path_count])
        index += path_count
    return paths


def collect_changed_files(
    *,
    event_name: str,
    base_sha: str,
    before_sha: str,
    head_sha: str,
) -> list[str]:
    """Collect an exact-SHA diff and fail closed when Git cannot resolve it."""
    if event_name == "pull_request":
        if not base_sha:
            raise CatalogError("pull_request classification requires base_sha")
        diff_range = f"{base_sha}...{head_sha}"
    elif before_sha and before_sha != ZERO_SHA:
        diff_range = f"{before_sha}...{head_sha}"
    else:
        diff_range = f"{head_sha}^...{head_sha}"

    completed = subprocess.run(
        [
            "git",
            "diff",
            "--name-status",
            "-z",
            "--find-renames",
            "--find-copies",
            "--diff-filter=ACDMRTUXB",
            diff_range,
        ],
        check=True,
        capture_output=True,
        text=False,
    )
    return _parse_name_status_paths(completed.stdout)


def evaluate_results(
    catalog: dict[str, Any],
    decision_matrix: dict[str, Any],
    results: dict[str, Any],
    *,
    expected_head_sha: str,
    observed_head_sha: str,
) -> list[str]:
    """Return all fail-closed violations for one coordinator run."""
    failures: list[str] = []
    if not expected_head_sha or expected_head_sha != observed_head_sha:
        failures.append(
            "SHA mismatch: "
            f"classified={expected_head_sha!r} observed={observed_head_sha!r}"
        )
    if decision_matrix.get("head_sha") != expected_head_sha:
        failures.append("decision matrix head_sha mismatch")
    if decision_matrix.get("config_version") != catalog.get("version"):
        failures.append("decision matrix config_version mismatch")

    gates = {
        cast(str, gate["id"]): cast(dict[str, Any], gate) for gate in catalog["gates"]
    }
    decisions = decision_matrix.get("decisions")
    if not isinstance(decisions, dict):
        return [*failures, "decision matrix decisions must be a mapping"]
    if set(decisions) != set(gates):
        failures.append("decision matrix gate set does not match catalog")
    if set(results) != set(gates):
        failures.append("result gate set does not match catalog")

    for gate_id, gate in gates.items():
        raw_decision = decisions.get(gate_id)
        raw_result = results.get(gate_id)
        if not isinstance(raw_decision, dict):
            failures.append(f"{gate_id}: missing decision")
            continue
        if not isinstance(raw_result, dict):
            failures.append(f"{gate_id}: missing result")
            continue
        decision = raw_decision.get("decision")
        reason = raw_decision.get("reason")
        required_result = raw_result.get("required")
        na_result = raw_result.get("not_applicable")
        if decision == REQUIRED:
            if required_result != SUCCESS:
                failures.append(f"{gate_id}: required result={required_result!r}")
            if na_result != SKIPPED:
                failures.append(f"{gate_id}: required but N/A result={na_result!r}")
        elif decision == NOT_APPLICABLE:
            allowed = set(cast(list[str], gate.get("allowed_results", [])))
            if (
                gate.get("not_applicable_allowed") is not True
                or NOT_APPLICABLE not in allowed
            ):
                failures.append(f"{gate_id}: N/A is not allowed")
            if not isinstance(reason, str) or not reason:
                failures.append(f"{gate_id}: N/A reason is missing")
            if required_result != SKIPPED:
                failures.append(
                    f"{gate_id}: N/A but required result={required_result!r}"
                )
            if na_result != SUCCESS:
                failures.append(f"{gate_id}: N/A result={na_result!r}")
            if raw_result.get("na_head_sha") != expected_head_sha:
                failures.append(f"{gate_id}: N/A SHA mismatch")
            if raw_result.get("na_reason") != reason:
                failures.append(f"{gate_id}: N/A reason mismatch")
        else:
            failures.append(f"{gate_id}: unknown decision={decision!r}")
    return failures


def _write_outputs(matrix: dict[str, Any]) -> None:
    output_path = Path(os.environ["GITHUB_OUTPUT"])
    compact = json.dumps(matrix, sort_keys=True, separators=(",", ":"))
    with output_path.open("a", encoding="utf-8") as handle:
        handle.write(f"head_sha={matrix['head_sha']}\n")
        handle.write(f"config_version={matrix['config_version']}\n")
        handle.write(f"decision_matrix={compact}\n")
        for gate_id, decision in matrix["decisions"].items():
            handle.write(f"{gate_id}={decision['decision']}\n")
            handle.write(f"{gate_id}-reason={decision['reason']}\n")


def _write_summary(
    matrix: dict[str, Any],
    results: dict[str, Any],
    *,
    run_url: str,
) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    lines = [
        "## pr-gate-complete",
        "",
        f"Exact head SHA: `{matrix['head_sha']}`",
        "",
        "| Owner | Decision | Conclusion | Run |",
        "| --- | --- | --- | --- |",
    ]
    for gate_id, decision in matrix["decisions"].items():
        record = results.get(gate_id, {})
        conclusion = (
            record.get("required")
            if decision["decision"] == REQUIRED
            else record.get("not_applicable")
        )
        lines.append(
            f"| `{gate_id}` | {decision['decision']} "
            f"({decision['reason']}) | {conclusion} | [run]({run_url}) |"
        )
    Path(summary_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _classify_command(args: argparse.Namespace) -> int:
    catalog = load_catalog(args.catalog)
    changed = collect_changed_files(
        event_name=args.event_name,
        base_sha=args.base_sha,
        before_sha=args.before_sha,
        head_sha=args.head_sha,
    )
    matrix = classify_changes(catalog, changed, head_sha=args.head_sha)
    args.artifact.parent.mkdir(parents=True, exist_ok=True)
    args.artifact.write_text(
        json.dumps(matrix, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_outputs(matrix)
    print(json.dumps(matrix, indent=2, sort_keys=True))
    return 0


def _aggregate_command(args: argparse.Namespace) -> int:
    catalog = load_catalog(args.catalog)
    matrix = _as_dict(
        json.loads(os.environ[args.decision_matrix_env]),
        label="decision matrix",
    )
    results = _as_dict(json.loads(os.environ[args.results_env]), label="results")
    failures = evaluate_results(
        catalog,
        matrix,
        results,
        expected_head_sha=args.expected_head_sha,
        observed_head_sha=args.observed_head_sha,
    )
    _write_summary(matrix, results, run_url=args.run_url)
    if failures:
        for failure in failures:
            print(f"::error::{failure}")
        return 1
    print(f"pr-gate-complete SUCCESS for {args.expected_head_sha}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    classify = subparsers.add_parser("classify")
    classify.add_argument("--catalog", type=Path, required=True)
    classify.add_argument("--event-name", required=True)
    classify.add_argument("--base-sha", default="")
    classify.add_argument("--before-sha", default="")
    classify.add_argument("--head-sha", required=True)
    classify.add_argument("--artifact", type=Path, required=True)
    classify.set_defaults(handler=_classify_command)

    aggregate = subparsers.add_parser("aggregate")
    aggregate.add_argument("--catalog", type=Path, required=True)
    aggregate.add_argument("--decision-matrix-env", required=True)
    aggregate.add_argument("--results-env", required=True)
    aggregate.add_argument("--expected-head-sha", required=True)
    aggregate.add_argument("--observed-head-sha", required=True)
    aggregate.add_argument("--run-url", required=True)
    aggregate.set_defaults(handler=_aggregate_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return cast(int, args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
