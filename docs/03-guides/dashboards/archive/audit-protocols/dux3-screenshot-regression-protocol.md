______________________________________________________________________

Version: 1.0.0
Status: archived
Class: published
Owner: BioETL Team
Last verified: '2026-07-29'
Issue: '#7073 (DUX3-32)'

______________________________________________________________________

# DUX3 screenshot regression protocol

## Viewports

| Name | Size |
| --- | --- |
| laptop | 1366×768 |
| workstation | 1440×900 |
| desktop | 1920×1080 |

## Selection

Use `reports/observability/dux3-audit-selection-notes.md` defaults.

## Pass criteria (each of 7 UIDs)

1. No internal vertical scrollbar on first-screen triage text panels
2. No clipped Status / First Action / scope-prefixed cells
3. No horizontal scroll except named explorers / wide forensic tables below fold
4. Scope prefixes visible without expanding collapsed rows
5. ID/Processed Records not required above fold on non-Run boards (collapsed shell OK)

## Tooling

Prefer `.codex/skills/grafana-dashboard-render/` when Grafana is up.
Store evidence under `reports/observability/grafana/` (existing tree).

## Baseline expectation

Static JSON enforcement landed with DUX3 residual apply script. Live capture
set is recommended at next render window; absence of live PNGs does not block
contract closeout when inventory + JSON markers are present.
