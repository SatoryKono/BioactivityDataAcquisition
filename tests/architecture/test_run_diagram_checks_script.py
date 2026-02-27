"""Architecture tests for unified diagram checks runner script."""

from __future__ import annotations

from pathlib import Path


def _script_text() -> str:
    script_path = Path("scripts/run_diagram_checks.sh")
    assert script_path.exists(), "scripts/run_diagram_checks.sh must exist"
    return script_path.read_text(encoding="utf-8")


def test_runner_supports_single_diagram_flag() -> None:
    script = _script_text()

    assert "--diagram <path>" in script
    assert "prepare_diagram_scope" in script
    assert "--diagram requires value" in script
    assert "--diagram must point to .mmd or .mermaid file" in script


def test_runner_uses_temp_manifests_for_single_diagram_scope() -> None:
    script = _script_text()

    assert 'TEMP_SOURCE_MANIFEST="$(mktemp' in script
    assert 'TEMP_RENDER_MANIFEST="$(mktemp' in script
    assert 'SOURCE_MANIFEST="$TEMP_SOURCE_MANIFEST"' in script
    assert 'RENDER_MANIFEST="$TEMP_RENDER_MANIFEST"' in script
    assert "trap cleanup_temp_manifests EXIT" in script


def test_runner_routes_checks_through_scope_manifests() -> None:
    script = _script_text()

    assert '--manifest "$SOURCE_MANIFEST"' in script
    assert '--manifest "$RENDER_MANIFEST"' in script
    assert '--source-manifest "$SOURCE_MANIFEST"' in script
    assert '--render-manifest "$RENDER_MANIFEST"' in script


def test_runner_renders_single_diagram_with_dir_and_filter() -> None:
    script = _script_text()

    assert "run_render_step()" in script
    assert '--dir "$REPO_ROOT/$diagram_dir"' in script
    assert '--filter "$diagram_stem"' in script
    assert '--puppeteer "$PUPPETEER_CFG"' in script
