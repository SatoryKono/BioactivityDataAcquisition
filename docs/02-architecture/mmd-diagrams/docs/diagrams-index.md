# BioETL Architecture Diagrams Index

*Updated: 2026-02-27*

> **Canonical root:** [docs/02-architecture/mmd-diagrams/](../README.md)
> **Policy:** [POL-LLM-DIAGRAMS-001](../../06-diagram-policy.md)
> **ADR:** [ADR-040](../../decisions/ADR-040-diagram-governance.md)

## Repository Layout

- Canonical `.mmd` sources:
  - `architecture/` — 32 files
  - `class-diagrams/` — 16 files
  - `foundation/` — 54 files
- Decomposed `.mermaid` views:
  - `views/` — 156 files
- Template:
  - `_template.mmd`

## Primary Entry Points

- Architecture overview: [README.md](../README.md)
- View inventory: [diagram-views-inventory.md](diagram-views-inventory.md)
- View decomposition plan: [diagram-views-plan.md](diagram-views-plan.md)
- Workflow guide: [DIAGRAM-WORKFLOW-GUIDE.md](DIAGRAM-WORKFLOW-GUIDE.md)
- Modernization program (draft): [diagram-modernization-program.md](diagram-modernization-program.md)
- Regression test plan: [diagram-regression-test-plan.md](diagram-regression-test-plan.md)

## Canonical Families

- Architecture core (18):
  - `architecture/01-high-level-hexagonal.mmd`
  - `architecture/02-layer-dependency-matrix.mmd`
  - `architecture/03-medallion-data-flow.mmd`
  - `architecture/04-pipeline-execution-flow.mmd`
  - `architecture/05-provider-adapter-hierarchy.mmd`
  - `architecture/06-storage-layer.mmd`
  - `architecture/07-dq-system.mmd`
  - `architecture/08-composite-pipeline.mmd`
  - `architecture/09-observability-stack.mmd`
  - `architecture/10-resilience-patterns.mmd`
  - `architecture/11-configuration-system.mmd`
  - `architecture/12-bootstrap-di-container.mmd`
  - `architecture/13-port-protocol-contracts.mmd`
  - `architecture/14-cli-interface-layer.mmd`
  - `architecture/15-batch-executor-internals.mmd`
  - `architecture/16-transformer-hierarchy.mmd`
  - `architecture/17-security-pii-audit.mmd`
  - `architecture/18-lock-checkpoint-shutdown.mmd`
- Class families (16): `class-diagrams/01-*.mmd` ... `class-diagrams/16-*.mmd`
- Foundation set (54): `foundation/01-*.mmd` ... `foundation/50-*.mmd` (with historical number gaps)

## Render And Validation

```bash
scripts/diagrams/run_diagram_checks.sh --profile pr
scripts/diagrams/run_diagram_checks.sh --profile pr --diagram docs/02-architecture/mmd-diagrams/foundation/30-port-adapter-mapping.mmd

# Or run checks individually:
python3 scripts/diagrams/lint_diagrams.py docs
python3 scripts/diagrams/lint_diagrams.py docs/02-architecture/mmd-diagrams --json > /tmp/diagram-lint.json || true
python3 scripts/diagrams/summarize_diagram_lint.py /tmp/diagram-lint.json
python3 scripts/docs/check_doc_links.py --links
bash scripts/diagrams/validate_mermaid_syntax.sh
bash docs/02-architecture/mmd-diagrams/render.sh
python3 scripts/diagrams/check_svg_text_visibility.py --manifest docs/02-architecture/mmd-diagrams/visual-smoke-manifest.txt
python3 scripts/diagrams/check_diagram_visual_smoke.py --manifest docs/02-architecture/mmd-diagrams/visual-smoke-manifest.txt
python3 scripts/diagrams/check_diagram_quality_gates.py --manifest docs/02-architecture/mmd-diagrams/quality-gate-manifest.txt
```

## Notes

- New canonical diagrams must be added as `.mmd` under `mmd-diagrams/**`.
- Decomposed views are maintained in `mmd-diagrams/views/*.mermaid`.
- Legacy snapshots may still exist in `docs/02-architecture/diagrams/mermaid/`, but they are not canonical for new work.
