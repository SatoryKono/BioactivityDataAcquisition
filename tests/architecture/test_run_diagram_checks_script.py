"""Architecture tests for unified diagram checks runner script."""

from __future__ import annotations

from pathlib import Path


def _script_text() -> str:
    script_path = Path("scripts/diagrams/run_diagram_checks.sh")
    assert script_path.exists(), "scripts/diagrams/run_diagram_checks.sh must exist"
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
    assert '--text-layer "$TEXT_LAYER"' in script
    assert '--puppeteer "$PUPPETEER_CFG"' in script


def test_runner_supports_text_layer_mode() -> None:
    script = _script_text()

    assert "--text-layer <mode>" in script
    assert "TEXT_LAYER=" in script
    assert "--text-layer requires value" in script
    assert "--text-layer must be one of: dual|fo-only|fallback-only" in script


def test_runner_hardens_puppeteer_config_lifecycle() -> None:
    script = _script_text()

    assert "--refresh-puppeteer-config" in script
    assert "FORCE_WRITE_PUPPETEER=0" in script
    assert "ensure_puppeteer_config()" in script
    assert "Using existing Puppeteer config" in script
    assert "validate_puppeteer_config" in script


def test_runner_has_browser_preflight_diagnostics() -> None:
    script = _script_text()

    assert "run_puppeteer_preflight()" in script
    assert "running as root (requires --no-sandbox" in script
    assert "executablePath not set (auto-discovery mode)" in script
    assert "args include --no-sandbox" in script


def test_runner_invokes_operator_guard_before_syntax_checks() -> None:
    script = _script_text()

    assert "run_operator_guard()" in script
    assert 'python3 "$REPO_ROOT/scripts/diagrams/fix_mermaid_operators.py"' in script
    assert '--check "$REPO_ROOT/docs/02-architecture/mmd-diagrams"' in script
    assert '--check "$REPO_ROOT/$DIAGRAM_PATH"' in script
    assert "DIAG-T000: Mermaid operator guard" in script


def test_runner_uses_canonical_scope_for_full_syntax_validation() -> None:
    script = _script_text()

    assert "validate_mermaid_syntax.sh" in script
    assert "--scope canonical" in script
