"""CI script to validate contract identity consistency and diagnostics."""

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
    """Convert registry issue into a JSON-serializable payload."""
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
    issues: list[RegistryValidationIssue],
    entries_count: int,
) -> None:
    """Persist identity diagnostics for CI artifact upload."""
    blocking_count = sum(
        1 for issue in issues if issue.severity == RegistryValidationSeverity.BLOCKING
    )
    warning_count = sum(
        1 for issue in issues if issue.severity == RegistryValidationSeverity.WARNING
    )
    payload = {
        "valid": valid,
        "entries_count": entries_count,
        "issue_count": len(issues),
        "blocking_issue_count": blocking_count,
        "warning_issue_count": warning_count,
        "issues": [_issue_payload(issue) for issue in issues],
    }
    diagnostics_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _build_identity_issues(registry: ContractRegistry) -> list[RegistryValidationIssue]:
    """Collect identity-focused issues from loaded registry entries."""
    issues: list[RegistryValidationIssue] = []
    for contract_ref, entry in sorted(registry.entries.items()):
        identity = entry.identity

        if identity.contract_ref != contract_ref:
            issues.append(
                RegistryValidationIssue(
                    message=(
                        f"Registry key mismatch with identity.contract_ref: "
                        f"{identity.contract_ref}"
                    ),
                    severity=RegistryValidationSeverity.BLOCKING,
                    contract_ref=contract_ref,
                    field="identity.contract_ref",
                )
            )

        for message in identity.validate():
            issues.append(
                RegistryValidationIssue(
                    message=message,
                    severity=RegistryValidationSeverity.BLOCKING,
                    contract_ref=contract_ref,
                    field="identity",
                )
            )

        has_identity_dq_ref = bool(identity.dq_policy_ref)
        has_identity_rule_bundle = bool(identity.rule_bundle_version)
        if has_identity_dq_ref != has_identity_rule_bundle:
            issues.append(
                RegistryValidationIssue(
                    message=(
                        "identity.dq_policy_ref and identity.rule_bundle_version "
                        "must be set together"
                    ),
                    severity=RegistryValidationSeverity.BLOCKING,
                    contract_ref=contract_ref,
                    field="identity",
                )
            )

        if (
            identity.dq_policy_ref
            and entry.dq_policy_ref
            and identity.dq_policy_ref != entry.dq_policy_ref
        ):
            issues.append(
                RegistryValidationIssue(
                    message="dq_policy_ref mismatch between identity and entry",
                    severity=RegistryValidationSeverity.BLOCKING,
                    contract_ref=contract_ref,
                    field="dq_policy_ref",
                )
            )

        if (
            identity.rule_bundle_version
            and entry.rule_bundle_version
            and identity.rule_bundle_version != entry.rule_bundle_version
        ):
            issues.append(
                RegistryValidationIssue(
                    message=("rule_bundle_version mismatch between identity and entry"),
                    severity=RegistryValidationSeverity.BLOCKING,
                    contract_ref=contract_ref,
                    field="rule_bundle_version",
                )
            )

        if not entry.supported_versions:
            issues.append(
                RegistryValidationIssue(
                    message="supported_versions is empty",
                    severity=RegistryValidationSeverity.WARNING,
                    contract_ref=contract_ref,
                    field="supported_versions",
                )
            )
        elif identity.contract_version not in entry.supported_versions:
            issues.append(
                RegistryValidationIssue(
                    message=(
                        f"identity version {identity.contract_version} not present in "
                        "supported_versions"
                    ),
                    severity=RegistryValidationSeverity.BLOCKING,
                    contract_ref=contract_ref,
                    field="supported_versions",
                )
            )

    return issues


def main() -> int:
    """Validate contract identity and write CI diagnostics."""
    repo_root = Path(__file__).resolve().parents[2]
    registry_path = repo_root / "configs" / "base" / "contract_registry.yaml"
    diagnostics_path = repo_root / "contract-identity-diagnostics.json"

    if not registry_path.exists():
        print("::error::Contract registry not found")
        _write_diagnostics(
            diagnostics_path,
            valid=False,
            issues=[
                RegistryValidationIssue(
                    message=f"Registry file not found: {registry_path}",
                    severity=RegistryValidationSeverity.BLOCKING,
                    contract_ref=None,
                    field="registry_path",
                )
            ],
            entries_count=0,
        )
        return 1

    try:
        registry = ContractRegistry(registry_path)
        print(
            f"::notice::Loaded contract registry with {len(registry.entries)} entries"
        )

        issues = _build_identity_issues(registry)
        blocking_issues = [
            issue
            for issue in issues
            if issue.severity == RegistryValidationSeverity.BLOCKING
        ]
        warning_issues = [
            issue
            for issue in issues
            if issue.severity == RegistryValidationSeverity.WARNING
        ]

        if warning_issues:
            print(f"::warning::{len(warning_issues)} identity warnings detected")
            for issue in warning_issues:
                print(
                    f"  - {issue.contract_ref}: {issue.message}"
                    f"{f' ({issue.field})' if issue.field else ''}"
                )

        if blocking_issues:
            print(f"::error::{len(blocking_issues)} identity blocking issues detected")
            for issue in blocking_issues:
                print(
                    f"  - {issue.contract_ref}: {issue.message}"
                    f"{f' ({issue.field})' if issue.field else ''}"
                )
            _write_diagnostics(
                diagnostics_path,
                valid=False,
                issues=issues,
                entries_count=len(registry.entries),
            )
            return 1

        print("::notice::Contract identity validation passed")
        _write_diagnostics(
            diagnostics_path,
            valid=True,
            issues=issues,
            entries_count=len(registry.entries),
        )
        return 0
    except Exception as exc:  # pragma: no cover - defensive CI error path
        print(f"::error::Contract identity validation failed with exception: {exc!s}")
        _write_diagnostics(
            diagnostics_path,
            valid=False,
            issues=[
                RegistryValidationIssue(
                    message=f"Unhandled exception: {exc!s}",
                    severity=RegistryValidationSeverity.BLOCKING,
                    contract_ref=None,
                    field="runtime",
                )
            ],
            entries_count=0,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
