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
import json
from dataclasses import asdict, dataclass
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


def _load_budgets(path: Path) -> dict[str, HotspotBudget]:
    payload = json.loads(path.read_text(encoding="utf-8"))
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


def _load_observations(path: Path) -> dict[str, list[HotspotObservation]]:
    if not path.exists():
        return {}

    grouped: dict[str, list[HotspotObservation]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        payload = line.strip()
        if not payload:
            continue
        record = json.loads(payload)
        key = str(record.get("benchmark_key", ""))
        if not key:
            continue
        grouped.setdefault(key, []).append(
            HotspotObservation(
                latency_ms=float(record["latency_ms"]),
                p95_latency_ms=float(record.get("p95_latency_ms", 0.0)),
                throughput_rps=float(record["throughput_rps"]),
                timestamp_unix=float(record.get("timestamp_unix", 0.0)),
            )
        )
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
) -> None:
    payload = {
        "window_size": window_size,
        "summary": summary,
        "benchmarks": [asdict(item) for item in report],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", "utf-8")


def _write_markdown_report(path: Path, markdown: str) -> None:
    """Write markdown degradation report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")


def main() -> int:
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
    args = parser.parse_args()

    budgets = _load_budgets(args.budgets)
    observations = _load_observations(args.observations)
    report = _compute_degradation(
        budgets,
        observations,
        window_size=max(1, args.window_size),
    )
    summary = _build_summary(report)
    normalized_window_size = max(1, args.window_size)
    markdown = _render_markdown(report, summary, window_size=normalized_window_size)

    _write_json_report(
        args.json_out,
        report,
        summary,
        window_size=normalized_window_size,
    )
    _write_markdown_report(args.markdown_out, markdown)
    print(
        "hotspot_degradation_report_generated",
        f"benchmarks={summary['total']}",
        f"over_budget={summary['failed']}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
