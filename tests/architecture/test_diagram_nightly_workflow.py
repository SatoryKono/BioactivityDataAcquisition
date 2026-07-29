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
