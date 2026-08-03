______________________________________________________________________

Version: 0.1.0
Status: draft
Class: internal-draft
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-13'

______________________________________________________________________

# Selector Resolution Contract Mirror

This document is a non-normative v3.0 mirror. The normative selector contract is
`docs/03-guides/dashboards/contracts/selector-contracts.yaml`.

## Current Shipped Mode

Current BioETL dashboards are role-based, not one universal selector bar.

Pipeline-summary dashboards:

- visible selectors: `pipeline`, `run_type`;
- optional visible selector: `stage` on Runtime and Data Quality;
- exact execution identifiers are not visible selectors.

Provider-first dashboard:

- visible selector: `provider`;
- hidden context: `pipeline_context`;
- detail-only hidden selector: `adapter`.

Workflow evidence dashboard:

- visible selectors: `workflow`, `status`, `step_status`, `step_kind`;
- hidden handoff context: `pipeline_context`, `run_type_context`,
  `provider_context`;
- no visible `pipeline` / `run_type`.

Forensic explorer:

- visible selectors: `pipeline`, `run_type`, `reason_code`, `field`,
  `run_id`, `payload_hash`;
- forensic selectors remain local to the explorer.

## Current Overview v3 Selector Rule

`1. Overview` v3 remains a pipeline-summary L0 dashboard unless the YAML
contracts are changed.

Current selectors:

- `pipeline`
- `run_type`
- Grafana time range

Current defaults:

- `pipeline=All`
- `run_type=All`

These defaults preserve the landing-page L0 behavior: the dashboard can answer
what is currently broken or degraded without selecting one exact run.

## Forbidden Current Behavior

Until a local run catalog exists, v3 specs must not require:

- visible `run_id` on Overview, Runtime, Data Quality, or Control Plane;
- visible `manifest_id` or `execution_fingerprint` selectors;
- Prometheus labels for exact execution identity;
- blanket `includeVars=true` handoff;
- propagation of `run_id` or `payload_hash` into non-target dashboards.

## Future Run-Catalog-Gated Mode

The future run catalog is design-only and local-only.

Required properties:

- backed by manifest index, ledger index, local API, or lightweight local table;
- supports `latest`, `previous`, and `exact` resolution;
- avoids Prometheus label explosion.

Minimum fields:

- `run_id`
- `pipeline_name`
- `workflow_name`
- `run_type`
- `started_at`
- `manifest_id`
- `status`

Optional fields:

- `provider`
- `execution_fingerprint`

Future selector:

- `run_selector_mode=latest|previous|exact`

Future hidden resolved context:

- `selected_run_id`
- `selected_manifest_id`
- `selected_started_at`

## Resolution States

Use these labels only after a run catalog or equivalent local source exists:

- `explicit_run`
- `single_run_auto_resolved`
- `multiple_runs_in_scope`
- `no_runs_in_scope`
- `unresolved`

Before that source exists, Overview v3 must describe exact-run resolution as
blocked, not partially implemented.
