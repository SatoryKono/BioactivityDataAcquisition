______________________________________________________________________

Version: 0.1.0
Status: draft
Class: internal-draft
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-08-05'

______________________________________________________________________

# Dashboards v3.0 Draft Spec

> **Historical draft** — not a shipping contract. Canonical shipped portfolio is
> **7 dashboards** `0..6` (Trust → Run Explorer). See
> [dashboard-inventory.md](../dashboard-inventory.md).

This directory defines the draft v3.0 specification line for future BioETL
dashboards. It is a documentation/spec layer only. It does not replace the
shipped dashboards in `grafana/dashboards/*.json`.

## Scope

v3.0 documents an execution-aware dashboard family and a concrete
`1. Overview` hybrid L0 specification.

Current shipped baseline:

- `bioetl-overview-v2` remains the canonical shipped Overview dashboard
- it preserves the frozen v3 first-screen header and hybrid layout baseline
- it exposes visible `workflow`, `pipeline`, `run_type`, and `run_id`
  selectors
- it keeps `pipeline` + `run_type` as the truthful current-status scope
- `run_id` remains a visible execution-hint bridge, not an exact selector

The shipped dashboard source of truth remains:

- `grafana/dashboards/*.json`
- `docs/03-guides/dashboards/contracts/selector-contracts.yaml`
- `docs/03-guides/dashboards/contracts/navigation-links.yaml`

Markdown files in this directory are explanatory mirrors and draft specs. They
MUST NOT redefine selector, navigation, or time-handoff behavior independently
from the machine-readable contracts.

## Current vs Future Capability

Current implementable mode:

- visible selectors follow the shipped dashboard-family contract;
- `1. Overview` now exposes `workflow` + `pipeline` + `run_type` + `run_id`
  + Grafana time range;
- current status still anchors on `pipeline` + `run_type`;
- `1. Overview` remains an L0 answer-first dashboard, not a forensic surface;
- exact execution fields may be rendered only when a resolved run evidence
  source exists.

Future gated mode:

- exact run selection depends on a local-only run catalog;
- `run_selector_mode=latest|previous|exact` remains design-only until that
  catalog exists;
- `selected_run_id`, `selected_manifest_id`, and `selected_started_at` are
  future hidden context fields, not shipped visible selectors.

## Documents

- `template/README.md` — template index and source-of-truth boundaries.
- `template/run-centric-dashboard-template.md` — execution-aware dashboard
  template. The filename is retained for plan compatibility; the normative term
  is execution-aware.
- `template/selector-resolution-contract.md` — non-normative selector
  resolution mirror and future run-catalog gates.
- `template/panel-contract.md` — shared v3 panel content rules.
- `1-overview.md` — `1. Overview` v3 hybrid L0 spec.

## Non-Goals

- No immediate rewrite of shipped Grafana JSON.
- No new Prometheus high-cardinality labels for `run_id`, `manifest_id`,
  `payload_hash`, `record_id`, or equivalent forensic identifiers.
- No blanket `includeVars=true` dashboard navigation.
- No claim that Overview is fully run-centric.
- No new normative selector or navigation contract outside the YAML contracts.

## Validation Expectations

When v3.0 docs change, validate against the current dashboard policy surfaces:

```bash
uv run python -m scripts.engineering.qa report-dashboard-inventory --check --json
uv run python -m scripts.engineering.qa check-dashboard-visual-semantics
uv run python -m pytest -q tests/integration/test_grafana_selector_contract.py tests/integration/test_grafana_dashboard_links.py tests/integration/test_grafana_variable_reference.py
```

If shipped dashboard behavior changes later, also update the relevant
`grafana/dashboards/*.json`, YAML contracts, and dashboard usage docs in the
same change set.
