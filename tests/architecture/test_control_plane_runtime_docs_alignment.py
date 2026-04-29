"""Architecture guards for published control-plane docs/runtime alignment."""

from __future__ import annotations

from pathlib import Path

from bioetl.domain.control_plane.run_ledger import (
    COMPOSITE_RUN_LEDGER_STAGE_NAMES,
    ORDINARY_RUN_LEDGER_STAGE_NAMES,
    RUN_LEDGER_BASELINE_EVENT_TYPES,
)

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
CURRENT_BASELINE_EVENTS = RUN_LEDGER_BASELINE_EVENT_TYPES


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


def test_published_control_plane_docs_describe_dual_mode_resume_contract() -> None:
    """Published docs must state the intentional ordinary/composite resume split."""
    expected_fragments = (
        "ordinary resume uses checkpoint snapshot state",
        "composite resume uses checkpoint snapshot state as the base",
        "last_event_id",
    )
    for path in PUBLISHED_CONTROL_PLANE_DOCS:
        text = path.read_text(encoding="utf-8").lower()
        missing = [fragment for fragment in expected_fragments if fragment not in text]
        assert not missing, (
            f"{path.relative_to(PROJECT_ROOT)} is missing dual-mode resume contract "
            f"fragments: {missing}"
        )


def test_published_control_plane_docs_describe_resume_identity_anchors() -> None:
    """Published docs must describe semantic vs occurrence-scoped resume identity."""
    expected_fragments = (
        "execution_fingerprint",
        "composite_run_identity",
        "occurrence-scoped",
        "current_identity",
        "checkpoint_identity",
    )
    for path in PUBLISHED_CONTROL_PLANE_DOCS:
        text = path.read_text(encoding="utf-8").lower()
        missing = [fragment for fragment in expected_fragments if fragment not in text]
        assert not missing, (
            f"{path.relative_to(PROJECT_ROOT)} is missing resume identity "
            f"fragments: {missing}"
        )


def test_published_control_plane_docs_describe_exact_replay_hard_fail_policy() -> None:
    """Published docs must freeze exact replay coercion to hard_fail."""
    expected_fragments = (
        "exact replay",
        "hard_fail",
    )
    for path in PUBLISHED_CONTROL_PLANE_DOCS:
        text = path.read_text(encoding="utf-8").lower()
        missing = [fragment for fragment in expected_fragments if fragment not in text]
        assert not missing, (
            f"{path.relative_to(PROJECT_ROOT)} is missing exact replay policy "
            f"fragments: {missing}"
        )


def test_contract_doc_enumerates_supported_execution_paths() -> None:
    """The published contract doc should freeze the supported execution matrix."""
    text = CONTRACT_DOC.read_text(encoding="utf-8").lower()
    expected_fragments = (
        "## supported execution paths",
        "`ordinary success`",
        "`ordinary failure`",
        "`ordinary shutdown`",
        "`ordinary resume`",
        "`composite success`",
        "`composite failure`",
        "`composite shutdown`",
        "`composite resume`",
        "manifest exists before execution starts",
        "no supported execution path may bypass manifest creation",
    )
    missing = [fragment for fragment in expected_fragments if fragment not in text]
    assert not missing, (
        "docs/04-reference/contracts/run-manifest-ledger.md is missing supported "
        f"execution-path contract fragments: {missing}"
    )


def test_contract_doc_freezes_canonical_stage_sets() -> None:
    """Published contract doc should enumerate ordinary and composite stage sets."""
    text = CONTRACT_DOC.read_text(encoding="utf-8").lower()
    expected_fragments = (
        "## canonical stage sets",
        "ordinary runner stages",
        "composite runner stages",
        *ORDINARY_RUN_LEDGER_STAGE_NAMES,
        *COMPOSITE_RUN_LEDGER_STAGE_NAMES,
    )
    missing = [fragment for fragment in expected_fragments if fragment not in text]
    assert not missing, (
        "docs/04-reference/contracts/run-manifest-ledger.md is missing canonical "
        f"stage-set fragments: {missing}"
    )


def test_published_control_plane_docs_describe_snapshot_identity_anchors() -> None:
    """Published traceability docs must keep snapshot/content-hash anchors visible."""
    expected_fragments = (
        "input_snapshot_ids",
        "snapshot_id",
        "content_hash",
    )
    for path in (CONTRACT_DOC, CLI_DOC, RUNBOOK_DOC):
        text = path.read_text(encoding="utf-8").lower()
        missing = [fragment for fragment in expected_fragments if fragment not in text]
        assert not missing, (
            f"{path.relative_to(PROJECT_ROOT)} is missing snapshot identity "
            f"fragments: {missing}"
        )
