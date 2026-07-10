#!/usr/bin/env python3
"""Unified entry point for scripts/engineering/repo/ commands.

Usage:
    python -m scripts.engineering.repo <command> [args...]
    python -m scripts.engineering.repo --help

Commands:
    check-inventory    Check scripts inventory drift
    sync-inventory     Refresh scripts inventory manifest
    sync-wrapper-caller-matrix  Refresh scripts wrapper caller matrix
    check-catalog      Validate catalog governance policy
    check-versions     Check version consistency across project files
    check-actions-runtime-policy  Validate GitHub Actions runtime-compatible refs
    check-cleanliness  Audit repository root layout allowlist
    check-cleanup-governance  Block unsafe broad cleanup instructions
    check-reports-quality-ttl  Fail on expired reports/quality TTL artifacts
    check-root-governance-docs  Validate root-governance docs against allowlist/catalog
    check-root-review-registry  Validate root-hygiene review registry
    cleanup-root-local-clutter  Preview/apply reviewed root-local clutter cleanup
    split-testing-roadmap  Create or preview #2511 child issues
    sync-docs-issues   Preview or apply docs-sync issue metadata
    publish-tdx-audit-issues  Publish or reopen TDX-AUDIT GitHub issues
    generate-branch-cleanup-inventory  Build branch cleanup inventory JSON (phase 0)
    apply-branch-cleanup  Apply branch cleanup phases 1-2 (dry-run by default)
    cleanup-branch-candidates  Preview or apply curated local branch cleanup plan
    check-all          Run read-only checks sequentially
    all                Alias for check-all
"""

from __future__ import annotations

import sys
from pathlib import Path

from scripts.engineering.common.cli_dispatch import (
    dispatch_cli,
    print_help,
    print_unknown_command,
    python_command,
    run_command,
    shell_command,
)

COMMANDS = {
    "check-inventory": "check_scripts_inventory.py",
    "sync-inventory": "sync_scripts_inventory.py",
    "sync-wrapper-caller-matrix": "generate_scripts_wrapper_caller_matrix.py",
    "check-catalog": "check_scripts_catalog.py",
    "check-versions": "check_version_consistency.py",
    "check-actions-runtime-policy": "check_github_actions_runtime_policy.py",
    "check-cleanliness": "audit_root_cleanliness.py",
    "check-cleanup-governance": "check_cleanup_governance.py",
    "check-reports-quality-ttl": "check_reports_quality_ttl.py",
    "check-root-governance-docs": "check_root_governance_docs.py",
    "check-root-review-registry": "check_root_hygiene_review_registry.py",
    "cleanup-root-local-clutter": "cleanup_root_local_clutter.py",
    "preflight-cleanup": "preflight_cleanup.sh",
    "split-testing-roadmap": "split_testing_roadmap_issue.py",
    "sync-docs-issues": "sync_docs_issues.py",
    "publish-tdx-audit-issues": "publish_tdx_audit_issues.py",
    "cleanup-branch-candidates": "cleanup_branch_candidates.sh",
}
COMMAND_SPECS = {
    name: python_command(script)
    for name, script in COMMANDS.items()
    if script.endswith(".py")
}
COMMAND_SPECS["preflight-cleanup"] = shell_command(COMMANDS["preflight-cleanup"])
COMMAND_SPECS["cleanup-branch-candidates"] = shell_command(
    COMMANDS["cleanup-branch-candidates"]
)

CHECK_COMMANDS = (
    "check-inventory",
    "check-catalog",
    "check-versions",
    "check-actions-runtime-policy",
    "check-cleanliness",
    "check-cleanup-governance",
    "check-reports-quality-ttl",
    "check-root-governance-docs",
    "check-root-review-registry",
)

_DIR = Path(__file__).parent


def _run_branch_cleanup(subcommand: str, rest: list[str]) -> int:
    from scripts.engineering.repo.branch_cleanup import main as branch_cleanup_main

    return branch_cleanup_main([subcommand, *rest])


def _run_check_all(rest: list[str]) -> int:
    for name in CHECK_COMMANDS:
        print(f"\n{'=' * 60}")
        print(f"  {name}")
        print(f"{'=' * 60}\n")
        rc = run_command(COMMAND_SPECS[name], rest, base_dir=_DIR)
        if rc != 0:
            print(f"\n[FAIL] {name} exited with code {rc}", file=sys.stderr)
            return rc
    print(f"\n{'=' * 60}")
    print("  All read-only checks passed.")
    print(f"{'=' * 60}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]

    if not args or args[0] in ("--help", "-h"):
        print_help(__doc__ or "")
        return 0

    cmd, rest = args[0], args[1:]

    if cmd in {"all", "check-all"}:
        return _run_check_all(rest)

    if cmd == "generate-branch-cleanup-inventory":
        return _run_branch_cleanup("inventory", rest)

    if cmd == "apply-branch-cleanup":
        return _run_branch_cleanup("apply", rest)

    if cmd not in COMMAND_SPECS:
        return print_unknown_command(
            cmd,
            COMMAND_SPECS,
            extra_available=("all", "check-all"),
        )

    return dispatch_cli(
        [cmd, *rest],
        help_text=__doc__ or "",
        commands=COMMAND_SPECS,
        base_dir=_DIR,
        extra_available=("all", "check-all"),
    )


if __name__ == "__main__":
    raise SystemExit(main())
