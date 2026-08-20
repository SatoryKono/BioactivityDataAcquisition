#!/usr/bin/env python3
"""Run a reproducible, secret-free benchmark of Codex model profiles."""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import platform
import re
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any, Final

SCHEMA_VERSION: Final = "bioetl-codex-profile-benchmark-v1"
REPO_ROOT: Final = Path(__file__).resolve().parents[3]
EQUIVALENT_QUALITY_MARGIN: Final = 5


@dataclasses.dataclass(frozen=True)
class Profile:
    name: str
    model: str
    reasoning_effort: str
    use_case: str


@dataclasses.dataclass(frozen=True)
class Task:
    name: str
    category: str
    prompt: str
    expected_answer: dict[str, Any]
    expected_validation: tuple[str, ...]


PROFILES: Final = {
    "fast": Profile("fast", "gpt-5.6-luna", "low", "navigation and low-risk iteration"),
    "balanced": Profile(
        "balanced", "gpt-5.6-sol", "high", "default focused implementation and review"
    ),
    "deep": Profile(
        "deep", "gpt-5.6-sol", "max", "V4 architecture and difficult diagnosis"
    ),
}

_OUTPUT_INSTRUCTION = """
Do not inspect files and do not call tools. Use only the fixture above. Return
exactly one JSON object with this shape and no Markdown:
{"answer": <object>, "validation": [<short rubric tokens>]}
"""

TASKS: Final = (
    Task(
        name="code_navigation",
        category="code navigation",
        prompt="""BioETL fixture: an HTTP client implementation belongs in
src/bioetl/infrastructure/adapters/chembl/client.py; concrete dependency wiring
belongs in src/bioetl/composition/bootstrap/chembl.py. Interfaces may call
composition entrypoints but must not import infrastructure directly. Identify
the implementation owner, wiring owner, and forbidden dependency direction.
Use answer keys implementation_owner, wiring_owner, forbidden_direction."""
        + _OUTPUT_INSTRUCTION,
        expected_answer={
            "implementation_owner": "infrastructure",
            "wiring_owner": "composition",
            "forbidden_direction": "interfaces->infrastructure",
        },
        expected_validation=("architecture-test", "import-boundary"),
    ),
    Task(
        name="focused_fix",
        category="focused fix",
        prompt="""BioETL fixture: rows may repeat an id and the last occurrence
must win. Output must then be deterministic by ascending id. Options:
A preserve input order; B build id->row with last assignment then sort values by
id; C convert rows to a set. Choose the option and name the two behaviors it
preserves. Use answer keys option, duplicate_policy, ordering."""
        + _OUTPUT_INSTRUCTION,
        expected_answer={
            "option": "B",
            "duplicate_policy": "last-wins",
            "ordering": "ascending-id",
        },
        expected_validation=("duplicate-last-wins", "deterministic-order"),
    ),
    Task(
        name="planning",
        category="planning",
        prompt="""BioETL fixture: RF-A updates a schema. RF-B implements code and
depends on A. RF-C adds regression tests and depends on B. RF-D updates docs and
depends on B. In the answer, identify these steps only as A, B, C, and D (without
the RF- prefix). Give one valid order and identify the step that may run in
parallel with C after B. Validation must cover both the dependency DAG and the
post-change gates. Use answer keys order (array) and parallel_with_c."""
        + _OUTPUT_INSTRUCTION,
        expected_answer={"order": ["A", "B", "C", "D"], "parallel_with_c": "D"},
        expected_validation=("dependency-dag", "post-change-gates"),
    ),
    Task(
        name="test_diagnosis",
        category="test diagnosis",
        prompt="""BioETL fixture: test_two passes alone but fails after test_one.
Both tests receive the same module-scoped mutable list fixture; test_one appends
to it and no cleanup runs. Classify the root cause and choose the narrow first
validation: A increase timeout; B function-scope/reset fixture and run the two
nodes in order; C retry five times. Use answer keys root_cause and option."""
        + _OUTPUT_INSTRUCTION,
        expected_answer={"root_cause": "shared-mutable-state", "option": "B"},
        expected_validation=("ordered-reproduction", "isolated-retest"),
    ),
    Task(
        name="architecture_review",
        category="high-risk architecture review",
        prompt="""BioETL fixture import matrix: domain imports only domain;
application imports domain/application; infrastructure imports
domain/infrastructure; composition may import all except interfaces; interfaces
may import domain/application/composition/interfaces. Review:
I1 application->infrastructure, I2 interfaces->composition,
I3 infrastructure->composition, I4 domain->application. Return sorted violation
ids and severity P0. Use answer keys violations (array) and severity."""
        + _OUTPUT_INSTRUCTION,
        expected_answer={"violations": ["I1", "I3", "I4"], "severity": "P0"},
        expected_validation=("architecture-suite", "dual-verification"),
    ),
)


def _normalize(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip().casefold().replace(" ", "-")
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()}
    return value


def _tokens(value: str) -> set[str]:
    return {
        token[:-1] if len(token) > 3 and token.endswith("s") else token
        for token in re.findall(r"[a-z0-9]+", value.casefold())
    }


def _matches(actual: Any, expected: Any) -> bool:
    if isinstance(expected, list) and isinstance(actual, list):
        return {_normalize(item) for item in actual} == {
            _normalize(item) for item in expected
        }
    if isinstance(expected, str) and isinstance(actual, str):
        if len(expected) == 1:
            return actual.strip().casefold() == expected.casefold()
        return _tokens(expected) <= _tokens(actual)
    return bool(_normalize(actual) == _normalize(expected))


def _render_prompt(task: Task) -> str:
    tokens = json.dumps(list(task.expected_validation))
    return (
        task.prompt
        + "\nFor the validation array, select the applicable exact tokens from: "
        + tokens
        + "."
    )


def score_response(task: Task, payload: dict[str, Any]) -> dict[str, int]:
    answer = payload.get("answer")
    answer_dict = answer if isinstance(answer, dict) else {}
    expected_items = list(task.expected_answer.items())
    matched = sum(
        _matches(answer_dict.get(key), expected) for key, expected in expected_items
    )
    correctness = round(60 * matched / len(expected_items))
    validation = payload.get("validation")
    validation_items = (
        {_normalize(item) for item in validation if isinstance(item, str)}
        if isinstance(validation, list)
        else set()
    )
    expected_validation = {_normalize(item) for item in task.expected_validation}
    validation_score = round(
        40 * len(validation_items & expected_validation) / len(expected_validation)
    )
    return {
        "correctness": correctness,
        "validation_completeness": validation_score,
        "total": correctness + validation_score,
    }


def _agent_payload(text: str) -> dict[str, Any] | None:
    candidate = text.strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            parsed = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def _completed_agent_response(event: dict[str, Any]) -> dict[str, Any] | None:
    if event.get("type") != "item.completed":
        return None
    item = event.get("item")
    if not isinstance(item, dict) or item.get("type") != "agent_message":
        return None
    message = item.get("text")
    return _agent_payload(message) if isinstance(message, str) else None


def _completed_turn_usage(event: dict[str, Any]) -> dict[str, int] | None:
    raw_usage = event.get("usage")
    if event.get("type") != "turn.completed" or not isinstance(raw_usage, dict):
        return None
    return {
        key: int(value) for key, value in raw_usage.items() if isinstance(value, int)
    }


def parse_jsonl(stdout: str) -> tuple[dict[str, Any] | None, dict[str, int]]:
    response: dict[str, Any] | None = None
    usage: dict[str, int] = {}
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        completed_response = _completed_agent_response(event)
        if completed_response is not None:
            response = completed_response
        completed_usage = _completed_turn_usage(event)
        if completed_usage is not None:
            usage = completed_usage
    return response, usage


def _command(profile: Profile, prompt: str) -> list[str]:
    return [
        "codex",
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "-m",
        profile.model,
        "-c",
        f'model_reasoning_effort="{profile.reasoning_effort}"',
        "-s",
        "read-only",
        "--disable",
        "plugins",
        "--disable",
        "apps",
        "--json",
        prompt,
    ]


def run_task(profile: Profile, task: Task, timeout_seconds: float) -> dict[str, Any]:
    retries = 0
    started = time.monotonic()
    response: dict[str, Any] | None = None
    usage: dict[str, int] = {}
    returncode: int | None = None
    for attempt in range(2):
        try:
            result = subprocess.run(
                _command(profile, _render_prompt(task)),
                cwd=REPO_ROOT,
                check=False,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            returncode = result.returncode
            response, usage = parse_jsonl(result.stdout)
        except (OSError, subprocess.TimeoutExpired):
            returncode = None
            response = None
            usage = {}
        if returncode == 0 and response is not None:
            break
        retries = attempt + 1
    scores = score_response(task, response or {})
    input_tokens = usage.get("input_tokens", 0)
    cached_tokens = usage.get("cached_input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    return {
        "task": task.name,
        "category": task.category,
        "status": "passed" if returncode == 0 and response is not None else "failed",
        "wall_time_ms": round((time.monotonic() - started) * 1000),
        "retries": retries,
        "scores": scores,
        "tokens": {
            "input": input_tokens,
            "cached_input": cached_tokens,
            "output": output_tokens,
            "reasoning_output": usage.get("reasoning_output_tokens", 0),
            "billable_proxy": max(0, input_tokens - cached_tokens) + output_tokens,
        },
        "output_retained": False,
    }


def _mean(values: list[int]) -> float:
    return round(statistics.mean(values), 2) if values else 0.0


def _profile_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "runs": len(results),
        "mean_score": _mean([item["scores"]["total"] for item in results]),
        "mean_correctness": _mean([item["scores"]["correctness"] for item in results]),
        "mean_validation_completeness": _mean(
            [item["scores"]["validation_completeness"] for item in results]
        ),
        "median_wall_time_ms": round(
            statistics.median(item["wall_time_ms"] for item in results)
        ),
        "total_billable_token_proxy": sum(
            item["tokens"]["billable_proxy"] for item in results
        ),
        "retry_rate": round(sum(item["retries"] for item in results) / len(results), 3),
        "failed_runs": sum(item["status"] != "passed" for item in results),
    }


def _recommendation(
    summaries: dict[str, dict[str, Any]], profile_names: list[str]
) -> dict[str, Any]:
    default_candidates = [name for name in profile_names if name != "fast"]
    quality_reference = max(
        summaries[name]["mean_score"] for name in default_candidates
    )
    equivalent = [
        name
        for name in default_candidates
        if summaries[name]["mean_score"]
        >= quality_reference - EQUIVALENT_QUALITY_MARGIN
        and summaries[name]["failed_runs"] == 0
    ]
    selected = min(
        equivalent,
        key=lambda name: (
            summaries[name]["median_wall_time_ms"],
            summaries[name]["total_billable_token_proxy"],
        ),
        default="deep",
    )
    deep_score = summaries.get("deep", {}).get("mean_score", 0.0)
    selected_score = summaries[selected]["mean_score"]
    return {
        "default": selected,
        "quality_reference_score": quality_reference,
        "equivalent_quality_margin": EQUIVALENT_QUALITY_MARGIN,
        "selection_order": ["quality", "median_wall_time", "billable_token_proxy"],
        "deep_score": deep_score,
        "deep_noninferior_to_default": (
            "deep" in summaries
            and deep_score >= selected_score - EQUIVALENT_QUALITY_MARGIN
        ),
        "fast_default_eligible": False,
        "agents_max_threads": 3,
    }


def _version(command: list[str]) -> str:
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout.strip().splitlines()[0] if result.stdout.strip() else "unknown"


def collect_benchmark(
    profile_names: list[str], *, timeout_seconds: float
) -> dict[str, Any]:
    results: dict[str, list[dict[str, Any]]] = {}
    for profile_name in profile_names:
        profile = PROFILES[profile_name]
        results[profile_name] = [
            run_task(profile, task, timeout_seconds) for task in TASKS
        ]
    summaries = {
        name: _profile_summary(profile_results)
        for name, profile_results in results.items()
    }
    recommendation = _recommendation(summaries, profile_names)
    return {
        "schema_version": SCHEMA_VERSION,
        "environment": {
            "codex_cli": _version(["codex", "--version"]),
            "repository_commit": _version(["git", "rev-parse", "HEAD"]),
            "os": platform.system(),
            "architecture": platform.machine(),
            "task_count": len(TASKS),
            "timeout_seconds": timeout_seconds,
            "session_persistence": "ephemeral",
            "sandbox": "read-only",
            "user_config": "ignored",
            "plugins": "disabled",
        },
        "benchmark_definition": {
            "source": "scripts/ai/codex/profile_benchmark.py",
            "categories": [task.category for task in TASKS],
            "rubric": "60 correctness + 40 validation completeness",
            "prompt_sha256": {
                task.name: hashlib.sha256(_render_prompt(task).encode()).hexdigest()
                for task in TASKS
            },
            "secrets_in_inputs": False,
        },
        "profiles": {
            name: dataclasses.asdict(PROFILES[name]) for name in profile_names
        },
        "results": results,
        "summaries": summaries,
        "recommendation": recommendation,
        "privacy": {
            "model_outputs_retained": False,
            "stderr_retained": False,
            "credentials_retained": False,
            "user_paths_retained": False,
        },
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profiles",
        nargs="+",
        choices=sorted(PROFILES),
        default=list(PROFILES),
    )
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.timeout_seconds <= 0:
        raise SystemExit("--timeout-seconds must be positive")
    output = args.output if args.output.is_absolute() else REPO_ROOT / args.output
    output = output.resolve()
    quality_root = (REPO_ROOT / "reports/quality").resolve()
    if not output.is_relative_to(quality_root) or output.suffix != ".json":
        raise SystemExit("--output must be a .json file under reports/quality")
    report = collect_benchmark(args.profiles, timeout_seconds=args.timeout_seconds)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "summaries": report["summaries"],
                "recommendation": report["recommendation"],
            },
            indent=2,
        )
    )
    failed = any(summary["failed_runs"] for summary in report["summaries"].values())
    deep_regressed = (
        "deep" in args.profiles
        and not report["recommendation"]["deep_noninferior_to_default"]
    )
    return 1 if failed or deep_regressed else 0


if __name__ == "__main__":
    raise SystemExit(main())
