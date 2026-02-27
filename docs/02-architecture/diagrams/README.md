# Diagram governance index

This folder stores governance artifacts for BioETL diagram optimization.

## Files

- `.mermaidrc.json` — shared Mermaid renderer configuration.
- `_template.mmd` — baseline template with required metadata.
- `00-legend.mmd` — canonical legend for diagram semantics.

## Authoring policy

1. Every Mermaid source MUST include:
   - `%%{init: ...}%%`
   - `%% View: ... %%`
1. User-facing diagrams SHOULD stay below 20 nodes.
1. If a full view is overloaded, create split views:
   - `*-overview`
   - `*-domain`
   - `*-infra`
   - `*-dataflow`

## Validation commands

```bash
python3 scripts/diagram_audit.py --docs docs --out-md /tmp/diagram_inventory.md --out-csv /tmp/diagram_inventory.csv --use-git
bash scripts/validate_diagrams.sh docs
```
