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
"""Architecture tests for nightly diagram workflow wiring."""

from __future__ import annotations

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture


def test_nightly_workflow_exists_and_is_scheduled() -> None:
    workflow_path = Path(".github/workflows/diagram-nightly.yml")
    assert workflow_path.exists(), "diagram-nightly workflow file must exist"

    workflow = workflow_path.read_text(encoding="utf-8")
    assert "schedule:" in workflow
    assert "workflow_dispatch:" in workflow
    assert "run_diagram_nightly_suite.py" in workflow


def test_nightly_workflow_includes_mermaid_canary_matrix() -> None:
    workflow = Path(".github/workflows/diagram-nightly.yml").read_text(encoding="utf-8")

    assert "mermaid-minor-canary" in workflow
    assert "matrix:" in workflow
    assert "mermaid_version" in workflow
    assert "continue-on-error: ${{ matrix.allow_failure }}" in workflow

    # The composite action explicitly installs the browser revision required by
    # the pinned Mermaid CLI's own Puppeteer dependency.
    composite = Path(".github/actions/setup-mermaid/action.yml")
    sources = workflow + (
        composite.read_text(encoding="utf-8") if composite.exists() else ""
    )
    assert "node node_modules/puppeteer/install.js" in sources
    assert 'require("puppeteer").executablePath()' in sources
    assert "puppeteer" in sources


def test_nightly_workflow_render_requires_svgo() -> None:
    workflow = Path(".github/workflows/diagram-nightly.yml").read_text(encoding="utf-8")

    assert "Render diagrams" in workflow
    assert 'REQUIRE_SVGO: "1"' in workflow


def test_nightly_workflow_maintains_idempotent_stale_diagram_alert() -> None:
    """Scheduled freshness failures must update one issue and fail meaningfully."""
    workflow = Path(".github/workflows/diagram-nightly.yml").read_text(encoding="utf-8")

    assert "issues: write" in workflow
    assert "github.event_name == 'schedule'" in workflow
    assert "[DIAGRAM-FRESHNESS] Refresh diagrams older than 150 days" in workflow
    assert 'gh issue list --state open --search "${ALERT_TITLE} in:title"' in workflow
    assert 'item.get("title") == title' in workflow
    assert 'gh issue edit "$existing"' in workflow
    assert "gh issue create --title" in workflow
    assert 'gh issue close "$existing"' in workflow
    assert "exceed the 150-day freshness threshold" in workflow
    assert "exit 1" in workflow


def test_nightly_stale_alert_uses_job_scoped_least_permissions() -> None:
    """Only the reporting job may write issues; repository contents stay read-only."""
    workflow = Path(".github/workflows/diagram-nightly.yml").read_text(encoding="utf-8")
    job_prefix = workflow.split("  mermaid-minor-canary:", maxsplit=1)[0]

    assert "permissions:\n      contents: read\n      issues: write" in job_prefix
    assert workflow.count("issues: write") == 1


def test_nightly_canary_manifest_stays_inside_repo() -> None:
    """check_svg_text_visibility refuses paths outside the checkout."""
    workflow = Path(".github/workflows/diagram-nightly.yml").read_text(encoding="utf-8")

    assert "reports/diagrams/canary/manifest-" in workflow
    assert "/tmp/diagram-canary-manifest.txt" not in workflow
    assert "11.4.0" not in workflow
