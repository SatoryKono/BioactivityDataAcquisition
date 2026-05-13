______________________________________________________________________

Version: 0.1.0
Status: draft
Class: internal-draft
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-13'

______________________________________________________________________

# 1. Overview v3.0 Hybrid L0 Spec

## Purpose

`1. Overview` v3 is the L0 answer-first BioETL dashboard. It tells an operator
what is currently broken or degraded and where to drill down first.

It is not a forensic dashboard and must not require exact run selection to
answer its primary question.

## ONE BIG QUESTION

What is currently broken or degraded in BioETL, and what is the first
diagnostic surface the operator should open?

## Why Overview Remains Hybrid

Overview must preserve two roles:

- L0 aggregate/operator summary for immediate triage;
- optional execution-aware context when the selected scope resolves to one
  proven run.

The aggregate role is primary. The resolved-run role is supporting and must not
push the L0 answer below the fold.

## Selectors

Current visible selectors:

- `pipeline`
- `run_type`
- Grafana time range

Current defaults:

- `pipeline=All`
- `run_type=All`

Forbidden current selectors:

- visible `run_id`
- visible `manifest_id`
- visible `execution_fingerprint`
- visible `payload_hash`

Current shipped draft (`bioetl-overview-v3`) keeps this exact selector set.

Future exact-run resolution may use `run_selector_mode` and hidden
`selected_run_id` only after the local run catalog gate is satisfied.

## Resolution Rules

Current mode:

- Overview does not resolve one exact run by default.
- Aggregate L0 panels must work with `All/All` landing scope.
- Missing current-state evidence renders `UNKNOWN`, not `OK`.

Future gated mode:

- explicit exact run selection may resolve to `explicit_run`;
- a scope with exactly one cataloged run may resolve to
  `single_run_auto_resolved`;
- multiple runs resolve to `multiple_runs_in_scope`;
- empty scope resolves to `no_runs_in_scope`;
- unresolved state keeps exact identity panels unavailable.

## Row-By-Row Layout

Row 0: L0 Policy Header

- `ONE BIG QUESTION`
- current scope
- provenance summary
- availability / risk notes
- `First action`

Row 1: Navigation

- panel `id=1000`;
- top-level bus `0..5`;
- global adjunct links as required by navigation contract;
- explicit `var-*` and time handoff.

Row 2: L0 Answer

- System Status;
- Next Action;
- L0 Inputs / trust context.

Row 3: Current Subsystem Summary

- Runtime blockers;
- Data Quality status;
- Gold lifecycle;
- Control Plane trust;
- Provider Global;
- Workflow Selected / Workflow Global.

Row 4: Optional Resolved-Run Context

- shown only when exact execution evidence is resolved;
- may include identity and record movement;
- does not replace aggregate L0 status.

Current shipped draft behavior:

- `bioetl-overview-v3` shows a future-hook `Run Identity` block instead of fake
  exact run metadata;
- `Records / Invariants` documents the accounting model and routes the operator
  to `4. Data Quality` / `Silver Reject Explorer` for exact bounded evidence.

Below Fold: Evidence

- selected-range evidence;
- raw metrics;
- diagnostic tables;
- links to runbooks and explorer surfaces.

Collapsed Rows

- tracing/logging diagnostics;
- verbose raw data;
- forensic detail not needed for first-pass triage.

## Required Panels

- `ONE BIG QUESTION / Scope / Provenance`
- `System Status`
- `Next Action`
- `L0 Inputs`
- `Runtime Blockers`
- `DQ Status`
- `Gold Lifecycle`
- `Control Plane`
- `Provider Global`
- `Workflow Selected`
- `Workflow Global`

## Optional Panels

- resolved run identity;
- resolved run record movement;
- selected-range trends;
- raw metric table;
- logs/traces handoff explanation.

Optional panels must not duplicate canonical KPI ownership unless they add
explicit context or are labeled as mirrors.

## Removed / Forbidden Patterns

- Overview as pure forensic dashboard.
- Visible `run_id` selector.
- Prometheus exact-run labels.
- `includeVars=true` navigation.
- `run_id` or `payload_hash` handoff to non-target dashboards.
- Self-link duplication in the navigation bus.
- Treating `No data` as healthy current status.
- Putting the primary L0 answer below selected-range evidence.

## Handoff Rules

Overview routes first to:

- `2. Runtime` for runtime blockers or execution failures;
- `0. Control Plane` for replay/resume, manifest, ledger, or telemetry trust;
- `4. Data Quality` for quality posture and Silver reject fallout;
- `3. Provider Health` for provider degradation;
- `5. Workflow` for workflow evidence, with reset-scope semantics;
- `Silver Reject Explorer` only for bounded forensic reject investigation.

Navigation must follow `contracts/navigation-links.yaml`.

## Mapping From `bioetl-overview-v2`

Carry forward:

- `System Status`;
- `Next Action`;
- `L0 Inputs`;
- runtime blocker signal;
- DQ status signal;
- Gold lifecycle signal;
- Control Plane signal;
- provider global context;
- workflow selected/global context;
- Silver reject evidence as L0 context and drilldown route.

Keep aggregate:

- landing `All/All` scope;
- current subsystem summaries;
- first drilldown recommendation.

Move below fold or gate:

- exact run identity;
- execution fingerprint;
- manifest/config/contract hash table;
- record-level or payload-level details.

## Acceptance Criteria

- First screen answers the L0 question without exact run selection.
- Overview is documented as hybrid L0, not pure run-centric or forensic.
- Selector behavior references the YAML selector contract.
- Navigation behavior references the YAML navigation contract.
- Exact-run behavior is explicitly gated by a local run catalog.
- No forbidden forensic identifiers leak into non-target dashboard links.
- `No data`, valid zero, and `UNKNOWN` semantics are explicit.
