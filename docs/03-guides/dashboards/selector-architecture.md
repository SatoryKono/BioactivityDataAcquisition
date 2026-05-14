______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-08'

______________________________________________________________________

# Grafana Selector Architecture

Дата сверки: **2026-05-08**  
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

The repo does **not** currently ship one flat universal selector bar for all
dashboards. It ships a **role-based selector contract** by dashboard family.

## Dashboard families

### Pipeline summary

Dashboards:

- `0. Control Plane`
- `1. Overview`
- `2. Runtime`
- `4. Data Quality`

These surfaces answer pipeline-scoped operator questions and remain
Prometheus-first. Their shipped top-level selectors are built around:

- `pipeline`
- `run_type`
- optional `stage`
- Grafana time range

### Provider-first

Dashboard:

- `3. Provider Health`

This surface is intentionally provider-first:

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
triage. It ships:

- `workflow`
- `status`
- `step_status`
- `step_kind`
- Grafana time range

It does **not** currently ship:

- `pipeline`
- `run_type`
- `run_id`
- exact execution selection

### Forensic explorer

Dashboard:

- `Silver Reject Explorer`

This surface is API-backed and forensic by design. It ships:

- `pipeline`
- `run_type`
- `reason_code`
- `field`
- `run_id`
- `payload_hash`
- Grafana time range

These selectors must stay isolated from Prometheus dashboards.

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

Future execution-aware selectors include:

- `run_selector_mode`
- `started_at`
- `run_id`
- `manifest_id`
- `execution_fingerprint`

These are **not** universal shipped selectors today.

`bioetl-overview-v2` is the current hybrid Overview baseline: it exposes a
control-plane-backed `run_id` selector with default `-` for the optional `ID`
panel only. The selector is not a Prometheus label filter and does not make
exact-run selection a universal dashboard contract. `bioetl-overview-v3`
remains only a draft/snapshot surface for the same selector shape.

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
- `run_id`
- `payload_hash`
- `manifest_id`
- `execution_fingerprint`

These stay out of universal Prometheus dashboards and dashboard-to-dashboard
handoms unless an explicit future contract says otherwise.

## Ship-now selector contract

The current shipped selector model is:

- `0. Control Plane`: `pipeline`, `run_type`, time range
- `1. Overview`: `workflow`, `pipeline`, `run_type`, `run_id`, time range
- `2. Runtime`: `pipeline`, `run_type`, `stage`, time range
- `3. Provider Health`: `provider`, hidden `pipeline_context`, hidden
  detail-only `adapter`, time range
- `4. Data Quality`: `pipeline`, `run_type`, `stage`, time range
- `5. Workflow`: `workflow`, `status`, `step_status`, `step_kind`, time range
- `Silver Reject Explorer`: `pipeline`, `run_type`, `reason_code`, `field`,
  `run_id`, `payload_hash`, time range

This contract is intentionally role-based. It is unified by taxonomy and family
rules, not by forcing every dashboard to expose the same selector list.

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

## Why exact execution selection is not shipped everywhere today

The repo already has canonical execution anchors such as:

- `run_id`
- `manifest_id`
- `execution_fingerprint`
- `PipelineContext.started_at`

But these anchors live in control-plane artifacts, manifests, sidecars, and
diagnostic surfaces. They do not currently exist as one universal Grafana
selector datasource.

Prometheus is also the wrong place to solve this because project rules forbid
high-cardinality runtime identifiers such as `run_id`, `manifest_id`, and
`record_id` as dashboard label selectors.

## Future local-only run catalog

Before BioETL can ship `latest / previous / exact` execution selection on
summary dashboards, it needs a local-only run catalog.

Minimum schema:

- `run_id`
- `pipeline_name`
- `workflow_name` if available
- `run_type`
- `started_at`
- `manifest_id`
- `status`
- optional `provider`
- optional `execution_fingerprint`

Allowed source candidates:

- manifest index
- ledger index
- lightweight local API
- local table-backed run index

Not allowed:

- Prometheus label explosion for execution identifiers

## Future execution selector model

After the run catalog exists, eligible dashboards may adopt:

- `run_selector_mode=latest`
- `run_selector_mode=previous`
- `run_selector_mode=exact`

Resolved hidden context would then be:

- `selected_run_id`
- `selected_manifest_id`
- `selected_started_at`

Initial candidate dashboards:

- `2. Runtime`
- `4. Data Quality`
- `0. Control Plane`
- possibly `1. Overview`

Excluded by default:

- `3. Provider Health`
- `5. Workflow`
- `Silver Reject Explorer`

## Future workflow + pipeline dual-scope evaluation

The repo does **not** currently assume that every dashboard should expose both
`workflow` and `pipeline`.

Dual-scope `workflow + pipeline` is a future candidate only for dashboards that
can prove:

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
