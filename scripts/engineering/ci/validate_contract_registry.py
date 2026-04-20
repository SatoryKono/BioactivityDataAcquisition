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


def _missing_registry_issue(registry_path: Path) -> RegistryValidationIssue:
    return RegistryValidationIssue(
        message=f"Registry file not found: {registry_path}",
        severity=RegistryValidationSeverity.BLOCKING,
        contract_ref=None,
        field="registry_path",
    )


def _issues_by_severity(
    issues: list[RegistryValidationIssue],
) -> tuple[list[RegistryValidationIssue], list[RegistryValidationIssue]]:
    blocking = [
        issue
        for issue in issues
        if issue.severity == RegistryValidationSeverity.BLOCKING
    ]
    warnings = [
        issue
        for issue in issues
        if issue.severity == RegistryValidationSeverity.WARNING
    ]
    return blocking, warnings


def _print_issue_group(
    *,
    issues: list[RegistryValidationIssue],
    label: str,
    annotation: str,
) -> None:
    if not issues:
        return
    print(f"{annotation}{len(issues)} {label}:")
    for issue in issues:
        print(f"  - {issue.contract_ref}: {issue.message} ({issue.field})")


def _print_validation_issues(
    issues: list[RegistryValidationIssue],
) -> None:
    if not issues:
        print("::notice::All registry entries are valid")
        return

    print(f"::warning::Found {len(issues)} validation issues")
    blocking, warnings = _issues_by_severity(issues)
    _print_issue_group(
        issues=blocking,
        label="blocking issues found",
        annotation="::error::",
    )
    _print_issue_group(
        issues=warnings,
        label="non-blocking warnings",
        annotation="::warning::",
    )


def _finalize_validation(
    *,
    diagnostics_path: Path,
    registry: ContractRegistry,
    validation_issues: list[RegistryValidationIssue],
    filesystem_issues: list[RegistryValidationIssue],
) -> int:
    has_blocking_validation_issues = any(
        issue.severity == RegistryValidationSeverity.BLOCKING
        for issue in validation_issues
    )
    has_errors = has_blocking_validation_issues or bool(filesystem_issues)

    _write_diagnostics(
        diagnostics_path,
        valid=not has_errors,
        validation_issues=validation_issues,
        filesystem_issues=filesystem_issues,
        entries_count=len(registry.entries),
    )

    if has_errors:
        print("::error::Contract registry validation failed")
        return 1

    print("::notice::Contract registry validation passed")
    print(f"registry_hash={registry.registry_hash}")
    return 0


def main() -> int:
    """Main validation entry point."""
    repo_root = Path(__file__).resolve().parents[3]
    registry_path = repo_root / "configs/base/contract_registry.yaml"
    diagnostics_path = repo_root / "contract-registry-diagnostics.json"

    if not registry_path.exists():
        print("::error::Contract registry not found")
        _write_diagnostics(
            diagnostics_path,
            valid=False,
            validation_issues=[_missing_registry_issue(registry_path)],
            filesystem_issues=[],
            entries_count=0,
        )
        return 1

    try:
        registry = ContractRegistry(registry_path)
        print(
            f"::notice::Loaded contract registry with {len(registry.entries)} entries"
        )

        validation_result = registry.validate_all()
        _print_validation_issues(list(validation_result.issues))

        fs_result = registry.validate_filesystem_consistency()

        if fs_result.valid:
            print("::notice::Filesystem consistency validated")
        else:
            print(f"::error::Filesystem consistency issues found:")
            for issue in fs_result.issues:
                print(f"  - {issue.contract_ref}: {issue.message} ({issue.field})")

        return _finalize_validation(
            diagnostics_path=diagnostics_path,
            validation_issues=list(validation_result.issues),
            filesystem_issues=list(fs_result.issues),
            registry=registry,
        )

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

    return 0


if __name__ == "__main__":
    sys.exit(main())
