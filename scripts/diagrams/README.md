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

## When to Use

| Command | When | Trigger |
|---------|------|---------|
| `lint` | After editing `.mmd`/`.mermaid` files; validates metadata, naming, staleness, palettes | Pre-commit hook + nightly CI |
| `lint-summarize` | After `lint` produces a report; generates human-readable summary | Manual, post-lint |
| `lint-budget` | After lint run; enforces quality budget thresholds | CI gate (nightly) |
| `check-artifacts` | After rendering diagrams; validates SVG/PNG artifacts exist and are non-empty | Nightly CI (post-render) |
| `check-quality-gates` | Before merge; implements DIAG-T018..T023 regression gates (edge markers, classdefs, node counts) | CI gate (`architecture.yml` + nightly) |
| `check-visual-smoke` | After rendering; visual baseline comparison (DIAG-T026) | Nightly CI |
| `check-svg-text` | After rendering SVGs; validates text readability (DIAG-T014..T015) | Nightly CI |
| `check-class-methods` | After modifying class diagrams; validates method render integrity | Manual or nightly |
| `check-pdf-bounds` | After generating PDF bundles; validates image bounds | Manual, post-render |
| `check-padding` | When diagrams have layout issues; analyzes padding problems | Manual, on-demand |
| `fix-operators` | When diagrams contain invalid thick-arrow operators (`==>` → `-->`) | Manual codemod |
| `fix-svg-text` | When SVG text is not rendering properly; injects text fallback | Manual codemod |
| `fix-svg-styles` | When SVG styles are missing or inconsistent; injects standard styles | Manual codemod |
| `fix-foreign-object` | When SVGs contain incompatible foreignObject elements; strips them | Manual codemod |
| `fix-orphans` | After diagram edits leave disconnected nodes; use `--check` to detect, `--fix` to remove | Pre-commit hook or manual |
| `fix-sizes` | When diagrams have inconsistent dimensions; normalizes sizes | Manual codemod |
| `fix-pagebreaks` | When PDF bundles have pagebreak issues | Manual, post-render |
| `render-pdf` | Before release or documentation delivery; generates architecture PDF bundle | Manual, pre-release |
| `render-pdf-desc` | When PDF with full descriptions is needed | Manual, on-demand |
| `render-docx` | When DOCX export is needed for external review | Manual, on-demand |
| `render-views` | When views-focused bundle is needed | Manual, on-demand |
| `nightly` | Full Phase 2 diagram validation (DIAG-T024..T029) | Scheduled nightly (2:20 UTC) |

## Other Files

| File | Description |
|------|-------------|
| `generate_all_bundles.py` | Generate all diagram bundles at once |
| `run_diagram_checks.sh` | Shell wrapper for diagram checks |
| `run_diagram_docs_agent.sh` | Shell wrapper for diagram docs agent |
| `validate_mermaid_syntax.sh` | Validate Mermaid syntax |
| `svg2png.mjs` | Node.js SVG-to-PNG converter |
| `pagebreak.lua` | Pandoc Lua filter for pagebreaks |
