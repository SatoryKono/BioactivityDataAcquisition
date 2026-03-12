# scripts/diagrams — Diagram Quality & Render

Diagram lint, render, quality pipeline, and visual verification tooling.

## Unified Entry Point

```bash
python -m scripts.diagrams --help
python -m scripts.diagrams <command> [args...]
```

## Commands

### Lint

| Command | Script | Description |
|---------|--------|-------------|
| `lint` | `lint_diagrams.py` | Lint architecture diagrams (.mmd/.mermaid) |
| `lint-summarize` | `summarize_diagram_lint.py` | Summarize diagram lint report |
| `lint-budget` | `enforce_diagram_quality_budget.py` | Enforce diagram quality budget |

### Check

| Command | Script | Description |
|---------|--------|-------------|
| `check-artifacts` | `check_diagram_artifacts.py` | Check diagram artifact manifest |
| `check-quality-gates` | `check_diagram_quality_gates.py` | Check diagram quality gates |
| `check-visual-smoke` | `check_diagram_visual_smoke.py` | Visual smoke test for diagrams |
| `check-svg-text` | `check_svg_text_visibility.py` | Check SVG text visibility |
| `check-class-methods` | `check_class_method_render_integrity.py` | Check class method render integrity |
| `check-pdf-bounds` | `check_pdf_image_bounds.py` | Check PDF image bounds |
| `check-padding` | `report_diagram_padding.py` | Report diagram padding issues |

### Fix

| Command | Script | Description |
|---------|--------|-------------|
| `fix-operators` | `fix_mermaid_operators.py` | Fix Mermaid operators |
| `fix-svg-text` | `add_svg_text_fallback.py` | Add SVG text fallback |
| `fix-svg-styles` | `inject_svg_styles.py` | Inject SVG styles |
| `fix-foreign-object` | `strip_svg_foreign_object.py` | Strip SVG foreignObject elements |
| `fix-orphans` | `prune_orphan_nodes.py` | Prune orphan nodes in diagrams |
| `fix-sizes` | `uniform_diagram_sizes.py` | Uniform diagram sizes |
| `fix-pagebreaks` | `fix_pagebreaks_in_bundles.py` | Fix pagebreaks in bundles |

### Render

| Command | Script | Description |
|---------|--------|-------------|
| `render-pdf` | `generate_architecture_bundle.py` | Generate architecture PDF bundle |
| `render-pdf-desc` | `generate_with_descriptions_pdf.py` | Generate PDF with descriptions |
| `render-docx` | `generate_with_descriptions_docx.py` | Generate DOCX with descriptions |
| `render-views` | `generate_views_bundle.py` | Generate views bundle |

### Suite

| Command | Script | Description |
|---------|--------|-------------|
| `nightly` | `run_diagram_nightly_suite.py` | Run full diagram nightly suite |

## Other Files

| File | Description |
|------|-------------|
| `generate_all_bundles.py` | Generate all diagram bundles at once |
| `run_diagram_checks.sh` | Shell wrapper for diagram checks |
| `run_diagram_docs_agent.sh` | Shell wrapper for diagram docs agent |
| `validate_mermaid_syntax.sh` | Validate Mermaid syntax |
| `svg2png.mjs` | Node.js SVG-to-PNG converter |
| `pagebreak.lua` | Pandoc Lua filter for pagebreaks |
