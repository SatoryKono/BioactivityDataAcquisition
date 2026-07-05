"""Unit tests for reports/quality TTL guardrail."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.engineering.repo import check_reports_quality_ttl as module
from scripts.ops.support.repo.cleanup_repository import ReportsWorkspaceEvidence


pytestmark = pytest.mark.unit


def _row(
    path: str,
    *,
    ttl_days: int | None,
    age_days: int | None,
    ttl_expired: bool | None,
    owner: str | None = "Engineering / Quality",
    entry_id: str | None = "reports_quality_pretest_guardrails_history",
) -> ReportsWorkspaceEvidence:
    return ReportsWorkspaceEvidence(
        path=Path(path),
        classification="PRUNE_CANDIDATE" if ttl_expired else "RETAIN",
        tracked=False,
        exists=True,
        has_history=False,
        reference_hits=0,
        generator=None,
        commit_policy=None,
        reason="test fixture",
        retention_entry_id=entry_id,
        retention_owner=owner,
        retention_ttl_days=ttl_days,
        age_days=age_days,
        ttl_expired=ttl_expired,
    )


def test_collect_expired_reports_quality_ttl_filters_only_expired_quality_rows(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        module,
        "collect_reports_workspace_evidence",
        lambda repo_root: [
            _row(
                "reports/quality/pretest_guardrails_20260602_062619.json",
                ttl_days=30,
                age_days=31,
                ttl_expired=True,
            ),
            _row(
                "reports/quality/pretest_guardrails_20260703_062619.json",
                ttl_days=30,
                age_days=0,
                ttl_expired=False,
            ),
            _row(
                "reports/observability/runtime_cardinality_inventory.json",
                ttl_days=None,
                age_days=None,
                ttl_expired=None,
                owner=None,
                entry_id=None,
            ),
        ],
    )

    rows = module.collect_expired_reports_quality_ttl(tmp_path)

    assert [row.rel_path for row in rows] == [
        "reports/quality/pretest_guardrails_20260602_062619.json"
    ]


def test_main_returns_zero_when_no_expired_rows(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        module, "collect_expired_reports_quality_ttl", lambda repo_root: []
    )

    rc = module.main(["--repo-root", str(tmp_path)])

    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "OK: reports/quality TTL guardrail passed.\n"
    assert captured.err == ""


def test_main_reports_expired_rows(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        module,
        "collect_expired_reports_quality_ttl",
        lambda repo_root: [
            _row(
                "reports/quality/pretest_guardrails_20260602_062619.json",
                ttl_days=30,
                age_days=31,
                ttl_expired=True,
            )
        ],
    )

    rc = module.main(["--repo-root", str(tmp_path)])

    captured = capsys.readouterr()
    assert rc == 1
    assert captured.out == ""
    assert "expired reports/quality TTL artifacts detected" in captured.err
    assert "pretest_guardrails_20260602_062619.json" in captured.err
    assert "age_days=31 ttl_days=30" in captured.err
