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
"""Architecture tests for diagram regression CI workflow wiring."""

from __future__ import annotations

import os
import stat
from pathlib import Path
import subprocess
import sys

import pytest

pytestmark = pytest.mark.architecture

_STALE_WORKFLOW_NEEDLE = b"validate-mermaid.yml"
_STALE_SCAN_SKIP_DIRS = frozenset(
    {
        "99-archive",
        "archive",
        "reports",
        "site",
        "exports",
        "generated",
        "descriptions",
        "bundles",
        "__pycache__",
    }
)
_MAX_STALE_SCAN_BYTES = 1_048_576
_FILE_ATTRIBUTE_RECALL_ON_OPEN = 0x00040000
_FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x00400000
_CLOUD_PLACEHOLDER_ATTRIBUTES = (
    _FILE_ATTRIBUTE_RECALL_ON_OPEN | _FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS
)
_STALE_SCAN_SUFFIXES = {".md", ".yml", ".yaml", ".py"}

ROUTER_IMPORT_COMMANDS = (
    "check-quality-gates",
    "check-padding",
    "fix-svg-styles",
    "fix-pagebreaks",
    "render-desc-indexes",
)


@pytest.mark.parametrize("command", ROUTER_IMPORT_COMMANDS)
def test_diagram_router_commands_bootstrap_repository_imports(command: str) -> None:
    root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    result = subprocess.run(
        [sys.executable, "-m", "scripts.diagrams", command, "--help"],
        cwd=root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_docs_workflow_includes_quality_gates_step() -> None:
    workflow = Path(".github/workflows/docs.yml").read_text(encoding="utf-8")

    assert "check_diagram_quality_gates.py" in workflow
    assert "diagrams/manifests/quality-gates.txt" in workflow
    assert "diagram-quality-report.json" in workflow
    assert "diagrams-quality-report" in workflow
    assert "diagram-visual-smoke.json" in workflow


def test_docs_workflow_includes_artifact_validation_step() -> None:
    workflow = Path(".github/workflows/docs.yml").read_text(encoding="utf-8")

    assert "check_diagram_artifacts.py" in workflow
    assert "diagrams/manifests/visual-smoke.txt" in workflow


def test_docs_workflow_validates_embedded_mermaid_blocks() -> None:
    workflow = Path(".github/workflows/docs.yml").read_text(encoding="utf-8")

    assert "--include-embedded" in workflow
    assert "'docs/**/*.md'" in workflow


def test_docs_workflow_only_renders_when_renderer_inputs_change() -> None:
    workflow = Path(".github/workflows/docs.yml").read_text(encoding="utf-8")

    assert "render_sources_changed:" in workflow
    assert (
        "needs.detect-diagram-changes.outputs.render_sources_changed == 'true'"
        in workflow
    )


def test_docs_workflow_publishes_step_summary() -> None:
    workflow = Path(".github/workflows/docs.yml").read_text(encoding="utf-8")

    assert "Publish diagram quality summary" in workflow
    assert "GITHUB_STEP_SUMMARY" in workflow


def test_docs_workflow_installs_the_pinned_mermaid_puppeteer_runtime() -> None:
    workflow = Path(".github/workflows/docs.yml").read_text(encoding="utf-8")

    # Puppeteer chrome install may be inline or in the composite action
    composite = Path(".github/actions/setup-mermaid/action.yml")
    sources = workflow + (
        composite.read_text(encoding="utf-8") if composite.exists() else ""
    )
    assert "node node_modules/puppeteer/install.js" in sources
    assert 'require("puppeteer").executablePath()' in sources
    assert 'test -x "${PUPPETEER_EXECUTABLE}"' in sources


def test_docs_workflow_runs_doc_integrity_guardrails() -> None:
    workflow = Path(".github/workflows/docs.yml").read_text(encoding="utf-8")

    assert "Run documentation integrity guardrails" in workflow
    assert "python -m scripts.docs check-links" in workflow
    assert "--report-json reports/docs-link-check-report.json" in workflow
    assert "--report-json docs/reports/docs-link-check-report.json" not in workflow


def test_docs_workflow_diagram_drift_uses_pr_base_ref() -> None:
    workflow = Path(".github/workflows/docs.yml").read_text(encoding="utf-8")

    assert "BASE_REF: ${{ github.base_ref }}" in workflow
    assert 'base_ref="origin/${BASE_REF}"' in workflow
    assert (
        '[[ "${BASE_REF}" != "main" && "${BASE_REF}" != "develop" ]]'
        in workflow
    )
    assert "origin/${{ github.base_ref }}" not in workflow
    assert 'git diff --name-only "${base_ref}"...HEAD' in workflow
    drift_block = workflow.split("check-diagram-drift:", maxsplit=1)[1]
    assert "origin/main...HEAD" not in drift_block


def test_docs_workflow_diagram_change_filter_covers_regression_tests() -> None:
    workflow = Path(".github/workflows/docs.yml").read_text(encoding="utf-8")

    assert "'tests/architecture/test_diagram*.py'" in workflow


def test_docs_workflow_render_requires_strict_svgo() -> None:
    workflow = Path(".github/workflows/docs.yml").read_text(encoding="utf-8")

    assert 'REQUIRE_SVGO: "1"' in workflow
    assert "Render diagrams with unified script" in workflow


def _is_cloud_placeholder(st: os.stat_result) -> bool:
    attrs = int(getattr(st, "st_file_attributes", 0) or 0)
    return bool(attrs & _CLOUD_PLACEHOLDER_ATTRIBUTES)


def _iter_stale_workflow_scan_files(root: Path) -> list[Path]:
    """Walk active trees, skipping archive/generated/cloud placeholders."""
    if not root.exists():
        return []
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in _STALE_SCAN_SKIP_DIRS]
        for name in filenames:
            path = Path(dirpath) / name
            if path.suffix not in _STALE_SCAN_SUFFIXES:
                continue
            try:
                st = path.stat()
            except OSError:
                continue
            if not stat.S_ISREG(st.st_mode) or _is_cloud_placeholder(st):
                continue
            if st.st_size > _MAX_STALE_SCAN_BYTES:
                continue
            found.append(path)
    return found


def test_vendored_mermaid_workflow_renamed_and_references_are_current() -> None:
    old_workflow = Path(".github/workflows/validate-mermaid.yml")
    new_workflow = Path(".github/workflows/validate-vendored-mermaid-assets.yml")

    assert not old_workflow.exists()
    assert new_workflow.exists()

    active_paths = [
        Path(".github/workflows"),
        Path("docs/00-project/governance"),
        Path("docs/02-architecture/diagrams"),
        Path("docs/04-reference"),
        Path("scripts/diagrams"),
    ]
    stale_hits: list[str] = []
    for root in active_paths:
        for path in _iter_stale_workflow_scan_files(root):
            try:
                payload = path.read_bytes()
            except OSError:
                continue
            if _STALE_WORKFLOW_NEEDLE in payload:
                stale_hits.append(path.as_posix())

    assert stale_hits == []


def test_windows_render_wrapper_delegates_to_canonical_renderer() -> None:
    wrapper = Path("scripts/diagrams/render.ps1")

    assert wrapper.exists()
    content = wrapper.read_text(encoding="utf-8")
    assert "docs\\02-architecture\\diagrams\\tooling\\render.sh" in content
    assert "GIT_BASH" in content
    assert "@RenderArgs" in content
