"""Validate consistency between contract registry and DQ contract configs."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load YAML mapping from path."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def _is_semver(value: str) -> bool:
    """Validate simple semantic version (X.Y.Z)."""
    parts = value.split(".")
    return len(parts) == 3 and all(part.isdigit() for part in parts)


def _issue(
    *,
    severity: str,
    contract_ref: str | None,
    message: str,
    path: str | None = None,
) -> dict[str, Any]:
    """Build structured issue payload."""
    return {
        "severity": severity,
        "contract_ref": contract_ref,
        "path": path,
        "message": message,
    }


def _contract_file_candidates(repo_root: Path, contract_ref: str) -> list[Path]:
    """Return candidate DQ contract config paths for registry contract_ref."""
    if "." not in contract_ref:
        return []
    provider, entity = contract_ref.split(".", 1)
    contracts_root = repo_root / "configs" / "contracts"
    return [
        contracts_root / provider / f"{entity}.yaml",
        contracts_root / provider / f"{entity}.json",
    ]


def _load_contract_file(path: Path) -> dict[str, Any]:
    """Load YAML or JSON contract config file."""
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"Expected mapping in {path}")
        return data
    return _load_yaml(path)


def _find_existing(paths: list[Path]) -> Path | None:
    """Return first existing path."""
    for path in paths:
        if path.exists():
            return path
    return None


def _expected_ref(entry: dict[str, Any], key: str) -> str | None:
    """Resolve expected DQ reference field from identity or root entry."""
    identity = entry.get("identity")
    identity_val = identity.get(key) if isinstance(identity, dict) else None
    if isinstance(identity_val, str) and identity_val:
        return identity_val
    entry_val = entry.get(key)
    if isinstance(entry_val, str) and entry_val:
        return entry_val
    return None


def _validate_entry(
    *,
    contract_ref: str,
    entry: dict[str, Any],
    contract_data: dict[str, Any],
    contract_path: Path,
) -> list[dict[str, Any]]:
    """Validate one registry entry against one DQ contract file."""
    issues: list[dict[str, Any]] = []
    identity = entry.get("identity")
    expected_version = (
        identity.get("contract_version")
        if isinstance(identity, dict)
        and isinstance(identity.get("contract_version"), str)
        else None
    )
    expected_rule_bundle = _expected_ref(entry, "rule_bundle_version")
    expected_dq_policy_ref = _expected_ref(entry, "dq_policy_ref")
    contract_path_str = str(contract_path)

    if contract_data.get("contract_ref") != contract_ref:
        issues.append(
            _issue(
                severity="blocking",
                contract_ref=contract_ref,
                path=contract_path_str,
                message=(
                    "contract_ref mismatch between registry and DQ config: "
                    f"{contract_data.get('contract_ref')!r} != {contract_ref!r}"
                ),
            )
        )

    if expected_version is None:
        issues.append(
            _issue(
                severity="warning",
                contract_ref=contract_ref,
                path=contract_path_str,
                message="registry identity.contract_version is missing",
            )
        )
    elif contract_data.get("contract_version") != expected_version:
        issues.append(
            _issue(
                severity="blocking",
                contract_ref=contract_ref,
                path=contract_path_str,
                message=(
                    "contract_version mismatch between registry and DQ config: "
                    f"{contract_data.get('contract_version')!r} != {expected_version!r}"
                ),
            )
        )
    elif not _is_semver(str(expected_version)):
        issues.append(
            _issue(
                severity="blocking",
                contract_ref=contract_ref,
                path=contract_path_str,
                message=(
                    f"registry contract_version {expected_version!r} "
                    "is not semantic version"
                ),
            )
        )

    if expected_rule_bundle is None:
        issues.append(
            _issue(
                severity="warning",
                contract_ref=contract_ref,
                path=contract_path_str,
                message="rule_bundle_version missing in registry identity/entry",
            )
        )
    elif contract_data.get("rule_bundle_version") != expected_rule_bundle:
        issues.append(
            _issue(
                severity="blocking",
                contract_ref=contract_ref,
                path=contract_path_str,
                message=(
                    "rule_bundle_version mismatch between registry and DQ config: "
                    f"{contract_data.get('rule_bundle_version')!r} "
                    f"!= {expected_rule_bundle!r}"
                ),
            )
        )

    if expected_dq_policy_ref is None:
        issues.append(
            _issue(
                severity="warning",
                contract_ref=contract_ref,
                path=contract_path_str,
                message="dq_policy_ref missing in registry identity/entry",
            )
        )
    elif contract_data.get("dq_policy_ref") != expected_dq_policy_ref:
        issues.append(
            _issue(
                severity="blocking",
                contract_ref=contract_ref,
                path=contract_path_str,
                message=(
                    "dq_policy_ref mismatch between registry and DQ config: "
                    f"{contract_data.get('dq_policy_ref')!r} != {expected_dq_policy_ref!r}"
                ),
            )
        )

    return issues


def _collect_orphan_contract_files(
    repo_root: Path,
    known_contract_refs: set[str],
) -> list[dict[str, Any]]:
    """Collect warning issues for DQ contract files not represented in registry."""
    issues: list[dict[str, Any]] = []
    contracts_root = repo_root / "configs" / "contracts"
    if not contracts_root.exists():
        return issues

    for path in sorted(contracts_root.rglob("*")):
        if path.suffix not in {".yaml", ".json"}:
            continue
        relative = path.relative_to(contracts_root)
        if len(relative.parts) < 2:
            continue
        provider = relative.parts[0]
        entity = relative.stem
        contract_ref = f"{provider}.{entity}"
        if contract_ref in known_contract_refs:
            continue
        issues.append(
            _issue(
                severity="warning",
                contract_ref=contract_ref,
                path=str(path),
                message="DQ contract file has no matching registry entry",
            )
        )
    return issues


def main() -> int:
    """Run registry<->DQ consistency validation."""
    repo_root = Path(__file__).resolve().parents[2]
    registry_path = repo_root / "configs" / "base" / "contract_registry.yaml"
    diagnostics_path = repo_root / "contract-registry-dq-diagnostics.json"

    if not registry_path.exists():
        diagnostics_path.write_text(
            json.dumps(
                {
                    "valid": False,
                    "checked_entries_count": 0,
                    "issue_count": 1,
                    "issues": [
                        _issue(
                            severity="blocking",
                            contract_ref=None,
                            path=str(registry_path),
                            message="contract registry file not found",
                        )
                    ],
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        print("::error::Contract registry file not found")
        return 1

    registry_data = _load_yaml(registry_path)
    entries = registry_data.get("entries")
    if not isinstance(entries, dict):
        raise ValueError("contract registry entries must be a mapping")

    issues: list[dict[str, Any]] = []
    known_refs = set(entries.keys())
    checked_entries = 0

    for contract_ref, entry in sorted(entries.items()):
        if not isinstance(entry, dict):
            issues.append(
                _issue(
                    severity="blocking",
                    contract_ref=str(contract_ref),
                    path=str(registry_path),
                    message="registry entry is not a mapping",
                )
            )
            continue
        checked_entries += 1
        candidates = _contract_file_candidates(repo_root, str(contract_ref))
        contract_path = _find_existing(candidates)
        if contract_path is None:
            issues.append(
                _issue(
                    severity="blocking",
                    contract_ref=str(contract_ref),
                    path=str(candidates[0]) if candidates else None,
                    message="missing DQ contract config file for registry entry",
                )
            )
            continue

        try:
            contract_data = _load_contract_file(contract_path)
        except Exception as exc:  # pragma: no cover - defensive script path
            issues.append(
                _issue(
                    severity="blocking",
                    contract_ref=str(contract_ref),
                    path=str(contract_path),
                    message=f"failed to load DQ contract file: {exc!s}",
                )
            )
            continue

        issues.extend(
            _validate_entry(
                contract_ref=str(contract_ref),
                entry=entry,
                contract_data=contract_data,
                contract_path=contract_path,
            )
        )

    issues.extend(_collect_orphan_contract_files(repo_root, known_refs))

    blocking_issues = [issue for issue in issues if issue["severity"] == "blocking"]
    payload = {
        "valid": len(blocking_issues) == 0,
        "checked_entries_count": checked_entries,
        "issue_count": len(issues),
        "blocking_issue_count": len(blocking_issues),
        "issues": issues,
    }
    diagnostics_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    if blocking_issues:
        print(
            f"::error::Registry<->DQ reference consistency failed with "
            f"{len(blocking_issues)} blocking issue(s)"
        )
        for issue in blocking_issues:
            print(f"  - {issue['contract_ref']}: {issue['message']}")
        return 1

    warning_count = len(issues) - len(blocking_issues)
    if warning_count:
        print(
            f"::warning::Registry<->DQ consistency passed with "
            f"{warning_count} warning(s)"
        )
    else:
        print("::notice::Registry<->DQ consistency passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
