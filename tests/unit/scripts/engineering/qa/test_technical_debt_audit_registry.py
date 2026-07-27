"""Tests for SHA-pinned technical-debt audit lifecycle tooling."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.engineering.qa.technical_debt_audit_registry import (
    compute_evidence_surface_sha256,
    resolve_current_technical_debt_audit,
    validate_technical_debt_audit_registry,
)

pytestmark = pytest.mark.unit


def _write_registry_fixture(root: Path) -> Path:
    evidence = root / "reports/quality/evidence.json"
    evidence.parent.mkdir(parents=True)
    evidence.write_text('{"value":1}\n', encoding="utf-8")
    current_report = root / "reports/quality/current.md"
    evidence_hash = compute_evidence_surface_sha256(
        root,
        ["reports/quality/evidence.json"],
    )
    current_report.write_text(
        "Lifecycle status: current\n"
        "Audited commit SHA: `1111111111111111111111111111111111111111`\n"
        f"Evidence surface SHA-256: `{evidence_hash}`\n",
        encoding="utf-8",
    )
    archived_report = root / "docs/99-archive/reports/quality/old.md"
    archived_report.parent.mkdir(parents=True)
    archived_report.write_text("Historical audit.\n", encoding="utf-8")
    registry = root / "configs/quality/technical_debt_audit_registry.yaml"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        "version: 1\n"
        "current_audit_id: audit-current\n"
        "audits:\n"
        "  - id: audit-current\n"
        "    status: current\n"
        "    report_path: reports/quality/current.md\n"
        "    audited_commit_sha: '1111111111111111111111111111111111111111'\n"
        f"    evidence_surface_sha256: '{evidence_hash}'\n"
        "    evidence_paths:\n"
        "      - reports/quality/evidence.json\n"
        "  - id: audit-old\n"
        "    status: superseded\n"
        "    report_path: docs/99-archive/reports/quality/old.md\n",
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
    (tmp_path / "reports/quality/evidence.json").write_text(
        '{"value":2}\n',
        encoding="utf-8",
    )

    issues = validate_technical_debt_audit_registry(
        tmp_path,
        registry,
        verify_git_commit=False,
    )

    assert "current audit evidence_surface_sha256 is stale" in issues


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
