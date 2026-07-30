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
SEMANTIC_SUMMARY_PATTERN = re.compile(
    r"<!-- technical-debt-audit-summary: (?P<payload>\{.*\}) -->"
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
    records: list[Any],
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


def build_current_audit_semantic_summary(
    root: Path,
    current: TechnicalDebtAuditRecord,
) -> dict[str, Any]:
    """Build the report headline summary from the pinned evidence surface."""

    def load_evidence(relative_path: str) -> dict[str, Any]:
        if relative_path not in current.evidence_paths:
            raise ValueError(f"semantic audit evidence is not pinned: {relative_path}")
        payload = json.loads((root / relative_path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(
                f"semantic audit evidence must be a mapping: {relative_path}"
            )
        return payload

    coverage = load_evidence("reports/quality/module-coverage-inventory.json")
    scorecard = load_evidence("reports/quality/architecture-quality-scorecard.json")
    governance = load_evidence("reports/quality/debt-governance-gates.json")
    compatibility = load_evidence("reports/quality/compatibility-importer-census.json")
    coverage_summary = coverage["summary"]
    status_counts = coverage_summary["status_counts"]
    governance_summary = governance["summary"]
    scorecard_metrics = scorecard["metrics"]
    compatibility_summary = compatibility["summary"]
    highlighted_modules = {
        "bioetl.domain.composite.config",
        "bioetl.application.composite.merger",
    }
    retained_entrypoints = [
        {
            "module": row["module_name"],
            "src_importers": row["src_importer_count"],
            "test_importers": row["test_importer_count"],
        }
        for row in compatibility.get("retained_entrypoints", [])
        if row.get("module_name") in highlighted_modules
    ]
    return {
        "audit_id": current.audit_id,
        "audited_commit_sha": current.audited_commit_sha,
        "evidence_surface_sha256": current.evidence_surface_sha256,
        "debt_governance": {
            "gate_count": governance_summary["gate_count"],
            "pass_count": governance_summary["pass_count"],
            "fail_count": governance_summary["fail_count"],
        },
        "architecture_quality": {
            "integral_score": scorecard["integral_score"],
            "interpretation": scorecard["interpretation"],
        },
        "module_inventory": {
            "source_module_count": coverage_summary["source_module_count"],
            "fully_covered": status_counts["fully_covered"],
            "partially_covered": status_counts["partially_covered"],
            "no_executable_lines": status_counts["no_executable_lines"],
            "uncovered": status_counts["uncovered"],
            "unmeasured": status_counts["unmeasured"],
        },
        "compatibility": {
            "transition": scorecard_metrics["transition_compat_count"],
            "sunset": scorecard_metrics["sunset_compat_count"],
            "expired": scorecard_metrics["expired_compat_count"],
            "twin_pairs": compatibility_summary["twin_pair_count"],
            "retained_entrypoints": retained_entrypoints,
        },
        "layer_violations": scorecard_metrics["layer_violations"],
    }


def render_current_technical_debt_audit(
    root: Path,
    current: TechnicalDebtAuditRecord,
) -> str:
    """Render the current audit deterministically from its pinned evidence."""
    summary = build_current_audit_semantic_summary(root, current)
    module = summary["module_inventory"]
    module_total = sum(
        module[key]
        for key in (
            "fully_covered",
            "partially_covered",
            "no_executable_lines",
            "uncovered",
            "unmeasured",
        )
    )
    semantic_json = json.dumps(summary, sort_keys=True, separators=(",", ":"))
    governance = summary["debt_governance"]
    architecture = summary["architecture_quality"]
    compatibility = summary["compatibility"]
    retained_rows = "".join(
        f"| `{row['module']}` | {row['src_importers']} | {row['test_importers']} |\n"
        for row in compatibility["retained_entrypoints"]
    )
    return (
        "# Total Technical Debt Audit: GitHub main\n\n"
        "Lifecycle status: current\n\n"
        f"Audited commit SHA: `{current.audited_commit_sha}`\n\n"
        f"Evidence surface SHA-256: `{current.evidence_surface_sha256}`\n\n"
        f"Registry: {DEFAULT_REGISTRY_PATH.as_posix()}\n\n"
        f"<!-- technical-debt-audit-summary: {semantic_json} -->\n\n"
        "## Executive summary\n\n"
        f"1. Debt-governance gates: **{governance['pass_count']} pass / "
        f"{governance['fail_count']} fail** (`{governance['pass_count']}/"
        f"{governance['gate_count']}` debt-governance gates passing).\n"
        f"1. Architecture quality integral score: **{architecture['integral_score']}** "
        f"(`{architecture['interpretation']}`). Integral score "
        f"`{architecture['integral_score']}`.\n"
        "1. Module inventory:\n"
        f"   - source_module_count: **{module['source_module_count']}**\n"
        f"   - fully_covered: **{module['fully_covered']}**\n"
        f"   - partially_covered: **{module['partially_covered']}**\n"
        f"   - no_executable_lines: **{module['no_executable_lines']}**\n"
        f"   - uncovered: **{module['uncovered']}**\n"
        f"   - unmeasured: **{module['unmeasured']}**\n"
        f"   - check: status total = {module_total} == source_module_count\n"
        "1. Compatibility transition/sunset/expired: "
        f"**{compatibility['transition']}/{compatibility['sunset']}/"
        f"{compatibility['expired']}**; twin pairs: "
        f"**{compatibility['twin_pairs']}**.\n"
        f"1. Layer violations: **{summary['layer_violations']}**.\n\n"
        "## Evidence anchors\n\n"
        + "".join(f"- `{path}`\n" for path in current.evidence_paths)
        + "\n## Reproducibility\n\n"
        "```bash\n"
        "python -m scripts.engineering.qa validate-technical-debt-audit --json\n"
        "python -m scripts.engineering.qa validate-technical-debt-audit "
        "--update-current\n"
        "```\n\n"
        "## Compatibility retained entrypoints (importer census)\n\n"
        "| module | src importers | test importers |\n"
        "| --- | ---: | ---: |\n"
        f"{retained_rows}"
    )


def _validate_current_semantics(root: Path, current: Any) -> list[str]:
    report_path = root / current.report_path
    if not report_path.is_file():
        return []
    match = SEMANTIC_SUMMARY_PATTERN.search(report_path.read_text(encoding="utf-8"))
    if match is None:
        return ["current audit is missing machine-readable semantic summary"]
    try:
        actual = json.loads(match.group("payload"))
        expected = build_current_audit_semantic_summary(root, current)
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return [f"current audit semantic summary is invalid: {exc}"]
    if actual != expected:
        return ["current audit semantic summary is stale"]
    expected_report = render_current_technical_debt_audit(root, current)
    if report_path.read_text(encoding="utf-8") != expected_report:
        return ["current audit Markdown is not the deterministic rendered report"]
    return []


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
    issues.extend(_validate_current_semantics(root, current))
    return issues


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=_repo_root())
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY_PATH)
    parser.add_argument("--print-current", action="store_true")
    parser.add_argument("--print-evidence-hash", action="store_true")
    parser.add_argument("--update-current", action="store_true")
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
    if args.update_current:
        report_path = root / current.report_path
        report_path.write_text(
            render_current_technical_debt_audit(root, current),
            encoding="utf-8",
        )
        print(f"Updated technical-debt audit: {current.report_path}")
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
