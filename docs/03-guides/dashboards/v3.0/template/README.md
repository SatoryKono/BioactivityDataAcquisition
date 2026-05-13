______________________________________________________________________

Version: 0.1.0
Status: draft
Class: internal-draft
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-13'

______________________________________________________________________

# v3.0 Dashboard Template Index

This directory contains reusable draft specs for the v3.0 dashboard line.

## Source Of Truth

These templates are not normative sources for shipped selector or navigation
behavior.

Normative contracts:

- `docs/03-guides/dashboards/contracts/selector-contracts.yaml`
- `docs/03-guides/dashboards/contracts/navigation-links.yaml`

Reference mirrors:

- `docs/03-guides/dashboards/selector-architecture.md`
- `docs/03-guides/dashboards/variable-reference.md`
- `docs/03-guides/dashboards/navigation-contract.md`
- `docs/03-guides/dashboards/dashboard-requirements-comprehensive.md`
- `docs/03-guides/dashboards/dashboard-audit-checklist.md`

## Template Files

- `run-centric-dashboard-template.md` — execution-aware layout and data-source
  expectations.
- `selector-resolution-contract.md` — current selector behavior plus future
  run-catalog resolution gates.
- `panel-contract.md` — shared panel content and first-screen policy rules.

## Usage Rule

Apply these templates only to future v3 specs or implementations. For shipped
v2 dashboards, use the current JSON and YAML contracts as source of truth.
