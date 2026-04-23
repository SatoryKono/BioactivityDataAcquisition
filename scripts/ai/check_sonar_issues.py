#!/usr/bin/env python3
"""Check whether the repository has a trustworthy current Sonar baseline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from scripts.ai.sonar_issue_processor import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_SONAR_URL,
    DEFAULT_TOKEN_ENV_VAR,
    build_baseline_report,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit whether the current Sonar baseline is trustworthy.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to sonar-project.properties.",
    )
    parser.add_argument(
        "--sonar-url",
        default=DEFAULT_SONAR_URL,
        help="SonarQube / SonarCloud base URL.",
    )
    parser.add_argument(
        "--token-env-var",
        default=DEFAULT_TOKEN_ENV_VAR,
        help="Environment variable that stores the Sonar token.",
    )
    parser.add_argument(
        "--strict-live",
        action="store_true",
        help="Exit non-zero if a live Sonar measurement cannot be obtained.",
    )
    parser.add_argument(
        "--max-quarantine-entries",
        type=int,
        help="Fail if sonar.exclusions grows above this file-count threshold.",
    )
    parser.add_argument(
        "--require-authoritative-scope",
        action="store_true",
        help=(
            "Fail if the live Sonar project still reports findings outside "
            "sonar.sources or inside the current sonar.exclusions quarantine."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    from os import getenv

    report = build_baseline_report(
        config_path=args.config,
        sonar_url=args.sonar_url,
        token=getenv(args.token_env_var),
    )

    quarantine = report["quarantine"]
    live_issues = report["live_issues"]
    assessment = report["assessment"]

    print("Sonar baseline audit")
    print("===================")
    print(f"Config: {quarantine['config_path']}")
    print(f"Quarantined files: {quarantine['entry_count']}")
    print(
        "Historical near-zero Sonar status stale: "
        f"{'yes' if assessment['historical_near_zero_status_is_stale'] else 'no'}"
    )
    print("Top quarantine buckets:")
    for bucket in quarantine["top_buckets"]:
        print(f"  - {bucket['path_prefix']}: {bucket['count']}")

    ratchet_failed = False
    if args.max_quarantine_entries is not None:
        ratchet_failed = quarantine["entry_count"] > args.max_quarantine_entries
        print(
            "Quarantine ratchet: "
            f"{quarantine['entry_count']} / {args.max_quarantine_entries}"
        )
        if ratchet_failed:
            print("Quarantine ratchet status: exceeded")
        else:
            print("Quarantine ratchet status: within limit")

    if live_issues["status"] == "ok":
        print(f"Live unresolved issues: {live_issues['total']}")
        print(
            "Live supported-scope issues: "
            f"{live_issues.get('supported_scope_total', 0)}"
        )
        print(
            "Live supported non-quarantined issues: "
            f"{live_issues.get('supported_non_quarantined_total', 0)}"
        )
        print(
            "Live supported quarantined issues: "
            f"{live_issues.get('supported_quarantined_total', 0)}"
        )
        print(
            "Live out-of-scope issues: "
            f"{live_issues.get('out_of_scope_total', 0)}"
        )
        authoritative_scope_failed = False
        if args.require_authoritative_scope:
            authoritative_scope_failed = bool(
                assessment.get("live_scope_drift_detected")
                or assessment.get("live_quarantine_drift_detected")
            )
            print(
                "Authoritative scope status: "
                f"{'drift-detected' if authoritative_scope_failed else 'ready'}"
            )
        print("Live baseline status: ready")
        return 1 if ratchet_failed or authoritative_scope_failed else 0

    print("Live baseline status: not ready")
    print(f"Reason: {live_issues.get('reason', 'unknown')}")
    message = live_issues.get("message")
    if message:
        print(f"Message: {message}")
    if ratchet_failed:
        return 1
    return 1 if args.strict_live else 0


if __name__ == "__main__":
    raise SystemExit(main())
