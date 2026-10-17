#!/usr/bin/env python3
"""Generate degradation reports for hotspot performance budgets.

Consumes:
- tests/performance/hotspot_budgets.json
- JSONL observations from tests/performance/test_hotspot_budgets.py

Produces:
- machine-readable JSON report
- markdown report suitable for CI step summary/artifacts
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from statistics import median
from typing import Any


@dataclass(frozen=True)
class HotspotBudget:
    """Single budget entry for a hotspot benchmark."""

    key: str
    baseline_latency_ms: float
    baseline_throughput_rps: float
    max_regression_pct: float
    p95_latency_ms: float
    max_p95_regression_pct: float


@dataclass(frozen=True)
class HotspotObservation:
    """Single benchmark observation captured from runtime execution."""

    latency_ms: float
    p95_latency_ms: float
    throughput_rps: float
    timestamp_unix: float


@dataclass(frozen=True)
class BenchmarkDegradation:
    """Computed degradation status for one benchmark key."""

    benchmark_key: str
    samples: int
    window_size: int
    window_latency_ms: float
    window_p95_latency_ms: float
    window_throughput_rps: float
    baseline_latency_ms: float
    baseline_throughput_rps: float
    max_regression_pct: float
    latency_regression_pct: float
    p95_regression_pct: float
    throughput_regression_pct: float
    within_budget: bool


def _load_budgets(path: Path, *, root: Path | None = None) -> dict[str, HotspotBudget]:
    from scripts.engineering.common.repo_paths import read_text_confined

    payload = json.loads(
        read_text_confined(path, root=root, allow_external_absolute=True)
    )
    raw_map: dict[str, Any] = payload.get("benchmarks", {})
    return {
        key: HotspotBudget(
            key=key,
            baseline_latency_ms=float(raw["baseline_latency_ms"]),
            baseline_throughput_rps=float(raw["baseline_throughput_rps"]),
            max_regression_pct=float(raw["max_regression_pct"]),
            p95_latency_ms=float(raw.get("p95_latency_ms", 0.0)),
            max_p95_regression_pct=float(raw.get("max_p95_regression_pct", 0.35)),
        )
        for key, raw in raw_map.items()
    }


class HotspotLoadError(Exception):
    """Observations are missing or are not a usable measurement."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _finite_float(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("unusable number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("non-finite number")
    return number


def _observation_from_record(record: Mapping[str, Any]) -> HotspotObservation:
    latency_ms = _finite_float(record.get("latency_ms"))
    if latency_ms <= 0:
        raise ValueError("non-positive latency")
    if "p95_latency_ms" in record:
        p95_latency_ms = _finite_float(record.get("p95_latency_ms"))
        if p95_latency_ms <= 0:
            raise ValueError("non-positive p95")
    else:
        p95_latency_ms = 0.0
    return HotspotObservation(
        latency_ms=latency_ms,
        p95_latency_ms=p95_latency_ms,
        throughput_rps=_finite_float(record.get("throughput_rps")),
        timestamp_unix=_finite_float(record.get("timestamp_unix", 0.0)),
    )


def _load_observations(
    path: Path, *, root: Path | None = None
) -> dict[str, list[HotspotObservation]]:
    from scripts.engineering.common.repo_paths import read_text_confined_or_none

    content = read_text_confined_or_none(path, root=root, allow_external_absolute=True)
    if content is None or not content.strip():
        raise HotspotLoadError("missing_observations")

    grouped: dict[str, list[HotspotObservation]] = {}
    for line in content.splitlines():
        payload = line.strip()
        if not payload:
            continue
        try:
            record = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise HotspotLoadError("malformed_observations") from exc
        if not isinstance(record, dict):
            raise HotspotLoadError("malformed_observations")
        key = record.get("benchmark_key")
        if not isinstance(key, str) or not key:
            raise HotspotLoadError("malformed_observations")
        try:
            observation = _observation_from_record(record)
        except (TypeError, ValueError) as exc:
            raise HotspotLoadError("malformed_observations") from exc
        grouped.setdefault(key, []).append(observation)
    if not grouped:
        raise HotspotLoadError("missing_observations")
    return grouped


def _median_window(values: list[float], size: int) -> float:
    if not values:
        return 0.0
    window = values[-size:] if size > 0 else values
    return float(median(window))


def _compute_degradation(
    budgets: dict[str, HotspotBudget],
    observations: dict[str, list[HotspotObservation]],
    *,
    window_size: int,
) -> list[BenchmarkDegradation]:
    results: list[BenchmarkDegradation] = []
    for key, budget in budgets.items():
        records = observations.get(key, [])
        if not records:
            continue
        results.append(
            _benchmark_degradation(
                key=key,
                budget=budget,
                records=records,
                window_size=window_size,
            )
        )
    return sorted(results, key=lambda item: item.benchmark_key)


def _benchmark_degradation(
    *,
    key: str,
    budget: HotspotBudget,
    records: list[HotspotObservation],
    window_size: int,
) -> BenchmarkDegradation:
    """Compute degradation status for one benchmark key."""
    latency_series = [item.latency_ms for item in records]
    p95_series = [item.p95_latency_ms for item in records]
    throughput_series = [item.throughput_rps for item in records]
    window_latency = _median_window(latency_series, window_size)
    window_p95 = _median_window(p95_series, window_size)
    window_throughput = _median_window(throughput_series, window_size)
    latency_regression = _latency_regression(window_latency, budget)
    p95_regression = _p95_regression(window_p95, budget)
    throughput_regression = _throughput_regression(window_throughput, budget)
    within_budget = _within_budget(
        budget=budget,
        latency_regression=latency_regression,
        p95_regression=p95_regression,
        throughput_regression=throughput_regression,
    )
    return BenchmarkDegradation(
        benchmark_key=key,
        samples=len(records),
        window_size=min(window_size, len(records)),
        window_latency_ms=window_latency,
        window_p95_latency_ms=window_p95,
        window_throughput_rps=window_throughput,
        baseline_latency_ms=budget.baseline_latency_ms,
        baseline_throughput_rps=budget.baseline_throughput_rps,
        max_regression_pct=budget.max_regression_pct,
        latency_regression_pct=latency_regression,
        p95_regression_pct=p95_regression,
        throughput_regression_pct=throughput_regression,
        within_budget=within_budget,
    )


def _latency_regression(window_latency: float, budget: HotspotBudget) -> float:
    """Compute regression versus baseline latency."""
    if budget.baseline_latency_ms <= 0:
        return 0.0
    return (window_latency - budget.baseline_latency_ms) / budget.baseline_latency_ms


def _p95_regression(window_p95: float, budget: HotspotBudget) -> float:
    """Compute regression versus baseline p95 latency."""
    if budget.p95_latency_ms <= 0:
        return 0.0
    return (window_p95 - budget.p95_latency_ms) / budget.p95_latency_ms


def _throughput_regression(window_throughput: float, budget: HotspotBudget) -> float:
    """Compute throughput regression versus baseline throughput."""
    if budget.baseline_throughput_rps <= 0:
        return 0.0
    return (
        budget.baseline_throughput_rps - window_throughput
    ) / budget.baseline_throughput_rps


def _within_budget(
    *,
    budget: HotspotBudget,
    latency_regression: float,
    p95_regression: float,
    throughput_regression: float,
) -> bool:
    """Return True when all regressions remain within configured budgets."""
    return (
        latency_regression <= budget.max_regression_pct
        and throughput_regression <= budget.max_regression_pct
        and (
            budget.p95_latency_ms <= 0
            or p95_regression <= budget.max_p95_regression_pct
        )
    )


def _build_summary(report: list[BenchmarkDegradation]) -> dict[str, int]:
    total = len(report)
    failed = sum(1 for item in report if not item.within_budget)
    passed = total - failed
    return {"total": total, "passed": passed, "failed": failed}


def _render_degradation_bar(value: float, *, width: int = 16) -> str:
    """Render an ASCII bar for positive regression values."""
    ratio = max(value, 0.0)
    filled = int(min(1.0, ratio) * width)
    return "#" * filled + "-" * (width - filled)


def _render_markdown(
    report: list[BenchmarkDegradation],
    summary: dict[str, int],
    *,
    window_size: int,
) -> str:
    lines = [
        "# Hotspot Degradation Report",
        "",
        f"- window_size: {window_size}",
        f"- benchmarks_total: {summary['total']}",
        f"- within_budget: {summary['passed']}",
        f"- over_budget: {summary['failed']}",
        "",
    ]
    if not report:
        lines.append("No observations found for configured hotspot benchmarks.")
        return "\n".join(lines) + "\n"

    header = (
        "| Benchmark | Samples | Lat(ms) | P95(ms) | Thr(r/s)"
        " | Lat Reg | P95 Reg | Thr Reg | Budget | Status | Trend |"
    )
    separator = (
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |"
    )
    lines.extend([header, separator])
    for item in report:
        worst = max(
            item.latency_regression_pct,
            item.p95_regression_pct,
            item.throughput_regression_pct,
        )
        status = "PASS" if item.within_budget else "FAIL"
        lines.append(
            "| "
            f"{item.benchmark_key} | "
            f"{item.samples} | "
            f"{item.window_latency_ms:.2f} | "
            f"{item.window_p95_latency_ms:.2f} | "
            f"{item.window_throughput_rps:.2f} | "
            f"{item.latency_regression_pct * 100:.1f}% | "
            f"{item.p95_regression_pct * 100:.1f}% | "
            f"{item.throughput_regression_pct * 100:.1f}% | "
            f"{item.max_regression_pct * 100:.1f}% | "
            f"{status} | "
            f"`{_render_degradation_bar(worst)}` |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def _write_json_report(
    path: Path,
    report: list[BenchmarkDegradation],
    summary: dict[str, int],
    *,
    window_size: int,
    root: Path | None = None,
) -> None:
    from scripts.engineering.common.repo_paths import write_text_confined

    payload = {
        "benchmarks": [asdict(item) for item in report],
        "reason": "over_budget" if summary["failed"] > 0 else "within_budget",
        "summary": summary,
        "verdict": "measured",
        "window_size": window_size,
    }
    write_text_confined(
        path,
        json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
        root=root,
        allow_external_absolute=True,
    )


def _write_markdown_report(
    path: Path, markdown: str, *, root: Path | None = None
) -> None:
    """Write markdown degradation report."""
    from scripts.engineering.common.repo_paths import write_text_confined

    write_text_confined(path, markdown, root=root, allow_external_absolute=True)


def _write_hotspot_failure(
    json_out: Path,
    markdown_out: Path,
    reason: str,
    *,
    root: Path,
) -> None:
    from scripts.engineering.common.repo_paths import write_text_confined

    payload = {
        "benchmarks": [],
        "reason": reason,
        "summary": None,
        "verdict": "failed",
        "window_size": None,
    }
    write_text_confined(
        json_out,
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        root=root,
        allow_external_absolute=True,
    )
    write_text_confined(
        markdown_out,
        f"# Hotspot Degradation Report\n\n- verdict: failed\n- reason: {reason}\n",
        root=root,
        allow_external_absolute=True,
    )


def hotspot_report_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--observations",
        type=Path,
        required=True,
        help="Path to hotspot observation JSONL file.",
    )
    parser.add_argument(
        "--budgets",
        type=Path,
        default=Path("tests/performance/hotspot_budgets.json"),
        help="Path to hotspot budgets JSON.",
    )
    parser.add_argument(
        "--window-size",
        type=int,
        default=5,
        help="Rolling statistical window size for median aggregation.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        required=True,
        help="Output path for machine-readable degradation report JSON.",
    )
    parser.add_argument(
        "--markdown-out",
        type=Path,
        required=True,
        help="Output path for markdown degradation report.",
    )
    args = parser.parse_args(argv)
    from scripts.engineering.common.repo_paths import REPO_ROOT

    root = REPO_ROOT
    try:
        observations = _load_observations(args.observations, root=root)
        budgets = _load_budgets(args.budgets, root=root)
    except HotspotLoadError as exc:
        _write_hotspot_failure(args.json_out, args.markdown_out, exc.reason, root=root)
        return 1
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        ValueError,
        KeyError,
        TypeError,
    ):
        _write_hotspot_failure(
            args.json_out,
            args.markdown_out,
            "malformed_observations",
            root=root,
        )
        return 1
    missing = [key for key in budgets if not observations.get(key)]
    unknown = [key for key in observations if key not in budgets]
    if not observations or missing or unknown:
        reason = (
            "missing_observations" if not observations else "incomplete_observations"
        )
        _write_hotspot_failure(args.json_out, args.markdown_out, reason, root=root)
        return 1
    report = _compute_degradation(
        budgets,
        observations,
        window_size=max(1, args.window_size),
    )
    summary = _build_summary(report)
    normalized_window_size = max(1, args.window_size)
    if type(summary.get("failed")) is not int or summary["total"] < 1:
        _write_hotspot_failure(
            args.json_out, args.markdown_out, "missing_summary", root=root
        )
        return 1
    markdown = _render_markdown(report, summary, window_size=normalized_window_size)
    _write_json_report(
        args.json_out,
        report,
        summary,
        window_size=normalized_window_size,
        root=root,
    )
    _write_markdown_report(args.markdown_out, markdown, root=root)
    print(
        "hotspot_degradation_report_generated",
        f"benchmarks={summary['total']}",
        f"over_budget={summary['failed']}",
    )
    return 0


def judge_hotspot_report(payload: object) -> tuple[str, str]:
    """Return status and reason. Missing summary.failed is not a pass."""
    if not isinstance(payload, dict):
        return "failed", "malformed_report"
    if payload.get("verdict") != "measured":
        reason = payload.get("reason")
        if isinstance(reason, str) and reason:
            return "failed", reason
        return "failed", "missing_verdict"
    summary = payload.get("summary")
    if not isinstance(summary, dict) or type(summary.get("failed")) is not int:
        return "failed", "missing_summary"
    failed = summary["failed"]
    total = summary.get("total")
    if type(total) is not int or total < 1:
        return "failed", "zero_observations"
    if failed < 0 or failed > total:
        return "failed", "invalid_summary"
    if failed > 0:
        return "failed", "over_budget"
    if not _hotspot_rows_match(payload, total=total):
        return "failed", "inconsistent_summary"
    return "passed", "within_budget"


def _hotspot_rows_match(payload: Mapping[str, object], *, total: int) -> bool:
    rows = payload.get("benchmarks")
    if not isinstance(rows, list) or len(rows) != total:
        return False
    return all(
        isinstance(row, dict) and row.get("within_budget") is True for row in rows
    )


def gate_hotspot_report_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail closed on a hotspot report.")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=None)
    args = parser.parse_args(argv)
    from scripts.engineering.common.repo_paths import REPO_ROOT, read_text_confined

    root = args.output_root or REPO_ROOT
    try:
        text = read_text_confined(args.report, root=root)
    except ValueError:
        print("rejected_output_path", file=sys.stderr)
        return 2
    except OSError:
        print("missing_report", file=sys.stderr)
        return 1
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        print("malformed_report", file=sys.stderr)
        return 1
    status, reason = judge_hotspot_report(payload)
    print(json.dumps({"reason": reason, "status": status}, sort_keys=True))
    return 0 if status == "passed" else 1


_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_RUN_ID_RE = re.compile(r"^[1-9]\d*$")
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_REGRESSION_THRESHOLD = Decimal("0.1")
_SCOPE_PREFIXES = ("tests/benchmarks/", "tests/performance/")
_Measurement = tuple[str, str, str, str, Decimal]


def _dump(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n"


def _resolve_gitdir(repo: Path) -> Path | None:
    git_entry = repo / ".git"
    if git_entry.is_dir():
        return git_entry
    if not git_entry.is_file():
        return None
    try:
        text = git_entry.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return None
    if not text.startswith("gitdir: "):
        return None
    raw = Path(text[8:].strip())
    gitdir = raw if raw.is_absolute() else (git_entry.parent / raw)
    gitdir = gitdir.resolve(strict=False)
    return gitdir if gitdir.is_dir() else None


def _sha_from_ref(gitdir: Path, ref: str) -> str | None:
    ref_path = gitdir / ref
    if ref_path.is_file():
        try:
            value = ref_path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError):
            return None
        return value if _SHA_RE.fullmatch(value) else None
    packed = gitdir / "packed-refs"
    if not packed.is_file():
        return None
    try:
        lines = packed.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return None
    for line in lines:
        if not line or line.startswith("#") or line.startswith("^"):
            continue
        sha, _, name = line.partition(" ")
        if name == ref and _SHA_RE.fullmatch(sha):
            return sha
    return None


def _common_gitdir(gitdir: Path) -> Path:
    pointer = gitdir / "commondir"
    if not pointer.is_file():
        return gitdir
    try:
        raw = Path(pointer.read_text(encoding="utf-8").strip())
    except (OSError, UnicodeError):
        return gitdir
    resolved = raw if raw.is_absolute() else gitdir / raw
    resolved = resolved.resolve(strict=False)
    return resolved if resolved.is_dir() else gitdir


def read_checkout_sha(repo: Path) -> str | None:
    """Read the checked-out commit from the gitdir, without ancestry."""
    gitdir = _resolve_gitdir(repo)
    if gitdir is None:
        return None
    try:
        head = (gitdir / "HEAD").read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return None
    if _SHA_RE.fullmatch(head):
        return head
    if not head.startswith("ref: "):
        return None
    ref = head[5:].strip()
    return _sha_from_ref(gitdir, ref) or _sha_from_ref(_common_gitdir(gitdir), ref)


def _decimal_mean(value: object) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    try:
        number = Decimal(value if isinstance(value, str) else str(value))
    except InvalidOperation:
        return None
    if not number.is_finite():
        return None
    if isinstance(value, str) and value not in {str(number), format(number, "f")}:
        return None
    return number


def _scope_of(identity: str) -> str | None:
    normalized = identity.replace("\\", "/")
    for prefix in _SCOPE_PREFIXES:
        if normalized.startswith(prefix):
            return prefix
    return None


def _github_identity(env: Mapping[str, str]) -> tuple[dict[str, str] | None, str]:
    if env.get("GITHUB_ACTIONS") != "true":
        return None, "unproven_environment"
    run_id = env.get("GITHUB_RUN_ID", "")
    attempt = env.get("GITHUB_RUN_ATTEMPT", "")
    server = env.get("GITHUB_SERVER_URL", "")
    repository = env.get("GITHUB_REPOSITORY", "")
    if (
        _RUN_ID_RE.fullmatch(run_id) is None
        or _RUN_ID_RE.fullmatch(attempt) is None
        or _REPO_RE.fullmatch(repository) is None
        or server != "https://github.com"
    ):
        return None, "unproven_run"
    return {
        "environment": "github-actions",
        "event_name": env.get("GITHUB_EVENT_NAME", ""),
        "repository": repository,
        "run_attempt": attempt,
        "run_id": run_id,
        "run_url": f"{server}/{repository}/actions/runs/{run_id}",
        "synthetic_merge": "true"
        if env.get("GITHUB_EVENT_NAME") == "pull_request"
        else "false",
    }, ""


def _entry_mean(stats: object) -> Decimal | str:
    if stats is None or stats == {}:
        return "skipped"
    if not isinstance(stats, dict):
        return "malformed_entries"
    if "mean" not in stats:
        return "incomplete_evidence"
    mean = _decimal_mean(stats.get("mean"))
    rounds = stats.get("rounds")
    if mean is None or mean <= 0:
        return "unusable_measurement"
    if type(rounds) is not int or rounds < 1:
        return "incomplete_evidence"
    return mean


def _entry_identity(entry: Mapping[str, object]) -> tuple[str, str] | None:
    identity = entry.get("fullname")
    if not isinstance(identity, str) or not identity.strip():
        identity = entry.get("name")
    if not isinstance(identity, str) or not identity.strip():
        return None
    scope = _scope_of(identity)
    if scope is None:
        return None
    return identity, scope


def _classify_benchmark_entry(entry: object) -> _Measurement | str:
    if not isinstance(entry, dict):
        return "malformed_entries"
    has_error = entry.get("has_error", False)
    if not isinstance(has_error, bool):
        return "malformed_entries"
    if has_error:
        return "execution_error"
    mean = _entry_mean(entry.get("stats", None))
    if not isinstance(mean, Decimal):
        return mean
    identity = _entry_identity(entry)
    if identity is None:
        return "incomplete_evidence"
    return (identity[0], identity[1], "", "", mean)


def _fold_entry_outcomes(
    outcomes: list[_Measurement | str],
) -> str | list[_Measurement]:
    if "malformed_entries" in outcomes:
        return "malformed_entries"
    if "execution_error" in outcomes:
        return "execution_error"
    if "unusable_measurement" in outcomes:
        return "unusable_measurement"
    measurements = [item for item in outcomes if isinstance(item, tuple)]
    skipped = outcomes.count("skipped")
    if "incomplete_evidence" in outcomes or (measurements and skipped):
        return "incomplete_evidence"
    if not measurements:
        return "all_skipped"
    return measurements


def _assess_entries(benchmarks: object) -> str | list[_Measurement]:
    if not isinstance(benchmarks, list):
        return "malformed_entries"
    if not benchmarks:
        return "zero_execution"
    return _fold_entry_outcomes(
        [_classify_benchmark_entry(entry) for entry in benchmarks]
    )


def _measurement_context(
    payload: Mapping[str, object],
    measurements: list[_Measurement],
) -> tuple[str, str, list[_Measurement]] | str:
    context = payload.get("bioetl_measurement")
    if not isinstance(context, dict):
        return "incomplete_evidence"
    dataset = context.get("dataset")
    environment = context.get("environment")
    if not isinstance(dataset, str) or not dataset.strip():
        return "incomplete_evidence"
    if environment != "github-actions":
        return "unproven_environment"
    bound = [
        (test_id, scope, dataset, "github-actions", mean)
        for test_id, scope, _dataset, _environment, mean in measurements
    ]
    return dataset, "github-actions", bound


def _baseline_measurement(row: object) -> _Measurement | None:
    if not isinstance(row, dict):
        return None
    test_id = row.get("test_id")
    scope = row.get("scope")
    dataset = row.get("dataset")
    environment = row.get("environment")
    mean = _decimal_mean(row.get("mean"))
    if (
        not isinstance(test_id, str)
        or scope not in _SCOPE_PREFIXES
        or not isinstance(dataset, str)
        or environment != "github-actions"
        or mean is None
        or mean <= 0
    ):
        return None
    return (test_id, scope, dataset, environment, mean)


def _load_baseline(payload: object) -> tuple[str, list[_Measurement]] | str:
    if not isinstance(payload, dict):
        return "invalid_baseline"
    if payload.get("adoption") != "measured":
        return "insufficient_baseline"
    if payload.get("schema_version") != 1:
        return "invalid_baseline"
    try:
        threshold = Decimal(str(payload.get("threshold")))
    except InvalidOperation:
        return "invalid_baseline"
    if threshold != _REGRESSION_THRESHOLD:
        return "invalid_baseline"
    baseline_sha = payload.get("baseline_sha")
    if not isinstance(baseline_sha, str) or _SHA_RE.fullmatch(baseline_sha) is None:
        return "invalid_baseline"
    rows = payload.get("tests")
    if not isinstance(rows, list) or not rows:
        return "insufficient_baseline"
    parsed = _parse_baseline_rows(rows)
    if isinstance(parsed, str):
        return parsed
    return baseline_sha, parsed


def _parse_baseline_rows(rows: list[object]) -> list[_Measurement] | str:
    parsed: list[_Measurement] = []
    seen: set[tuple[str, str, str, str]] = set()
    for row in rows:
        measurement = _baseline_measurement(row)
        if measurement is None or measurement[:4] in seen:
            return "invalid_baseline"
        seen.add(measurement[:4])
        parsed.append(measurement)
    return parsed


def _comparison_row(
    *,
    test_id: str,
    scope: str,
    dataset: str,
    environment: str,
    baseline_mean: str | None,
    current_mean: str | None,
    delta_ratio: str | None,
    verdict: str,
) -> dict[str, object]:
    return {
        "baseline_mean": baseline_mean,
        "current_mean": current_mean,
        "dataset": dataset,
        "delta_ratio": delta_ratio,
        "environment": environment,
        "scope": scope,
        "test_id": test_id,
        "threshold": str(_REGRESSION_THRESHOLD),
        "verdict": verdict,
    }


def _paired_comparison(
    item: _Measurement,
    base_mean: Decimal,
) -> tuple[dict[str, object], bool, bool]:
    delta = (item[4] - base_mean) / base_mean
    limit = base_mean * (Decimal(1) + _REGRESSION_THRESHOLD)
    if item[4] > limit:
        verdict = "measured_regression"
        regressed = True
        still_improved = False
    elif delta < 0:
        verdict = "improvement"
        regressed = False
        still_improved = True
    else:
        verdict = "within_threshold"
        regressed = False
        still_improved = False
    return (
        _comparison_row(
            test_id=item[0],
            scope=item[1],
            dataset=item[2],
            environment=item[3],
            baseline_mean=str(base_mean),
            current_mean=str(item[4]),
            delta_ratio=format(delta, "f"),
            verdict=verdict,
        ),
        regressed,
        still_improved,
    )


def _comparison_reason(
    *,
    missing: bool,
    regression: bool,
    improved: bool,
    rows: list[dict[str, object]],
) -> str:
    if missing:
        return "missing_baseline_test"
    if regression:
        return "measured_regression"
    if improved and any(row["verdict"] == "improvement" for row in rows):
        return "improvement"
    return "within_threshold"


def _compare_measurements(
    current: list[_Measurement],
    baseline: list[_Measurement],
) -> tuple[str, list[dict[str, object]]]:
    current_keys = {(item[0], item[1], item[2], item[3]) for item in current}
    baseline_by_key = {
        (item[0], item[1], item[2], item[3]): item[4] for item in baseline
    }
    contexts = {(item[1], item[2], item[3]) for item in current}
    baseline_contexts = {(row[1], row[2], row[3]) for row in baseline}
    if not contexts or not contexts.issubset(baseline_contexts):
        return "insufficient_baseline", []
    if not baseline_contexts.issubset(contexts):
        return "missing_baseline_scope", []
    rows: list[dict[str, object]] = []
    missing = False
    regression = False
    improved = True
    for key, base_mean in sorted(baseline_by_key.items()):
        if key not in current_keys:
            missing = True
            rows.append(
                _comparison_row(
                    test_id=key[0],
                    scope=key[1],
                    dataset=key[2],
                    environment=key[3],
                    baseline_mean=str(base_mean),
                    current_mean=None,
                    delta_ratio=None,
                    verdict="missing_baseline_test",
                )
            )
    for item in sorted(current, key=lambda row: row[0]):
        key = (item[0], item[1], item[2], item[3])
        base_mean = baseline_by_key.get(key)
        if base_mean is None:
            improved = False
            rows.append(
                _comparison_row(
                    test_id=item[0],
                    scope=item[1],
                    dataset=item[2],
                    environment=item[3],
                    baseline_mean=None,
                    current_mean=str(item[4]),
                    delta_ratio=None,
                    verdict="new_test",
                )
            )
            continue
        row, regressed, still_improved = _paired_comparison(item, base_mean)
        regression = regression or regressed
        improved = improved and still_improved
        rows.append(row)
    rows.sort(key=lambda row: str(row["test_id"]))
    return (
        _comparison_reason(
            missing=missing,
            regression=regression,
            improved=improved,
            rows=rows,
        ),
        rows,
    )


def _commit_is_clean(commit_info: object, revision: str) -> bool:
    if not isinstance(commit_info, dict) or commit_info.get("id") != revision:
        return False
    dirty = commit_info.get("dirty", "missing")
    return dirty in {None, False}


def _provenance(
    payload: Mapping[str, object],
    *,
    checkout_sha: str,
    repo: Path,
    env: Mapping[str, str],
) -> tuple[str, dict[str, str]] | str:
    source = payload.get("bioetl_source")
    if not isinstance(source, dict):
        return "malformed_entries"
    revision = source.get("revision")
    if not isinstance(revision, str) or _SHA_RE.fullmatch(revision) is None:
        return "wrong_sha"
    if source.get("revision_method") not in {None, "gitdir_head_file"}:
        return "unproven_checkout"
    if source.get("revision_method") != "gitdir_head_file":
        return "unproven_checkout"
    head = read_checkout_sha(repo)
    if head is None:
        return "unproven_checkout"
    github_sha = env.get("GITHUB_SHA", "")
    if github_sha and github_sha != head:
        return "checkout_sha_mismatch"
    if checkout_sha and checkout_sha != head:
        return "checkout_sha_mismatch"
    if revision != head:
        return "wrong_sha"
    if not _commit_is_clean(payload.get("commit_info"), revision):
        return "incomplete_evidence"
    identity, identity_reason = _github_identity(env)
    if identity is None:
        return identity_reason
    return revision, identity


def _emit_reducer(
    args: argparse.Namespace,
    root: Path,
    status: str,
    reason: str,
    extra: dict[str, object] | None = None,
) -> int:
    from scripts.engineering.common.repo_paths import write_text_confined

    body: dict[str, object] = {"reason": reason, "status": status}
    if extra:
        body.update(extra)
    text = _dump(body)
    for path in (args.gate_out, args.manifest_out):
        write_text_confined(path, text, root=root)
    _copy_revision_evidence(args, root, body, text)
    return 0 if status == "passed" else 1


def _copy_revision_evidence(
    args: argparse.Namespace,
    root: Path,
    body: Mapping[str, object],
    text: str,
) -> None:
    from scripts.engineering.common.repo_paths import write_text_confined

    measured = body.get("measured_sha")
    raw_sha = body.get("raw_sha256")
    if (
        not isinstance(measured, str)
        or _SHA_RE.fullmatch(measured) is None
        or not isinstance(raw_sha, str)
        or len(raw_sha) != 64
    ):
        return
    folder = args.evidence_dir / measured / raw_sha
    for name in ("benchmark-gate.json", "benchmark-manifest.json"):
        write_text_confined(folder / name, text, root=root)


def _resolved_under_root(path: Path, root: Path) -> Path:
    confined = path if path.is_absolute() else root / path
    resolved = confined.resolve(strict=False)
    resolved.relative_to(root.resolve(strict=False))
    return resolved


def _confine_reducer_outputs(args: argparse.Namespace, root: Path) -> bool:
    from scripts.engineering.common.repo_paths import write_text_confined

    try:
        resolved = [
            _resolved_under_root(path, root)
            for path in (
                args.raw_json,
                args.manifest_out,
                args.gate_out,
                args.baseline,
                args.evidence_dir,
            )
        ]
        if len(set(resolved)) != len(resolved):
            raise ValueError("reducer outputs must be distinct files")
        write_text_confined(
            args.gate_out,
            _dump({"reason": "in_progress", "status": "failed"}),
            root=root,
        )
    except (ValueError, OSError):
        return False
    return True


def _read_reducer_bytes(path: Path, root: Path) -> bytes | str:
    from scripts.engineering.common.repo_paths import read_bytes_confined

    try:
        return read_bytes_confined(path, root=root)
    except FileNotFoundError:
        return "missing_observations"
    except ValueError:
        return "rejected_output_path"
    except OSError:
        return "missing_observations"


def _decode_measurement_payload(raw_bytes: bytes) -> dict[str, Any] | str:
    if not raw_bytes:
        return "empty_input"
    try:
        raw_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return "invalid_encoding"
    try:
        payload = json.loads(raw_text, parse_constant=_reject_non_finite)
    except (json.JSONDecodeError, ValueError):
        return "malformed_json"
    if not isinstance(payload, dict):
        return "malformed_json"
    return payload


def _read_baseline_document(path: Path, root: Path) -> object | str:
    from scripts.engineering.common.repo_paths import read_text_confined

    try:
        return json.loads(read_text_confined(path, root=root))
    except FileNotFoundError:
        return "insufficient_baseline"
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return "invalid_baseline"


def _store_raw_evidence(
    args: argparse.Namespace,
    root: Path,
    measured_sha: str,
    raw_sha: str,
    raw_bytes: bytes,
) -> str | None:
    from scripts.engineering.common.repo_paths import write_bytes_confined

    try:
        write_bytes_confined(
            args.evidence_dir / f"{measured_sha}/{raw_sha}/benchmark-measurements.json",
            raw_bytes,
            root=root,
        )
    except (OSError, ValueError):
        return "rejected_output_path"
    return None


def _candidate_summary(
    measurements: list[_Measurement],
    identity: Mapping[str, str],
    *,
    measured_sha: str,
    raw_sha: str,
    scopes: list[str],
) -> dict[str, object]:
    return {
        "adoption": "proposed",
        "baseline_sha": measured_sha,
        "dataset": measurements[0][2],
        "environment": identity["environment"],
        "raw_sha256": raw_sha,
        "run_attempt": identity["run_attempt"],
        "run_id": identity["run_id"],
        "run_url": identity["run_url"],
        "schema_version": 1,
        "scopes": scopes,
        "tests": [
            {
                "dataset": item[2],
                "environment": item[3],
                "mean": str(item[4]),
                "scope": item[1],
                "test_id": item[0],
            }
            for item in measurements
        ],
        "threshold": str(_REGRESSION_THRESHOLD),
    }


def _propose_initial_candidate(
    args: argparse.Namespace,
    root: Path,
    measurements: list[_Measurement],
    identity: Mapping[str, str],
    *,
    measured_sha: str,
    raw_bytes: bytes,
    raw_sha: str,
) -> int:
    from scripts.engineering.common.repo_paths import write_text_confined

    stored = _store_raw_evidence(args, root, measured_sha, raw_sha, raw_bytes)
    if stored is not None:
        return _emit_reducer(args, root, "failed", stored, {"raw_sha256": raw_sha})
    scopes = sorted({item[1] for item in measurements})
    write_text_confined(
        args.evidence_dir / measured_sha / raw_sha / "benchmark-summary-candidate.json",
        _dump(
            _candidate_summary(
                measurements,
                identity,
                measured_sha=measured_sha,
                raw_sha=raw_sha,
                scopes=scopes,
            )
        ),
        root=root,
    )
    return _emit_reducer(
        args,
        root,
        "failed",
        "insufficient_baseline",
        {"measured_sha": measured_sha, "raw_sha256": raw_sha},
    )


def _finish_reduction(
    args: argparse.Namespace,
    root: Path,
    measurements: list[_Measurement],
    identity: Mapping[str, str],
    *,
    measured_sha: str,
    raw_bytes: bytes,
    raw_sha: str,
) -> int:
    from scripts.engineering.common.repo_paths import write_text_confined

    baseline_document = _read_baseline_document(args.baseline, root)
    if baseline_document == "insufficient_baseline":
        return _propose_initial_candidate(
            args,
            root,
            measurements,
            identity,
            measured_sha=measured_sha,
            raw_bytes=raw_bytes,
            raw_sha=raw_sha,
        )
    if isinstance(baseline_document, str):
        return _emit_reducer(
            args, root, "failed", baseline_document, {"raw_sha256": raw_sha}
        )
    loaded = _load_baseline(baseline_document)
    if loaded == "insufficient_baseline":
        return _propose_initial_candidate(
            args,
            root,
            measurements,
            identity,
            measured_sha=measured_sha,
            raw_bytes=raw_bytes,
            raw_sha=raw_sha,
        )
    if isinstance(loaded, str):
        return _emit_reducer(
            args,
            root,
            "failed",
            loaded,
            {"measured_sha": measured_sha, "raw_sha256": raw_sha},
        )
    baseline_sha, baseline_rows = loaded
    reason, comparisons = _compare_measurements(measurements, baseline_rows)
    status = "passed" if reason in {"within_threshold", "improvement"} else "failed"
    scopes = sorted({item[1] for item in measurements})
    stored = _store_raw_evidence(args, root, measured_sha, raw_sha, raw_bytes)
    if stored is not None:
        return _emit_reducer(args, root, "failed", stored, {"raw_sha256": raw_sha})
    if status == "passed":
        write_text_confined(
            args.evidence_dir
            / measured_sha
            / raw_sha
            / "benchmark-summary-candidate.json",
            _dump(
                _candidate_summary(
                    measurements,
                    identity,
                    measured_sha=measured_sha,
                    raw_sha=raw_sha,
                    scopes=scopes,
                )
            ),
            root=root,
        )
    return _emit_reducer(
        args,
        root,
        status,
        reason,
        {
            "baseline_sha": baseline_sha,
            "comparisons": comparisons,
            "dataset": measurements[0][2],
            "environment": identity["environment"],
            "event_name": identity["event_name"],
            "measured_sha": measured_sha,
            "raw_sha256": raw_sha,
            "run_attempt": identity["run_attempt"],
            "run_id": identity["run_id"],
            "run_url": identity["run_url"],
            "scopes": scopes,
            "synthetic_merge": identity["synthetic_merge"] == "true",
            "threshold": str(_REGRESSION_THRESHOLD),
        },
    )


def reduce_benchmark_evidence_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reduce benchmark measurements into a fail-closed gate."
    )
    parser.add_argument("--raw-json", type=Path, required=True)
    parser.add_argument("--manifest-out", type=Path, required=True)
    parser.add_argument("--gate-out", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--checkout-sha", default="")
    parser.add_argument("--repo", type=Path, default=None)
    args = parser.parse_args(argv)
    from scripts.engineering.common.repo_paths import REPO_ROOT

    root = args.output_root or REPO_ROOT
    repo = args.repo or REPO_ROOT
    if not _confine_reducer_outputs(args, root):
        print("rejected_output_path", file=sys.stderr)
        return 2
    raw_bytes = _read_reducer_bytes(args.raw_json, root)
    if raw_bytes == "rejected_output_path":
        print("rejected_output_path", file=sys.stderr)
        return 2
    if isinstance(raw_bytes, str):
        return _emit_reducer(args, root, "failed", raw_bytes)
    decoded = _decode_measurement_payload(raw_bytes)
    if isinstance(decoded, str):
        return _emit_reducer(args, root, "failed", decoded)
    raw_sha = hashlib.sha256(raw_bytes).hexdigest()
    assessed = _assess_entries(decoded.get("benchmarks"))
    if isinstance(assessed, str):
        return _emit_reducer(args, root, "failed", assessed, {"raw_sha256": raw_sha})
    context = _measurement_context(decoded, assessed)
    if isinstance(context, str):
        return _emit_reducer(args, root, "failed", context, {"raw_sha256": raw_sha})
    _dataset, _environment, measurements = context
    provenance = _provenance(
        decoded,
        checkout_sha=args.checkout_sha,
        repo=repo,
        env=os.environ,
    )
    if isinstance(provenance, str):
        return _emit_reducer(args, root, "failed", provenance, {"raw_sha256": raw_sha})
    measured_sha, identity = provenance
    return _finish_reduction(
        args,
        root,
        measurements,
        identity,
        measured_sha=measured_sha,
        raw_bytes=raw_bytes,
        raw_sha=raw_sha,
    )


def _reject_non_finite(value: str) -> None:
    raise ValueError(value)


def main(argv: list[str] | None = None) -> int:
    args = list(argv) if argv is not None else sys.argv[1:]
    if args and args[0] == "reduce-benchmark-evidence":
        return reduce_benchmark_evidence_main(args[1:])
    if args and args[0] == "gate-hotspot-report":
        return gate_hotspot_report_main(args[1:])
    return hotspot_report_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
