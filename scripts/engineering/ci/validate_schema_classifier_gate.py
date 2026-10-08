"""CI gate for schema classifier-driven contract governance.

This script compares changed published contract artifacts between git revisions,
classifies schema diffs (patch/minor/major/manual_review), and enforces:

1. major changes require a major version bump in contract registry;
2. major changes require migration guide entry for old->new version;
3. manual_review classifications are blocking until resolved.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from bioetl.domain.control_plane.contract_registry_helpers import (
    parse_semver,
    resolve_path,
)
from bioetl.domain.behavior.schema_classifier import create_schema_classifier
from bioetl.domain.types.schema_policy import ChangeClassification


@dataclass(frozen=True)
class ClassificationRecord:
    """Classification result for one contract artifact."""

    contract_ref: str
    artifact_path: str
    classification: str
    old_version: str | None
    new_version: str | None
    breaking_changes_count: int
    non_breaking_changes_count: int
    requires_manual_review: bool


@dataclass(frozen=True)
class GateIssue:
    """Blocking issue produced by the governance gate."""

    contract_ref: str | None
    artifact_path: str | None
    message: str


def _git_stdout(repo_root: Path, *args: str) -> str:
    """Run git command and return stdout, with Windows fallback candidates."""
    candidates = [os.environ.get("GIT_EXE"), "git"]
    if sys.platform.startswith("win"):
        candidates.extend(
            [
                r"C:\Program Files\Git\cmd\git.exe",
                r"C:\Program Files\Git\bin\git.exe",
            ]
        )

    last_error: subprocess.CalledProcessError | None = None
    for executable in candidates:
        if not executable:
            continue
        from scripts.engineering.common.repo_paths import ensure_safe_cli_argv

        completed = subprocess.run(  # NOSONAR - argv via ensure_safe_cli_argv
            ensure_safe_cli_argv([executable, *[str(a) for a in args]]),
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if completed.returncode == 0:
            return completed.stdout
        last_error = subprocess.CalledProcessError(
            completed.returncode,
            [executable, *args],
            output=completed.stdout,
            stderr=completed.stderr,
        )

    if last_error is not None:
        raise last_error
    raise RuntimeError("No git executable candidates available")


def _coerce_ref_arg(value: str | None) -> str | None:
    """Normalize optional git ref argument."""
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _detect_base_ref(repo_root: Path, explicit_base_ref: str | None) -> str:
    """Resolve base git ref for comparison."""
    if explicit_base_ref is not None:
        return explicit_base_ref
    # Default local behavior: compare against previous commit.
    return _git_stdout(repo_root, "rev-parse", "HEAD~1").strip()


def _load_registry_yaml(content: str) -> dict[str, Any]:
    """Load registry YAML payload with shape validation."""
    data = yaml.safe_load(content)
    if not isinstance(data, dict):
        raise ValueError("Contract registry must be a mapping")
    entries = data.get("entries")
    if not isinstance(entries, dict):
        raise ValueError("Contract registry must contain entries mapping")
    return data


def _load_registry_from_fs(registry_path: Path) -> dict[str, Any]:
    """Load current registry from filesystem."""
    return _load_registry_yaml(registry_path.read_text(encoding="utf-8"))


def _load_registry_from_git(
    repo_root: Path, *, base_ref: str, registry_rel_path: str
) -> dict[str, Any] | None:
    """Load base registry from git reference when file exists."""
    try:
        content = _git_stdout(repo_root, "show", f"{base_ref}:{registry_rel_path}")
    except subprocess.CalledProcessError:
        return None
    return _load_registry_yaml(content)


def _changed_paths(repo_root: Path, *, base_ref: str, head_ref: str) -> set[str]:
    """Return changed file paths between two git refs."""
    stdout = _git_stdout(repo_root, "diff", "--name-only", base_ref, head_ref)
    return {line.strip() for line in stdout.splitlines() if line.strip()}


def _artifact_relpath_for_entry(
    repo_root: Path, registry_path: Path, artifact_path: str
) -> str | None:
    """Resolve registry artifact reference into repo-relative path."""
    absolute = resolve_path(artifact_path, registry_path.parent)
    try:
        return absolute.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return None


def _contract_artifact_index(
    *,
    repo_root: Path,
    registry_path: Path,
    entries: dict[str, Any],
) -> dict[str, str]:
    """Build map repo-relative artifact path -> contract_ref."""
    index: dict[str, str] = {}
    for contract_ref, entry in entries.items():
        if not isinstance(entry, dict):
            continue
        artifacts = entry.get("published_artifacts")
        if not isinstance(artifacts, list):
            continue
        for artifact in artifacts:
            if not isinstance(artifact, str):
                continue
            relpath = _artifact_relpath_for_entry(repo_root, registry_path, artifact)
            if relpath is None:
                continue
            index[relpath] = str(contract_ref)
    return index


def _major_transition_issues(
    *,
    contract_ref: str,
    old_version: str | None,
    new_version: str | None,
    migration_guides: dict[str, str],
) -> list[GateIssue]:
    """Return blocking issues for major classification governance rules."""
    issues: list[GateIssue] = []
    if old_version is None or new_version is None:
        issues.append(
            GateIssue(
                contract_ref=contract_ref,
                artifact_path=None,
                message=(
                    "major change classified but old/new contract versions are "
                    "not available in registry comparison"
                ),
            )
        )
        return issues

    if old_version == new_version:
        issues.append(
            GateIssue(
                contract_ref=contract_ref,
                artifact_path=None,
                message=(
                    f"major change requires major version bump "
                    f"(old={old_version}, new={new_version})"
                ),
            )
        )
    else:
        try:
            old_semver = parse_semver(old_version)
            new_semver = parse_semver(new_version)
        except ValueError as exc:
            issues.append(
                GateIssue(
                    contract_ref=contract_ref,
                    artifact_path=None,
                    message=(
                        "major change requires valid semantic versions in registry: "
                        f"{exc!s}"
                    ),
                )
            )
        else:
            if new_semver[0] <= old_semver[0]:
                issues.append(
                    GateIssue(
                        contract_ref=contract_ref,
                        artifact_path=None,
                        message=(
                            "major change requires incrementing major version "
                            f"(old={old_version}, new={new_version})"
                        ),
                    )
                )

    transition_key = f"{old_version}->{new_version}"
    if not migration_guides:
        issues.append(
            GateIssue(
                contract_ref=contract_ref,
                artifact_path=None,
                message=(
                    "major change requires migration_guides entry "
                    f"for transition {transition_key}"
                ),
            )
        )
    elif transition_key not in migration_guides:
        issues.append(
            GateIssue(
                contract_ref=contract_ref,
                artifact_path=None,
                message=(
                    f"migration_guides missing required transition key {transition_key}"
                ),
            )
        )
    return issues


def _entry_version(entry: dict[str, Any] | None) -> str | None:
    """Extract contract version from registry entry payload."""
    if not isinstance(entry, dict):
        return None
    identity = entry.get("identity")
    if not isinstance(identity, dict):
        return None
    value = identity.get("contract_version")
    if isinstance(value, str) and value:
        return value
    return None


def _entry_migration_guides(entry: dict[str, Any] | None) -> dict[str, str]:
    """Extract migration_guides from entry payload."""
    if not isinstance(entry, dict):
        return {}
    value = entry.get("migration_guides")
    if not isinstance(value, dict):
        return {}
    return {str(k): str(v) for k, v in value.items()}


def _read_json_file(path: Path) -> dict[str, Any]:
    """Read and parse JSON file from filesystem."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _read_json_from_git(
    repo_root: Path, *, base_ref: str, relpath: str
) -> dict[str, Any] | None:
    """Read JSON file content from base git reference."""
    try:
        content = _git_stdout(repo_root, "show", f"{base_ref}:{relpath}")
    except subprocess.CalledProcessError:
        return None
    data = json.loads(content)
    if not isinstance(data, dict):
        return None
    return data


def _issue_payload(issue: GateIssue) -> dict[str, Any]:
    """Serialize gate issue for diagnostics file."""
    return {
        "contract_ref": issue.contract_ref,
        "artifact_path": issue.artifact_path,
        "message": issue.message,
    }


def _record_payload(record: ClassificationRecord) -> dict[str, Any]:
    """Serialize classification record for diagnostics file."""
    return {
        "contract_ref": record.contract_ref,
        "artifact_path": record.artifact_path,
        "classification": record.classification,
        "old_version": record.old_version,
        "new_version": record.new_version,
        "breaking_changes_count": record.breaking_changes_count,
        "non_breaking_changes_count": record.non_breaking_changes_count,
        "requires_manual_review": record.requires_manual_review,
    }


def _write_diagnostics(
    path: Path,
    *,
    base_ref: str,
    head_ref: str,
    changed_contract_sources: list[str],
    changed_artifacts: list[str],
    records: list[ClassificationRecord],
    issues: list[GateIssue],
) -> None:
    """Write classifier gate diagnostics artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "valid": len(issues) == 0,
        "base_ref": base_ref,
        "head_ref": head_ref,
        "changed_contract_source_count": len(changed_contract_sources),
        "changed_contract_sources": changed_contract_sources,
        "changed_artifact_count": len(changed_artifacts),
        "changed_artifacts": changed_artifacts,
        "classification_count": len(records),
        "classifications": [_record_payload(record) for record in records],
        "issue_count": len(issues),
        "issues": [_issue_payload(issue) for issue in issues],
    }
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _changed_contract_sources(changed: set[str]) -> list[str]:
    """Return changed contract source modules from the git diff."""
    return sorted(
        path
        for path in changed
        if path.startswith("src/bioetl/domain/contracts/") and path.endswith(".py")
    )


def _source_without_artifact_issues(
    *,
    changed_sources: list[str],
    changed_artifacts: list[str],
) -> list[GateIssue]:
    """Return issue when contract source changed without artifact update."""
    if not changed_sources or changed_artifacts:
        return []
    return [
        GateIssue(
            contract_ref=None,
            artifact_path=None,
            message=(
                "contract source changed but no published contract artifact changed; "
                "cannot classify schema diff"
            ),
        )
    ]


def _classify_artifact_change(
    *,
    repo_root: Path,
    base_ref: str,
    relpath: str,
    classifier: Any,
) -> tuple[ChangeClassification, int, int, bool]:
    """Classify one changed published artifact against its base revision."""
    new_schema = _read_json_file(repo_root / relpath)
    old_schema = _read_json_from_git(repo_root, base_ref=base_ref, relpath=relpath)
    if old_schema is None:
        # New artifact in current diff; classify as MINOR by policy default.
        return ChangeClassification.MINOR, 0, 0, False
    result = classifier.classify_changes(old_schema, new_schema)
    return (
        result.classification,
        len(result.breaking_changes),
        len(result.non_breaking_changes),
        result.requires_manual_review,
    )


def _artifact_classification_record(
    *,
    contract_ref: str,
    relpath: str,
    classification: ChangeClassification,
    old_version: str | None,
    new_version: str | None,
    breaking_changes_count: int,
    non_breaking_changes_count: int,
    requires_manual_review: bool,
) -> ClassificationRecord:
    """Build one serialized classification record."""
    return ClassificationRecord(
        contract_ref=contract_ref,
        artifact_path=relpath,
        classification=classification.value,
        old_version=old_version,
        new_version=new_version,
        breaking_changes_count=breaking_changes_count,
        non_breaking_changes_count=non_breaking_changes_count,
        requires_manual_review=requires_manual_review,
    )


def _classification_gate_issues(
    *,
    contract_ref: str,
    relpath: str,
    classification: ChangeClassification,
    old_version: str | None,
    new_version: str | None,
    current_entry: dict[str, Any] | None,
) -> list[GateIssue]:
    """Return governance issues for one classification outcome."""
    if classification == ChangeClassification.MANUAL_REVIEW:
        return [
            GateIssue(
                contract_ref=contract_ref,
                artifact_path=relpath,
                message=(
                    "schema diff classified as manual_review; provide explicit "
                    "migration/change decision before merge"
                ),
            )
        ]
    if classification != ChangeClassification.MAJOR:
        return []
    return _major_transition_issues(
        contract_ref=contract_ref,
        old_version=old_version,
        new_version=new_version,
        migration_guides=_entry_migration_guides(current_entry),
    )


def _evaluate_changed_artifact(
    *,
    repo_root: Path,
    base_ref: str,
    relpath: str,
    contract_ref: str,
    classifier: Any,
    current_entry: dict[str, Any] | None,
    base_entry: dict[str, Any] | None,
) -> tuple[ClassificationRecord, list[GateIssue]]:
    """Classify one changed artifact and derive governance issues."""
    (
        classification,
        breaking_changes_count,
        non_breaking_changes_count,
        requires_manual_review,
    ) = _classify_artifact_change(
        repo_root=repo_root,
        base_ref=base_ref,
        relpath=relpath,
        classifier=classifier,
    )
    old_version = _entry_version(base_entry)
    new_version = _entry_version(current_entry)
    record = _artifact_classification_record(
        contract_ref=contract_ref,
        relpath=relpath,
        classification=classification,
        old_version=old_version,
        new_version=new_version,
        breaking_changes_count=breaking_changes_count,
        non_breaking_changes_count=non_breaking_changes_count,
        requires_manual_review=requires_manual_review,
    )
    return record, _classification_gate_issues(
        contract_ref=contract_ref,
        relpath=relpath,
        classification=classification,
        old_version=old_version,
        new_version=new_version,
        current_entry=current_entry,
    )


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-sha", default=None)
    parser.add_argument("--head-sha", default="HEAD")
    parser.add_argument(
        "--diagnostics-path",
        default="reports/quality/contract-schema-classifier-diagnostics.json",
    )
    return parser.parse_args()


def main() -> int:
    """Run classifier gate and return process exit code."""
    args = _parse_args()
    repo_root = Path(__file__).resolve().parents[3]
    registry_path = repo_root / "configs" / "base" / "contract_registry.yaml"
    diagnostics_path = repo_root / str(args.diagnostics_path)

    base_ref = _detect_base_ref(repo_root, _coerce_ref_arg(args.base_sha))
    head_ref = str(args.head_sha)

    current_registry = _load_registry_from_fs(registry_path)
    current_entries = current_registry["entries"]
    base_registry = _load_registry_from_git(
        repo_root,
        base_ref=base_ref,
        registry_rel_path="configs/base/contract_registry.yaml",
    )
    base_entries = base_registry.get("entries", {}) if base_registry else {}
    if not isinstance(base_entries, dict):
        base_entries = {}

    changed = _changed_paths(repo_root, base_ref=base_ref, head_ref=head_ref)
    changed_sources = _changed_contract_sources(changed)
    artifact_index = _contract_artifact_index(
        repo_root=repo_root,
        registry_path=registry_path,
        entries=current_entries,
    )
    changed_artifacts = sorted(path for path in changed if path in artifact_index)

    records: list[ClassificationRecord] = []
    issues: list[GateIssue] = []
    classifier = create_schema_classifier()
    issues.extend(
        _source_without_artifact_issues(
            changed_sources=changed_sources,
            changed_artifacts=changed_artifacts,
        )
    )

    for relpath in changed_artifacts:
        contract_ref = artifact_index[relpath]
        current_entry = current_entries.get(contract_ref)
        base_entry = base_entries.get(contract_ref)
        record, artifact_issues = _evaluate_changed_artifact(
            repo_root=repo_root,
            base_ref=base_ref,
            relpath=relpath,
            contract_ref=contract_ref,
            classifier=classifier,
            current_entry=current_entry,
            base_entry=base_entry,
        )
        records.append(record)
        issues.extend(artifact_issues)

    _write_diagnostics(
        diagnostics_path,
        base_ref=base_ref,
        head_ref=head_ref,
        changed_contract_sources=changed_sources,
        changed_artifacts=changed_artifacts,
        records=records,
        issues=issues,
    )

    if issues:
        print(f"::error::{len(issues)} schema governance issue(s) detected")
        for issue in issues:
            print(f"  - {issue.contract_ref or 'global'}: {issue.message}")
        return 1

    print("::notice::Schema classifier governance gate passed")
    print(f"checked_contract_artifacts={len(records)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
