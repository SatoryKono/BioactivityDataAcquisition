"""Keep the F1 acceptance blocker bound to the billing evidence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "reports/engineering/finances/billing_manifest.json"
REPORT = ROOT / "reports/engineering/ci/acceptance_f1_report.md"


def test_f1_acceptance_report_preserves_unverified_financial_status() -> None:
    """Do not turn missing source billing data into an acceptance claim."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    report = REPORT.read_text(encoding="utf-8")

    assert manifest["status"] == "AWAITING_DATA"
    assert manifest["financial_effect"] == "не установлен"
    assert manifest["expected_checksum"] == "PENDING"
    assert manifest["billing_access_owner"] is None
    assert "#12366" in report
    assert '"не установлен"' in report
    assert 'expected_checksum: "PENDING"' in report
    assert manifest["blocker"] in report
