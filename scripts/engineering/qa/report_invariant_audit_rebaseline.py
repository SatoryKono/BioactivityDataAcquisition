#!/usr/bin/env python3
"""Generate/check the June 2026 invariant-audit rebaseline matrix."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_JSON_OUTPUT = (
    PROJECT_ROOT / "reports" / "quality" / "invariant-audit-rebaseline-2026-06-19.json"
)
DEFAULT_MD_OUTPUT = (
    PROJECT_ROOT / "reports" / "quality" / "invariant-audit-rebaseline-2026-06-19.md"
)

ALLOWED_CLASSIFICATIONS = frozenset(
    {
        "implemented",
        "stale-evidence",
        "duplicate-existing-issue",
        "needs-follow-up",
        "not-applicable",
    }
)
REBASELINE_ISSUES = ("#5461", "#5462", "#5463")
ISSUE_5451 = "#5451"
ISSUE_5447 = "#5447"
ISSUE_5450 = "#5450"


@dataclass(frozen=True)
class FindingRebaseline:
    """One row in the stale-audit rebaseline matrix."""

    finding_id: str
    original_severity: str
    theme: str
    original_claim: str
    cited_paths: tuple[str, ...]
    classification: str
    current_source_anchors: tuple[str, ...]
    current_test_anchors: tuple[str, ...]
    existing_issue_anchors: tuple[str, ...]
    rationale: str


FINDINGS: tuple[FindingRebaseline, ...] = (
    FindingRebaseline(
        finding_id="F01",
        original_severity="CRITICAL",
        theme="Batch FSM lifecycle",
        original_claim="Batch FSM state machine was reported missing.",
        cited_paths=("src/bioetl/domain/batch.py", "tests/unit/test_batch.py"),
        classification="implemented",
        current_source_anchors=(
            "src/bioetl/application/core/lifecycle/batch_fsm.py",
            "src/bioetl/domain/aggregates/_batch_lifecycle.py",
        ),
        current_test_anchors=("tests/unit/application/core/test_batch_fsm.py",),
        existing_issue_anchors=("#5444", ISSUE_5451),
        rationale=(
            "The original paths are stale; current Batch lifecycle/FSM guards "
            "exist and are covered by focused transition tests."
        ),
    ),
    FindingRebaseline(
        finding_id="F02",
        original_severity="CRITICAL",
        theme="PipelineRun completion invariant",
        original_claim="PipelineRun COMPLETED was reported as unguarded.",
        cited_paths=("src/bioetl/domain/pipeline.py", "tests/unit/test_pipeline.py"),
        classification="implemented",
        current_source_anchors=(
            "src/bioetl/domain/aggregates/pipeline_run.py",
            "src/bioetl/domain/aggregates/_pipeline_run_mixins.py",
        ),
        current_test_anchors=(
            "tests/unit/domain/aggregates/test_pipeline_run.py",
            "tests/unit/domain/aggregates/test_pipeline_run_invariant_properties.py",
        ),
        existing_issue_anchors=("#5443", ISSUE_5451),
        rationale=(
            "The aggregate completion path checks recorded stages before "
            "COMPLETED and the stale top-level pipeline path is absent."
        ),
    ),
    FindingRebaseline(
        finding_id="F03",
        original_severity="CRITICAL",
        theme="Sanctioned HTTP client usage",
        original_claim="Direct HTTP calls were reported outside UnifiedHTTPClient.",
        cited_paths=(
            "src/bioetl/infrastructure/chembl_client.py",
            "src/bioetl/infrastructure/pubchem_client.py",
        ),
        classification="implemented",
        current_source_anchors=("src/bioetl/infrastructure/adapters/http/client.py",),
        current_test_anchors=(
            "tests/architecture/test_adapter_http_client_enforcement.py",
            "tests/unit/infrastructure/adapters/http/test_http_client.py",
        ),
        existing_issue_anchors=("#5417", ISSUE_5447, ISSUE_5451),
        rationale=(
            "Legacy client paths cited by the audit are absent; runtime adapters "
            "are guarded against direct requests/httpx client construction."
        ),
    ),
    FindingRebaseline(
        finding_id="F04",
        original_severity="HIGH",
        theme="Quarantine payload immutability",
        original_claim="Quarantine payloads were reported mutable.",
        cited_paths=("src/bioetl/domain/quarantine.py",),
        classification="implemented",
        current_source_anchors=(
            "src/bioetl/domain/aggregates/quarantine_entry.py",
            "src/bioetl/domain/aggregates/_quarantine_value_objects.py",
            "src/bioetl/domain/ports/quality/quarantine.py",
        ),
        current_test_anchors=(
            "tests/architecture/test_quarantine_immutability.py",
            "tests/unit/domain/aggregates/test_quarantine_entry.py",
        ),
        existing_issue_anchors=("#5420", "#5445", ISSUE_5451),
        rationale=(
            "The cited module is stale; current quarantine aggregate/port "
            "surfaces have explicit immutability guards and tests."
        ),
    ),
    FindingRebaseline(
        finding_id="F05",
        original_severity="HIGH",
        theme="META_FIELDS content-hash exclusion",
        original_claim="META_FIELDS exclusion from content hash was reported missing.",
        cited_paths=("src/bioetl/domain/hashing.py",),
        classification="implemented",
        current_source_anchors=(
            "src/bioetl/domain/constants.py",
            "src/bioetl/domain/transformations/hashing.py",
        ),
        current_test_anchors=(
            "tests/unit/contracts/test_content_hash_contract.py",
            "tests/contract/test_content_hash_schema_drift_contract.py",
        ),
        existing_issue_anchors=(ISSUE_5447, ISSUE_5451),
        rationale=(
            "Hashing moved under domain transformations; META_FIELDS are "
            "centralized and schema-drift/content-hash contracts cover exclusion."
        ),
    ),
    FindingRebaseline(
        finding_id="F06",
        original_severity="HIGH",
        theme="Observability canonical labels and run identity",
        original_claim="Observability events were reported without canonical labels.",
        cited_paths=("src/bioetl/infrastructure/observability.py",),
        classification="implemented",
        current_source_anchors=(
            "src/bioetl/domain/_observability_contract_core.py",
            "src/bioetl/domain/observability_contract.py",
        ),
        current_test_anchors=(
            "tests/unit/domain/test_observability_contract.py",
            "tests/architecture/test_observability_signal_governance.py",
            "tests/architecture/test_observability_metric_governance.py",
        ),
        existing_issue_anchors=("#5446", ISSUE_5451),
        rationale=(
            "The current contract is domain-owned and enforces run identity and "
            "canonical labels through dedicated unit and architecture tests."
        ),
    ),
    FindingRebaseline(
        finding_id="F07",
        original_severity="HIGH",
        theme="Gold strict validation",
        original_claim="Gold layer strict validation was reported absent.",
        cited_paths=("src/bioetl/domain/medallion.py", "tests/unit/test_medallion.py"),
        classification="implemented",
        current_source_anchors=(
            "src/bioetl/infrastructure/storage/gold/validation_mixin.py",
            "src/bioetl/domain/contracts/gold/_strict_gold_contract_schema.py",
        ),
        current_test_anchors=(
            "tests/architecture/test_gold_strict_validation_policy.py",
            "tests/contract/test_gold_schema_strict_violations.py",
            "tests/unit/storage/gold/test_strict_validation.py",
        ),
        existing_issue_anchors=("#5448", ISSUE_5451),
        rationale=(
            "The top-level medallion path is stale for this claim; strict Gold "
            "schema validation is enforced through storage and contract tests."
        ),
    ),
    FindingRebaseline(
        finding_id="F08",
        original_severity="MEDIUM",
        theme="Retry determinism",
        original_claim="Retry delays were reported as non-deterministic.",
        cited_paths=("src/bioetl/infrastructure/http_client.py",),
        classification="implemented",
        current_source_anchors=(
            "src/bioetl/domain/resilience.py",
            "src/bioetl/infrastructure/adapters/http/client_retry_mixin.py",
        ),
        current_test_anchors=(
            "tests/unit/infrastructure/adapters/http/test_retry_config.py",
            "tests/unit/infrastructure/adapters/http/test_client_retry_mixin.py",
        ),
        existing_issue_anchors=(ISSUE_5447, ISSUE_5451),
        rationale=(
            "RetryConfig uses deterministic hash-based jitter; tests cover "
            "same-input stability and cross-process stability."
        ),
    ),
    FindingRebaseline(
        finding_id="F09",
        original_severity="MEDIUM",
        theme="Checkpoint resume anchors",
        original_claim="Checkpoint resume contract/config/runtime anchors were reported missing.",
        cited_paths=(),
        classification="implemented",
        current_source_anchors=(
            "src/bioetl/application/services/checkpoint_compatibility_service.py",
            "src/bioetl/application/services/control_plane/manifest/diagnostics/resume_contract.py",
            "src/bioetl/application/composite/checkpoint/_anchor_context.py",
        ),
        current_test_anchors=(
            "tests/integration/ci/test_reproducibility_contract_manifest_diff.py",
            "tests/unit/application/composite/checkpoint/test_checkpoint_service.py",
        ),
        existing_issue_anchors=("#5449", ISSUE_5451),
        rationale=(
            "Resume compatibility and composite checkpoint anchors are current "
            "control-plane surfaces with strict mismatch tests."
        ),
    ),
    FindingRebaseline(
        finding_id="F10",
        original_severity="MEDIUM",
        theme="Business logic placement in infrastructure",
        original_claim="Business logic was reported in provider infrastructure clients.",
        cited_paths=(
            "src/bioetl/infrastructure/chembl_client.py",
            "src/bioetl/infrastructure/pubchem_client.py",
        ),
        classification="duplicate-existing-issue",
        current_source_anchors=(
            "src/bioetl/infrastructure/adapters/chembl/",
            "src/bioetl/infrastructure/adapters/pubchem/",
        ),
        current_test_anchors=(
            "tests/architecture/test_strict_architecture_contracts.py",
            "tests/architecture/test_adapter_contracts.py",
        ),
        existing_issue_anchors=(ISSUE_5450, ISSUE_5451),
        rationale=(
            "The audit evidence used legacy paths and broad conditional-count "
            "heuristics. Current layer-boundary/business-placement remediation "
            "is already tracked by closed architecture issues."
        ),
    ),
    FindingRebaseline(
        finding_id="F11",
        original_severity="MEDIUM",
        theme="Composite merge determinism",
        original_claim="Composite merge determinism tests were reported missing.",
        cited_paths=("src/bioetl/domain/composite.py", "tests/unit/test_composite.py"),
        classification="implemented",
        current_source_anchors=(
            "src/bioetl/domain/composite/",
            "src/bioetl/application/composite/merger.py",
        ),
        current_test_anchors=(
            "tests/contract/test_composite_merge_golden.py",
            "tests/unit/application/composite/test_merger.py",
            "tests/unit/application/composite/test_composite_merge_conflicts.py",
        ),
        existing_issue_anchors=("#5449", ISSUE_5451),
        rationale=(
            "Composite code is package-based rather than a single domain file; "
            "golden and unit tests cover stable ordering/conflict behavior."
        ),
    ),
    FindingRebaseline(
        finding_id="F12",
        original_severity="MEDIUM",
        theme="Schema drift detection",
        original_claim="Schema drift detection was reported absent.",
        cited_paths=(),
        classification="implemented",
        current_source_anchors=(
            "src/bioetl/domain/transformations/drift.py",
            "src/bioetl/infrastructure/storage/silver/schema_drift_operations.py",
        ),
        current_test_anchors=(
            "tests/e2e/test_pipeline_with_schema_drift_e2e.py",
            "tests/contract/silver_schemas/test_selected_pipeline_schema_drift.py",
            "tests/contract/test_content_hash_schema_drift_contract.py",
        ),
        existing_issue_anchors=("#5448", ISSUE_5451),
        rationale=(
            "Schema drift is implemented and exercised by Silver schema and "
            "pipeline drift tests."
        ),
    ),
    FindingRebaseline(
        finding_id="F13",
        original_severity="MEDIUM",
        theme="Infrastructure imports application",
        original_claim="Infrastructure-to-application imports were reported as potential violations.",
        cited_paths=("src/bioetl/infrastructure/**",),
        classification="implemented",
        current_source_anchors=("src/bioetl/infrastructure/",),
        current_test_anchors=(
            "tests/architecture/test_strict_architecture_contracts.py",
        ),
        existing_issue_anchors=(ISSUE_5450, ISSUE_5451),
        rationale=(
            "Current strict architecture contracts include an infrastructure "
            "boundary test forbidding application imports outside sanctioned seams."
        ),
    ),
    FindingRebaseline(
        finding_id="F14",
        original_severity="MEDIUM",
        theme="Critical-path integration coverage",
        original_claim="Critical-path integration coverage was reported missing.",
        cited_paths=("tests/integration",),
        classification="duplicate-existing-issue",
        current_source_anchors=("tests/integration/",),
        current_test_anchors=(
            "tests/integration/ci/test_reproducibility_contract_manifest_diff.py",
            "tests/integration/composite/test_composite_cross_validation.py",
            "tests/integration/infrastructure/storage/test_gold_writer_versioning.py",
        ),
        existing_issue_anchors=(ISSUE_5450, ISSUE_5451),
        rationale=(
            "The broad integration-coverage concern was already part of the "
            "closed architecture gap wave; the current repo has targeted "
            "critical-path integration tests."
        ),
    ),
    FindingRebaseline(
        finding_id="F15",
        original_severity="LOW",
        theme="Governance audit trail",
        original_claim="Immutable audit trail/governance logging was reported incomplete.",
        cited_paths=(),
        classification="implemented",
        current_source_anchors=(
            "src/bioetl/domain/control_plane/run_ledger.py",
            "src/bioetl/domain/control_plane/workflow_ledger.py",
            "src/bioetl/infrastructure/control_plane/file_run_ledger_store.py",
        ),
        current_test_anchors=(
            "tests/unit/application/services/test_run_ledger_service.py",
            "tests/unit/application/core/test_runner.py",
            "tests/unit/application/composite/test_runner.py",
        ),
        existing_issue_anchors=(ISSUE_5450, ISSUE_5451),
        rationale=(
            "Run/workflow ledger surfaces and runner ledger tests provide the "
            "current governance audit trail anchors."
        ),
    ),
    FindingRebaseline(
        finding_id="F16",
        original_severity="LOW",
        theme="Dead abstractions",
        original_claim="Repository interfaces were reported as potential dead abstractions.",
        cited_paths=("src/bioetl/domain/ports/",),
        classification="implemented",
        current_source_anchors=(
            "reports/quality/dead-code-inventory.json",
            "reports/quality/port-adapter-factory-coverage.json",
        ),
        current_test_anchors=(
            "tests/architecture/test_port_contracts.py",
            "tests/architecture/test_retirement_candidate_triage.py",
            "tests/architecture/test_source_test_facade_ownership.py",
        ),
        existing_issue_anchors=(ISSUE_5450, ISSUE_5451),
        rationale=(
            "Dead-code/port-adapter coverage inventories are the current "
            "governance surfaces for abstraction review; the audit did not cite "
            "a concrete live removable abstraction."
        ),
    ),
    FindingRebaseline(
        finding_id="F17",
        original_severity="LOW",
        theme="Compatibility shim lifecycle",
        original_claim="Compatibility shims were reported as lacking a removal process.",
        cited_paths=(),
        classification="implemented",
        current_source_anchors=(
            "configs/quality/config_compatibility_registry.yaml",
            "configs/quality/compatibility_facade_inventory.yaml",
            "reports/quality/compatibility-importer-census.json",
        ),
        current_test_anchors=(
            "tests/architecture/test_config_transition_registry.py",
            "tests/architecture/test_public_facade_inventory.py",
            "tests/architecture/test_public_surface_importer_census_governance.py",
        ),
        existing_issue_anchors=("#5410", "#5435", ISSUE_5450, ISSUE_5451),
        rationale=(
            "Compatibility shape/facade registries, importer census, and ratchet "
            "guards already define bounded lifecycle and no-growth behavior."
        ),
    ),
)


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _path_status(repo_root: Path, relative_path: str) -> dict[str, object]:
    if relative_path.endswith("/**"):
        base = relative_path[:-3]
        exists = (repo_root / base).exists()
    else:
        exists = (repo_root / relative_path).exists()
    return {"path": relative_path, "exists": exists}


def _anchor_exists(repo_root: Path, relative_path: str) -> bool:
    return (repo_root / relative_path).exists()


def _finding_to_row(finding: FindingRebaseline, repo_root: Path) -> dict[str, object]:
    return {
        "finding_id": finding.finding_id,
        "original_severity": finding.original_severity,
        "theme": finding.theme,
        "original_claim": finding.original_claim,
        "cited_paths": [_path_status(repo_root, path) for path in finding.cited_paths],
        "classification": finding.classification,
        "current_source_anchors": list(finding.current_source_anchors),
        "current_test_anchors": list(finding.current_test_anchors),
        "existing_issue_anchors": list(finding.existing_issue_anchors),
        "rationale": finding.rationale,
    }


def _severity_counts(rows: list[dict[str, object]]) -> dict[str, int]:
    return dict(sorted(Counter(str(row["original_severity"]) for row in rows).items()))


def _classification_counts(rows: list[dict[str, object]]) -> dict[str, int]:
    return dict(sorted(Counter(str(row["classification"]) for row in rows).items()))


def _missing_cited_paths(rows: list[dict[str, object]]) -> list[str]:
    missing: list[str] = []
    for row in rows:
        cited_paths = row["cited_paths"]
        if not isinstance(cited_paths, list):
            continue
        for status in cited_paths:
            assert isinstance(status, dict)
            if not status["exists"]:
                missing.append(str(status["path"]))
    return sorted(set(missing))


def build_invariant_audit_rebaseline(repo_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """Build the invariant-audit rebaseline report from the curated matrix."""
    resolved_root = repo_root.resolve()
    rows = [_finding_to_row(finding, resolved_root) for finding in FINDINGS]
    missing_paths = _missing_cited_paths(rows)
    return {
        "schema_version": 1,
        "policy_scope": "invariant_audit_rebaseline",
        "audit_source": "June 2026 invariant/determinism/replay-safety audit",
        "review_date": "2026-06-19",
        "repository": "SatoryKono/BioactivityDataAcquisition",
        "rebaseline_issues": list(REBASELINE_ISSUES),
        "summary": {
            "total_findings": len(rows),
            "severity_counts": _severity_counts(rows),
            "classification_counts": _classification_counts(rows),
            "missing_cited_path_count": len(missing_paths),
            "missing_cited_paths": missing_paths,
            "needs_follow_up_count": sum(
                1 for row in rows if row["classification"] == "needs-follow-up"
            ),
        },
        "gates": {
            "stale_path_gate": {
                "mode": "require_current_anchors_for_missing_cited_paths",
                "status": "pass",
            },
            "duplicate_issue_gate": {
                "mode": "require_existing_issue_anchor_or_current_evidence",
                "status": "pass",
            },
            "current_anchor_gate": {
                "mode": "require_existing_current_source_and_test_anchors",
                "status": "pass",
            },
        },
        "findings": rows,
    }


def _load_json(path: Path, *, root: Path | None = None) -> Any:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=root or REPO_ROOT)
    return json.loads(path.read_text(encoding="utf-8"))  # NOSONAR - path confined


def _issue_numbers_from_payload(payload: Any) -> set[str]:
    """Extract issue anchors from a local GitHub issue search/export payload."""
    if isinstance(payload, dict):
        if "items" in payload:
            return _issue_numbers_from_payload(payload["items"])
        if "issues" in payload:
            return _issue_numbers_from_payload(payload["issues"])
        value = payload.get("number") or payload.get("issue_number")
        if value is not None:
            return {f"#{int(value)}"}
        return set()
    if isinstance(payload, list):
        anchors: set[str] = set()
        for item in payload:
            anchors.update(_issue_numbers_from_payload(item))
        return anchors
    return set()


def _validate_current_anchors(
    row: dict[str, object],
    *,
    repo_root: Path,
) -> list[str]:
    violations: list[str] = []
    finding_id = str(row["finding_id"])
    source_anchor_values = row["current_source_anchors"]
    test_anchor_values = row["current_test_anchors"]
    source_anchors = (
        [str(path) for path in source_anchor_values]
        if isinstance(source_anchor_values, list)
        else []
    )
    test_anchors = (
        [str(path) for path in test_anchor_values]
        if isinstance(test_anchor_values, list)
        else []
    )
    if row["classification"] == "implemented":
        if not source_anchors:
            violations.append(f"{finding_id}: implemented row has no source anchors")
        if not test_anchors:
            violations.append(f"{finding_id}: implemented row has no test anchors")
    for path in source_anchors + test_anchors:
        if not _anchor_exists(repo_root, path):
            violations.append(f"{finding_id}: current anchor missing: {path}")
    return violations


def _validate_finding_identity(
    row: dict[str, Any],
    *,
    seen_ids: set[str],
) -> list[str]:
    violations: list[str] = []
    finding_id = str(row.get("finding_id", ""))
    if not finding_id:
        violations.append("finding row has empty finding_id")
    if finding_id in seen_ids:
        violations.append(f"duplicate finding_id: {finding_id}")
    seen_ids.add(finding_id)
    classification = str(row.get("classification", ""))
    if classification not in ALLOWED_CLASSIFICATIONS:
        violations.append(f"{finding_id}: invalid classification {classification!r}")
    return violations


def _missing_cited_paths_from(cited_paths: list[Any]) -> list[str]:
    return [
        str(path_status.get("path"))
        for path_status in cited_paths
        if isinstance(path_status, dict) and not bool(path_status.get("exists"))
    ]


def _shape_errors_for_anchors(finding_id: str, row: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    for key in (
        "current_source_anchors",
        "current_test_anchors",
        "existing_issue_anchors",
    ):
        if not isinstance(row.get(key), list):
            violations.append(f"{finding_id}: {key} must be a list")
    return violations


def _extract_finding_anchor_lists(
    finding_id: str,
    row: dict[str, Any],
) -> tuple[list[Any], list[Any], list[Any], list[str]] | None:
    cited_paths = row.get("cited_paths")
    if not isinstance(cited_paths, list):
        return None
    if _shape_errors_for_anchors(finding_id, row):
        return None
    source_anchors = row.get("current_source_anchors")
    test_anchors = row.get("current_test_anchors")
    issue_anchors = row.get("existing_issue_anchors")
    assert isinstance(source_anchors, list)
    assert isinstance(test_anchors, list)
    assert isinstance(issue_anchors, list)
    return (
        source_anchors,
        test_anchors,
        issue_anchors,
        _missing_cited_paths_from(cited_paths),
    )


def _anchor_presence_violations(
    *,
    finding_id: str,
    classification: str,
    source_anchors: list[Any],
    test_anchors: list[Any],
    issue_anchors: list[Any],
    missing_cited_paths: list[str],
) -> list[str]:
    violations: list[str] = []
    has_any_anchor = bool(source_anchors or test_anchors or issue_anchors)
    if missing_cited_paths and not has_any_anchor:
        violations.append(
            f"{finding_id}: missing cited paths require current anchors or issues"
        )
    needs_evidence = classification in {
        "duplicate-existing-issue",
        "stale-evidence",
    }
    if needs_evidence and not has_any_anchor:
        violations.append(
            f"{finding_id}: {classification} rows need duplicate or current evidence"
        )
    return violations


def _issue_anchor_violations(
    *,
    finding_id: str,
    issue_anchors: list[Any],
    known_issues: set[str] | None,
) -> list[str]:
    if known_issues is None:
        return []
    missing_issues = [
        str(anchor) for anchor in issue_anchors if str(anchor) not in known_issues
    ]
    if not missing_issues:
        return []
    return [
        f"{finding_id}: issue anchors missing from issue export: "
        + ", ".join(missing_issues)
    ]


def _validate_finding_anchors(
    row: dict[str, Any],
    *,
    repo_root: Path,
    known_issues: set[str] | None,
) -> list[str]:
    finding_id = str(row.get("finding_id", ""))
    classification = str(row.get("classification", ""))
    if not isinstance(row.get("cited_paths"), list):
        return [f"{finding_id}: cited_paths must be a list"]
    extracted = _extract_finding_anchor_lists(finding_id, row)
    if extracted is None:
        return _shape_errors_for_anchors(finding_id, row)
    source_anchors, test_anchors, issue_anchors, missing_cited_paths = extracted
    violations = _anchor_presence_violations(
        finding_id=finding_id,
        classification=classification,
        source_anchors=source_anchors,
        test_anchors=test_anchors,
        issue_anchors=issue_anchors,
        missing_cited_paths=missing_cited_paths,
    )
    violations.extend(_validate_current_anchors(row, repo_root=repo_root))
    violations.extend(
        _issue_anchor_violations(
            finding_id=finding_id,
            issue_anchors=issue_anchors,
            known_issues=known_issues,
        )
    )
    return violations


def validate_rebaseline_report(
    report: dict[str, Any],
    *,
    repo_root: Path = PROJECT_ROOT,
    github_issues_payload: Any | None = None,
) -> list[str]:
    """Return validation violations for an invariant-audit rebaseline report."""
    violations: list[str] = []
    rows = report.get("findings")
    if not isinstance(rows, list):
        return ["report findings must be a list"]
    if len(rows) != 17:
        violations.append(f"expected 17 findings, found {len(rows)}")

    seen_ids: set[str] = set()
    known_issues = (
        _issue_numbers_from_payload(github_issues_payload)
        if github_issues_payload is not None
        else None
    )
    for row in rows:
        if not isinstance(row, dict):
            violations.append("finding rows must be mappings")
            continue
        violations.extend(_validate_finding_identity(row, seen_ids=seen_ids))
        violations.extend(
            _validate_finding_anchors(
                row, repo_root=repo_root, known_issues=known_issues
            )
        )

    return violations


def render_markdown(report: dict[str, Any]) -> str:
    """Render a human-reviewable Markdown matrix."""
    summary = report["summary"]
    lines = [
        "# Invariant Audit Rebaseline: June 2026",
        "",
        f"Review date: `{report['review_date']}`",
        f"Repository: `{report['repository']}`",
        f"Tracker issues: {', '.join(report['rebaseline_issues'])}",
        "",
        "## Summary",
        "",
        f"- Total findings: `{summary['total_findings']}`",
        f"- Needs follow-up: `{summary['needs_follow_up_count']}`",
        f"- Missing cited paths rebaselined: `{summary['missing_cited_path_count']}`",
        f"- Classification counts: `{summary['classification_counts']}`",
        f"- Severity counts: `{summary['severity_counts']}`",
        "",
        "## Matrix",
        "",
        "| ID | Severity | Theme | Classification | Current anchors | Issues |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["findings"]:
        anchors = [
            *[f"`{path}`" for path in row["current_source_anchors"]],
            *[f"`{path}`" for path in row["current_test_anchors"]],
        ]
        lines.append(
            "| {finding_id} | {severity} | {theme} | `{classification}` | {anchors} | {issues} |".format(
                finding_id=row["finding_id"],
                severity=row["original_severity"],
                theme=row["theme"],
                classification=row["classification"],
                anchors="<br>".join(anchors),
                issues=", ".join(row["existing_issue_anchors"]),
            )
        )
    lines.extend(
        [
            "",
            "## Gate Interpretation",
            "",
            "- Missing original paths do not create implementation work unless "
            "current repo evidence also reproduces the gap.",
            "- Duplicate remediation themes must point to existing GitHub issue anchors before new issues are opened.",
            "- `needs-follow-up` rows must be backed by current source/test anchors and a GitHub issue.",
            "",
        ]
    )
    return "\n".join(lines)


def _check_file(path: Path, expected: str) -> bool:
    if not path.exists():
        print(f"[drift] missing: {path}")
        return False
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=REPO_ROOT)
    actual = path.read_text(encoding="utf-8")  # NOSONAR - path confined
    if actual == expected:
        return True
    print(f"[drift] mismatch: {path}")
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD_OUTPUT)
    parser.add_argument(
        "--github-issues-json",
        type=Path,
        help="Optional local GitHub issue search/export JSON for duplicate-anchor validation.",
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--update", action="store_true")
    args = parser.parse_args(argv)

    report = build_invariant_audit_rebaseline(args.repo_root)
    github_payload = (
        _load_json(args.github_issues_json) if args.github_issues_json else None
    )
    violations = validate_rebaseline_report(
        report,
        repo_root=args.repo_root,
        github_issues_payload=github_payload,
    )
    if violations:
        print("[invalid] invariant audit rebaseline report:")
        for violation in violations:
            print(f"- {violation}")
        return 1

    json_text = _canonical_json(report)
    markdown_text = render_markdown(report)
    if args.check:
        ok = _check_file(args.json_out, json_text)
        ok = _check_file(args.md_out, markdown_text) and ok
        return 0 if ok else 1
    if args.update:
        from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

        json_out = resolve_output_path(args.json_out, root=REPO_ROOT)
        md_out = resolve_output_path(args.md_out, root=REPO_ROOT)
        json_out.parent.mkdir(parents=True, exist_ok=True)
        md_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(  # NOSONAR - path confined by resolve_output_path
            json_text, encoding="utf-8"
        )
        md_out.write_text(  # NOSONAR - path confined by resolve_output_path
            markdown_text, encoding="utf-8"
        )
        return 0
    print(json_text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
