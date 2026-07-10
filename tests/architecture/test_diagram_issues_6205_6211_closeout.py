"""Closeout guards for diagram audit issues #6205 through #6211."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "diagram-issues-6205-6211-closeout.json"
EXPECTED_ISSUES = {6205, 6206, 6207, 6208, 6209, 6210, 6211}


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_issue_pack_6205_6211_closeout_artifact_is_complete() -> None:
    closeout = _load_json(CLOSEOUT)

    assert closeout["schema_version"] == "diagram-issues-6205-6211-closeout-v1"
    assert closeout["debt_budget_policy"] == "flat_or_decreasing_only"
    assert set(closeout["issues"]) == EXPECTED_ISSUES
    assert set(closeout["outcomes"]) == {str(number) for number in EXPECTED_ISSUES}

    missing_evidence = [
        relative_path
        for issue in closeout["outcomes"].values()
        for relative_path in issue["evidence"]
        if not (ROOT / relative_path).exists()
    ]
    assert missing_evidence == []
    assert all(issue["status"] == "closeable" for issue in closeout["outcomes"].values())


def test_issue_6205_rendered_artifact_policy_is_aligned() -> None:
    gitignore = _read(".gitignore")
    readme = _read("docs/02-architecture/diagrams/README.md")
    workflow = _read(".github/workflows/docs.yml")

    assert "mmd-diagrams" not in gitignore
    assert "/docs/02-architecture/diagrams/mermaid/png" not in gitignore
    assert "tracked render baselines" in readme
    assert "tracked rendered baseline" in readme
    assert "check-diagram-drift" in workflow
    assert "expected_svg" in workflow


def test_issue_6206_mermaid_cli_version_parity_is_enforced() -> None:
    wrapper = _read("scripts/diagrams/mmdc_wrapper.sh")
    renderer = _read("docs/02-architecture/diagrams/tooling/render.sh")
    readme = _read("docs/02-architecture/diagrams/README.md")

    assert 'MMDC_REQUIRED_VERSION="${MMDC_REQUIRED_VERSION:-10.6.1}"' in wrapper
    assert "MMDC_ALLOW_VERSION_DRIFT" in wrapper
    assert "minlag/mermaid-cli:10.6.1" in wrapper
    assert "enforce_mmdc_version" in renderer
    assert "MMDC_REQUIRED_VERSION=10.6.1" in readme


def test_issue_6207_renderer_uses_atomic_svg_and_png_writes() -> None:
    renderer = _read("docs/02-architecture/diagrams/tooling/render.sh")

    assert "replace_atomically" in renderer
    assert '.${base}.svg.tmp.XXXXXX' in renderer
    assert '.${base}.png.tmp.XXXXXX' in renderer
    assert 'replace_atomically "$svg_tmp" "$svg_out"' in renderer
    assert 'replace_atomically "$png_tmp" "$png_out"' in renderer


def test_issue_6208_embedded_mermaid_validation_is_repo_wide() -> None:
    validator = _read("scripts/diagrams/validate_mermaid_syntax.sh")
    workflow = _read(".github/workflows/docs.yml")

    assert "--include-embedded" in validator
    assert "embedded-mermaid" in validator
    assert "99-archive" in validator
    assert "--include-embedded" in workflow


def test_issue_6209_visual_smoke_emits_json_report() -> None:
    smoke = _read("scripts/diagrams/check_diagram_visual_smoke.py")
    workflow = _read(".github/workflows/docs.yml")
    runner = _read("scripts/diagrams/run_diagram_checks.sh")

    assert "diagram-visual-smoke-report-v1" in smoke
    assert "--json-out" in smoke
    assert "diagram-visual-smoke.json" in workflow
    assert "diagram-visual-smoke.json" in runner


def test_issue_6210_windows_powershell_workflow_is_documented() -> None:
    readme = _read("docs/02-architecture/diagrams/README.md")
    workflow_guide = _read(
        "docs/02-architecture/diagrams/governance/DIAGRAM-WORKFLOW-GUIDE.md"
    )

    assert "### Windows / PowerShell" in readme
    assert "Git Bash or WSL" in readme
    assert ".venv-win" in readme
    assert "--svg-only" in readme
    assert "MMDC_FORCE_DOCKER=1" in readme
    assert "Windows / PowerShell" in workflow_guide


def test_issue_6211_mkdocs_publication_target_is_validation_only() -> None:
    publication_policy = _read("docs/00-project/governance/06-doc-publication-policy.md")
    readme = _read("docs/02-architecture/diagrams/README.md")
    workflow = _read(".github/workflows/docs.yml")

    assert "validation/build workflow, not a GitHub Pages deployment workflow" in publication_policy
    assert "MkDocs is validation-only" in readme
    assert "validate-mkdocs" in workflow
    assert "deploy" not in workflow.lower()
