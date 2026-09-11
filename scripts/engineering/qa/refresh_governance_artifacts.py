"""Governance artifact refresh recipe entrypoint (#6794 / architecture audit).

Run after write-capable changes under ``src/bioetl/**`` (and related quality
configs) to refresh inventories/baselines required by architecture gates.

Usage (repo root):

    python -m scripts.engineering.qa.refresh_governance_artifacts
    python -m scripts.engineering.qa.refresh_governance_artifacts --check

The command is fail-closed: any generator or checker failure is propagated to
the caller. It does not raise tech-debt budgets or create new registries.
Prefer shrink-only scorecard sync after measured improvements.

CI-family rebind (telemetry / test-gov / flaky / evidence / remote-main /
dataflow) MUST use ``python -m scripts.engineering.qa refresh-ci-drift-families``
instead. That path does not call ``_ratchet_family_budgets``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
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
            "scripts.engineering.qa.report_architecture_debt_remote_main_baseline",
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

    # 10) Remote-main architecture debt evidence is an input to the final rollup.
    _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa.report_architecture_debt_remote_main_baseline",
            "--update",
        ]
    )

    # 11) Debt governance gates rollup MUST run last (#7465).
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
    print(
        "  python -m scripts.engineering.qa "
        "report-architecture-debt-remote-main-baseline --check"
    )
    print("  python -m scripts.engineering.qa report-debt-governance-gates --check")
    print(
        "  pytest tests/architecture/test_quality_debt_scorecard.py "
        "tests/architecture/test_hotspot_growth_family_ratchets.py -q --tb=line"
    )


def _refresh_targeted_coverage_closeout() -> None:
    """Revalidate targeted tests before rebinding their source-bound closeout."""
    from defusedxml import ElementTree as ET

    path = ROOT / "reports/quality/low-coverage-targeted-tests-6045.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    inventory = json.loads(
        (ROOT / "reports/quality/module-coverage-inventory.json").read_text(
            encoding="utf-8"
        )
    )
    digest = inventory["source_tree_sha256"]
    if payload["module_coverage_inventory_source_tree_sha256"] == digest:
        return
    tests = sorted(
        {p for row in payload["targeted_modules"] for p in row["targeted_tests"]}
    )
    junit = ROOT / "reports/quality/low-coverage-6045-revalidation.xml"
    command = [
        sys.executable,
        "-m",
        "pytest",
        *tests,
        "-q",
        "--no-cov",
        f"--junitxml={junit}",
    ]
    _run(command)
    suites = ET.parse(junit).getroot().findall("testsuite")
    if not suites or any(int(s.get("skipped", "0")) for s in suites):
        raise SystemExit(
            "Targeted coverage closeout requires executed, non-skipped tests"
        )
    payload["module_coverage_inventory_source_tree_sha256"] = digest
    payload["validation"][0] = {
        "command": "python -m pytest " + " ".join(tests) + " -q --no-cov",
        "status": "pass",
        "tests": sum(int(s.get("tests", "0")) for s in suites),
    }
    _write_text_atomically(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def refresh(*, check_only: bool) -> None:
    """Refresh or verify governance artifacts in deterministic order."""
    if check_only:
        _run_check_only()
        return
    _run_refresh()
    _refresh_targeted_coverage_closeout()


_CI_DRIFT_FAMILY_ORDER = (
    "test-gov",
    "flaky-fingerprint",
    "telemetry",
    "evidence",
    "remote-main",
    "dataflow",
)
_PIPELINE_NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")
_CURRENT_AUDIT_ID_PREFIX = "\n  - id: "


def _assert_commit_is_ancestor(commit: str) -> None:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise SystemExit(
            f"telemetry --source-commit must be an ancestor of HEAD (got {commit!r})"
        )


def _print_issues(prefix: str, issues: list[str]) -> None:
    print(prefix)
    for issue in issues:
        print(f"- {issue}")


def _replace_current_evidence_hash(
    registry_text: str, *, current_id: str, old: str, live: str
) -> str:
    """Rewrite evidence_surface_sha256 only inside the current audit record."""
    marker = f"- id: {current_id}"
    start = registry_text.find(marker)
    if start < 0:
        raise SystemExit(f"current audit id not found in registry: {current_id}")
    next_id = registry_text.find(_CURRENT_AUDIT_ID_PREFIX, start + len(marker))
    end = next_id if next_id >= 0 else len(registry_text)
    block = registry_text[start:end]
    if block.count(old) != 1:
        raise SystemExit(
            "expected exactly one evidence_surface_sha256 in the current audit "
            f"record, found {block.count(old)}"
        )
    return registry_text[:start] + block.replace(old, live, 1) + registry_text[end:]


def _rewrite_current_audit_report(*, old: str, live: str, current: object) -> None:
    from scripts.engineering.qa.technical_debt_audit_registry import (
        SEMANTIC_SUMMARY_END,
        SEMANTIC_SUMMARY_START,
        build_current_audit_semantic_summary,
        render_current_audit_semantic_summary,
    )

    report_path = ROOT / current.report_path  # type: ignore[attr-defined]
    report = report_path.read_text(encoding="utf-8")
    report = report.replace(
        f"Evidence surface SHA-256: `{old}`",
        f"Evidence surface SHA-256: `{live}`",
    )
    start = report.find(SEMANTIC_SUMMARY_START)
    end = report.find(SEMANTIC_SUMMARY_END, start + len(SEMANTIC_SUMMARY_START))
    if start >= 0 and end >= 0:
        new_block = render_current_audit_semantic_summary(
            build_current_audit_semantic_summary(ROOT, current)
        )
        report = report[:start] + new_block + report[end + len(SEMANTIC_SUMMARY_END) :]
    if not report.endswith("\n"):
        report += "\n"
    _write_text_atomically(report_path, report)


def _rebind_evidence_surface(*, check_only: bool) -> int:
    """Rebind current-audit evidence_surface_sha256 without changing budgets."""
    from scripts.engineering.qa.technical_debt_audit_registry import (
        DEFAULT_REGISTRY_PATH,
        compute_evidence_surface_sha256,
        load_technical_debt_audit_registry,
        validate_technical_debt_audit_registry,
    )

    current_id, records = load_technical_debt_audit_registry(ROOT)
    current = next(record for record in records if record.audit_id == current_id)
    live = compute_evidence_surface_sha256(ROOT, current.evidence_paths)
    if check_only:
        issues = validate_technical_debt_audit_registry(ROOT)
        if issues:
            _print_issues("Technical-debt audit registry validation failed:", issues)
            return 1
        print(f"evidence_surface_sha256 current: {live}")
        return 0
    old = current.evidence_surface_sha256
    if old == live:
        print("evidence_surface_sha256 already aligned")
        return 0
    if not isinstance(old, str) or not old:
        raise SystemExit("current audit is missing evidence_surface_sha256")
    registry_path = ROOT / DEFAULT_REGISTRY_PATH
    updated = _replace_current_evidence_hash(
        registry_path.read_text(encoding="utf-8"),
        current_id=current_id,
        old=old,
        live=live,
    )
    _write_text_atomically(registry_path, updated)
    current_id, records = load_technical_debt_audit_registry(ROOT)
    current = next(record for record in records if record.audit_id == current_id)
    _rewrite_current_audit_report(old=old, live=live, current=current)
    issues = validate_technical_debt_audit_registry(ROOT)
    if issues:
        _print_issues("evidence rebind left validation issues:", issues)
        return 1
    print(f"evidence_surface_sha256 rebound {old[:12]} -> {live[:12]}")
    return 0


def _cmd_test_gov(*, check_only: bool, **_: object) -> list[str]:
    cmd = [
        sys.executable,
        "-m",
        "scripts.engineering.qa.report_test_governance_audit",
    ]
    if check_only:
        cmd.append("--check")
        return cmd
    cmd.extend(
        [
            "--json-out",
            _TEST_GOVERNANCE_JSON,
            "--fixture-duplication-out",
            _FIXTURE_DUPLICATION_JSON,
        ]
    )
    return cmd


def _cmd_flaky(*, check_only: bool, **_: object) -> list[str]:
    cmd = [
        sys.executable,
        "-m",
        "scripts.engineering.qa",
        "report-flaky-test-burndown-review",
    ]
    if check_only:
        cmd.append("--check")
    return cmd


def _cmd_remote_main(*, check_only: bool, **_: object) -> list[str]:
    return [
        sys.executable,
        "-m",
        "scripts.engineering.qa",
        "report-architecture-debt-remote-main-baseline",
        "--check" if check_only else "--update",
    ]


def _cmd_dataflow(*, check_only: bool, pipeline: str, **_: object) -> list[str]:
    if _PIPELINE_NAME_RE.fullmatch(pipeline) is None:
        raise SystemExit(f"invalid --pipeline name: {pipeline!r}")
    cmd = [
        sys.executable,
        "-m",
        "scripts.diagrams",
        "generate-dataflows",
        "--pipeline",
        pipeline,
    ]
    if check_only:
        cmd.append("--check")
    return cmd


def _run_telemetry(*, check_only: bool, telemetry: argparse.Namespace) -> int:
    if check_only:
        return _run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/architecture/test_test_telemetry_baseline.py",
                "tests/architecture/test_test_telemetry_governance.py",
                "-q",
                "--tb=short",
            ]
        )
    missing = [
        name
        for name, value in (
            ("--coverage-percent", telemetry.coverage_percent),
            ("--source-commit", telemetry.source_commit),
            ("--source-run-id", telemetry.source_run_id),
            ("--source-run-url", telemetry.source_run_url),
        )
        if value in (None, "")
    ]
    if missing:
        raise SystemExit(
            "telemetry --update requires "
            + ", ".join(missing)
            + " (Tests-run ancestor of HEAD; do not copy test-governance SHA)"
        )
    _assert_commit_is_ancestor(str(telemetry.source_commit))
    return _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.ci.update_test_telemetry_baseline",
            "--coverage-percent",
            str(telemetry.coverage_percent),
            "--source-branch",
            str(telemetry.source_branch),
            "--source-commit",
            str(telemetry.source_commit),
            "--source-run-id",
            str(telemetry.source_run_id),
            "--source-event",
            str(telemetry.source_event),
            "--source-run-url",
            str(telemetry.source_run_url),
        ]
    )


_FAMILY_COMMANDS = {
    "test-gov": _cmd_test_gov,
    "flaky-fingerprint": _cmd_flaky,
    "remote-main": _cmd_remote_main,
    "dataflow": _cmd_dataflow,
}


def _run_ci_drift_family(
    family: str,
    *,
    check_only: bool,
    telemetry: argparse.Namespace,
    pipeline: str,
) -> int:
    if family == "evidence":
        return _rebind_evidence_surface(check_only=check_only)
    if family == "telemetry":
        return _run_telemetry(check_only=check_only, telemetry=telemetry)
    builder = _FAMILY_COMMANDS.get(family)
    if builder is None:
        raise SystemExit(f"unknown CI drift family: {family}")
    return _run(builder(check_only=check_only, pipeline=pipeline))


def run_ci_drift_families(argv: list[str]) -> int:
    """Refresh or check CI drift families without ratcheting hotspot budgets.

    This path MUST NOT call ``_ratchet_family_budgets`` or the full
    ``refresh_governance_artifacts`` recipe.
    """
    parser = argparse.ArgumentParser(
        prog="python -m scripts.engineering.qa refresh-ci-drift-families",
        description=(
            "Coupled --check/--update for generated CI families. "
            "Does not call _ratchet_family_budgets or raise max_count/exemptions."
        ),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="Verify selected families (default when --update is omitted).",
    )
    mode.add_argument(
        "--update",
        action="store_true",
        help="Refresh selected families via canonical reporters.",
    )
    parser.add_argument("--test-gov", action="store_true")
    parser.add_argument("--flaky-fingerprint", action="store_true")
    parser.add_argument("--telemetry", action="store_true")
    parser.add_argument("--evidence", action="store_true")
    parser.add_argument("--remote-main", action="store_true")
    parser.add_argument("--dataflow", action="store_true")
    parser.add_argument(
        "--pipeline",
        default="chembl_activity",
        help="Pipeline name for --dataflow (default: chembl_activity).",
    )
    parser.add_argument("--coverage-percent", type=float, default=None)
    parser.add_argument("--source-branch", default="main")
    parser.add_argument("--source-commit", default="")
    parser.add_argument("--source-run-id", default="")
    parser.add_argument(
        "--source-event",
        choices=("push", "pull_request"),
        default="push",
    )
    parser.add_argument("--source-run-url", default="")
    args = parser.parse_args(argv)
    selected = [
        name for name in _CI_DRIFT_FAMILY_ORDER if getattr(args, name.replace("-", "_"))
    ]
    if not selected:
        parser.error(
            "pass at least one family flag: --test-gov --flaky-fingerprint "
            "--telemetry --evidence --remote-main --dataflow"
        )
    check_only = not args.update
    print(
        "CI drift families "
        + ("check" if check_only else "update")
        + ": "
        + ", ".join(selected)
    )
    for family in selected:
        code = _run_ci_drift_family(
            family,
            check_only=check_only,
            telemetry=args,
            pipeline=str(args.pipeline),
        )
        if code:
            return code
    print("CI drift families complete (no budget ratchet)")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["ci-drift-families"]:
        return run_ci_drift_families(args[1:])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify key governance artifacts (no write where possible).",
    )
    parsed = parser.parse_args(args)
    refresh(check_only=parsed.check)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
