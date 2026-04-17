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
    fix-operators        Fix Mermaid operators
    fix-svg-text         Add SVG text fallback
    fix-svg-styles       Inject SVG styles
    fix-foreign-object   Strip SVG foreignObject elements
    fix-orphans          Prune orphan nodes in diagrams
    fix-sizes            Uniform diagram sizes
    fix-pagebreaks       Fix pagebreaks in bundles

Render:
    docs-agent           Run full diagram docs pipeline
    render-pdf           Refresh architecture Markdown bundle (legacy entrypoint)
    render-pdf-desc      Generate PDF with descriptions
    render-docx          Generate DOCX with descriptions
    render-views         Refresh views Markdown bundle
    render-desc-indexes  Refresh description indexes

Suite:
    nightly              Run full diagram nightly suite
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

COMMANDS: dict[str, str] = {
    # Lint
    "lint": "lint_diagrams.py",
    "lint-summarize": "summarize_diagram_lint.py",
    "lint-budget": "enforce_diagram_quality_budget.py",
    # Check
    "checks": "run_diagram_checks.sh",
    "check-artifacts": "check_diagram_artifacts.py",
    "check-quality-gates": "check_diagram_quality_gates.py",
    "check-visual-smoke": "check_diagram_visual_smoke.py",
    "check-svg-text": "check_svg_text_visibility.py",
    "check-class-methods": "check_class_method_render_integrity.py",
    "check-pdf-bounds": "check_pdf_image_bounds.py",
    "check-padding": "report_diagram_padding.py",
    # Fix
    "fix-operators": "fix_mermaid_operators.py",
    "fix-svg-text": "add_svg_text_fallback.py",
    "fix-svg-styles": "inject_svg_styles.py",
    "fix-foreign-object": "strip_svg_foreign_object.py",
    "fix-orphans": "prune_orphan_nodes.py",
    "fix-sizes": "uniform_diagram_sizes.py",
    "fix-pagebreaks": "fix_pagebreaks_in_bundles.py",
    # Render
    "docs-agent": "run_diagram_docs_agent.sh",
    "render-pdf": "generate_architecture_bundle.py",
    "render-pdf-desc": "generate_with_descriptions_pdf.py",
    "render-docx": "generate_with_descriptions_docx.py",
    "render-views": "generate_views_bundle.py",
    "render-desc-indexes": "generate_description_indexes.py",
    # Suite
    "nightly": "run_diagram_nightly_suite.py",
}

_DIR = Path(__file__).parent


def _run_script(name: str, argv: list[str]) -> int:
    script = _DIR / name
    command = [sys.executable, str(script), *argv]
    if script.suffix == ".sh":
        command = ["bash", str(script), *argv]
    result = subprocess.run(command, check=False)
    return result.returncode


def _print_help() -> None:
    print(__doc__ or "", end="")


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]

    if not args or args[0] in ("--help", "-h"):
        _print_help()
        return 0

    cmd, rest = args[0], args[1:]

    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print(f"Available: {', '.join(sorted(COMMANDS))}", file=sys.stderr)
        return 2

    return _run_script(COMMANDS[cmd], rest)


if __name__ == "__main__":
    raise SystemExit(main())
