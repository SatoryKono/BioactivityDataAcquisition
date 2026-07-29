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
"""Unit tests for run-manifest universe-report gate helpers."""

from __future__ import annotations

import pytest

import importlib
from types import SimpleNamespace


pytestmark = pytest.mark.unit

run_manifest_commands = importlib.import_module(
    "bioetl.interfaces.cli.commands.run_manifest"
)


def test_universe_report_required_universal_claim_uses_governed_gate() -> None:
    report = SimpleNamespace(
        universal_claim={"claimed": True},
        durable_evidence_coverage_claim={"claimed": False},
        governed_full_corpus_gate={"satisfied": False},
    )

    assert (
        run_manifest_commands._has_required_universal_exact_replay_claim(report)
        is False
    )


def test_universe_report_required_universal_claim_accepts_satisfied_gate() -> None:
    report = SimpleNamespace(
        universal_claim={"claimed": True},
        durable_evidence_coverage_claim={"claimed": True},
        governed_full_corpus_gate={"satisfied": True},
    )

    assert (
        run_manifest_commands._has_required_universal_exact_replay_claim(report) is True
    )
