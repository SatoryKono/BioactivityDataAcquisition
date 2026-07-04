______________________________________________________________________

Version: 0.1.0
Status: draft
Class: internal-draft
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-13'

______________________________________________________________________

# Execution-Aware Dashboard Template

The filename keeps the original planning term `run-centric`, but the template is
intentionally named execution-aware. Exact run selection is a future capability
blocked by the local run catalog contract.

## Purpose

Use this template for dashboards that need to combine:

- operator answer-first status;
- current dashboard-family selectors;
- optional resolved-run context when a single execution can be proven;
- explicit handoff to deeper diagnostic surfaces.

Do not use it to turn L0/L1 operator dashboards into forensic record explorers.

## Applicability

Use this template when:

- the dashboard has one `ONE BIG QUESTION`;
- first screen can answer status and first action without exact run selection;
- resolved-run details are supporting context rather than the primary answer;
- selector behavior can be described through the existing selector contract or
  the future run-catalog gate.

Do not use this template when:

- the dashboard is provider-first and should remain selected by `provider`;
- the dashboard is workflow evidence and should remain selected by workflow
  status/step fields;
- the dashboard is forensic-only, such as Silver Reject Explorer;
- the design requires Prometheus labels for high-cardinality execution IDs.

## Layout Grammar

Row 0: Policy Header

- `ONE BIG QUESTION`
- current scope
- provenance summary
- availability / risk notes
- `First action`

Row 1: Navigation

- navigation panel `id=1000`;
- top-level bus `0. Control Plane`, `1. Overview`, `2. Runtime`,
  `3. Provider Health`, `4. Data Quality`, `5. Workflow`;
- current dashboard visible as disabled item;
- adjunct links when required by the navigation contract.

Row 2: Scope + Status

- selected dashboard-family scope;
- current verdict;
- cause summary;
- trust/no-data marker only when required to interpret the verdict.

Row 3: Records + Next Action

- aggregate record movement and quality posture;
- no exact run fields unless a resolved run evidence source exists;
- action text derived from verdict class.

Below Fold: Resolved Execution Context

- optional exact run identity;
- optional control-plane/manifest evidence;
- selected-range evidence and raw diagnostic tables.

Collapsed Rows

- tracing-only, raw, verbose, or forensic details;
- no critical first-pass signal may live only in a collapsed row.

## Datasource Expectations

Current shipped mode:

- selectors: current dashboard-family contract;
- status: Prometheus current-status recording rules or bounded aggregate
  metrics;
- records: Prometheus metrics or control-plane aggregates;
- next action: rule-based text or low-cardinality route logic.

Future gated mode:

- selectors and identity: local run catalog backed by manifest, ledger, local
  API, or lightweight local table;
- exact identity fields: hidden resolved context, not Prometheus labels;
- no high-cardinality Prometheus label explosion.

## Severity Semantics

Use BioETL canonical status vocabulary:

- `OK`
- `WARN`
- `CRIT`
- `UNKNOWN`

For L0/L1 status cards:

- `0` maps to `OK`;
- `1` maps to `WARN`;
- `>=2` maps to `CRIT`;
- `null` maps to `UNKNOWN`.

## No-Data Policy

- Current-status panels must not silently treat `No data` as `OK`.
- Use `or vector(0)` only for true zero-event counters.
- Missing status data remains `UNKNOWN`.
- HTTP-backed or control-plane-backed exact-run blocks must distinguish valid
  empty result, unsupported filter chain, and backend failure.

## Handoff Policy

All dashboard navigation follows `contracts/navigation-links.yaml`:

- `includeVars=false`;
- explicit `var-*` URL parameters;
- dashboard links include `${__url_time_range}`;
- no self-link duplication;
- no `run_id` or `payload_hash` leakage into non-target dashboards;
- cross-scope transitions must make reset/context-mapping semantics explicit.
