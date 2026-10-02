"""Regression checks for fail-closed live acceptance."""

from __future__ import annotations

import pytest

from scripts.ops.observability.green_acceptance import Case, command, green_failures


@pytest.mark.parametrize("kind", ["pipeline", "workflow", "composite"])
def test_every_launch_has_limit_1000(kind):
    args = command(Case(kind, "chembl_assay"))
    assert args[args.index("--limit") + 1] == "1000"
    assert args[args.index("--required-persistence-profile") + 1] == "replay_ready"


def test_all_green_passes():
    assert (
        green_failures(
            "success",
            {"saved_evidence_status": "OK", "replay_readiness_status": "OK"},
            {"verdict": "OK", "evidence_completeness": "COMPLETE"},
        )
        == []
    )


@pytest.mark.parametrize(
    "value", [None, "UNKNOWN", "INCOMPLETE", "N/A", "WARN", "ERROR", "QUERY ERROR"]
)
@pytest.mark.parametrize("field", ["saved_evidence_status", "replay_readiness_status"])
def test_non_green_evidence_fails(field, value):
    presentation = {
        "saved_evidence_status": "OK",
        "replay_readiness_status": "OK",
        field: value,
    }
    assert green_failures(
        "success", presentation, {"verdict": "OK", "evidence_completeness": "COMPLETE"}
    )


@pytest.mark.parametrize(
    "status", ["failed", "running", "partial", "shutdown", "unknown"]
)
def test_failed_execution_cannot_be_hidden_by_green_evidence(status):
    assert green_failures(
        status,
        {"saved_evidence_status": "OK", "replay_readiness_status": "OK"},
        {"verdict": "OK", "evidence_completeness": "COMPLETE"},
    )
