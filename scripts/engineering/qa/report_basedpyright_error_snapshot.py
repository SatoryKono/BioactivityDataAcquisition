#!/usr/bin/env python3
"""Generate shrink-only basedpyright product error snapshot (#6926 / #6950).

Primary input is a basedpyright JSON report for **src/bioetl** product residual
(e.g. reports/bp_live.json). For tests/scripts advisory residual see
``report_basedpyright_tests_snapshot`` (PD2-0).

Optional live regen when basedpyright CLI is available:

    basedpyright --outputjson src/bioetl > reports/bp_live.json
    python -m scripts.engineering.qa.report_basedpyright_error_snapshot

Usage:
    python -m scripts.engineering.qa.report_basedpyright_error_snapshot
    python -m scripts.engineering.qa.report_basedpyright_error_snapshot --check
    python -m scripts.engineering.qa.report_basedpyright_error_snapshot --source reports/bp_live.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE = ROOT / "reports" / "bp_live.json"
DEFAULT_OUTPUT = ROOT / "reports" / "quality" / "basedpyright-error-snapshot.json"


def _rel_bioetl(path: str) -> str:
    normalized = path.replace("\\", "/")
    marker = "src/bioetl/"
    if marker in normalized:
        return normalized.split(marker, 1)[1]
    return normalized


def build_snapshot(source: Path) -> dict[str, Any]:
    payload = json.loads(source.read_text(encoding="utf-8"))
    summary = payload.get("summary") if isinstance(payload, dict) else {}
    diags = payload.get("generalDiagnostics") if isinstance(payload, dict) else []
    if not isinstance(diags, list):
        diags = []
    errors = [d for d in diags if isinstance(d, dict) and d.get("severity") == "error"]
    warnings = [
        d for d in diags if isinstance(d, dict) and d.get("severity") == "warning"
    ]

    by_rule = Counter(str(d.get("rule") or "unknown") for d in errors)
    by_layer: Counter[str] = Counter()
    by_file: Counter[str] = Counter()
    for d in errors:
        rel = _rel_bioetl(str(d.get("file") or ""))
        by_file[rel] += 1
        layer = rel.split("/", 1)[0] if "/" in rel else rel
        if layer:
            by_layer[layer] += 1

    return {
        "schema_version": "basedpyright-error-snapshot-v1",
        "linked_issue": "#6950",
        "parent_epic": "#6949",
        "prior_baseline_issue": "#6926",
        "snapshot_date": date.today().isoformat(),
        "generated_by": "scripts.engineering.qa.report_basedpyright_error_snapshot",
        "source_report": str(source.relative_to(ROOT)).replace("\\", "/"),
        "policy": {
            "direction": "shrink_only",
            "tech_debt_budget_growth": "forbidden",
            "merge_blocking_type_gate": "mypy src/bioetl (CI)",
            "project_diagnostics_surface": "product src/bioetl basedpyright errors (advisory unless promoted)",
            "tests_advisory_snapshot": "reports/quality/basedpyright-tests-snapshot.json",
            "warnings": "advisory; not merge-blocking in this campaign",
        },
        "regen": {
            "preferred": [
                "basedpyright --outputjson src/bioetl > reports/bp_live.json",
                "python -m scripts.engineering.qa.report_basedpyright_error_snapshot --source reports/bp_live.json",
            ],
            "check": [
                "python -m scripts.engineering.qa.report_basedpyright_error_snapshot --source reports/bp_live.json --check",
            ],
            "tests_advisory": [
                "basedpyright --outputjson > reports/bp_workspace.json",
                "python -m scripts.engineering.qa.report_basedpyright_tests_snapshot --source reports/bp_workspace.json",
            ],
            "notes": [
                "If basedpyright CLI is unavailable, keep reports/bp_live.json from IDE export and re-run the snapshot command.",
                "Do not use full-workspace error counts as the product residual baseline.",
            ],
        },
        "summary": {
            "files_analyzed": int((summary or {}).get("filesAnalyzed") or 0),
            "error_count": len(errors),
            "warning_count": len(warnings),
            "source_summary_error_count": int((summary or {}).get("errorCount") or 0),
            "source_summary_warning_count": int(
                (summary or {}).get("warningCount") or 0
            ),
        },
        "by_rule": dict(by_rule.most_common()),
        "by_layer": dict(by_layer.most_common()),
        "top_files": [
            {"path": path, "error_count": count}
            for path, count in by_file.most_common(40)
        ],
    }


def write_snapshot(*, source: Path, output: Path) -> dict[str, Any]:
    snapshot = build_snapshot(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return snapshot


def check_snapshot(*, source: Path, output: Path) -> None:
    if not output.is_file():
        raise SystemExit(f"missing snapshot: {output}")
    committed = json.loads(output.read_text(encoding="utf-8"))
    live = build_snapshot(source)
    committed_errors = int(committed.get("summary", {}).get("error_count", 0))
    live_errors = int(live.get("summary", {}).get("error_count", 0))
    if live_errors > committed_errors:
        raise SystemExit(
            "basedpyright error residual grew: "
            f"live={live_errors} committed={committed_errors}"
        )
    print(
        f"[ok] basedpyright error residual non-growth: "
        f"live={live_errors} committed={committed_errors}"
    )


def _try_live_basedpyright(target: Path) -> bool:
    exe = shutil.which("basedpyright")
    if exe is None:
        local = ROOT / ".venv-win" / "Scripts" / "basedpyright.exe"
        exe = str(local) if local.is_file() else None
    if not exe:
        return False
    try:
        completed = subprocess.run(
            [exe, "--outputjson"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    if completed.returncode not in {0, 1}:
        # pyright-style tools use 1 when diagnostics exist
        if not completed.stdout.strip():
            return False
    if not completed.stdout.strip():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(completed.stdout, encoding="utf-8")
    return True


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help="basedpyright JSON report path",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="snapshot output path",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify live error count does not exceed committed snapshot",
    )
    parser.add_argument(
        "--refresh-source",
        action="store_true",
        help="Attempt live basedpyright --outputjson before snapshotting",
    )
    args = parser.parse_args(argv)
    source = args.source if args.source.is_absolute() else ROOT / args.source
    output = args.json_out if args.json_out.is_absolute() else ROOT / args.json_out

    if args.refresh_source:
        if _try_live_basedpyright(source):
            print(f"[updated] refreshed source report: {source}")
        else:
            print(
                f"[skip] live basedpyright refresh unavailable; using existing {source}"
            )

    if not source.is_file():
        raise SystemExit(f"missing basedpyright source report: {source}")

    if args.check:
        check_snapshot(source=source, output=output)
        return

    snapshot = write_snapshot(source=source, output=output)
    print(
        "[updated] wrote basedpyright error snapshot: "
        f"{output} errors={snapshot['summary']['error_count']} "
        f"warnings={snapshot['summary']['warning_count']}"
    )


if __name__ == "__main__":
    main()
