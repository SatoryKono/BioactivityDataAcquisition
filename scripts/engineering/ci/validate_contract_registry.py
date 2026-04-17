"""CI script to validate contract registry consistency."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from bioetl.domain.control_plane.contract_registry import (
    ContractRegistry,
    RegistryValidationIssue,
    RegistryValidationSeverity,
)


def _issue_payload(issue: RegistryValidationIssue) -> dict[str, Any]:
    """Convert a registry issue into JSON payload."""
    return {
        "message": issue.message,
        "severity": issue.severity.value,
        "contract_ref": issue.contract_ref,
        "field": issue.field,
    }


def _write_diagnostics(
    diagnostics_path: Path,
    *,
    valid: bool,
    validation_issues: list[RegistryValidationIssue],
    filesystem_issues: list[RegistryValidationIssue],
    entries_count: int,
) -> None:
    """Write registry diagnostics for CI artifact collection."""
    combined = [*validation_issues, *filesystem_issues]
    blocking_count = sum(
        1 for issue in combined if issue.severity == RegistryValidationSeverity.BLOCKING
    )
    warning_count = sum(
        1 for issue in combined if issue.severity == RegistryValidationSeverity.WARNING
    )
    payload = {
        "valid": valid,
        "entries_count": entries_count,
        "validation_issue_count": len(validation_issues),
        "filesystem_issue_count": len(filesystem_issues),
        "blocking_issue_count": blocking_count,
        "warning_issue_count": warning_count,
        "validation_issues": [_issue_payload(issue) for issue in validation_issues],
        "filesystem_issues": [_issue_payload(issue) for issue in filesystem_issues],
    }
    diagnostics_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    """Main validation entry point."""
    repo_root = Path(__file__).resolve().parents[2]
    registry_path = repo_root / "configs/base/contract_registry.yaml"
    diagnostics_path = repo_root / "contract-registry-diagnostics.json"

    if not registry_path.exists():
        print("::error::Contract registry not found")
        _write_diagnostics(
            diagnostics_path,
            valid=False,
            validation_issues=[
                RegistryValidationIssue(
                    message=f"Registry file not found: {registry_path}",
                    severity=RegistryValidationSeverity.BLOCKING,
                    contract_ref=None,
                    field="registry_path",
                )
            ],
            filesystem_issues=[],
            entries_count=0,
        )
        return 1

    try:
        # Load registry
        registry = ContractRegistry(registry_path)
        print(
            f"::notice::Loaded contract registry with {len(registry.entries)} entries"
        )

        # Validate all entries
        validation_result = registry.validate_all()

        if validation_result.valid:
            print("::notice::All registry entries are valid")
        else:
            print(f"::warning::Found {len(validation_result.issues)} validation issues")

            # Count by severity
            blocking = [
                issue
                for issue in validation_result.issues
                if issue.severity == RegistryValidationSeverity.BLOCKING
            ]
            warnings = [
                issue
                for issue in validation_result.issues
                if issue.severity == RegistryValidationSeverity.WARNING
            ]

            if blocking:
                print(f"::error::{len(blocking)} blocking issues found:")
                for issue in blocking:
                    print(f"  - {issue.contract_ref}: {issue.message} ({issue.field})")

            if warnings:
                print(f"::warning::{len(warnings)} non-blocking warnings:")
                for issue in warnings:
                    print(f"  - {issue.contract_ref}: {issue.message} ({issue.field})")

        # Validate filesystem consistency
        fs_result = registry.validate_filesystem_consistency()

        if fs_result.valid:
            print("::notice::Filesystem consistency validated")
        else:
            print(f"::error::Filesystem consistency issues found:")
            for issue in fs_result.issues:
                print(f"  - {issue.contract_ref}: {issue.message} ({issue.field})")

        # Determine overall result
        has_blocking_validation_issues = any(
            issue.severity == RegistryValidationSeverity.BLOCKING
            for issue in validation_result.issues
        )
        has_filesystem_issues = not fs_result.valid
        has_errors = has_blocking_validation_issues or has_filesystem_issues

        _write_diagnostics(
            diagnostics_path,
            valid=not has_errors,
            validation_issues=list(validation_result.issues),
            filesystem_issues=list(fs_result.issues),
            entries_count=len(registry.entries),
        )

        if has_errors:
            print("::error::Contract registry validation failed")
            return 1
        else:
            print("::notice::Contract registry validation passed")
            print(f"registry_hash={registry.registry_hash}")
            return 0

    except Exception as exc:  # pragma: no cover - defensive CI error path
        print(f"::error::Contract registry validation failed with exception: {exc!s}")
        _write_diagnostics(
            diagnostics_path,
            valid=False,
            validation_issues=[
                RegistryValidationIssue(
                    message=f"Unhandled exception: {exc!s}",
                    severity=RegistryValidationSeverity.BLOCKING,
                    contract_ref=None,
                    field="runtime",
                )
            ],
            filesystem_issues=[],
            entries_count=0,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
