"""Governance artifact refresh recipe entrypoint (#6794 / architecture audit).

Run after write-capable changes under ``src/bioetl/**`` (and related quality
configs) to refresh inventories/baselines required by architecture gates.

Usage (repo root):

    python -m scripts.engineering.qa.refresh_governance_artifacts
    python -m scripts.engineering.qa.refresh_governance_artifacts --check

Does NOT raise tech-debt budgets. Does NOT rewrite baselines unless the
underlying source tree changed. Prefer shrink-only scorecard sync after
measured improvements.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _run(cmd: list[str], *, check: bool = True) -> int:
    print("+", " ".join(cmd))
    completed = subprocess.run(cmd, cwd=ROOT, check=False)
    if check and completed.returncode != 0:
        raise SystemExit(completed.returncode)
    return completed.returncode


def _sync_scorecard_hotspot_metrics_from_baseline() -> None:
    """Copy measured hotspot metrics from baseline into scorecard (no budget growth)."""
    import yaml

    baseline_path = ROOT / "reports/quality/hotspot-family-baseline.json"
    scorecard_path = ROOT / "configs/quality/debt_scorecard.yaml"
    if not baseline_path.exists() or not scorecard_path.exists():
        print("SKIP scorecard sync: baseline or scorecard missing")
        return

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    by_name = {
        row["name"]: row
        for row in baseline.get("families", [])
        if isinstance(row, dict) and isinstance(row.get("name"), str)
    }
    scorecard = yaml.safe_load(scorecard_path.read_text(encoding="utf-8"))
    metric_names = (
        "duplication_clusters",
        "files",
        "total_loc",
        "files_ge_250_loc",
        "helper_function_ratio",
        "max_internal_fan_in",
        "max_internal_fan_in_module",
    )
    families = (
        scorecard.get("hotspot_family_ratchets", {}).get("families", [])
        if isinstance(scorecard, dict)
        else []
    )
    changed = 0
    for family in families:
        if not isinstance(family, dict):
            continue
        name = family.get("name")
        if name not in by_name:
            continue
        base = by_name[str(name)]
        metrics = family.setdefault("metrics", {})
        if not isinstance(metrics, dict):
            continue
        for metric in metric_names:
            if metrics.get(metric) != base.get(metric):
                metrics[metric] = base.get(metric)
                changed += 1
        # Ratchet budgets down to measured bounded_growth only when lower.
        live_budgets = base.get("bounded_growth_budgets") or {}
        budgets = family.get("bounded_growth_budgets") or {}
        if isinstance(live_budgets, dict) and isinstance(budgets, dict):
            for key, live_val in live_budgets.items():
                if key in budgets and isinstance(live_val, int) and isinstance(
                    budgets.get(key), int
                ):
                    if live_val < budgets[key]:
                        budgets[key] = live_val
                        changed += 1
            family["bounded_growth_budgets"] = budgets

    if changed:
        scorecard_path.write_text(
            yaml.safe_dump(
                scorecard,
                sort_keys=False,
                allow_unicode=True,
                width=100,
            ),
            encoding="utf-8",
        )
        print(f"SYNC scorecard hotspot metrics ({changed} field updates)")
    else:
        print("SYNC scorecard hotspot metrics: already aligned")


def refresh(*, check_only: bool) -> None:
    """Refresh or verify governance artifacts in deterministic order."""
    if check_only:
        _run(
            [
                sys.executable,
                "-m",
                "scripts.engineering.qa.report_hotspot_family_baseline",
                "--check",
            ],
            check=False,
        )
        _run(
            [
                sys.executable,
                "-m",
                "scripts.engineering.qa.report_dead_code_inventory",
                "--check",
            ],
            check=False,
        )
        _run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/architecture/test_module_coverage_inventory.py::"
                "test_module_coverage_inventory_source_tree_hash_is_current",
                "tests/architecture/test_quality_debt_scorecard.py::"
                "test_debt_scorecard_hotspot_family_metrics_match_committed_baseline",
                "-q",
                "--tb=no",
            ]
        )
        print("CHECK: governance artifacts current")
        return

    # 1) Module coverage inventory (hash path; allow missing coverage.xml)
    _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa.report_module_coverage_inventory",
            "--allow-missing-coverage-xml",
        ]
    )

    # 2) Optional root helper when present
    refresh_helper = ROOT / "_refresh_module_coverage_inventory.py"
    if refresh_helper.exists():
        _run([sys.executable, str(refresh_helper)])

    # 3) Hotspot family baseline (measured)
    _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa.report_hotspot_family_baseline",
            "--update",
        ]
    )

    # 4) Align scorecard measured metrics to baseline (no budget growth)
    _sync_scorecard_hotspot_metrics_from_baseline()

    # 5) Dead-code inventory
    _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa.report_dead_code_inventory",
        ]
    )

    # 6) Debt governance gates rollup
    _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa.report_debt_governance_gates",
        ],
        check=False,
    )

    # 7) Architecture quality scorecard
    _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa.report_architecture_quality_scorecard",
        ],
        check=False,
    )

    print("REFRESH complete. Recommended verification:")
    print("  python -m scripts.engineering.qa.refresh_governance_artifacts --check")
    print(
        "  pytest tests/architecture/test_quality_debt_scorecard.py "
        "tests/architecture/test_hotspot_growth_family_ratchets.py -q --tb=line"
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify key governance artifacts (no write where possible).",
    )
    args = parser.parse_args(argv)
    refresh(check_only=args.check)


if __name__ == "__main__":
    main()
