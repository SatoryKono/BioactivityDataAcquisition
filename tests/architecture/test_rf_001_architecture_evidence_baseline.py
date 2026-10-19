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
"""RF-001 guards for architecture evidence and planning baseline prose."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from tests.architecture.quality_artifacts import (
    quality_artifact_path,
)


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CURRENT_STATE = ROOT / "docs/02-architecture/current-state-inventory.md"
PLAYBOOK = ROOT / "docs/00-project/governance/08-debt-ownership-playbook.md"
FULL_APP_DUPLICATION = quality_artifact_path("full-app-duplication-baseline.json")
SCORECARD = ROOT / "configs/quality/debt_scorecard.yaml"
EXEMPTIONS = ROOT / "configs/quality/architecture_metric_exemptions.yaml"


def _read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _read_yaml(path: Path) -> dict[str, object]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_current_state_inventory_matches_full_app_duplication_baseline() -> None:
    """Inventory prose must not stale the actionable/raw duplication split."""
    baseline = _read_json(FULL_APP_DUPLICATION)
    summary = baseline["summary"]
    assert isinstance(summary, dict)
    actionable = summary["total_duplicate_clusters"]
    raw = summary["total_raw_duplicate_clusters"]
    excluded = summary["total_excluded_duplicate_clusters"]

    inventory = CURRENT_STATE.read_text(encoding="utf-8")

    assert f"`{actionable}` actionable / `{raw}` raw excluded clusters" in inventory
    assert "current actionable duplication is zero" in inventory
    assert raw == excluded
    assert "`43` clusters" not in inventory


def test_owner_diversification_policy_surfaces_use_scorecard_q3_anchor() -> None:
    """Exemption policy and playbook must mirror the scorecard start quarter."""
    scorecard = _read_yaml(SCORECARD)
    exemptions = _read_yaml(EXEMPTIONS)
    governance = scorecard["governance"]
    assert isinstance(governance, dict)
    owner_diversification = governance["owner_diversification"]
    assert isinstance(owner_diversification, dict)
    starts_quarter = owner_diversification["starts_quarter"]

    policy = exemptions["policy"]
    assert isinstance(policy, dict)
    sync = policy["owner_diversification_sync"]
    assert isinstance(sync, dict)
    playbook = PLAYBOOK.read_text(encoding="utf-8")

    assert starts_quarter == "2026-Q3"
    assert sync["starts_quarter"] == starts_quarter
    assert "owner_registry_q3_subsystems" in playbook
    assert "Q3 scorecard decomposition targets" in playbook
    assert "Q2 scorecard decomposition targets" not in playbook
    assert "owner_registry_q2_subsystems" not in playbook
