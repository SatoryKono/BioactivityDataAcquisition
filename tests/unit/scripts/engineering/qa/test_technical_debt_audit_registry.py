# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for SHA-pinned technical-debt audit lifecycle tooling."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.engineering.qa.technical_debt_audit_registry import (
    TechnicalDebtAuditRecord,
    build_current_audit_semantic_summary,
    compute_evidence_surface_sha256,
    render_current_audit_semantic_summary,
    resolve_current_technical_debt_audit,
    validate_technical_debt_audit_registry,
)

pytestmark = pytest.mark.unit


def _write_registry_fixture(root: Path) -> Path:
    quality = root / "reports/quality"
    quality.mkdir(parents=True)
    (quality / "module-coverage-inventory.json").write_text(
        '{"summary":{"source_module_count":3,"status_counts":'
        '{"fully_covered":1,"partially_covered":1,"no_executable_lines":1,'
        '"uncovered":0,"unmeasured":0}}}\n',
        encoding="utf-8",
    )
    (quality / "debt-governance-gates.json").write_text(
        '{"summary":{"gate_count":2,"pass_count":2,"fail_count":0,"warn_count":0}}\n',
        encoding="utf-8",
    )
    (quality / "architecture-quality-scorecard.json").write_text(
        '{"integral_score":9.5,"interpretation":"good",'
        '"metrics":{"transition_compat_count":0,"sunset_compat_count":0,'
        '"expired_compat_count":0,"twin_pair_count":0,"layer_violations":0}}\n',
        encoding="utf-8",
    )
    (quality / "contract-coverage-matrix.json").write_text(
        '{"schema_version":"contract-v1"}\n',
        encoding="utf-8",
    )
    waivers = root / "configs/quality/constructor_waivers.yaml"
    waivers.parent.mkdir(parents=True)
    waivers.write_text("KnownAggregate:\n  max_args: 8\n", encoding="utf-8")
    evidence_paths = [
        "configs/quality/constructor_waivers.yaml",
        "reports/quality/architecture-quality-scorecard.json",
        "reports/quality/contract-coverage-matrix.json",
        "reports/quality/debt-governance-gates.json",
        "reports/quality/module-coverage-inventory.json",
    ]
    evidence_hash = compute_evidence_surface_sha256(
        root,
        evidence_paths,
    )
    record = TechnicalDebtAuditRecord(
        audit_id="audit-current",
        status="current",
        report_path="reports/quality/current.md",
        audited_commit_sha="1111111111111111111111111111111111111111",
        evidence_surface_sha256=evidence_hash,
        evidence_paths=tuple(evidence_paths),
    )
    semantic_summary = build_current_audit_semantic_summary(root, record)
    current_report = quality / "current.md"
    current_report.write_text(
        "Lifecycle status: current\n"
        "Audited commit SHA: `1111111111111111111111111111111111111111`\n"
        f"Evidence surface SHA-256: `{evidence_hash}`\n"
        "Debt-governance gates: **2 pass / 0 fail**\n"
        "Architecture quality integral score: **9.5** (`good`)\n"
        "source_module_count: **3**\n"
        "fully_covered: **1**\n"
        "partially_covered: **1**\n"
        "no_executable_lines: **1**\n"
        "uncovered: **0**\n"
        "unmeasured: **0**\n"
        "= 3 == source_module_count\n"
        "Contract coverage matrix schema: **contract-v1**\n"
        "Constructor waivers (shrink-only inventory): **1** entries\n"
        "Compatibility transition/sunset/expired: **0/0/0**; twin pairs: **0**\n"
        "Layer violations: **0**\n"
        f"{render_current_audit_semantic_summary(semantic_summary)}\n",
        encoding="utf-8",
    )
    archived_report = root / "docs/99-archive/reports/quality/old.md"
    archived_report.parent.mkdir(parents=True)
    archived_report.write_text("Historical audit.\n", encoding="utf-8")
    registry = root / "configs/quality/technical_debt_audit_registry.yaml"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry_payload = (
        "version: 1\n"
        "current_audit_id: audit-current\n"
        "audits:\n"
        "  - id: audit-current\n"
        "    status: current\n"
        "    report_path: reports/quality/current.md\n"
        "    audited_commit_sha: '1111111111111111111111111111111111111111'\n"
        f"    evidence_surface_sha256: '{evidence_hash}'\n"
        "    evidence_paths:\n"
        + "".join(f"      - {path}\n" for path in evidence_paths)
        + "  - id: audit-old\n"
        "    status: superseded\n"
        "    report_path: docs/99-archive/reports/quality/old.md\n"
    )
    registry.write_text(
        registry_payload,
        encoding="utf-8",
    )
    return registry.relative_to(root)


def test_registry_resolves_exactly_one_current_audit(tmp_path: Path) -> None:
    registry = _write_registry_fixture(tmp_path)

    current = resolve_current_technical_debt_audit(tmp_path, registry)
    issues = validate_technical_debt_audit_registry(
        tmp_path,
        registry,
        verify_git_commit=False,
    )

    assert current == tmp_path / "reports/quality/current.md"
    assert issues == []


def test_registry_detects_evidence_content_drift(tmp_path: Path) -> None:
    registry = _write_registry_fixture(tmp_path)
    (tmp_path / "reports/quality/contract-coverage-matrix.json").write_text(
        '{"schema_version":"contract-v2"}\n',
        encoding="utf-8",
    )

    issues = validate_technical_debt_audit_registry(
        tmp_path,
        registry,
        verify_git_commit=False,
    )

    assert "current audit evidence_surface_sha256 is stale" in issues


def test_registry_detects_semantic_summary_drift(tmp_path: Path) -> None:
    registry = _write_registry_fixture(tmp_path)
    report = tmp_path / "reports/quality/current.md"
    report.write_text(
        report.read_text(encoding="utf-8").replace(
            '"source_module_count": 3',
            '"source_module_count": 4',
        ),
        encoding="utf-8",
    )

    issues = validate_technical_debt_audit_registry(
        tmp_path,
        registry,
        verify_git_commit=False,
    )

    assert "current audit semantic summary is stale" in issues


def test_registry_detects_human_headline_drift(tmp_path: Path) -> None:
    registry = _write_registry_fixture(tmp_path)
    report = tmp_path / "reports/quality/current.md"
    report.write_text(
        report.read_text(encoding="utf-8").replace(
            "source_module_count: **3**",
            "source_module_count: **4**",
        ),
        encoding="utf-8",
    )

    issues = validate_technical_debt_audit_registry(
        tmp_path,
        registry,
        verify_git_commit=False,
    )

    assert any(
        issue.startswith("current audit headline metric is stale:") for issue in issues
    )


def test_evidence_hash_is_independent_of_checkout_line_endings(
    tmp_path: Path,
) -> None:
    evidence = tmp_path / "reports/quality/evidence.json"
    evidence.parent.mkdir(parents=True)
    evidence.write_bytes(b'{\r\n  "value": 1\r\n}\r\n')
    windows_hash = compute_evidence_surface_sha256(
        tmp_path,
        ["reports/quality/evidence.json"],
    )

    evidence.write_bytes(b'{\n  "value": 1\n}\n')

    assert (
        compute_evidence_surface_sha256(
            tmp_path,
            ["reports/quality/evidence.json"],
        )
        == windows_hash
    )
