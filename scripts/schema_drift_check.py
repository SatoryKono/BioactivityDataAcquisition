#!/usr/bin/env python3
"""CI checker for schema drift register.

Reads docs/05-operations/verification/schema-review.md and enforces:
- blocking: missing_required, broken_pk
- warning: additive_drift
"""

from __future__ import annotations

from pathlib import Path
import sys

REPORT_PATH = Path("docs/05-operations/verification/schema-review.md")
EXPECTED_HEADER = ["Pipeline", "Field", "Location", "Problem Type", "Risk"]
BLOCKING_TYPES = {"missing_required", "broken_pk"}
WARNING_TYPES = {"additive_drift"}


def _normalize(cell: str) -> str:
    return cell.strip().strip("`").lower().replace(" ", "_")


def _parse_rows(content: str) -> list[dict[str, str]]:
    lines = content.splitlines()
    header_idx = -1

    for idx, line in enumerate(lines):
        if not line.strip().startswith("|"):
            continue
        parts = [part.strip() for part in line.split("|")[1:-1]]
        if parts == EXPECTED_HEADER:
            header_idx = idx
            break

    if header_idx == -1:
        raise ValueError(
            "Missing required drift table header: "
            "Pipeline | Field | Location | Problem Type | Risk"
        )

    rows: list[dict[str, str]] = []
    for line in lines[header_idx + 2 :]:
        if not line.strip().startswith("|"):
            if rows:
                break
            continue

        parts = [part.strip() for part in line.split("|")[1:-1]]
        if len(parts) != 5:
            continue

        pipeline, field, location, problem_type, risk = parts
        if _normalize(pipeline) == "_none_":
            continue

        rows.append(
            {
                "pipeline": pipeline,
                "field": field,
                "location": location,
                "problem_type": _normalize(problem_type),
                "risk": _normalize(risk),
            }
        )

    return rows


def main() -> int:
    if not REPORT_PATH.exists():
        sys.stderr.write(f"::error::{REPORT_PATH} not found\n")
        return 2

    content = REPORT_PATH.read_text(encoding="utf-8")
    rows = _parse_rows(content)

    blocking_hits = [r for r in rows if r["problem_type"] in BLOCKING_TYPES]
    warning_hits = [r for r in rows if r["problem_type"] in WARNING_TYPES]
    unknown_hits = [
        r
        for r in rows
        if r["problem_type"] not in BLOCKING_TYPES
        and r["problem_type"] not in WARNING_TYPES
    ]

    for hit in warning_hits:
        sys.stdout.write(
            "::warning::"
            f"additive_drift: {hit['pipeline']} / {hit['field']} "
            f"at {hit['location']} (risk={hit['risk']})\n"
        )

    if unknown_hits:
        for hit in unknown_hits:
            sys.stderr.write(
                "::error::"
                f"Unknown problem type '{hit['problem_type']}' in "
                f"{hit['pipeline']} / {hit['field']}\n"
            )
        return 2

    if blocking_hits:
        for hit in blocking_hits:
            sys.stderr.write(
                "::error::"
                f"blocking drift ({hit['problem_type']}): {hit['pipeline']} / "
                f"{hit['field']} at {hit['location']} (risk={hit['risk']})\n"
            )
        return 1

    sys.stdout.write(
        f"Drift check passed: blocking=0, warnings={len(warning_hits)}, "
        f"rows={len(rows)}\n"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        sys.stderr.write(f"::error::{error}\n")
        raise SystemExit(2) from None
