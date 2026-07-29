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
"""Residual documentation keyword guards (docs Phase 4.3 lightweight).

Fails closed when high-traffic operator docs reintroduce known-false SoT claims
from the 2026-07 monitoring cut / DQ hard_fail correction wave.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_active_dq_guides_do_not_claim_hierarchical_hard_fail_025() -> None:
    """Hierarchical base hard_fail is 0.50 (configs/base/quality.yaml)."""
    paths = [
        "docs/03-guides/dq-configuration.md",
        "docs/04-reference/contracts/dq-contracts.md",
        "docs/05-operations/runbooks/pipeline-failure-dq.md",
        "docs/02-architecture/data-layers.md",
        "docs/03-guides/pipeline-configuration.md",
    ]
    offenders: list[str] = []
    for rel in paths:
        text = _read(rel)
        if "hard_fail: 0.25" in text or "hard_fail=0.25" in text:
            offenders.append(rel)
        # hierarchical narrative claiming 25%
        if "hard_fail: 0.25" in text.replace("`", ""):
            offenders.append(rel)
    assert not offenders, (
        "Active DQ guides must not claim hierarchical hard_fail 0.25; "
        f"offenders={offenders}"
    )


def test_monitoring_guide_does_not_route_to_retired_dashboard_titles() -> None:
    """Operator investigation matrix must not route to retired Workflow/Alerts boards."""
    text = _read("docs/05-operations/01-monitoring-guide.md")
    # Allow mentions only in retired/removal prose, not as live matrix targets
    assert "| Composite workflow | `5. Workflow` |" not in text
    assert "| Alerts и SLO | `6. Alerts & SLO` |" not in text
    assert "Loki drilldown не находит" not in text
    assert "Incident Workspace" in text
    assert "Run Explorer" in text


def test_current_state_inventory_lists_seven_shipped_dashboards() -> None:
    text = _read("docs/02-architecture/current-state-inventory.md")
    for uid in (
        "bioetl-control-plane-v1.json",
        "bioetl-overview-v2.json",
        "bioetl-runtime.json",
        "bioetl-provider-health-v2.json",
        "bioetl-dq-v2.json",
        "bioetl-incident-v1.json",
        "bioetl-run-explorer-v1.json",
    ):
        assert uid in text
    # Retired boards must not appear as live file rows without retirement context
    assert "grafana/dashboards/bioetl-workflow-overview.json` |" not in text
    assert "grafana/dashboards/bioetl-alerts-slo.json` |" not in text
    assert "grafana/dashboards/bioetl-silver-reject-explorer.json` |" not in text


def test_observability_checklist_does_not_require_tempo_spans() -> None:
    text = _read("docs/05-operations/runbooks/observability-checklist.md")
    assert "Tempo contains" not in text
    assert "checkpoint_save` spans" not in text or "Do **not**" in text
