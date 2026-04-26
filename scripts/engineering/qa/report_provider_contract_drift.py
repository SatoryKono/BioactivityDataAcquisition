#!/usr/bin/env python3
"""Generate a machine-readable provider contract drift report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.contract._provider_contract_replay import (
    PROVIDER_CONTRACT_REPLAY_PROBES,
    build_provider_contract_replay_report,
)

DEFAULT_OUTPUT = Path("reports/quality/provider-contract-drift-report.json")
_SEVERITY_RANK = {"benign": 0, "warning": 1, "breaking": 2}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a machine-readable provider contract drift report."
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output JSON path.",
    )
    parser.add_argument(
        "--fail-on",
        choices=["breaking", "warning", "never"],
        default="breaking",
        help="Exit non-zero when the maximum observed severity reaches this threshold.",
    )
    return parser.parse_args()


def build_provider_contract_drift_report() -> dict[str, Any]:
    """Build aggregated provider contract drift diagnostics."""
    reports = [
        build_provider_contract_replay_report(case)
        for case in PROVIDER_CONTRACT_REPLAY_PROBES
    ]
    provider_summary: dict[str, dict[str, Any]] = {}

    for report in reports:
        provider = cast(str, report["provider"])
        summary = provider_summary.setdefault(
            provider,
            {
                "probe_count": 0,
                "benign_count": 0,
                "warning_count": 0,
                "breaking_count": 0,
                "max_severity": "benign",
            },
        )
        summary["probe_count"] += 1
        severity = cast(str, report["severity"])
        summary[f"{severity}_count"] += 1
        if (
            _SEVERITY_RANK[severity]
            > _SEVERITY_RANK[cast(str, summary["max_severity"])]
        ):
            summary["max_severity"] = severity

    max_severity = "benign"
    for report in reports:
        severity = cast(str, report["severity"])
        if _SEVERITY_RANK[severity] > _SEVERITY_RANK[max_severity]:
            max_severity = severity

    return {
        "schema_version": 1,
        "report_kind": "provider_contract_drift",
        "source_kind": "vcr_replay",
        "totals": {
            "provider_count": len(provider_summary),
            "probe_count": len(reports),
            "benign_count": sum(
                1 for report in reports if report["severity"] == "benign"
            ),
            "warning_count": sum(
                1 for report in reports if report["severity"] == "warning"
            ),
            "breaking_count": sum(
                1 for report in reports if report["severity"] == "breaking"
            ),
            "max_severity": max_severity,
        },
        "providers": provider_summary,
        "reports": reports,
    }


def main() -> int:
    args = _parse_args()
    output_path = Path(args.output)
    payload = build_provider_contract_drift_report()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[report-provider-contract-drift] wrote {output_path}")

    if args.fail_on == "never":
        return 0

    threshold = _SEVERITY_RANK[cast(str, args.fail_on)]
    max_severity = cast(str, payload["totals"]["max_severity"])
    if _SEVERITY_RANK[max_severity] >= threshold:
        print(
            "[report-provider-contract-drift] FAIL: "
            f"max severity {max_severity!r} reached fail-on threshold {args.fail_on!r}"
        )
        return 1

    print(
        "[report-provider-contract-drift] PASS: "
        f"max severity {max_severity!r} is below fail-on threshold {args.fail_on!r}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
