#!/usr/bin/env python3
"""Recalibrate hotspot performance budgets from observation JSONL.

Expected JSONL record shape:
{
  "benchmark_key": "silver_write_merge_600",
  "latency_ms": 123.4,
  "throughput_rps": 99.9
}
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
ALLOWED_BUDGETS_ROOT = (REPO_ROOT / "tests" / "performance").resolve()


def _percentile(values: list[float], q: float) -> float:
    """Return percentile with linear interpolation."""
    if not values:
        raise ValueError("cannot compute percentile of empty list")
    if len(values) == 1:
        return values[0]

    xs = sorted(values)
    pos = (len(xs) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return xs[lo]
    weight = pos - lo
    return xs[lo] * (1.0 - weight) + xs[hi] * weight


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_observations(path: Path) -> dict[str, dict[str, list[float]]]:
    grouped: dict[str, dict[str, list[float]]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        _append_observation(grouped, json.loads(line))
    return grouped


def _append_observation(
    grouped: dict[str, dict[str, list[float]]],
    record: dict[str, Any],
) -> None:
    """Append one parsed observation record to the grouped series."""
    key = str(record["benchmark_key"])
    grouped.setdefault(key, {"latency_ms": [], "throughput_rps": []})
    grouped[key]["latency_ms"].append(float(record["latency_ms"]))
    grouped[key]["throughput_rps"].append(float(record["throughput_rps"]))


def _recalibrated_benchmark(
    cfg: dict[str, Any],
    obs: dict[str, list[float]],
    *,
    latency_q: float,
    throughput_q: float,
) -> None:
    """Apply recalibrated baseline values to one benchmark config."""
    cfg["baseline_latency_ms"] = round(
        _percentile(obs["latency_ms"], latency_q),
        3,
    )
    cfg["baseline_throughput_rps"] = round(
        _percentile(obs["throughput_rps"], throughput_q),
        3,
    )


def recalibrate(
    budgets_path: Path,
    observations_path: Path,
    *,
    latency_q: float,
    throughput_q: float,
) -> tuple[dict[str, Any], list[str]]:
    budgets = _load_json(budgets_path)
    observations = _load_observations(observations_path)
    benchmark_map: dict[str, Any] = budgets.get("benchmarks", {})
    changed: list[str] = []

    for key, cfg in benchmark_map.items():
        obs = observations.get(key)
        if not obs:
            continue
        _recalibrated_benchmark(
            cfg,
            obs,
            latency_q=latency_q,
            throughput_q=throughput_q,
        )
        changed.append(key)

    return budgets, changed


def _write_updated_budgets(path: Path, payload: dict[str, Any]) -> None:
    """Write recalibrated hotspot budgets back to disk."""
    validated_path = _validate_budgets_path(path)
    validated_path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _validate_budgets_path(path: Path) -> Path:
    """Validate budget path to avoid writing outside performance budget scope."""
    resolved = path.resolve()
    if not resolved.is_relative_to(ALLOWED_BUDGETS_ROOT):
        raise ValueError(
            "Budgets path must stay under tests/performance for safe recalibration."
        )
    if resolved.suffix != ".json":
        raise ValueError("Budgets path must be a JSON file.")
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Recalibrate tests/performance/hotspot_budgets.json from JSONL observations."
    )
    parser.add_argument(
        "--budgets",
        type=Path,
        default=Path("tests/performance/hotspot_budgets.json"),
        help="Budgets JSON path.",
    )
    parser.add_argument(
        "--observations",
        type=Path,
        required=True,
        help="Observation JSONL path.",
    )
    parser.add_argument(
        "--latency-q",
        type=float,
        default=1.0,
        help="Latency percentile for baseline (default: 1.0 for CI-stable max observed).",
    )
    parser.add_argument(
        "--throughput-q",
        type=float,
        default=0.0,
        help="Throughput percentile for baseline (default: 0.0 for CI-stable min observed).",
    )
    args = parser.parse_args()
    try:
        budgets_path = _validate_budgets_path(args.budgets)
    except ValueError as error:
        print(f"Invalid budgets path: {error}")
        return 2

    updated, changed = recalibrate(
        budgets_path,
        args.observations,
        latency_q=args.latency_q,
        throughput_q=args.throughput_q,
    )

    if not changed:
        print("No matching observations found for configured benchmarks.")
        return 1

    _write_updated_budgets(budgets_path, updated)
    print(f"Updated {len(changed)} benchmark baselines:")
    for key in changed:
        print(f"- {key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
