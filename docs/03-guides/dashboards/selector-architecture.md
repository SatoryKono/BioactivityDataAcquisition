______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-08-05'

______________________________________________________________________

# Grafana Selector Architecture

Дата сверки: **2026-08-05**
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
control-plane identity context, is preserved between primary dashboards that
expose the same selector, and MUST NOT become a Prometheus label.
The control-plane selector resolver exposes `/ops/control-plane/selector-context`
for coherent local selector tuples and `/ops/control-plane/filter-options` for
Grafana option lists.
Dashboard-to-dashboard navigation passes only the shared shell
`workflow/pipeline/run_type` plus target-specific bounded vars; it does not rely
on native Grafana semantic variable copying.

## Selector catalog availability

Generated HTTP variables opt into `allow_stale=1`. The availability policy is
defined in `catalog_availability` in the machine-readable contract above.
Ready options include the complete projection, including run labels, so serving
them does not reread manifests, ledger entries, or report identities. Concurrent
requests for the same query share one refresh. Scope, timezone and selection
policy are isolated by the cache key.

An eligible older snapshot is marked `[STALE catalog]` in option labels; values
remain unchanged. This mark concerns the option catalog, not the run verdict.
The JSON `catalog` object exposes snapshot identity, age, refresh state and the
last refresh error. Adding `status_only=1` to the same query inspects this state
without starting work. A cold or expired catalog still returns typed 503/504;
it is never converted into `NO MATCHES` or `All`. Callers without the opt-in keep
strict behavior. Startup prewarms the unscoped workflow options; other scopes
warm on demand. Shutdown stops new refresh admission and bounds its wait while
existing disk work drains.

Deploy the backend before provisioning the generated dashboard changes. To
roll back the opt-in, remove `allow_stale=1` in the canonical generator and
regenerate the dashboards before rolling back the backend.

## Dashboard families

The approved ADR-053 cutover ships **exactly five dashboards**. The machine
inventory and selector contracts are authoritative for current owned variables.

- Saved-run surfaces: Replay Readiness, Run Overview, Data Quality. Their exact
  `run_id` narrows Ops HTTP evidence, never Prometheus labels. DQ additionally
  owns `stage` (default All).
- Incident Workspace owns CURRENT triage plus GLOBAL and selected-range fleet
  diagnostics; it owns `provider` and `read_latency_quantile` in addition to the
  shared workflow/pipeline/run_type/run_id shell. Exact run evidence in its lower
  summary is distinct from CURRENT/range Prometheus queries.
- Run Explorer owns the disk-indexed latest-ten catalog and shared selector shell;
  selection opens exact saved-run evidence rather than promising range filtering.
- `bioetl-runtime`, `bioetl-provider-health-v2`, `bioetl-workflow-overview`,
  `bioetl-alerts-slo` and Silver Reject Explorer are retired standalone surfaces.
  Runtime diagnostics belong to Incident's Fleet row; saved provider checks belong
  to Overview panel 9480. Exact record forensics use CLI `bioetl quarantine inspect`.

See [dashboard-inventory.md](dashboard-inventory.md) and
[navigation-contract.md](navigation-contract.md) for current destinations.

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
control-plane HTTP surface. It is preserved across primary dashboard links for
identity/provenance rows, not Prometheus time-series. `run_selector_mode`,
`started_at`, `manifest_id`, and `execution_fingerprint` remain
future/local-catalog candidates.

`bioetl-overview-v2` is the current hybrid Overview baseline.

### Hidden context selectors

Currently shipped (verified against `grafana/dashboards/*.json`):

- `pipeline_context` — Provider Health return-path only
- `adapter` — Provider Health detail-only
- `provider_hint` — Pipeline Diagnostics hidden heuristic for provider-scoped
  alert panels (not a visible operator selector)

Retired with Workflow Overview (do not reintroduce on primary boards):

- `workflow_context`
- `pipeline_context_exact`
- `run_type_context` / `run_type_context_exact`
- `provider_context` / `provider_context_exact`

Future reserved:

- `selected_run_id`
- `selected_manifest_id`
- `selected_started_at`

### Forensic-only selectors

Forensic identifiers remain **CLI / API scoped** after Silver Reject Explorer
removal. They MUST NOT reappear as Prometheus dashboard label selectors:

- `reason_code`
- `field`
- `quarantine_run_id`
- `payload_hash`
- `manifest_id`
- `execution_fingerprint`

Use `bioetl quarantine inspect` for exact reject forensics.

## Ship-now selector contract

The current shipped selector model (five dashboards):

- Replay Readiness, Run Overview and Run Explorer: workflow, pipeline, run_type,
  run_id and time range; auxiliary HTTP lookup variables remain dashboard-owned.
- Data Quality: the shared shell plus stage (default All).
- Incident Workspace: the shared shell plus provider and read_latency_quantile.

Hidden propagation is distinct from visible filtering. Handoffs carry only
variables owned by the target; they never use blanket `includeVars=true`, never
map primary `run_id` into `quarantine_run_id`, and never transfer retired provider
`pipeline_context` or `adapter` variables to Overview.

## Why exact execution filtering is not shipped everywhere today

The repo already has canonical execution anchors such as:

- `run_id`
- `manifest_id`
- `execution_fingerprint`
- `PipelineContext.started_at`

`run_id` is now exposed through the shared context shell and preserved as
identity/provenance context between primary dashboards. The other anchors live
in control-plane artifacts, manifests, sidecars, and diagnostic surfaces. They
do not currently exist as a universal Grafana filtering model for
Prometheus-backed current-status panels.

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
- blanket `includeVars=true` propagation of `run_id`
- mapping primary `run_id` into Silver `quarantine_run_id` on generic links

Native Grafana query variables can consume resolver option lists, but they
cannot safely auto-write sibling visible selectors. Full last-run defaults and
bidirectional auto-selection require a custom selector shell/plugin that calls
`/ops/control-plane/selector-context` and writes variables as one transaction.
The repo ships that plugin at `grafana/plugins/bioetl-selectorshell-panel`
(`autoApplyLastRunDefaults` + exact-run sync). Primary dashboard JSON does not
embed the unsigned panel by default; local Grafana must allow the plugin id.

**Default selection policy (SEL-P0 / #7550):**

- Overview fleet landing: `All/All/All/-`
- Non-Overview native `run_type` default: `backfill`
- `run_id` list order: `started_at` desc with `-` first; Grafana `sort=0`
- URL `var-*` handoffs win over auto-default
- Prom Status stays pipeline/run_type scoped; exact `run_id` is HTTP identity only

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
- `5. Data Quality`
- `0. Control Plane`
- maybe `2. Overview`

Excluded by default:

- `4. Provider Health`
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
