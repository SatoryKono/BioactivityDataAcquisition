"""Architecture guards for published control-plane docs/runtime alignment."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CONTRACT_DOC = PROJECT_ROOT / "docs/04-reference/contracts/run-manifest-ledger.md"
ADR_DOC = (
    PROJECT_ROOT
    / "docs/02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md"
)
CLI_DOC = PROJECT_ROOT / "docs/04-reference/cli.md"
RUNBOOK_DOC = PROJECT_ROOT / "docs/05-operations/runbooks/run-manifest-inspection.md"

PUBLISHED_CONTROL_PLANE_DOCS = (
    CONTRACT_DOC,
    ADR_DOC,
    CLI_DOC,
    RUNBOOK_DOC,
)
CURRENT_BASELINE_EVENTS = (
    "manifest_created",
    "run_started",
    "stage_started",
    "stage_completed",
    "artifact_published",
    "run_finished",
    "run_failed",
    "run_shutdown",
    "dq_policy_applied",
)


def test_published_control_plane_docs_cover_current_baseline_events() -> None:
    """Published control-plane surfaces must document the current event baseline."""
    for path in PUBLISHED_CONTROL_PLANE_DOCS:
        text = path.read_text(encoding="utf-8")
        missing = [event for event in CURRENT_BASELINE_EVENTS if event not in text]
        assert not missing, (
            f"{path.relative_to(PROJECT_ROOT)} is missing current baseline events: "
            f"{missing}"
        )


def test_published_control_plane_docs_do_not_describe_stage_failed_baseline() -> None:
    """Published baseline docs intentionally model stage failure through run_failed."""
    for path in PUBLISHED_CONTROL_PLANE_DOCS:
        text = path.read_text(encoding="utf-8")
        assert "stage_failed" not in text, (
            f"{path.relative_to(PROJECT_ROOT)} documents unsupported "
            "stage_failed baseline semantics."
        )
