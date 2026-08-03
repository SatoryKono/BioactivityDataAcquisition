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
from bioetl.infrastructure.config.contract_registry_loader import (
    resolve_contract_registry_path,
)
from bioetl.infrastructure.control_plane import FileContractRegistryStore


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
    diagnostics_path.parent.mkdir(parents=True, exist_ok=True)
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
        issues.extend(_build_entry_identity_issues(contract_ref, entry))
    return issues


def _build_entry_identity_issues(
    contract_ref: str,
    entry: Any,
) -> list[RegistryValidationIssue]:
    identity = entry.identity
    issues: list[RegistryValidationIssue] = []
    issues.extend(_build_contract_ref_mismatch_issues(contract_ref, identity))
    issues.extend(_build_identity_validation_issues(contract_ref, identity))
    issues.extend(_build_identity_pairing_issues(contract_ref, identity))
    issues.extend(_build_identity_entry_mismatch_issues(contract_ref, identity, entry))
    issues.extend(_build_supported_versions_issues(contract_ref, identity, entry))
    return issues


def _build_contract_ref_mismatch_issues(
    contract_ref: str,
    identity: Any,
) -> list[RegistryValidationIssue]:
    if identity.contract_ref == contract_ref:
        return []
    return [
        RegistryValidationIssue(
            message=(
                f"Registry key mismatch with identity.contract_ref: "
                f"{identity.contract_ref}"
            ),
            severity=RegistryValidationSeverity.BLOCKING,
            contract_ref=contract_ref,
            field="identity.contract_ref",
        )
    ]


def _build_identity_validation_issues(
    contract_ref: str,
    identity: Any,
) -> list[RegistryValidationIssue]:
    return [
        RegistryValidationIssue(
            message=message,
            severity=RegistryValidationSeverity.BLOCKING,
            contract_ref=contract_ref,
            field="identity",
        )
        for message in identity.validate()
    ]


def _build_identity_pairing_issues(
    contract_ref: str,
    identity: Any,
) -> list[RegistryValidationIssue]:
    has_identity_dq_ref = bool(identity.dq_policy_ref)
    has_identity_rule_bundle = bool(identity.rule_bundle_version)
    if has_identity_dq_ref == has_identity_rule_bundle:
        return []
    return [
        RegistryValidationIssue(
            message=(
                "identity.dq_policy_ref and identity.rule_bundle_version "
                "must be set together"
            ),
            severity=RegistryValidationSeverity.BLOCKING,
            contract_ref=contract_ref,
            field="identity",
        )
    ]


def _build_identity_entry_mismatch_issues(
    contract_ref: str,
    identity: Any,
    entry: Any,
) -> list[RegistryValidationIssue]:
    issues: list[RegistryValidationIssue] = []
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
                message="rule_bundle_version mismatch between identity and entry",
                severity=RegistryValidationSeverity.BLOCKING,
                contract_ref=contract_ref,
                field="rule_bundle_version",
            )
        )
    return issues


def _build_supported_versions_issues(
    contract_ref: str,
    identity: Any,
    entry: Any,
) -> list[RegistryValidationIssue]:
    if not entry.supported_versions:
        return [
            RegistryValidationIssue(
                message="supported_versions is empty",
                severity=RegistryValidationSeverity.WARNING,
                contract_ref=contract_ref,
                field="supported_versions",
            )
        ]
    if identity.contract_version in entry.supported_versions:
        return []
    return [
        RegistryValidationIssue(
            message=(
                f"identity version {identity.contract_version} not present in "
                "supported_versions"
            ),
            severity=RegistryValidationSeverity.BLOCKING,
            contract_ref=contract_ref,
            field="supported_versions",
        )
    ]


def main() -> int:
    """Validate contract identity and write CI diagnostics."""
    repo_root = Path(__file__).resolve().parents[3]
    registry_path = resolve_contract_registry_path(repo_root=repo_root)
    diagnostics_path = repo_root / "reports/quality/contract-identity-diagnostics.json"

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
        registry = FileContractRegistryStore(registry_path).load()
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
