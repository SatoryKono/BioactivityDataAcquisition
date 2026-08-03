# scripts/diagrams — Diagram Quality & Render

Diagram lint, render, quality pipeline, and visual verification tooling.

## Unified Entry Point

```bash
python -m scripts.diagrams --help
python -m scripts.diagrams <command> [args...]
```

## Commands

### Lint

| Command          | Script                              | Description                                |
| ---------------- | ----------------------------------- | ------------------------------------------ |
| `lint`           | `lint_diagrams.py`                  | Lint architecture diagrams (.mmd/.mermaid) |
| `lint-summarize` | `summarize_diagram_lint.py`         | Summarize diagram lint report              |
| `lint-budget`    | `enforce_diagram_quality_budget.py` | Enforce diagram quality budget             |

### Check

| Command               | Script                                                    | Description                                                           |
| --------------------- | --------------------------------------------------------- | --------------------------------------------------------------------- |
| `checks`              | `run_diagram_checks.sh`                                   | Run unified diagram validation profiles (`pr`, `nightly`, `quick`)    |
| `check-artifacts`     | `check_diagram_artifacts.py`                              | Check required SVG artifacts and optional PNG compatibility artifacts |
| `check-quality-gates` | `check_diagram_quality_gates.py`                          | Check diagram quality gates                                           |
| `check-visual-smoke`  | `check_diagram_visual_smoke.py`                           | Visual smoke test for diagrams; supports `--json-out`                 |
| `check-svg-text`      | `check_svg_text_visibility.py`                            | Check SVG text visibility                                             |
| `check-class-methods` | `scripts/diagrams/check_class_method_render_integrity.py` | Check class method render integrity                                   |
| `check-pdf-bounds`    | `check_pdf_image_bounds.py`                               | Check PDF image bounds                                                |
| `check-padding`       | `report_diagram_padding.py`                               | Report diagram padding issues                                         |

### Fix

| Command              | Script                                          | Description                      |
| -------------------- | ----------------------------------------------- | -------------------------------- |
| `apply-elk`          | `apply_elk_layout.py`                           | Add or audit ELK init            |
| `differentiate-linkstyle` | `differentiate_linkstyle.py`                | Add semantic linkStyle groups    |
| `fix-operators`      | `fix_mermaid_operators.py`                      | Fix Mermaid operators            |
| `fix-svg-text`       | `add_svg_text_fallback.py`                      | Add SVG text fallback            |
| `fix-svg-styles`     | `scripts/diagrams/inject_svg_styles.py`         | Inject SVG styles                |
| `fix-foreign-object` | `strip_svg_foreign_object.py`                   | Strip SVG foreignObject elements |
| `harmonize-link-styles` | `harmonize_link_styles.py`                   | Harmonize rendered SVG links     |
| `fix-orphans`        | `prune_orphan_nodes.py`                         | Prune orphan nodes in diagrams   |
| `fix-sizes`          | `uniform_diagram_sizes.py`                      | Uniform diagram sizes            |
| `fix-pagebreaks`     | `scripts/diagrams/fix_pagebreaks_in_bundles.py` | Fix pagebreaks in bundles        |

### Render

| Command               | Script                                             | Description                                                |
| --------------------- | -------------------------------------------------- | ---------------------------------------------------------- |
| `generate-dataflows`  | `generate_pipeline_dataflows.py`                   | Generate source-backed pipeline views, passport, JSON IR, and field CSV |
| `docs-agent`          | `run_diagram_docs_agent.sh`                        | Run checks + DOCX export + PDF export pipeline             |
| `render-pdf`          | `generate_all_bundles.py --collection architecture` | Refresh architecture Markdown bundle via the canonical generator |
| `render-pdf-desc`     | `generate_with_descriptions_pdf.py`                | Generate PDF with descriptions                             |
| `render-docx`         | `generate_with_descriptions_docx.py`               | Generate DOCX with descriptions                            |
| `render-views`        | `generate_all_bundles.py --collection views`       | Refresh views Markdown bundle via the canonical generator  |
| `render-desc-indexes` | `scripts/diagrams/generate_description_indexes.py` | Refresh family-oriented description indexes                |

### Suite

| Command   | Script                         | Description                    |
| --------- | ------------------------------ | ------------------------------ |
| `nightly` | `run_diagram_nightly_suite.py` | Run full diagram nightly suite |

## When to Use

| Command               | When                                                                                                        | Trigger                                |
| --------------------- | ----------------------------------------------------------------------------------------------------------- | -------------------------------------- |
| `checks`              | When full diagram validation profile execution is needed from one entrypoint                                | Manual, CI wrappers                    |
| `lint`                | After editing `.mmd`/`.mermaid` files; validates metadata, naming, staleness, palettes                      | Pre-commit hook + nightly CI           |
| `lint-summarize`      | After `lint` produces a report; generates human-readable summary                                            | Manual, post-lint                      |
| `lint-budget`         | After lint run; enforces quality budget thresholds                                                          | CI gate (nightly)                      |
| `check-artifacts`     | After rendering diagrams; validates required SVG artifacts and, when requested, PNG compatibility artifacts | Nightly CI (post-render)               |
| `check-quality-gates` | Before merge; implements DIAG-T018..T023 regression gates (edge markers, classdefs, node counts)            | CI gate (`docs.yml` + nightly) |
| `check-visual-smoke`  | After rendering; visual baseline comparison (DIAG-T026)                                                     | Nightly CI                             |
| `check-svg-text`      | After rendering SVGs; validates text readability (DIAG-T014..T015)                                          | Nightly CI                             |
| `check-class-methods` | After modifying class diagrams; validates method render integrity                                           | Manual or nightly                      |
| `check-pdf-bounds`    | After generating PDF bundles; validates image bounds                                                        | Manual, post-render                    |
| `check-padding`       | When diagrams have layout issues; analyzes padding problems                                                 | Manual, on-demand                      |
| `apply-elk`           | When large flowchart diagrams need ELK init or routing normalization                                        | Manual codemod                         |
| `differentiate-linkstyle` | When dense flowcharts need semantic linkStyle classes                                                   | Manual codemod                         |
| `harmonize-link-styles` | After rendering when SVG link styles need cross-diagram harmonization                                     | Manual/CI post-render                  |
| `fix-operators`       | When diagrams contain invalid thick-arrow operators (`==>` → `-->`)                                         | Manual codemod                         |
| `fix-svg-text`        | When SVG text is not rendering properly; injects text fallback                                              | Manual codemod                         |
| `fix-svg-styles`      | When SVG styles are missing or inconsistent; injects standard styles                                        | Manual codemod                         |
| `fix-foreign-object`  | When SVGs contain incompatible foreignObject elements; strips them                                          | Manual codemod                         |
| `fix-orphans`         | After diagram edits leave disconnected nodes; use `--check` to detect, `--fix` to remove                    | Pre-commit hook or manual              |
| `fix-sizes`           | When diagrams have inconsistent dimensions; normalizes sizes                                                | Manual codemod                         |
| `fix-pagebreaks`      | When PDF bundles have pagebreak issues                                                                      | Manual, post-render                    |
| `docs-agent`          | When diagram checks and export artifacts must be regenerated together                                       | Manual, release prep                   |
| `render-pdf`          | When the architecture Markdown bundle needs refresh; legacy collection-specific entrypoint                  | Manual, on-demand                      |
| `render-pdf-desc`     | When PDF with full descriptions is needed                                                                   | Manual, on-demand                      |
| `render-docx`         | When DOCX export is needed for external review                                                              | Manual, on-demand                      |
| `render-views`        | When the views Markdown bundle needs refresh                                                                | Manual, on-demand                      |
| `render-desc-indexes` | When description indexes drift or card counts change                                                        | Manual, on-demand                      |
| `generate-dataflows`  | After `chembl_activity` config, filters, transformer, or Silver/Gold contracts change                        | Docs CI drift gate                     |
| `nightly`             | Full Phase 2 diagram validation (DIAG-T024..T029)                                                           | Scheduled nightly (2:20 UTC)           |

## Other Files

| File                                                         | Description                                                                                   |
| ------------------------------------------------------------ | --------------------------------------------------------------------------------------------- |
| `scripts/diagrams/generate_all_bundles.py`                   | Canonical Markdown bundle generator; supports `--collection` for targeted publication refresh |
| `scripts/diagrams/generate_description_indexes.py`           | Canonical generator for family-oriented description indexes                                   |
| `scripts/diagrams/generate_package_family_class_diagrams.py` | Supplemental package-family class-diagram generator                                           |
| `scripts/diagrams/diagram_paths.py`                          | Shared diagram path/constants helper used by rendering and validation tooling                 |
| `scripts/diagrams/run_diagram_checks.sh`                     | Canonical shell entrypoint for diagram validation profiles                                    |
| `scripts/diagrams/run_diagram_docs_agent.sh`                 | Canonical shell entrypoint for checks + export pipeline                                       |
| `scripts/diagrams/generate_with_descriptions_docx.py`        | Canonical DOCX exporter for description bundles                                               |
| `scripts/diagrams/generate_with_descriptions_pdf.py`         | Canonical PDF exporter for description bundles                                                |
| `scripts/diagrams/validate_mermaid_syntax.sh`                | Validate Mermaid syntax, including optional active-doc embedded fences via `--include-embedded` |
| `scripts/diagrams/svg2png.mjs`                               | Node.js SVG-to-PNG converter                                                                  |
| `scripts/diagrams/pagebreak.lua`                             | Pandoc Lua filter for pagebreaks                                                              |

## Bundle Generation Contract

- `scripts/diagrams/generate_all_bundles.py` is the canonical Markdown bundle generator for `architecture`, `class-diagrams`, `foundation`, and `views`.
- `scripts/diagrams/run_diagram_checks.sh`, `run_diagram_docs_agent.sh`, `generate_with_descriptions_docx.py`, and `generate_with_descriptions_pdf.py` are the canonical operational entrypoints; legacy `docs/00-project/ai/agents/scripts/diagrams/py-doc-bot-*` files are compatibility wrappers only.
- Markdown bundles prefer `svg/` renders as the primary publication artifact and fall back to `png/` only when an SVG is missing.
- `scripts/diagrams/generate_description_indexes.py` is the canonical generator for `descriptions/INDEX.md` and `descriptions/class/INDEX.md`.
- `python -m scripts.diagrams render-pdf` and `python -m scripts.diagrams render-views` are the supported public entrypoints for collection-specific bundle refresh.
- `visual-smoke.txt` remains the canonical PR-sized SVG smoke manifest; `visual-smoke-extended.txt` is the nightly blocking tier, `visual-smoke-broad.txt` is the nightly warn-only expansion tier, and `png-compatibility.txt` is a smaller curated manifest for PNG compatibility checks.
- `check_diagram_visual_smoke.py --json-out <path>` writes `diagram-visual-smoke-report-v1` machine-readable status for CI and local diagnostics.
- When bundle drift is corrected, prefer regenerating the narrow affected collection via `generate_all_bundles.py --collection <name>` instead of broad refresh of every derived artifact.
