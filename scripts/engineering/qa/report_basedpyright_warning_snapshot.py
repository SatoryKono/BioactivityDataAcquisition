#!/usr/bin/env python3
"""Shrink-only basedpyright product **warning** snapshot (PD6-9 / #7052).

Warnings remain advisory (not merge-blocking). This ledger locks a floor so
warning residual cannot grow silently across campaigns.

Usage:
    basedpyright --outputjson src/bioetl > reports/bp_live.json
    python -m scripts.engineering.qa.report_basedpyright_warning_snapshot --source reports/bp_live.json
    python -m scripts.engineering.qa.report_basedpyright_warning_snapshot --source reports/bp_live.json --check
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

ROOT = REPO_ROOT
DEFAULT_SOURCE = ROOT / "reports" / "bp_live.json"
DEFAULT_OUTPUT = ROOT / "reports" / "quality" / "basedpyright-warning-snapshot.json"

ANY_UNKNOWN_RULES = frozenset(
    {
        "reportAny",
        "reportExplicitAny",
        "reportUnknownMemberType",
        "reportUnknownVariableType",
        "reportUnknownArgumentType",
        "reportUnknownParameterType",
        "reportUnknownLambdaType",
    }
)


def _rel_bioetl(path: str) -> str:
    normalized = path.replace("\\", "/")
    marker = "src/bioetl/"
    if marker in normalized:
        return normalized.split(marker, 1)[1]
    return normalized


def _is_warning(diag: dict[str, Any]) -> bool:
    sev = str(diag.get("severity") or "").lower()
    return sev in {"warning", "2"}


def _is_error(diag: dict[str, Any]) -> bool:
    sev = str(diag.get("severity") or "").lower()
    return sev in {"error", "4"}



def _aggregate_warning_stats(
    warnings: list[dict[str, Any]],
) -> tuple[Counter[str], Counter[str], Counter[str], int, int]:
    by_rule: Counter[str] = Counter()
    by_layer: Counter[str] = Counter()
    by_file: Counter[str] = Counter()
    schema_ish = 0
    any_unknown = 0
    schema_markers = (
        "infrastructure/schemas/",
        "domain/contracts/gold/",
        "domain/schemas/",
    )
    for d in warnings:
        rule = str(d.get("rule") or "unknown")
        by_rule[rule] += 1
        if rule in ANY_UNKNOWN_RULES:
            any_unknown += 1
        rel = _rel_bioetl(str(d.get("file") or ""))
        by_file[rel] += 1
        layer = rel.split("/", 1)[0] if "/" in rel else rel
        if layer:
            by_layer[layer] += 1
        if any(key in rel for key in schema_markers):
            schema_ish += 1
    return by_rule, by_layer, by_file, schema_ish, any_unknown


def build_snapshot(source: Path) -> dict[str, Any]:
    source = resolve_output_path(source, root=ROOT)
    payload = json.loads(source.read_text(encoding="utf-8"))
    summary = payload.get("summary") if isinstance(payload, dict) else {}
    diags = payload.get("generalDiagnostics") if isinstance(payload, dict) else []
    if not isinstance(diags, list):
        diags = []

    warnings = [d for d in diags if isinstance(d, dict) and _is_warning(d)]
    errors = [d for d in diags if isinstance(d, dict) and _is_error(d)]

    by_rule, by_layer, by_file, schema_ish, any_unknown = _aggregate_warning_stats(warnings)

    return {
        "schema_version": "basedpyright-warning-snapshot-v1",
        "linked_issue": "#7052",
        "parent_epic": "#7042",
        "prior_baseline_issue": "#7043",
        "snapshot_date": date.today().isoformat(),
        "generated_by": "scripts.engineering.qa.report_basedpyright_warning_snapshot",
        "source_report": str(source.relative_to(ROOT)).replace("\\", "/"),
        "policy": {
            "direction": "shrink_only",
            "tech_debt_budget_growth": "forbidden",
            "merge_blocking": False,
            "merge_blocking_type_gate": "mypy src/bioetl (CI)",
            "product_errors_must_remain": 0,
            "surface": "product src/bioetl basedpyright warnings (advisory)",
            "notes": [
                "IDE ~15k Project Diagnostics often maps to this warning surface, not product errors.",
                "Do not promote warnings to merge-blocking without ADR.",
                "Do not bulk-edit silver_chembl_*.py without generator plan.",
            ],
        },
        "regen": {
            "preferred": [
                "basedpyright --outputjson src/bioetl > reports/bp_live.json",
                "python -m scripts.engineering.qa.report_basedpyright_warning_snapshot --source reports/bp_live.json",
            ],
            "check": [
                "python -m scripts.engineering.qa.report_basedpyright_warning_snapshot --source reports/bp_live.json --check",
            ],
        },
        "summary": {
            "files_analyzed": int((summary or {}).get("filesAnalyzed") or 0),
            "warning_count": len(warnings),
            "error_count": len(errors),
            "any_unknown_family_count": any_unknown,
            "schema_ish_warning_count": schema_ish,
            "source_summary_warning_count": int(
                (summary or {}).get("warningCount") or 0
            ),
            "source_summary_error_count": int((summary or {}).get("errorCount") or 0),
        },
        "by_rule": dict(by_rule.most_common()),
        "by_layer": dict(by_layer.most_common()),
        "top_files": [
            {"path": path, "warning_count": count}
            for path, count in by_file.most_common(40)
        ],
    }


def write_snapshot(*, source: Path, output: Path) -> dict[str, Any]:
    snapshot = build_snapshot(source)
    output = resolve_output_path(output, root=ROOT)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return snapshot


def check_snapshot(*, source: Path, output: Path) -> None:
    output = resolve_output_path(output, root=ROOT)
    if not output.is_file():
        raise SystemExit(f"missing warning snapshot: {output}")
    committed = json.loads(output.read_text(encoding="utf-8"))
    live = build_snapshot(source)
    c_warn = int(committed.get("summary", {}).get("warning_count", 0))
    l_warn = int(live.get("summary", {}).get("warning_count", 0))
    c_err = int(committed.get("summary", {}).get("error_count", 0))
    l_err = int(live.get("summary", {}).get("error_count", 0))
    if l_err > 0:
        raise SystemExit(
            f"product basedpyright errors must stay 0; live error_count={l_err}"
        )
    if l_warn > c_warn:
        raise SystemExit(
            "basedpyright warning residual grew: "
            f"live={l_warn} committed={c_warn}"
        )
    if c_err > 0:
        # committed ledger should also show 0 errors
        raise SystemExit(
            f"committed warning snapshot has product errors={c_err}; rebaseline"
        )
    print(
        "[ok] basedpyright warning residual non-growth: "
        f"live={l_warn} committed={c_warn}; errors live={l_err}"
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    source = args.source if args.source.is_absolute() else ROOT / args.source
    output = args.json_out if args.json_out.is_absolute() else ROOT / args.json_out
    if args.check:
        check_snapshot(source=source, output=output)
        return
    if not source.is_file():
        raise SystemExit(f"missing basedpyright source report: {source}")
    snap = write_snapshot(source=source, output=output)
    s = snap["summary"]
    print(
        "[updated] wrote basedpyright warning snapshot: "
        f"{output} warnings={s['warning_count']} errors={s['error_count']} "
        f"any_unknown={s['any_unknown_family_count']} schema_ish={s['schema_ish_warning_count']}"
    )


if __name__ == "__main__":
    main()
