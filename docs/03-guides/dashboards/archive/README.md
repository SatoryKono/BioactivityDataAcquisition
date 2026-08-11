______________________________________________________________________

Version: 1.0.0
Status: archived
Class: historical
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-08-11'

______________________________________________________________________

# Dashboard audit protocols (archived)

Historical DUX3–DUX7 audit protocols and campaign inventories. **Not operator
guidance.** Canonical shipped surface and active docs live one level up:

| Role | Path |
| --- | --- |
| **Current stable (shipped)** | [../README.md](../README.md), [../dashboard-inventory.md](../dashboard-inventory.md), `grafana/dashboards/*.json` |
| **Operator triage** | [../monitoring-index.md](../monitoring-index.md) |
| **v3 draft (non-shipping)** | [../v3.0/README.md](../v3.0/README.md) |

## Why archived

These materials document 2026-07 UX audit waves (DUX3–DUX7). Execution is complete;
keeping them under active `docs/03-guides/dashboards/` mixed audit residue with
operator docs. Issue #8632 consolidates the tree.

## Protocols

| File | Wave | Notes |
| --- | --- | --- |
| [dux3-audit-selection-notes.md](audit-protocols/dux3-audit-selection-notes.md) | DUX3 | Selection notes (#7054) |
| [dux3-residual-contracts.md](audit-protocols/dux3-residual-contracts.md) | DUX3 | Residual contracts (#7053) |
| [dux3-screenshot-regression-protocol.md](audit-protocols/dux3-screenshot-regression-protocol.md) | DUX3 | Screenshot protocol |
| [dux3-semantic-fixtures.md](audit-protocols/dux3-semantic-fixtures.md) | DUX3 | Semantic fixtures |
| [dux3-first-screen-inventory.json](audit-protocols/dux3-first-screen-inventory.json) | DUX3 | First-screen inventory dump |
| [dux4-title-scope-harness.md](audit-protocols/dux4-title-scope-harness.md) | DUX4 | Title/scope harness (#7089) |
| [dux4-field-override-inventory.json](audit-protocols/dux4-field-override-inventory.json) | DUX4 | Field override inventory |
| [dux4-panel-redesign-matrix.json](audit-protocols/dux4-panel-redesign-matrix.json) | DUX4 | Panel redesign matrix |
| [dux5-copy-dictionary.md](audit-protocols/dux5-copy-dictionary.md) | DUX5 | Operator copy dictionary (#7116) |
| [dux5-screenshot-regression-protocol.md](audit-protocols/dux5-screenshot-regression-protocol.md) | DUX5 | Screenshot protocol (#7133) |
| [dux6-residual-readability.md](audit-protocols/dux6-residual-readability.md) | DUX6 | Residual readability (#7139) |
| [dux7-live-residual-protocol.md](audit-protocols/dux7-live-residual-protocol.md) | DUX7 | Live residual protocol |

## Versioning strategy (active tree)

1. **Stable / shipped:** Dashboard System 2.0 — seven boards `0..6`, docs marked
   `Status: active` / `Class: published` (for example `dashboard-v2-usage.md`,
   panel inventories, design-system, contracts).
2. **Draft / future:** `v3.0/` — execution-aware draft only; not a shipping
   contract (`Status: draft`).
3. **Historical / audit:** this archive — do not link from operator runbooks.

Traceability: issue #8632 (DOC-C1-005).
