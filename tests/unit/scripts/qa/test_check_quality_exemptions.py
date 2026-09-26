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
"""Unit tests for the canonical quality-exemptions QA command."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.engineering.qa import check_quality_exemptions as exemptions

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "scripts" / "engineering" / "qa" / "check_quality_exemptions.py"
ARCHIVED_LIVE_PATH = (
    "docs/00-project/ai/agents/scripts/architecture-techdebt-automation.py"
)

pytestmark = pytest.mark.unit


def test_check_quality_exemptions_module_owns_implementation() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    assert ARCHIVED_LIVE_PATH not in source
    assert "evaluate_debt_scorecard" in source
    assert "validate_exemptions_registry" in source


def test_check_quality_exemptions_passes_current_zero_budget_registry() -> None:
    exit_code = exemptions.main(
        [
            "--registry",
            "configs/quality/architecture_metric_exemptions.yaml",
            "--scorecard",
            "configs/quality/debt_scorecard.yaml",
            "--mode",
            "auto",
            "--growth-mode",
            "auto",
            "--trend-report",
            "off",
        ]
    )
    assert exit_code == 0
