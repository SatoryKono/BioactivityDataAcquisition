______________________________________________________________________

Version: 0.1.0
Status: draft
Class: internal-draft
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-13'

______________________________________________________________________

# v3.0 Panel Contract

This document defines reusable panel content rules for v3.0 draft dashboards.
It complements, but does not replace, shipped dashboard JSON and YAML contracts.

## Policy Header

Every v3 operator dashboard starts with a visible first-screen policy header:

- `ONE BIG QUESTION`
- current scope in dashboard-family terms;
- provenance summary;
- availability / risk notes;
- `First action`.

Provenance summary includes:

- metric families, systems, tables, endpoints, or local artifacts;
- update cadence or schedule;
- transformation/runtime version, artifact version, `git_commit`, or other
  reproducible reference;
- latest successful refresh or latest run timestamp in UTC when available;
- owner/contact.

Availability / risk notes include:

- expected freshness window or SLA;
- known lag, partial-scope caveats, and source limitations;
- sensitivity classification or pointer to the monitoring guide.

## Navigation Panel

Navigation follows `contracts/navigation-links.yaml`.

Rules:

- use navigation panel `id=1000`;
- show the full top-level bus;
- render the current dashboard as disabled;
- omit machine-readable self-links;
- set `includeVars=false`;
- pass only explicit target-scoped `var-*` parameters;
- include `${__url_time_range}` for dashboard links;
- include `from=${__from}` and `to=${__to}` for Explore links;
- do not propagate forensic identifiers to non-target dashboards.

## Scope Panel

Scope panel content:

- dashboard question;
- selected dashboard-family scope;
- current selector values;
- whether exact execution context is unavailable, unresolved, or resolved;
- no claim that exact run resolution is available unless backed by a local
  run catalog or equivalent evidence source.

## Status Panel

Status panels use canonical BioETL semantics:

- `0` = `OK`;
- `1` = `WARN`;
- `>=2` = `CRIT`;
- `null` = `UNKNOWN`.

Current-status panels:

- are above the fold;
- do not depend on selected-range `$__range`;
- preserve `UNKNOWN` for missing current-state evidence;
- avoid `or vector(0)` unless the metric is a true zero-event counter.

## ID Panel

Exact identity fields are optional and gated. They may be shown only when the
dashboard has a resolved execution evidence source.

Allowed fields:

- `run_id`
- `manifest_id`
- `git_commit`
- `dependency_lock_hash`
- `config_hash`
- `resolved_config_hash`
- `effective_config_hash`
- `execution_fingerprint`
- `contract_ref`
- `contract_version`
- `contract_schema_hash`

If the run is unresolved, render this block as unavailable or below-fold
future context. Do not synthesize identity fields from Prometheus labels.

## Records Panel

Records panels may summarize:

- Bronze intake;
- Silver accepted records;
- filtered/rejected records;
- Gold output;
- quarantine evidence.

Any invariant must be defined with concrete terms and data sources before it is
used in a shipped dashboard. Do not publish symbolic invariants such as
`M + K = N` without a glossary and proof that the required metrics/contracts
exist.

## Next Action Panel

Next Action content must be concise and verdict-driven:

- `OK`: continue monitoring or inspect trend only if needed;
- `WARN`: inspect the most likely degraded subsystem;
- `CRIT`: route to the primary incident dashboard or runbook;
- `UNKNOWN`: validate telemetry/source trust before assuming health.

For Overview, dashboard-to-dashboard routing is preferred over record-level
forensics. Record-level drilldown belongs in dedicated explorer surfaces.
