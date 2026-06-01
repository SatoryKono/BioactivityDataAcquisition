"""Architecture tests for diagram regression CI workflow wiring."""

from __future__ import annotations

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture

def test_docs_workflow_includes_quality_gates_step() -> None:
    workflow = Path(".github/workflows/docs.yml").read_text(encoding="utf-8")

    assert "check_diagram_quality_gates.py" in workflow
    assert "diagrams/manifests/quality-gates.txt" in workflow
    assert "diagram-quality-report.json" in workflow
    assert "diagrams-quality-report" in workflow


def test_docs_workflow_includes_artifact_validation_step() -> None:
    workflow = Path(".github/workflows/docs.yml").read_text(encoding="utf-8")

    assert "check_diagram_artifacts.py" in workflow
    assert "diagrams/manifests/visual-smoke.txt" in workflow


def test_docs_workflow_publishes_step_summary() -> None:
    workflow = Path(".github/workflows/docs.yml").read_text(encoding="utf-8")

    assert "Publish diagram quality summary" in workflow
    assert "GITHUB_STEP_SUMMARY" in workflow


def test_docs_workflow_installs_puppeteer_chrome_runtime() -> None:
    workflow = Path(".github/workflows/docs.yml").read_text(encoding="utf-8")

    # Puppeteer chrome install may be inline or in the composite action
    composite = Path(".github/actions/setup-mermaid/action.yml")
    sources = workflow + (
        composite.read_text(encoding="utf-8") if composite.exists() else ""
    )
    assert "puppeteer browsers install chrome-headless-shell" in sources


def test_docs_workflow_runs_doc_integrity_guardrails() -> None:
    workflow = Path(".github/workflows/docs.yml").read_text(encoding="utf-8")

    assert "Run documentation integrity guardrails" in workflow
    assert "uv run python -m scripts.docs check-links" in workflow
