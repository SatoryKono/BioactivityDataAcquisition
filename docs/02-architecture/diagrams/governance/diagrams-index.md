______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# BioETL Architecture Diagrams Index

*Updated: 2026-03-19*

> **Canonical root:** [docs/02-architecture/diagrams/](../README.md)
> **Diagram governance:** [ADR-040](../../decisions/ADR-040-diagram-governance.md)
> **ADR:** [ADR-040](../../decisions/ADR-040-diagram-governance.md)

## Repository Layout

- Canonical `.mmd` sources:
  - `architecture/` — 82 files
  - `class-diagrams/` — 19 files
  - `foundation/` — 55 files
- Decomposed `.mermaid` views:
  - `views/` — 162 files
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

- Architecture core (48 primary topics; 82 `.mmd` files including decomposed sub-diagrams):
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
- Class families (19 `.mmd` files): `class-diagrams/01-*.mmd` ... `class-diagrams/16-*.mmd`, including focused method/operation catalogs (`01a`, `08a`, `14a`)
- Foundation set (55 `.mmd` files): `foundation/01-*.mmd` ... `foundation/50-*.mmd` (with historical number gaps)

## Render And Validation

```bash
scripts/diagrams/run_diagram_checks.sh --profile pr
scripts/diagrams/run_diagram_checks.sh --profile pr --diagram docs/02-architecture/diagrams/foundation/30-port-adapter-mapping.mmd

# Or run checks individually:
uv run python -m scripts.diagrams lint docs
uv run python scripts/diagrams/lint_diagrams.py docs/02-architecture/diagrams --json > /tmp/diagram-lint.json || true
uv run python -m scripts.diagrams lint-summarize /tmp/diagram-lint.json
uv run python -m scripts.docs check-links --links
bash scripts/diagrams/validate_mermaid_syntax.sh
bash docs/02-architecture/diagrams/tooling/render.sh
uv run python -m scripts.diagrams check-svg-text --manifest docs/02-architecture/diagrams/manifests/visual-smoke.txt
uv run python -m scripts.diagrams check-visual-smoke --manifest docs/02-architecture/diagrams/manifests/visual-smoke.txt
uv run python -m scripts.diagrams check-quality-gates --manifest docs/02-architecture/diagrams/manifests/quality-gates.txt
```

## Notes

- New canonical diagrams must be added as `.mmd` under `diagrams/**`.
- Decomposed views are maintained in `diagrams/views/*.mermaid`.
- Rendered `svg/` artifacts are the primary maintained publication output; sibling `png/` trees remain compatibility/export outputs and should be refreshed where those surfaces are still used.
- Legacy snapshots may still exist in `docs/02-architecture/diagrams/mermaid/`, but they are not canonical for new work.

## 2026-05-12 Expansion Batch

- Planning artifact: [diagram-expansion-2026-05-12.md](diagram-expansion-2026-05-12.md)
- Added 25 new canonical architecture diagrams focused on control-plane, composite preflight, provider-specific runtime flows, and config/traceability surfaces.
