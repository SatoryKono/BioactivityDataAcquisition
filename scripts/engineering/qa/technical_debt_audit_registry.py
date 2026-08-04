"""Resolve and validate the SHA-pinned technical-debt audit lifecycle."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

DEFAULT_REGISTRY_PATH = Path("configs/quality/technical_debt_audit_registry.yaml")
SHA_PATTERN = re.compile(r"^[0-9a-f]{40,64}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SEMANTIC_SUMMARY_START = "<!-- technical-debt-audit-summary-v1"
SEMANTIC_SUMMARY_END = "-->"
SEMANTIC_EVIDENCE_PATHS = frozenset(
    {
        "configs/quality/constructor_waivers.yaml",
        "reports/quality/architecture-quality-scorecard.json",
        "reports/quality/contract-coverage-matrix.json",
        "reports/quality/debt-governance-gates.json",
        "reports/quality/module-coverage-inventory.json",
    }
)


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
    """Hash ordered path/content identities independent of checkout line endings."""
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
                "sha256": hashlib.sha256(
                    evidence_path.read_text(encoding="utf-8").encode("utf-8")
                ).hexdigest(),
            }
        )
    canonical = json.dumps(
        identities,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _load_mapping(root: Path, relative_path: str) -> dict[str, Any]:
    path = root / relative_path
    if path.suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"semantic evidence must be a mapping: {relative_path}")
    return payload


def build_current_audit_semantic_summary(
    root: Path,
    current: TechnicalDebtAuditRecord,
) -> dict[str, Any]:
    """Build the canonical headline summary from the pinned evidence surface."""
    missing = sorted(SEMANTIC_EVIDENCE_PATHS.difference(current.evidence_paths))
    if missing:
        raise ValueError(
            "current audit semantic evidence_paths are incomplete: "
            + ", ".join(missing)
        )

    modules = _load_mapping(root, "reports/quality/module-coverage-inventory.json").get(
        "summary"
    )
    gates = _load_mapping(root, "reports/quality/debt-governance-gates.json").get(
        "summary"
    )
    scorecard = _load_mapping(
        root, "reports/quality/architecture-quality-scorecard.json"
    )
    contracts = _load_mapping(root, "reports/quality/contract-coverage-matrix.json")
    waivers = _load_mapping(root, "configs/quality/constructor_waivers.yaml")
    if not isinstance(modules, dict) or not isinstance(gates, dict):
        raise ValueError("semantic evidence summaries must be mappings")
    statuses = modules.get("status_counts")
    metrics = scorecard.get("metrics")
    if not isinstance(statuses, dict) or not isinstance(metrics, dict):
        raise ValueError("semantic evidence status_counts/metrics must be mappings")

    return {
        "audit_id": current.audit_id,
        "audited_commit_sha": current.audited_commit_sha,
        "evidence_surface_sha256": current.evidence_surface_sha256,
        "metrics": {
            "architecture_integral_score": scorecard.get("integral_score"),
            "architecture_interpretation": scorecard.get("interpretation"),
            "constructor_waiver_count": len(waivers),
            "contract_coverage_schema": contracts.get("schema_version"),
            "debt_gate_count": gates.get("gate_count"),
            "debt_gate_fail_count": gates.get("fail_count"),
            "debt_gate_pass_count": gates.get("pass_count"),
            "debt_gate_warn_count": gates.get("warn_count"),
            "expired_compat_count": metrics.get("expired_compat_count"),
            "fully_covered_module_count": statuses.get("fully_covered"),
            "layer_violation_count": metrics.get("layer_violations"),
            "no_executable_lines_module_count": statuses.get("no_executable_lines"),
            "partially_covered_module_count": statuses.get("partially_covered"),
            "source_module_count": modules.get("source_module_count"),
            "sunset_compat_count": metrics.get("sunset_compat_count"),
            "transition_compat_count": metrics.get("transition_compat_count"),
            "twin_pair_count": metrics.get("twin_pair_count"),
            "uncovered_module_count": statuses.get("uncovered"),
            "unmeasured_module_count": statuses.get("unmeasured"),
        },
        "schema_version": "technical-debt-audit-summary-v1",
    }


def render_current_audit_semantic_summary(summary: dict[str, Any]) -> str:
    """Render a deterministic machine-readable report block."""
    payload = json.dumps(summary, indent=2, sort_keys=True)
    return f"{SEMANTIC_SUMMARY_START}\n{payload}\n{SEMANTIC_SUMMARY_END}"


def _parse_report_semantic_summary(report: str) -> dict[str, Any]:
    start = report.find(SEMANTIC_SUMMARY_START)
    if start < 0:
        raise ValueError("current audit is missing semantic summary")
    payload_start = start + len(SEMANTIC_SUMMARY_START)
    end = report.find(SEMANTIC_SUMMARY_END, payload_start)
    if end < 0:
        raise ValueError("current audit semantic summary is unterminated")
    try:
        payload = json.loads(report[payload_start:end])
    except json.JSONDecodeError as exc:
        raise ValueError("current audit semantic summary is invalid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("current audit semantic summary must be a mapping")
    return payload


def _headline_markers(summary: dict[str, Any]) -> tuple[str, ...]:
    metrics = summary["metrics"]
    module_total = sum(
        metrics[key]
        for key in (
            "fully_covered_module_count",
            "partially_covered_module_count",
            "no_executable_lines_module_count",
            "uncovered_module_count",
            "unmeasured_module_count",
        )
    )
    return (
        f"Debt-governance gates: **{metrics['debt_gate_pass_count']} pass / "
        f"{metrics['debt_gate_fail_count']} fail**",
        f"Architecture quality integral score: **{metrics['architecture_integral_score']}** "
        f"(`{metrics['architecture_interpretation']}`)",
        f"source_module_count: **{metrics['source_module_count']}**",
        f"fully_covered: **{metrics['fully_covered_module_count']}**",
        f"partially_covered: **{metrics['partially_covered_module_count']}**",
        f"no_executable_lines: **{metrics['no_executable_lines_module_count']}**",
        f"uncovered: **{metrics['uncovered_module_count']}**",
        f"unmeasured: **{metrics['unmeasured_module_count']}**",
        f"= {module_total} == source_module_count",
        f"Contract coverage matrix schema: **{metrics['contract_coverage_schema']}**",
        f"Constructor waivers (shrink-only inventory): "
        f"**{metrics['constructor_waiver_count']}** entries",
        "Compatibility transition/sunset/expired: "
        f"**{metrics['transition_compat_count']}/{metrics['sunset_compat_count']}/"
        f"{metrics['expired_compat_count']}**; twin pairs: "
        f"**{metrics['twin_pair_count']}**",
        f"Layer violations: **{metrics['layer_violation_count']}**",
    )


def _validate_current_report_semantics(root: Path, current: Any) -> list[str]:
    report_path = root / current.report_path
    if not report_path.is_file():
        return []
    try:
        expected = build_current_audit_semantic_summary(root, current)
        actual = _parse_report_semantic_summary(report_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        return [str(exc)]
    issues: list[str] = []
    if actual != expected:
        issues.append("current audit semantic summary is stale")
    report = report_path.read_text(encoding="utf-8")
    for marker in _headline_markers(expected):
        if marker not in report:
            issues.append(f"current audit headline metric is stale: {marker}")
    return issues


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


def _validate_record_paths(
    root: Path,
    records: Sequence[Any],
) -> list[str]:
    issues: list[str] = []
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
    return issues


def _validate_current_commit(
    root: Path,
    current: Any,
    *,
    verify_git_commit: bool,
) -> list[str]:
    issues: list[str] = []
    if current.report_path.startswith("docs/99-archive/"):
        issues.append("current audit must not live in docs/99-archive")
    if current.audited_commit_sha is None or not SHA_PATTERN.fullmatch(
        current.audited_commit_sha
    ):
        issues.append("current audit requires an exact audited_commit_sha")
    elif verify_git_commit and not _commit_exists(root, current.audited_commit_sha):
        issues.append("current audited_commit_sha is not a local Git commit")
    return issues


def _validate_current_evidence_hash(root: Path, current: Any) -> list[str]:
    if current.evidence_surface_sha256 is None or not SHA256_PATTERN.fullmatch(
        current.evidence_surface_sha256
    ):
        return ["current audit requires evidence_surface_sha256"]
    try:
        actual_hash = compute_evidence_surface_sha256(root, current.evidence_paths)
    except (OSError, ValueError) as exc:
        return [str(exc)]
    if actual_hash != current.evidence_surface_sha256:
        return ["current audit evidence_surface_sha256 is stale"]
    return []


def _validate_current_report_markers(root: Path, current: Any) -> list[str]:
    report_path = root / current.report_path
    if not report_path.is_file():
        return []
    report = report_path.read_text(encoding="utf-8")
    issues: list[str] = []
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

    issues.extend(_validate_record_paths(root, records))
    issues.extend(
        _validate_current_commit(root, current, verify_git_commit=verify_git_commit)
    )
    issues.extend(_validate_current_evidence_hash(root, current))
    issues.extend(_validate_current_report_markers(root, current))
    issues.extend(_validate_current_report_semantics(root, current))
    return issues


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=_repo_root())
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY_PATH)
    parser.add_argument("--print-current", action="store_true")
    parser.add_argument("--print-evidence-hash", action="store_true")
    parser.add_argument("--print-semantic-summary", action="store_true")
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
    if args.print_semantic_summary:
        print(
            render_current_audit_semantic_summary(
                build_current_audit_semantic_summary(root, current)
            )
        )
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
