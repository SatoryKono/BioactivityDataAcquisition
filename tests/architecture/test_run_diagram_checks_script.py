"""Architecture tests for unified diagram checks runner script."""

from __future__ import annotations

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture


def _script_text() -> str:
    script_path = Path("scripts/diagrams/run_diagram_checks.sh")
    assert script_path.exists(), "scripts/diagrams/run_diagram_checks.sh must exist"
    return script_path.read_text(encoding="utf-8")


def _is_compat_wrapper(script: str) -> bool:
    return (
        "Compatibility wrapper" in script
        and 'exec bash "$REPO_ROOT/docs/00-project/ai/agents/scripts/diagrams/'
        in script
    )


def test_runner_wrapper_or_full_implementation_contract() -> None:
    """Runner must either expose full contract or delegate to canonical wrapper target."""
    script = _script_text()

    if _is_compat_wrapper(script):
        assert (
            'exec bash "$REPO_ROOT/docs/00-project/ai/agents/scripts/diagrams/'
            in script
        )
        assert '.sh" "$@"' in script
        return

    assert "--diagram <path>" in script
    assert "prepare_diagram_scope" in script
    assert "run_render_step()" in script
    assert "--text-layer <mode>" in script
    assert "--refresh-puppeteer-config" in script
    assert "run_puppeteer_preflight()" in script
    assert "run_operator_guard()" in script
    assert "validate_mermaid_syntax.sh" in script
    assert "--scope canonical" in script


def test_runner_full_mode_has_scope_manifest_controls() -> None:
    """When script is full implementation, it must route checks through scope manifests."""
    script = _script_text()
    if _is_compat_wrapper(script):
        return

    assert 'TEMP_SOURCE_MANIFEST="$(mktemp' in script
    assert 'TEMP_RENDER_MANIFEST="$(mktemp' in script
    assert '--manifest "$SOURCE_MANIFEST"' in script
    assert '--manifest "$RENDER_MANIFEST"' in script
    assert '--source-manifest "$SOURCE_MANIFEST"' in script
    assert '--render-manifest "$RENDER_MANIFEST"' in script
