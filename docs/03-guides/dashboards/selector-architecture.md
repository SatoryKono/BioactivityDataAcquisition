______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-16'

______________________________________________________________________

# Grafana Selector Architecture

Дата сверки: **2026-05-16**
Источник истины: `grafana/dashboards/*.json`

Machine-readable SSOT:
`docs/03-guides/dashboards/contracts/selector-contracts.yaml`

## Purpose

This document explains how BioETL shipped dashboards classify and use selectors.
It separates:

- current operator-safe dashboard filtering
- hidden cross-dashboard handoff context
- future execution-aware selection
- forensic-only selectors

The repo ships a shared **operator context shell** on primary dashboards `0..5`
and keeps role-specific selectors on top of that shell. The shell is not a
promise that every selector filters every current-status query.

Shared visible context shell:

- `workflow`
- `pipeline`
- `run_type`
- `run_id`

Role-specific extensions remain dashboard-owned. `run_id` is HTTP-backed
control-plane identity context only and MUST NOT become a Prometheus label.
The control-plane selector resolver exposes `/ops/control-plane/selector-context`
for coherent local selector tuples and `/ops/control-plane/filter-options` for
Grafana option lists.
Dashboard-to-dashboard navigation passes only the shared shell
`workflow/pipeline/run_type` plus target-specific bounded vars; it does not rely
on native Grafana semantic variable copying.

## Dashboard families

### Pipeline summary

Dashboards:

- `0. Control Plane`
- `1. Overview`
- `2. Runtime`
- `4. Data Quality`

These surfaces answer pipeline-scoped operator questions and remain
Prometheus-first for Status/diagnostic panels. Their shipped top-level
selectors include the shared context shell and optional role-specific filters:

- `workflow` as context/evidence
- `pipeline`
- `run_type`
- `run_id` as local identity context only
- optional `stage`
- Grafana time range

### Provider-first

Dashboard:

- `3. Provider Health`

This surface is intentionally provider-first, while still exposing the shared
context shell for provenance, identity, and processed-record evidence:

- `workflow` as context/evidence
- `pipeline` / `run_type` as context shell
- `run_id` as local identity context only
- visible `provider`
- hidden `pipeline_context`
- hidden detail-only `adapter`
- Grafana time range

`pipeline_context` preserves return-path context and is not a first-class
provider business selector.

### Workflow evidence

Dashboard:

- `5. Workflow`

This surface is selected-range workflow evidence, not current-state runtime
triage. It ships the shared context shell plus workflow-local filters:

- `workflow`
- `pipeline` / `run_type` as context shell
- `run_id` as local identity context only
- `status`
- `step_status`
- `step_kind`
- Grafana time range

### Forensic explorer

Dashboard:

- `Silver Reject Explorer`

This surface is API-backed and forensic by design. It ships:

- `pipeline`
- `run_type`
- `reason_code`
- `field`
- `quarantine_run_id`
- `payload_hash`
- Grafana time range

These selectors must stay isolated from Prometheus dashboards. The
`quarantine_run_id` variable calls the Quarantine API with backend
`dimension=run_id`, but its Grafana name is intentionally distinct from the
Control Plane `run_id` identity selector.

## Selector taxonomy

### Scope selectors

- `pipeline`
- `workflow`
- `provider`
- `stage`

These decide the business scope of the dashboard question.

### State filters

- `run_type`
- `status`
- `step_status`
- `step_kind`

These refine the selected scope without identifying one exact execution.

### Execution selectors

Execution-aware selectors include:

- `run_id`
- `run_selector_mode`
- `started_at`
- `manifest_id`
- `execution_fingerprint`

`run_id` is shipped in the primary context shell, backed by the local
control-plane HTTP surface. It selects local identity/provenance rows, not
Prometheus time-series. `run_selector_mode`, `started_at`, `manifest_id`, and
`execution_fingerprint` remain future/local-catalog candidates.

`bioetl-overview-v2` is the current hybrid Overview baseline and
`bioetl-overview-v3` remains a draft/snapshot for the same selector shape.

### Hidden context selectors

Currently shipped:

- `pipeline_context`
- `adapter`

Future reserved:

- `workflow_context`
- `selected_run_id`
- `selected_manifest_id`
- `selected_started_at`

### Forensic-only selectors

- `reason_code`
- `field`
- `quarantine_run_id`
- `payload_hash`
- `manifest_id`
- `execution_fingerprint`

These stay out of Prometheus dashboard label selectors and dashboard-to-dashboard
handoffs unless an explicit future contract says otherwise.

## Ship-now selector contract

The current shipped selector model is:

- `1. Overview`: `workflow`, `pipeline`, `run_type`, `run_id`, time range
- `0. Control Plane`: `workflow`, `pipeline`, `run_type`, `run_id`, time range
- `2. Runtime`: `workflow`, `pipeline`, `run_type`, `run_id`, `stage`, time range
- `3. Provider Health`: `workflow`, `pipeline`, `run_type`, `run_id`,
  `provider`, hidden `pipeline_context`, hidden detail-only `adapter`, time range
- `4. Data Quality`: `workflow`, `pipeline`, `run_type`, `run_id`, `stage`, time range
- `5. Workflow`: `workflow`, `pipeline`, `run_type`, `run_id`, `status`,
  `step_status`, `step_kind`, time range
- `Silver Reject Explorer`: `pipeline`, `run_type`, `reason_code`, `field`,
  `quarantine_run_id`, `payload_hash`, time range

This contract is unified by the shared context shell, taxonomy, and family
rules. It does not force every Status panel to consume every visible selector.

## Hidden handoff contract

Hidden selector propagation is a separate contract from visible filtering.

Shipped hidden handoff:

- `pipeline_context`

Shipped hidden detail-only scope:

- `adapter`

Rules:

- hidden vars preserve context or detail-only scope
- hidden vars do not automatically become visible selectors
- forensic identifiers do not propagate across dashboards by default
- no blanket `includeVars=true` semantics for cross-dashboard navigation

## Why exact execution filtering is not shipped everywhere today

The repo already has canonical execution anchors such as:

- `run_id`
- `manifest_id`
- `execution_fingerprint`
- `PipelineContext.started_at`

`run_id` is now exposed through the shared context shell, but it remains local
identity/provenance context. The other anchors live in control-plane artifacts,
manifests, sidecars, and diagnostic surfaces. They do not currently exist as a
universal Grafana filtering model for Prometheus-backed current-status panels.

Prometheus is also the wrong place to solve this because project rules forbid
high-cardinality runtime identifiers such as `run_id`, `manifest_id`, and
`record_id` as dashboard label selectors.

## Shipped local selector resolver

BioETL now ships a local-only selector resolver backed by run manifests and run
ledger terminal events. It supports the shared context shell without adding
high-cardinality Prometheus labels.

Endpoint surfaces:

- `/ops/control-plane/filter-options`
- `/ops/control-plane/selector-context`

Resolved fields:

- `run_id`
- `pipeline`
- `workflow` if available
- `run_type`
- `manifest_id`
- `status`
- `completed_at`
- optional `provider`

Resolution rules:

- exact `run_id` wins when selected
- otherwise `workflow` / `pipeline` / `run_type` scope resolves to the latest
  terminal run by ledger event time
- manifest `created_at` is fallback only when terminal ledger time is absent
- the dashboard `run_id` option list includes `-` as the no-exact-run default

Not allowed:

- Prometheus label explosion for execution identifiers
- cyclic Grafana variable dependencies
- dashboard-to-dashboard propagation of `run_id`

Native Grafana query variables can consume resolver option lists, but they
cannot safely auto-write sibling visible selectors. Full bidirectional
auto-selection requires a custom selector shell/plugin or another UI surface
that calls `/ops/control-plane/selector-context` and writes all variables as one
transaction.

## Future execution selector model

After the shipped resolver is paired with an execution-aware selector shell,
eligible dashboards may adopt:

- `run_selector_mode=latest`
- `run_selector_mode=previous`
- `run_selector_mode=exact`

Resolved hidden context would then be:

- `selected_run_id`
- `selected_manifest_id`
- `selected_started_at`

Initial candidate surfaces are the shared `ID` panels and any future
control-plane-backed tables. Prometheus-backed Status panels remain excluded
unless a future ADR explicitly defines low-cardinality projection semantics.

## Workflow + pipeline dual-scope evaluation

Primary dashboards expose both `workflow` and `pipeline` for context, but this
does not mean every current-status query evaluates the exact intersection.

Truthful `workflow + pipeline` filtering remains limited to panels that can
prove:

- truthful intersection semantics
- run-catalog-backed resolution
- explicit `No data` behavior for empty intersections

Candidate dashboards:

- `2. Runtime`
- `4. Data Quality`
- `0. Control Plane`
- maybe `1. Overview`

Excluded by default:

- `3. Provider Health`
- `5. Workflow`
- `Silver Reject Explorer`

## Validation surfaces

- `docs/03-guides/dashboards/contracts/selector-contracts.yaml`
- `docs/03-guides/dashboards/variable-reference.md`
- `tests/integration/test_grafana_selector_contract.py`
- `tests/integration/test_grafana_variable_reference.py`
- `tests/integration/test_grafana_config.py`

## Related references

- `docs/03-guides/dashboards/variable-reference.md`
- `docs/03-guides/dashboards/dashboard-v2-usage.md`
- `docs/03-guides/dashboards/navigation-contract.md`
- `docs/03-guides/dashboards/contracts/navigation-links.yaml`
