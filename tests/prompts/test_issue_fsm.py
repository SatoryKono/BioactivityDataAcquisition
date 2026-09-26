"""P1 #9808 — Issue FSM + target-branch close gate (DOCX гл.4.3)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def decide_issue_state(
    *,
    status: str,
    allow_issue_write: bool,
    fingerprint_match_open: bool = False,
    deferred: bool = False,
    no_actionable: bool = False,
) -> str:
    """Minimal FSM from fragments/issue-state-machine-v3.md.

    Priority: reuse (dedupe) > NOT_PROVEN/blocked > defer > create/blocked > no_issue.
    """
    if fingerprint_match_open:
        return "reuse"
    if no_actionable:
        return "no_issue"
    if status == "NOT_PROVEN":
        return "blocked"
    if deferred:
        return "defer"
    if status == "PROVEN" and allow_issue_write:
        return "create"
    if status == "PROVEN" and not allow_issue_write:
        return "blocked"
    return "blocked"


def can_close_issue(
    *,
    allow_close: bool,
    proven_on_origin_base: bool,
    required_checks_green: bool,
) -> bool:
    """Target-branch close gate (stage H). All three must hold."""
    return allow_close and proven_on_origin_base and required_checks_green


def test_proven_and_allow_true_creates() -> None:
    assert decide_issue_state(status="PROVEN", allow_issue_write=True) == "create"


def test_not_proven_blocked_or_no_issue() -> None:
    assert decide_issue_state(status="NOT_PROVEN", allow_issue_write=True) == "blocked"
    assert decide_issue_state(status="NOT_PROVEN", allow_issue_write=False) == "blocked"
    assert (
        decide_issue_state(
            status="NOT_PROVEN", allow_issue_write=True, no_actionable=True
        )
        == "no_issue"
    )


def test_matching_fingerprint_reuses() -> None:
    assert (
        decide_issue_state(
            status="PROVEN", allow_issue_write=True, fingerprint_match_open=True
        )
        == "reuse"
    )
    # reuse takes precedence even when NOT_PROVEN would otherwise block
    assert (
        decide_issue_state(
            status="NOT_PROVEN", allow_issue_write=False, fingerprint_match_open=True
        )
        == "reuse"
    )


def test_target_branch_close_gate_requires_all() -> None:
    assert (
        can_close_issue(
            allow_close=True, proven_on_origin_base=True, required_checks_green=True
        )
        is True
    )
    assert (
        can_close_issue(
            allow_close=False, proven_on_origin_base=True, required_checks_green=True
        )
        is False
    )
    assert (
        can_close_issue(
            allow_close=True, proven_on_origin_base=False, required_checks_green=True
        )
        is False
    )
    assert (
        can_close_issue(
            allow_close=True, proven_on_origin_base=True, required_checks_green=False
        )
        is False
    )


def test_defer_and_blocked_states() -> None:
    assert (
        decide_issue_state(status="PROVEN", allow_issue_write=True, deferred=True)
        == "defer"
    )
    assert decide_issue_state(status="PROVEN", allow_issue_write=False) == "blocked"
