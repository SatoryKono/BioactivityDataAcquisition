# Scripts Layout

This directory is being consolidated by function to reduce discovery time and
make CI entrypoints explicit.

## Current Status

| Area | Canonical Path | Status |
|---|---|---|
| Diagram tooling | `scripts/diagrams/` | Done (phase 1) |
| CI helpers | `scripts/ci/` | Existing |
| Dev helpers | `scripts/dev/` | Existing |
| Config tooling | `scripts/config/` | Planned |
| Docs tooling | `scripts/docs/` | Planned |
| Data tooling | `scripts/data/` | Planned |
| Quality/architecture tooling | `scripts/quality/` | Planned |
| Ops/security tooling | `scripts/ops/`, `scripts/security/` | Planned |

## Diagram Scripts

Canonical diagram scripts now live in:

- `scripts/diagrams/`

## Migration Rule

For new automation, use canonical paths only:

- `scripts/diagrams/run_diagram_checks.sh`
- `scripts/diagrams/lint_diagrams.py`
- `scripts/diagrams/validate_mermaid_syntax.sh`
- `scripts/diagrams/generate_with_descriptions_docx.py`
- `scripts/diagrams/generate_with_descriptions_pdf.py`
- `scripts/diagrams/run_diagram_docs_agent.sh`

Do not add new references to legacy wrapper paths under `scripts/`.

## Scripts Inventory Governance

Use the dedicated drift checker to keep script call-sites and status inventory
in sync:

- Check: `python scripts/check_scripts_inventory.py --check --manifest reports/quality/scripts_inventory_manifest.json`
- Update: `python scripts/check_scripts_inventory.py --update --manifest reports/quality/scripts_inventory_manifest.json`

Make targets:

- `make scripts-inventory-check`
- `make scripts-inventory-update`
