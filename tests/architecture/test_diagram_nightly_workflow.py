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

    # Puppeteer chrome install may be inline or in the composite action
    composite = Path(".github/actions/setup-mermaid/action.yml")
    sources = workflow + (
        composite.read_text(encoding="utf-8") if composite.exists() else ""
    )
    assert "puppeteer browsers install chrome-headless-shell" in sources
