"""Resolve and validate the SHA-pinned technical-debt audit lifecycle."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

DEFAULT_REGISTRY_PATH = Path("configs/quality/technical_debt_audit_registry.yaml")
SHA_PATTERN = re.compile(r"^[0-9a-f]{40,64}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class TechnicalDebtAuditRecord:
    """One current or superseded technical-debt audit record."""

    audit_id: str
    status: str
    report_path: str
    audited_commit_sha: str | None
    evidence_surface_sha256: str | None
    evidence_paths: tuple[str, ...]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _safe_relative_path(raw_path: str) -> str:
    pure_path = PurePosixPath(raw_path)
    if (
        pure_path.is_absolute()
        or ".." in pure_path.parts
        or pure_path.as_posix() != raw_path
    ):
        raise ValueError(
            f"audit registry path must be canonical and relative: {raw_path}"
        )
    return raw_path


def _record_from_mapping(payload: dict[str, Any]) -> TechnicalDebtAuditRecord:
    evidence_paths = payload.get("evidence_paths", [])
    if not isinstance(evidence_paths, list) or not all(
        isinstance(path, str) for path in evidence_paths
    ):
        raise ValueError(
            "technical-debt audit evidence_paths must be a list of strings"
        )
    required_strings = ("id", "status", "report_path")
    if not all(isinstance(payload.get(key), str) for key in required_strings):
        raise ValueError(
            "technical-debt audit records require id, status, and report_path"
        )
    return TechnicalDebtAuditRecord(
        audit_id=str(payload["id"]),
        status=str(payload["status"]),
        report_path=_safe_relative_path(str(payload["report_path"])),
        audited_commit_sha=(
            str(payload["audited_commit_sha"])
            if isinstance(payload.get("audited_commit_sha"), str)
            else None
        ),
        evidence_surface_sha256=(
            str(payload["evidence_surface_sha256"])
            if isinstance(payload.get("evidence_surface_sha256"), str)
            else None
        ),
        evidence_paths=tuple(_safe_relative_path(path) for path in evidence_paths),
    )


def load_technical_debt_audit_registry(
    root: Path,
    registry_path: Path | None = None,
) -> tuple[str, tuple[TechnicalDebtAuditRecord, ...]]:
    """Load the lifecycle registry and return its current id plus records."""
    relative_registry = registry_path or DEFAULT_REGISTRY_PATH
    payload = yaml.safe_load((root / relative_registry).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise ValueError("technical-debt audit registry must be a version 1 mapping")
    current_audit_id = payload.get("current_audit_id")
    raw_records = payload.get("audits")
    if not isinstance(current_audit_id, str) or not isinstance(raw_records, list):
        raise ValueError("registry requires current_audit_id and an audits list")
    records = tuple(
        _record_from_mapping(record)
        for record in raw_records
        if isinstance(record, dict)
    )
    if len(records) != len(raw_records):
        raise ValueError("each technical-debt audit entry must be a mapping")
    return current_audit_id, records


def resolve_current_technical_debt_audit(
    root: Path,
    registry_path: Path | None = None,
) -> Path:
    """Resolve the unique current technical-debt audit report path."""
    current_audit_id, records = load_technical_debt_audit_registry(
        root,
        registry_path,
    )
    current_records = [record for record in records if record.status == "current"]
    if len(current_records) != 1 or current_records[0].audit_id != current_audit_id:
        raise ValueError("registry must declare exactly one matching current audit")
    return root / current_records[0].report_path


def compute_evidence_surface_sha256(
    root: Path,
    evidence_paths: tuple[str, ...] | list[str],
) -> str:
    """Hash ordered path/content identities for audit evidence files."""
    identities: list[dict[str, str]] = []
    for relative_path in sorted(set(evidence_paths)):
        normalized = _safe_relative_path(relative_path)
        evidence_path = root / normalized
        if not evidence_path.is_file():
            raise FileNotFoundError(
                f"technical-debt audit evidence is missing: {normalized}"
            )
        identities.append(
            {
                "path": normalized,
                "sha256": hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
            }
        )
    canonical = json.dumps(
        identities,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _commit_exists(root: Path, commit_sha: str) -> bool:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{commit_sha}^{{commit}}"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.returncode == 0


def validate_technical_debt_audit_registry(
    root: Path,
    registry_path: Path | None = None,
    *,
    verify_git_commit: bool = True,
) -> list[str]:
    """Return deterministic lifecycle violations for the audit registry."""
    try:
        current_audit_id, records = load_technical_debt_audit_registry(
            root,
            registry_path,
        )
    except (OSError, UnicodeError, ValueError, yaml.YAMLError) as exc:
        return [str(exc)]

    issues: list[str] = []
    ids = [record.audit_id for record in records]
    if len(ids) != len(set(ids)):
        issues.append("audit ids must be unique")
    current_records = [record for record in records if record.status == "current"]
    if len(current_records) != 1:
        issues.append("registry must contain exactly one current audit")
        return issues
    current = current_records[0]
    if current.audit_id != current_audit_id:
        issues.append("current_audit_id must match the current audit record")

    for record in records:
        report_path = root / record.report_path
        if not report_path.is_file():
            issues.append(f"audit report is missing: {record.report_path}")
        if record.status == "superseded" and not record.report_path.startswith(
            "docs/99-archive/"
        ):
            issues.append(
                f"superseded audit must live in archive: {record.report_path}"
            )
    if current.report_path.startswith("docs/99-archive/"):
        issues.append("current audit must not live in docs/99-archive")
    if current.audited_commit_sha is None or not SHA_PATTERN.fullmatch(
        current.audited_commit_sha
    ):
        issues.append("current audit requires an exact audited_commit_sha")
    elif verify_git_commit and not _commit_exists(root, current.audited_commit_sha):
        issues.append("current audited_commit_sha is not a local Git commit")
    if current.evidence_surface_sha256 is None or not SHA256_PATTERN.fullmatch(
        current.evidence_surface_sha256
    ):
        issues.append("current audit requires evidence_surface_sha256")
    else:
        try:
            actual_hash = compute_evidence_surface_sha256(root, current.evidence_paths)
        except (OSError, ValueError) as exc:
            issues.append(str(exc))
        else:
            if actual_hash != current.evidence_surface_sha256:
                issues.append("current audit evidence_surface_sha256 is stale")

    report_path = root / current.report_path
    if report_path.is_file():
        report = report_path.read_text(encoding="utf-8")
        expected_markers = (
            "Lifecycle status: current",
            f"Audited commit SHA: `{current.audited_commit_sha}`",
            f"Evidence surface SHA-256: `{current.evidence_surface_sha256}`",
        )
        for marker in expected_markers:
            if marker not in report:
                issues.append(f"current audit is missing metadata marker: {marker}")
        if " / current" in report:
            issues.append("current audit must not use an ambiguous branch/current SHA")
    return issues


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=_repo_root())
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY_PATH)
    parser.add_argument("--print-current", action="store_true")
    parser.add_argument("--print-evidence-hash", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Validate or resolve the current technical-debt audit."""
    args = _build_parser().parse_args(argv)
    root = args.root.resolve()
    current_id, records = load_technical_debt_audit_registry(root, args.registry)
    current = next(record for record in records if record.audit_id == current_id)
    if args.print_current:
        print(root / current.report_path)
        return 0
    if args.print_evidence_hash:
        print(compute_evidence_surface_sha256(root, current.evidence_paths))
        return 0
    issues = validate_technical_debt_audit_registry(root, args.registry)
    if args.json:
        print(
            json.dumps({"issues": issues, "ok": not issues}, indent=2, sort_keys=True)
        )
    elif issues:
        print("Technical-debt audit registry validation failed:")
        for issue in issues:
            print(f"- {issue}")
    else:
        print(f"Technical-debt audit registry passed: {current.report_path}")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
