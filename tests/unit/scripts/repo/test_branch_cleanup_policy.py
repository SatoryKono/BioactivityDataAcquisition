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
"""Unit tests for branch cleanup policy helpers."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from scripts.engineering.repo._branch_cleanup_policy import (
    build_branch_record,
    categorize_branch,
    is_phase1_garbage_branch,
    is_protected_branch,
    is_stale_draft_pr_candidate,
    matches_stale_draft_branch_pattern,
    parse_cutoff,
    propose_owner_action,
    propose_worktree_action,
)

pytestmark = pytest.mark.unit

CUTOFF = parse_cutoff("2026-06-10T00:00:00+00:00")


@pytest.mark.parametrize(
    ("branch", "expected"),
    [
        ("main", True),
        ("master", True),
        ("master_20260601", True),
        ("master_20260709", True),
        ("main_20260701", True),
        ("main_20260514-2", False),
        ("bolt-optimize-as-py-7292696041886100102", False),
    ],
)
def test_is_protected_branch(branch: str, expected: bool) -> None:
    assert is_protected_branch(branch) is expected


@pytest.mark.parametrize(
    "branch",
    ["1", "2", "a1", "tmp", "tmp01", "tmp2", "tmp-audit-noop-cleanup", "ьфыеук"],
)
def test_is_phase1_garbage_branch(branch: str) -> None:
    assert is_phase1_garbage_branch(branch) is True


def test_protected_snapshot_is_not_phase1_garbage() -> None:
    assert is_phase1_garbage_branch("master_20260707") is False


@pytest.mark.parametrize(
    ("branch", "expected"),
    [
        ("bolt-optimize-as-py-7292696041886100102", True),
        ("bolt/optimize-polars-metrics-16319493333469337967", True),
        ("perf-optimize-polars-metrics-7128814062286004388", True),
        ("test-swarm-reports-11115732830350980092", True),
        ("fix/issue-6031-panel-title-governance", False),
        ("master_20260707", False),
    ],
)
def test_matches_stale_draft_branch_pattern(branch: str, expected: bool) -> None:
    assert matches_stale_draft_branch_pattern(branch) is expected


def test_is_stale_draft_pr_candidate_requires_old_draft() -> None:
    assert (
        is_stale_draft_pr_candidate(
            branch_name="bolt-optimize-as-py-7292696041886100102",
            created_at="2026-06-01T00:00:00Z",
            is_draft=True,
            labels=(),
            cutoff=CUTOFF,
        )
        is True
    )
    assert (
        is_stale_draft_pr_candidate(
            branch_name="bolt-optimize-as-py-7292696041886100102",
            created_at="2026-07-01T00:00:00Z",
            is_draft=True,
            labels=(),
            cutoff=CUTOFF,
        )
        is False
    )


def test_is_stale_draft_pr_candidate_honors_stale_label() -> None:
    assert (
        is_stale_draft_pr_candidate(
            branch_name="fix/issue-6031-panel-title-governance",
            created_at="2026-06-01T00:00:00Z",
            is_draft=True,
            labels=("stale",),
            cutoff=CUTOFF,
        )
        is True
    )


def test_build_branch_record_marks_phase2_for_stale_draft() -> None:
    record = build_branch_record(
        name="py-test-swarm-reports-17470800817558701356",
        sha="abc",
        committed_at="2026-05-01T00:00:00Z",
        cutoff=CUTOFF,
        open_pr_number=5184,
        open_pr_state="open",
        open_pr_draft=True,
        open_pr_created_at="2026-06-07T10:23:24Z",
        open_pr_labels=("stale",),
    )
    assert record.phase2_stale_draft is True
    assert categorize_branch(record.name) == "agent-reports"


def test_parse_cutoff_accepts_z_suffix() -> None:
    parsed = parse_cutoff("2026-06-10T00:00:00Z")
    assert parsed == datetime(2026, 6, 10, tzinfo=UTC)


@pytest.mark.parametrize(
    ("branch", "expected"),
    [
        ("master20260910", "dated-snapshot"),
        ("master20260910-2", "dated-snapshot"),
        ("master_20260601", "protected-snapshot"),
        ("temp-branch", "other"),
        ("12323", "other"),
        ("jules-wip", "agent-other"),
        ("codex/fix-main-snapshot", "agent-other"),
        ("fix/panel-title", "feature-fix"),
    ],
)
def test_categorize_branch_covers_live_noncompliant_names(
    branch: str, expected: str
) -> None:
    assert categorize_branch(branch) == expected


@pytest.mark.parametrize(
    ("branch", "open_pr", "expected"),
    [
        ("main", None, "keep"),
        ("master_20260709", None, "keep"),
        ("master20260910", None, "tag"),
        ("master20260910", 12, "keep"),
        ("12323", None, "delete"),
        ("tmp", None, "delete"),
        ("temp-branch", None, "review"),
        ("jules-wip", None, "review"),
        ("codex/fix-main-10266", None, "review"),
        ("fix/panel-title", None, "keep"),
        ("fix/panel-title", 9, "keep"),
        ("develop", None, "keep"),
    ],
)
def test_propose_owner_action_is_dry_run_only(
    branch: str, open_pr: int | None, expected: str
) -> None:
    assert (
        propose_owner_action(
            name=branch,
            protected=is_protected_branch(branch),
            open_pr_number=open_pr,
            category=categorize_branch(branch),
        )
        == expected
    )


def test_propose_worktree_action_does_not_unlock_or_prune() -> None:
    assert propose_worktree_action(
        branch="master20260910",
        detached=False,
        locked=True,
        prunable=True,
    ) == ("keep", "locked; confirm a live agent before unlock")
    assert (
        propose_worktree_action(
            branch=None,
            detached=True,
            locked=False,
            prunable=False,
        )[0]
        == "review"
    )
