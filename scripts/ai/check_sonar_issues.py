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


def _print_quarantine_summary(
    quarantine: dict[str, object],
    assessment: dict[str, object],
) -> None:
    """Print the repo-backed quarantine summary."""
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


def _print_quarantine_ratchet_status(
    *,
    entry_count: int,
    max_entries: int | None,
) -> bool:
    """Print the current quarantine ratchet status and return failure state."""
    if max_entries is None:
        return False
    ratchet_failed = entry_count > max_entries
    print(f"Quarantine ratchet: {entry_count} / {max_entries}")
    print(
        f"Quarantine ratchet status: {'exceeded' if ratchet_failed else 'within limit'}"
    )
    return ratchet_failed


def _print_live_issue_summary(live_issues: dict[str, object]) -> None:
    """Print the live Sonar issue summary for the current project."""
    print(f"Live unresolved issues: {live_issues['total']}")
    print(f"Live supported-scope issues: {live_issues.get('supported_scope_total', 0)}")
    print(
        "Live supported non-quarantined issues: "
        f"{live_issues.get('supported_non_quarantined_total', 0)}"
    )
    print(
        "Live supported quarantined issues: "
        f"{live_issues.get('supported_quarantined_total', 0)}"
    )
    print(f"Live out-of-scope issues: {live_issues.get('out_of_scope_total', 0)}")


def _print_live_issue_buckets(
    title: str,
    buckets: list[dict[str, object]],
) -> None:
    """Print hotspot buckets for one live-issue classification."""
    if not buckets:
        return
    print(title)
    for bucket in buckets[:5]:
        print(f"  - {bucket['path_prefix']}: {bucket['count']}")


def _is_authoritative_scope_failed(
    *,
    assessment: dict[str, object],
    require_authoritative_scope: bool,
) -> bool:
    """Return whether authoritative-scope enforcement should fail."""
    if not require_authoritative_scope:
        return False
    authoritative_scope_failed = bool(
        assessment.get("live_scope_drift_detected")
        or assessment.get("live_quarantine_drift_detected")
    )
    print(
        "Authoritative scope status: "
        f"{'drift-detected' if authoritative_scope_failed else 'ready'}"
    )
    return authoritative_scope_failed


def _handle_live_issue_summary(
    *,
    live_issues: dict[str, object],
    assessment: dict[str, object],
    require_authoritative_scope: bool,
    ratchet_failed: bool,
) -> int:
    """Print live Sonar status and return the correct process exit code."""
    _print_live_issue_summary(live_issues)
    _print_live_issue_buckets(
        "Supported-scope hotspots:",
        list(live_issues.get("supported_scope_buckets", [])),
    )
    _print_live_issue_buckets(
        "Out-of-scope hotspots:",
        list(live_issues.get("out_of_scope_buckets", [])),
    )
    authoritative_scope_failed = _is_authoritative_scope_failed(
        assessment=assessment,
        require_authoritative_scope=require_authoritative_scope,
    )
    print("Live baseline status: ready")
    return 1 if ratchet_failed or authoritative_scope_failed else 0


def _handle_missing_live_issue_summary(
    *,
    live_issues: dict[str, object],
    strict_live: bool,
    ratchet_failed: bool,
) -> int:
    """Print non-ready live Sonar status and return the correct process exit code."""
    print("Live baseline status: not ready")
    print(f"Reason: {live_issues.get('reason', 'unknown')}")
    status_code = live_issues.get("status_code")
    if status_code is not None:
        print(f"Status code: {status_code}")
    message = live_issues.get("message")
    if message:
        print(f"Message: {message}")
    if ratchet_failed:
        return 1
    return 1 if strict_live else 0


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

    _print_quarantine_summary(quarantine, assessment)
    ratchet_failed = _print_quarantine_ratchet_status(
        entry_count=quarantine["entry_count"],
        max_entries=args.max_quarantine_entries,
    )

    if live_issues["status"] == "ok":
        return _handle_live_issue_summary(
            live_issues=live_issues,
            assessment=assessment,
            require_authoritative_scope=args.require_authoritative_scope,
            ratchet_failed=ratchet_failed,
        )

    return _handle_missing_live_issue_summary(
        live_issues=live_issues,
        strict_live=args.strict_live,
        ratchet_failed=ratchet_failed,
    )


if __name__ == "__main__":
    raise SystemExit(main())
