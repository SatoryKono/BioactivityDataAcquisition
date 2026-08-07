#!/usr/bin/env python3
"""Unified entry point for scripts/diagrams/ commands.

Usage:
    python -m scripts.diagrams <command> [args...]
    python -m scripts.diagrams --help

Lint:
    lint                 Lint architecture diagrams (.mmd/.mermaid)
    lint-summarize       Summarize diagram lint report
    lint-budget          Enforce diagram quality budget

Check:
    checks               Run diagram validation profile runner
    check-artifacts      Check diagram artifact manifest
    check-quality-gates  Check diagram quality gates
    check-visual-smoke   Visual smoke test for diagrams
    check-svg-text       Check SVG text visibility
    check-class-methods  Check class method render integrity
    check-pdf-bounds     Check PDF image bounds
    check-padding        Report diagram padding issues

Fix:
    apply-elk            Add ELK init to large Mermaid flowcharts
    differentiate-linkstyle
                         Add semantic linkStyle groups to dense flowcharts
    fix-operators        Fix Mermaid operators
    fix-svg-text         Add SVG text fallback
    fix-svg-styles       Inject SVG styles
    fix-foreign-object   Strip SVG foreignObject elements
    harmonize-link-styles
                         Harmonize rendered SVG link styles
    fix-orphans          Prune orphan nodes in diagrams
    fix-sizes            Uniform diagram sizes
    fix-pagebreaks       Fix pagebreaks in bundles

Render:
    generate-dataflows   Generate pipeline dataflow diagrams and field inventories
    docs-agent           Run full diagram docs pipeline
    render-pdf           Refresh architecture Markdown bundle
    render-pdf-desc      Generate PDF with descriptions
    render-docx          Generate DOCX with descriptions
    render-views         Refresh views Markdown bundle
    render-desc-indexes  Refresh description indexes

Suite:
    nightly              Run full diagram nightly suite
"""

from __future__ import annotations

from pathlib import Path

from scripts.engineering.common.cli_dispatch import (
    dispatch_cli,
    module_command,
    python_command,
    shell_command,
)

COMMAND_SPECS = {
    # Lint
    "lint": python_command("lint/lint_diagrams.py"),
    "lint-summarize": python_command("lint/summarize_diagram_lint.py"),
    "lint-budget": python_command("lint/enforce_diagram_quality_budget.py"),
    # Check
    "checks": shell_command("run_diagram_checks.sh"),
    "check-artifacts": python_command("check/check_diagram_artifacts.py"),
    "check-quality-gates": python_command("check/check_diagram_quality_gates.py"),
    "check-visual-smoke": python_command("check/check_diagram_visual_smoke.py"),
    "check-svg-text": python_command("check/check_svg_text_visibility.py"),
    "check-class-methods": python_command(
        "check/check_class_method_render_integrity.py"
    ),
    "check-pdf-bounds": python_command("check/check_pdf_image_bounds.py"),
    "check-padding": python_command("check/report_diagram_padding.py"),
    # Fix
    "apply-elk": python_command("fix/apply_elk_layout.py"),
    "differentiate-linkstyle": python_command("fix/differentiate_linkstyle.py"),
    "fix-operators": python_command("fix/fix_mermaid_operators.py"),
    "fix-svg-text": python_command("fix/add_svg_text_fallback.py"),
    "fix-svg-styles": python_command("fix/fix_svg_styles.py"),
    "fix-foreign-object": python_command("fix/strip_svg_foreign_object.py"),
    "harmonize-link-styles": python_command("fix/harmonize_link_styles.py"),
    "fix-orphans": python_command("fix/prune_orphan_nodes.py"),
    "fix-sizes": python_command("fix/uniform_diagram_sizes.py"),
    "fix-pagebreaks": python_command("render/fix_pagebreaks_in_bundles.py"),
    # Render
    "generate-dataflows": module_command(
        "scripts.diagrams.render.generate_pipeline_dataflows"
    ),
    "docs-agent": shell_command("run_diagram_docs_agent.sh"),
    "render-pdf": python_command(
        "render/generate_all_bundles.py", "--collection", "architecture"
    ),
    "render-pdf-desc": python_command("render/generate_with_descriptions_pdf.py"),
    "render-docx": python_command("render/generate_with_descriptions_docx.py"),
    "render-views": python_command(
        "render/generate_all_bundles.py", "--collection", "views"
    ),
    "render-desc-indexes": python_command("render/generate_description_indexes.py"),
    # Suite
    "nightly": python_command("run_diagram_nightly_suite.py"),
}

_DIR = Path(__file__).parent


def main(argv: list[str] | None = None) -> int:
    return dispatch_cli(
        argv,
        help_text=__doc__ or "",
        commands=COMMAND_SPECS,
        base_dir=_DIR,
        sort_available=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
