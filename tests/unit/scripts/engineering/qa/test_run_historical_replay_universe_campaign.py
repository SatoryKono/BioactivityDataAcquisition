"""Unit tests for the historical replay universe QA campaign script."""

from __future__ import annotations

import pytest

from types import SimpleNamespace

from scripts.engineering.qa import run_historical_replay_universe_campaign as campaign


pytestmark = pytest.mark.unit

def test_required_universal_claim_uses_governed_full_corpus_gate() -> None:
    report = SimpleNamespace(
        universal_claim={"claimed": True},
        durable_evidence_coverage_claim={"claimed": False},
        governed_full_corpus_gate={"satisfied": False},
    )

    assert campaign._has_required_universal_exact_replay_claim(report) is False


def test_required_universal_claim_accepts_satisfied_gate() -> None:
    report = SimpleNamespace(
        universal_claim={"claimed": True},
        durable_evidence_coverage_claim={"claimed": True},
        governed_full_corpus_gate={"satisfied": True},
    )

    assert campaign._has_required_universal_exact_replay_claim(report) is True


def test_required_universal_claim_fails_closed_without_gate_payload() -> None:
    report = SimpleNamespace(
        universal_claim={"claimed": True},
        durable_evidence_coverage_claim={"claimed": True},
    )

    assert campaign._has_required_universal_exact_replay_claim(report) is False
