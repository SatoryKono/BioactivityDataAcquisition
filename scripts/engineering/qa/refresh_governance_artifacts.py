"""Governance artifact refresh recipe entrypoint (#6794 / architecture audit).

Run after write-capable changes under ``src/bioetl/**`` (and related quality
configs) to refresh inventories/baselines required by architecture gates.

Usage (repo root):

    python -m scripts.engineering.qa.refresh_governance_artifacts
    python -m scripts.engineering.qa.refresh_governance_artifacts --check

The command is fail-closed: any generator or checker failure is propagated to
the caller. It does not raise tech-debt budgets or create new registries.
Prefer shrink-only scorecard sync after measured improvements.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

_TEST_GOVERNANCE_JSON = "reports/quality/test-governance-current.json"
_FIXTURE_DUPLICATION_JSON = "reports/quality/test-fixture-asset-duplication.json"


def _write_text_atomically(path: Path, payload: str) -> None:
    """Write UTF-8/LF text through a same-directory atomic replacement."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            handle.write(payload)
        os.replace(temporary_path, path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def _run(cmd: list[str], *, check: bool = True) -> int:
    print("+", " ".join(cmd))
    completed = subprocess.run(cmd, cwd=ROOT, check=False)
    if check and completed.returncode != 0:
        raise SystemExit(completed.returncode)
    return completed.returncode


_HOTSPOT_METRIC_NAMES = (
    "duplication_clusters",
    "files",
    "total_loc",
    "files_ge_250_loc",
    "helper_function_ratio",
    "max_internal_fan_in",
    "max_internal_fan_in_module",
)


def _baseline_families_by_name(
    baseline: dict[str, object],
) -> dict[str, dict[str, object]]:
    raw_families = baseline.get("families", [])
    if not isinstance(raw_families, list):
        return {}
    return {
        row["name"]: row
        for row in raw_families
        if isinstance(row, dict) and isinstance(row.get("name"), str)
    }


def _sync_family_metrics(
    metrics: dict[str, object],
    base: dict[str, object],
) -> int:
    changed = 0
    for metric in _HOTSPOT_METRIC_NAMES:
        if metrics.get(metric) != base.get(metric):
            metrics[metric] = base.get(metric)
            changed += 1
    return changed


def _ratchet_family_budgets(family: dict[str, object], base: dict[str, object]) -> int:
    """Ratchet budgets down to measured bounded_growth only when lower."""
    live_budgets = base.get("bounded_growth_budgets") or {}
    budgets = family.get("bounded_growth_budgets") or {}
    if not isinstance(live_budgets, dict) or not isinstance(budgets, dict):
        return 0
    changed = 0
    for key, live_val in live_budgets.items():
        current = budgets.get(key)
        if (
            key in budgets
            and isinstance(live_val, int)
            and isinstance(current, int)
            and live_val < current
        ):
            budgets[key] = live_val
            changed += 1
    family["bounded_growth_budgets"] = budgets
    return changed


def _sync_one_scorecard_family(
    family: dict[str, object],
    by_name: dict[str, dict[str, object]],
) -> int:
    name = family.get("name")
    if name not in by_name:
        return 0
    base = by_name[str(name)]
    metrics = family.setdefault("metrics", {})
    if not isinstance(metrics, dict):
        return 0
    return _sync_family_metrics(metrics, base) + _ratchet_family_budgets(family, base)


def _sync_scorecard_hotspot_metrics_from_baseline() -> None:
    """Copy measured hotspot metrics from baseline into scorecard (no budget growth)."""
    import yaml

    baseline_path = ROOT / "reports/quality/hotspot-family-baseline.json"
    scorecard_path = ROOT / "configs/quality/debt_scorecard.yaml"
    if not baseline_path.exists() or not scorecard_path.exists():
        missing = [
            str(path.relative_to(ROOT))
            for path in (baseline_path, scorecard_path)
            if not path.exists()
        ]
        raise FileNotFoundError(
            "scorecard sync requires existing inputs: " + ", ".join(missing)
        )

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    by_name = _baseline_families_by_name(baseline)
    scorecard = yaml.safe_load(scorecard_path.read_text(encoding="utf-8"))
    families = (
        scorecard.get("hotspot_family_ratchets", {}).get("families", [])
        if isinstance(scorecard, dict)
        else []
    )
    changed = 0
    for family in families:
        if isinstance(family, dict):
            changed += _sync_one_scorecard_family(family, by_name)

    if changed:
        _write_text_atomically(
            scorecard_path,
            yaml.safe_dump(
                scorecard,
                sort_keys=False,
                allow_unicode=True,
                width=100,
            ),
        )
        print(f"SYNC scorecard hotspot metrics ({changed} field updates)")
    else:
        print("SYNC scorecard hotspot metrics: already aligned")


def _run_check_only() -> None:
    _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa.report_source_tree_manifest",
            "--check",
        ]
    )
    _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa.report_module_coverage_inventory",
            "--check",
            "--allow-missing-coverage-xml",
        ]
    )
    _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa.generate_architecture_dependency_map",
            "--check",
        ]
    )
    _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa.report_test_governance_audit",
            "--check",
        ]
    )
    _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa.report_hotspot_family_baseline",
            "--check",
        ]
    )
    _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa.report_dead_code_inventory",
            "--check",
        ]
    )
    _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa.report_live_residual_snapshot",
            "--check",
        ]
    )
    _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa",
            "report-debt-governance-gates",
            "--check",
        ]
    )
    _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/architecture/test_module_coverage_inventory_freshness.py::"
            "test_module_coverage_inventory_source_tree_hash_is_current",
            "tests/architecture/test_quality_debt_scorecard.py::"
            "test_debt_scorecard_hotspot_family_metrics_match_committed_baseline",
            "-q",
            "--tb=no",
        ]
    )
    print("CHECK: governance artifacts current")


def _run_refresh() -> None:
    # 0) Unified source-tree manifest (S6 / #9602)
    _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa.report_source_tree_manifest",
        ]
    )

    # 1) Module coverage inventory (hash path; allow missing coverage.xml)
    _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa.report_module_coverage_inventory",
            "--allow-missing-coverage-xml",
        ]
    )

    # 2) Architecture dependency map (generated docs)
    _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa.generate_architecture_dependency_map",
            "--update",
        ]
    )

    # 3) Test-governance snapshots
    _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa.report_test_governance_audit",
            "--json-out",
            _TEST_GOVERNANCE_JSON,
            "--fixture-duplication-out",
            _FIXTURE_DUPLICATION_JSON,
        ]
    )

    # 4) Hotspot family baseline (measured)
    _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa.report_hotspot_family_baseline",
            "--update",
        ]
    )

    # 5) Align scorecard measured metrics to baseline (no budget growth)
    _sync_scorecard_hotspot_metrics_from_baseline()

    # 6) Dead-code inventory
    _run([sys.executable, "-m", "scripts.engineering.qa.report_dead_code_inventory"])

    # 7) Architecture quality scorecard (input to debt gates)
    _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa.report_architecture_quality_scorecard",
        ]
    )

    # 8) Config surface backlog (input to debt gates / residual snapshot)
    _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa.report_config_surface_backlog",
        ]
    )

    # 9) Live residual snapshot for closeout non-growth freezes (#6891 / #7464)
    _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa.report_live_residual_snapshot",
        ]
    )

    # 10) Debt governance gates rollup MUST run last (#7465).
    # Any scorecard/baseline input refresh above invalidates committed gates until
    # this step rewrites reports/quality/debt-governance-gates.{json,md}.
    _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa",
            "report-debt-governance-gates",
            "--update",
        ]
    )

    print("REFRESH complete. Recommended verification:")
    print("  python -m scripts.engineering.qa.refresh_governance_artifacts --check")
    print("  python -m scripts.engineering.qa report-debt-governance-gates --check")
    print(
        "  pytest tests/architecture/test_quality_debt_scorecard.py "
        "tests/architecture/test_hotspot_growth_family_ratchets.py -q --tb=line"
    )


def refresh(*, check_only: bool) -> None:
    """Refresh or verify governance artifacts in deterministic order."""
    if check_only:
        _run_check_only()
        return
    _run_refresh()


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
