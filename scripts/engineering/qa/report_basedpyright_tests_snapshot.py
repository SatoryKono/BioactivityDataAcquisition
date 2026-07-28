#!/usr/bin/env python3
"""Advisory basedpyright snapshot for tests/scripts (PD2-0 / #6950).

Product residual remains ``reports/quality/basedpyright-error-snapshot.json``.
This module tracks the non-merge-blocking tests/workspace residual.

Usage:
    # From a full workspace basedpyright JSON export:
    basedpyright --outputjson > reports/bp_workspace.json
    python -m scripts.engineering.qa.report_basedpyright_tests_snapshot \\
        --source reports/bp_workspace.json

    # Shrink-only advisory check (tests error_count must not grow):
    python -m scripts.engineering.qa.report_basedpyright_tests_snapshot --check
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from scripts.engineering.common.repo_paths import resolve_output_path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE = ROOT / "reports" / "bp_workspace.json"
DEFAULT_OUTPUT = ROOT / "reports" / "quality" / "basedpyright-tests-snapshot.json"


def _rel(path: str) -> str:
    normalized = path.replace("\\", "/")
    for marker in ("tests/", "scripts/", "src/bioetl/", "src/"):
        if marker in normalized:
            return marker + normalized.split(marker, 1)[1]
    return normalized


def _area(path: str) -> str:
    rel = _rel(path)
    if rel.startswith("tests/"):
        return "tests"
    if rel.startswith("scripts/"):
        return "scripts"
    if rel.startswith("src/bioetl/"):
        return "src/bioetl"
    if rel.startswith("src/"):
        return "src/other"
    return "other"


def build_tests_snapshot(source: Path) -> dict[str, Any]:
    source = resolve_output_path(source, root=ROOT)
    payload = json.loads(
        source.read_text(encoding="utf-8")  # NOSONAR - path confined by resolve_output_path
    )
    summary = payload.get("summary") if isinstance(payload, dict) else {}
    diags = payload.get("generalDiagnostics") if isinstance(payload, dict) else []
    if not isinstance(diags, list):
        diags = []

    errors = [d for d in diags if isinstance(d, dict) and d.get("severity") == "error"]
    warnings = [
        d for d in diags if isinstance(d, dict) and d.get("severity") == "warning"
    ]

    # Advisory surface: tests + scripts only (exclude product src/bioetl).
    advisory_errors = [
        d
        for d in errors
        if _area(str(d.get("file") or "")) in {"tests", "scripts"}
    ]
    entity_errors = [
        d
        for d in advisory_errors
        if "tests/unit/domain/entities/" in _rel(str(d.get("file") or ""))
    ]

    by_area = Counter(_area(str(d.get("file") or "")) for d in errors)
    by_rule = Counter(str(d.get("rule") or "unknown") for d in advisory_errors)
    by_file = Counter(_rel(str(d.get("file") or "")) for d in advisory_errors)
    entity_by_file = Counter(_rel(str(d.get("file") or "")) for d in entity_errors)

    return {
        "schema_version": "basedpyright-tests-snapshot-v1",
        "linked_issue": "#6950",
        "parent_epic": "#6949",
        "snapshot_date": date.today().isoformat(),
        "generated_by": "scripts.engineering.qa.report_basedpyright_tests_snapshot",
        "source_report": str(source.relative_to(ROOT)).replace("\\", "/"),
        "policy": {
            "direction": "shrink_only",
            "tech_debt_budget_growth": "forbidden",
            "merge_blocking": False,
            "merge_blocking_type_gate": "mypy src/bioetl (CI)",
            "surface": "tests + scripts basedpyright errors (advisory)",
            "product_snapshot": "reports/quality/basedpyright-error-snapshot.json",
            "notes": [
                "Do not confuse this advisory surface with the product type gate.",
                "Entity unit-test cluster is tracked under by_entity_files (IDE ~4543 hypothesis).",
            ],
        },
        "regen": {
            "preferred": [
                "basedpyright --outputjson > reports/bp_workspace.json",
                "python -m scripts.engineering.qa.report_basedpyright_tests_snapshot "
                "--source reports/bp_workspace.json",
            ],
            "product": [
                "basedpyright --outputjson src/bioetl > reports/bp_live.json",
                "python -m scripts.engineering.qa.report_basedpyright_error_snapshot",
            ],
            "check": [
                "python -m scripts.engineering.qa.report_basedpyright_tests_snapshot --check",
            ],
        },
        "summary": {
            "files_analyzed": int((summary or {}).get("filesAnalyzed") or 0),
            "workspace_error_count": len(errors),
            "workspace_warning_count": len(warnings),
            "advisory_error_count": len(advisory_errors),
            "entity_tests_error_count": len(entity_errors),
            "source_summary_error_count": int((summary or {}).get("errorCount") or 0),
        },
        "by_area_all_errors": dict(by_area.most_common()),
        "by_rule_advisory": dict(by_rule.most_common()),
        "top_files_advisory": [
            {"path": path, "error_count": count}
            for path, count in by_file.most_common(40)
        ],
        "by_entity_files": [
            {"path": path, "error_count": count}
            for path, count in entity_by_file.most_common(20)
        ],
    }


def write_snapshot(*, source: Path, output: Path) -> dict[str, Any]:
    snapshot = build_tests_snapshot(source)
    output = resolve_output_path(output, root=ROOT)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return snapshot


def check_snapshot(*, source: Path, output: Path) -> None:
    output = resolve_output_path(output, root=ROOT)
    if not output.is_file():
        raise SystemExit(f"missing tests snapshot: {output}")
    committed = json.loads(
        output.read_text(encoding="utf-8")  # NOSONAR - path confined by resolve_output_path
    )
    live = build_tests_snapshot(source)
    committed_errors = int(committed.get("summary", {}).get("advisory_error_count", 0))
    live_errors = int(live.get("summary", {}).get("advisory_error_count", 0))
    if live_errors > committed_errors:
        raise SystemExit(
            "basedpyright tests/scripts advisory residual grew: "
            f"live={live_errors} committed={committed_errors}"
        )
    print(
        "[ok] basedpyright tests/scripts advisory non-growth: "
        f"live={live_errors} committed={committed_errors}"
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    source = args.source if args.source.is_absolute() else ROOT / args.source
    output = args.json_out if args.json_out.is_absolute() else ROOT / args.json_out
    if not source.is_file():
        # Fall back to dated workspace export if present
        alt = ROOT / "reports" / "bp_workspace_20260728.json"
        if alt.is_file():
            source = alt
        else:
            raise SystemExit(f"missing workspace basedpyright report: {source}")
    if args.check:
        check_snapshot(source=source, output=output)
        return
    snapshot = write_snapshot(source=source, output=output)
    s = snapshot["summary"]
    print(
        "[updated] wrote basedpyright tests snapshot: "
        f"{output} advisory_errors={s['advisory_error_count']} "
        f"entity_tests={s['entity_tests_error_count']} "
        f"workspace_errors={s['workspace_error_count']}"
    )


if __name__ == "__main__":
    main()
