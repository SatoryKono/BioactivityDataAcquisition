# Control Plane Dashboard Issue Pack 2026-05-07

*Status: Working planning artifact (non-normative)*
*Created: 2026-05-07*
*Updated: 2026-05-07*
*Scope: proposed GitHub issue breakdown from the `BioETL 0. Control Plane` dashboard audit*

## Purpose

This file converts the 2026-05-07 audit of
`grafana/dashboards/bioetl-control-plane-v1.json` into a bounded, issue-ready
GitHub backlog.

The audit outcome was not "rebuild the dashboard". The core Prometheus-backed
panel queries are structurally sound. The main defects are operator-surface
defects:

- stale and partially broken runbook links
- replay panel routing drift relative to alert/runbook baseline
- cross-dashboard handoff drift to `Provider Health`
- duplicated CTA surfaces and minor first-screen UX noise
- missing regression coverage for the above classes of drift

Primary supporting surfaces:

- `grafana/dashboards/bioetl-control-plane-v1.json`
- `docs/03-guides/dashboards/dashboard-v2-usage.md`
- `docs/05-operations/01-monitoring-guide.md`
- `docs/05-operations/runbooks/index.md`
- `grafana/prometheus-rules/bioetl_observability.yml`
- `tests/integration/test_grafana_config.py`
- `tests/integration/test_grafana_dashboard_links.py`
- `tests/integration/test_prometheus_rules_config.py`

## Suggested dependency order

1. Retire stale legacy GitHub links and resolve missing runbook targets
1. Align replay-family dashboard routing with the alert baseline
1. Normalize cross-dashboard handoff to `Provider Health`
1. Clean up first-screen CTA/copy/layout noise
1. Add regression coverage so the same drift does not return

## Issue 1

### Title

`CP-001 Fix stale Control Plane runbook links and retire legacy GitHub URLs`

### Suggested labels

- `bug`
- `observability`
- `documentation`

### Suggested scope

`Grafana / Operations Docs`

### Problem

`BioETL 0. Control Plane` still contains hardcoded links to the legacy GitHub
repository path `SatoryKono/BioactivityDataAcquisition/blob/main/...`. Several
of those links target runbooks that do not exist in the current repository,
including `replay-resume.md` and `replay-debugging.md`.

This creates a direct incident-response failure mode: an operator can click the
primary runbook CTA from a live dashboard and land on a dead or non-canonical
surface.

### Evidence

- `grafana/dashboards/bioetl-control-plane-v1.json` contains legacy GitHub
  URLs in multiple panels, including examples around lines `164`, `184`, `218`,
  `285`, `305`, `389`, `514`, and `632`
- `docs/05-operations/runbooks/replay-resume.md` is absent
- `docs/05-operations/runbooks/replay-debugging.md` is absent
- `docs/05-operations/runbooks/index.md` does not list those missing replay
  runbooks as maintained operator surfaces

### Proposed solution

Replace legacy hardcoded GitHub URLs in the dashboard with canonical current
targets, and decide per surface whether to:

- remap to an existing maintained runbook, or
- add the missing runbook document if it remains an intended operator surface

### Scope

- update runbook links in `grafana/dashboards/bioetl-control-plane-v1.json`
- remove references to missing or retired runbook paths
- ensure the linked runbooks are present in the current repository
- reconcile the final reachable runbook set with `docs/05-operations/runbooks/index.md`

### Non-goals

- do not rewrite panel queries that are already correct
- do not redesign the whole dashboard layout
- do not change unrelated dashboards in the same change unless required by a
  shared contract

### Acceptance criteria

- no legacy `SatoryKono/BioactivityDataAcquisition/blob/main/...` URLs remain
  in `bioetl-control-plane-v1.json`
- every runbook target referenced by the dashboard exists in the current repo
- the runbook index is consistent with the set of runbooks reachable from the
  dashboard
- relevant Grafana dashboard link tests pass

### Dependencies

- none; this issue is the first safe remediation step
- decisions made here feed Issues `CP-002` and `CP-005`

### Detailed implementation plan

1. Build a complete inventory of all Control Plane runbook links from:
   - dashboard-level `links`
   - panel `fieldConfig.defaults.links`
   - panel `options.dataLinks`
1. Classify each target into one of three buckets:
   - valid maintained local runbook
   - missing intended runbook
   - stale legacy GitHub URL that should not survive
1. Define the canonical target for every current legacy URL:
   - preserve the runbook family when the target exists and is still correct
   - remap to an existing maintained runbook when the old path is gone
   - only create a new runbook document if there is clear operational need and
     no existing maintained runbook covers the incident family
1. Update `grafana/dashboards/bioetl-control-plane-v1.json` so every operator
   link points to a maintained current-repo target.
1. Reconcile `docs/05-operations/runbooks/index.md` with the reachable runbook
   surface after the dashboard update.
1. Re-scan the repository to confirm no stale legacy repo URLs remain in the
   Control Plane dashboard.

### Validation plan

- repo search:
  - `rg -n "SatoryKono/BioactivityDataAcquisition|replay-resume|replay-debugging" grafana/dashboards/bioetl-control-plane-v1.json docs/05-operations/runbooks`
- JSON syntax validation for `grafana/dashboards/bioetl-control-plane-v1.json`
- narrow tests:
  - `tests/integration/test_grafana_dashboard_links.py -k control_plane`
  - any new/updated runbook existence checks added under `tests/integration`

### Risks and decisions

- if `replay-resume.md` or `replay-debugging.md` are still intended artifacts,
  remapping without explicit confirmation can hide a docs gap rather than solve
  it
- if some runbook URLs are shared with other dashboards, the final mapping
  should be extracted carefully so Control Plane does not diverge from the rest
  of the observability surface

## Issue 2

### Title

`CP-002 Align replay investigation panels with the replay alert runbook baseline`

### Suggested labels

- `bug`
- `observability`

### Suggested scope

`Grafana / Alerting`

### Problem

Several replay-related dashboard panels route operators to
`run-manifest-inspection.md`, while replay alerts in
`grafana/prometheus-rules/bioetl_observability.yml` route the same operational
class of failures to `checkpoint-debugging.md`.

This mismatch increases cognitive load during triage and can send operators
into the wrong investigation flow.

### Evidence

- replay panels in `grafana/dashboards/bioetl-control-plane-v1.json` currently
  route to manifest inspection around lines `783`, `867`, and `1202`
- replay alerts in `grafana/prometheus-rules/bioetl_observability.yml` route
  replay incidents to `docs/05-operations/runbooks/checkpoint-debugging.md`
  around lines `677`, `687`, and `697`
- `docs/05-operations/01-monitoring-guide.md` uses the checkpoint debugging
  family as the maintained replay/checkpoint investigation surface

### Proposed solution

Make replay-family dashboard handoff consistent with the alert baseline. If the
intended operator model is to split replay investigation between checkpoint and
manifest flows, that split must be documented explicitly and encoded
consistently across dashboard panels, alerts, and monitoring docs.

### Scope

- review replay-related panel links in Control Plane
- align them with the alert/runbook baseline
- update documentation if a new intentional split is introduced
- verify that replay-family panels route consistently

### Non-goals

- do not change metric names or alert expressions unless a real semantic defect
  is found
- do not merge manifest/ledger and replay troubleshooting into one generic
  runbook without explicit design intent

### Acceptance criteria

- replay-family panels route to the intended runbook family consistently
- dashboard routing and alert annotations no longer contradict each other
- monitoring docs describe the same operator path as the shipped dashboard
- narrow Grafana and Prometheus rule tests pass

### Dependencies

- should be executed after `CP-001`, because stale URL retirement and missing
  runbook cleanup affect the final routing map
- may require a small docs update in `docs/05-operations/01-monitoring-guide.md`

### Detailed implementation plan

1. Enumerate all replay-family panels in Control Plane, including:
   - `Monitor: Replay Not Reconstructable`
   - `Monitor: Replay Drift`
   - `Monitor: Replay Lag Seconds`
   - any adjacent replay/checkpoint panels that share the same operator path
1. Map each panel to the corresponding alert or recording-rule-backed incident
   family in `grafana/prometheus-rules/bioetl_observability.yml`.
1. Compare dashboard runbook routing against:
   - alert annotation runbooks
   - `docs/05-operations/01-monitoring-guide.md`
   - the current runbook index
1. Make an explicit decision between two supported models:
   - unified replay/checkpoint debugging path via
     `docs/05-operations/runbooks/checkpoint-debugging.md`
   - intentionally split routing where replay manifestations that are actually
     manifest/ledger problems stay on `run-manifest-inspection.md`
1. Update the Control Plane dashboard links to follow the chosen routing model
   consistently.
1. If the split model is retained, document the boundary in monitoring docs so
   future edits do not collapse back into implicit drift.

### Validation plan

- repo search for replay-family panel titles and their linked runbooks
- compare dashboard links against alert runbook annotations in
  `grafana/prometheus-rules/bioetl_observability.yml`
- run:
  - `tests/integration/test_grafana_dashboard_links.py -k control_plane`
  - `tests/integration/test_prometheus_rules_config.py -k 'replay or checkpoint'`

### Risks and decisions

- a naive blanket replacement of all replay links to `checkpoint-debugging.md`
  could erase a real semantic distinction if some panels are intentionally
  manifest-oriented
- this issue must preserve the operator mental model published in the
  monitoring guide, not just mechanically match a subset of alert annotations

## Issue 3

### Title

`CP-003 Normalize Control Plane to Provider Health handoff adapter fallback`

### Suggested labels

- `bug`
- `observability`
- `dashboard`

### Suggested scope

`Grafana Navigation Contract`

### Problem

The top-level `Provider Health` handoff in Control Plane currently sends
`var-adapter=unknown`, but the destination dashboard documents its fallback as
"All adapters when source has no adapter context."

This means the drilldown path can land in an over-constrained or empty target
scope even when the source dashboard had no adapter-specific context to pass.

### Evidence

- `grafana/dashboards/bioetl-control-plane-v1.json` line `53` hardcodes
  `var-adapter=unknown`
- `grafana/dashboards/bioetl-provider-health-v2.json` lines `1744-1762`
  define `adapter` with `includeAll: true` and document the fallback as
  "All adapters when source has no adapter context."

### Proposed solution

Make the handoff follow the documented destination contract by either omitting
`adapter` when there is no adapter context or passing the canonical all-state.

### Scope

- update the Control Plane top-level Provider Health link
- verify target dashboard behavior after the change
- align dashboard usage docs or navigation contract docs if needed

### Non-goals

- do not redesign Provider Health variable semantics wholesale
- do not broaden unrelated navigation contracts in the same change

### Acceptance criteria

- Control Plane no longer passes a non-canonical adapter fallback
- navigation from Control Plane to Provider Health lands in the documented
  default scope when adapter context is absent
- relevant navigation contract tests pass

### Dependencies

- logically independent from `CP-001` and `CP-002`
- should land before `CP-005` so regression coverage can lock in the final
  fallback semantics

### Detailed implementation plan

1. Confirm the intended adapter fallback contract on the destination dashboard:
   - inspect the `adapter` variable definition in
     `grafana/dashboards/bioetl-provider-health-v2.json`
   - confirm whether the documented fallback is represented by omission of the
     parameter, a canonical `All` state, or another URL-safe encoding
1. Review any existing navigation-contract tests that already assert Provider
   Health link behavior.
1. Replace `var-adapter=unknown` in the Control Plane top-level Provider Health
   handoff with the canonical no-context behavior.
1. Verify that the updated handoff still preserves the intended provider and
   pipeline context without over-constraining the destination dashboard.
1. Update docs only if the current published navigation semantics are unclear or
   incomplete.

### Validation plan

- repo search for `var-adapter=unknown` across dashboards and docs
- JSON validation for the edited dashboard
- run the targeted Grafana navigation/link tests that cover Control Plane and
  Provider Health handoff semantics

### Risks and decisions

- if Grafana expects a specific multi-select or `All` URL encoding, simply
  removing the parameter may not be equivalent to the documented fallback
- this issue should avoid quietly changing target dashboard variable semantics;
  the source handoff should adapt to the destination contract, not the reverse

## Issue 4

### Title

`CP-004 Clean up first-screen CTA duplication and copy/layout drift in Control Plane`

### Suggested labels

- `enhancement`
- `observability`
- `ux`

### Suggested scope

`Grafana Dashboard UX`

### Problem

The first screen already follows the intended answer-first design, but it
contains small UX defects:

- duplicate identical runbook links on KPI panels
- wording drift in the replay safety panel description
- an empty collapsed row titled `First Action` even though the real CTA exists
  as a dedicated panel

These issues do not break metrics, but they reduce clarity on the most
important operator screen.

### Evidence

- panel `891` duplicates the same runbook link in both
  `fieldConfig.defaults.links` and `options.dataLinks`
- panel `893` duplicates the same pattern
- line `124` in `bioetl-control-plane-v1.json` contains the description
  `0=OK only when Control-Plane Telemetry Missing is present`
- row `9001` is an empty collapsed row titled `First Action`

### Proposed solution

Retain the current answer-first layout, but remove duplicate CTA surfaces,
correct the replay safety copy, and either delete or repurpose the empty row.

### Scope

- remove duplicate identical panel links where one surface is sufficient
- correct first-screen operator copy to match documented semantics
- remove or repurpose the empty `First Action` row
- verify that the screen still presents the same first-action triage flow

### Non-goals

- do not overhaul the dashboard visual language
- do not add new panels without a strong operator need

### Acceptance criteria

- first-screen KPI panels expose one clear CTA per intended action
- replay safety copy matches documented control-plane semantics
- the empty `First Action` row is removed or turned into a useful surface
- first-screen dashboard tests remain green

### Dependencies

- can proceed in parallel with `CP-003`
- should preferably follow `CP-001` if the duplicate links point to stale
  runbook targets so the cleanup is done against the final canonical URLs

### Detailed implementation plan

1. Audit the first screen as a complete operator surface, not as isolated
   fields:
   - identify all visible CTA affordances
   - confirm which ones are primary versus redundant
1. For panels `891` and `893`, remove one of the two duplicate link surfaces:
   - keep the mechanism that best matches current project conventions for
     stat/KPI panels
   - preserve clickability while eliminating repeated identical actions
1. Reconcile the replay safety description with the semantics documented in
   `docs/03-guides/dashboards/dashboard-v2-usage.md`.
1. Decide whether row `9001` should be:
   - removed entirely, or
   - repurposed into a meaningful grouping surface
1. Re-check the first viewport after the cleanup to ensure the answer-first
   layout still presents the same trust KPIs and next action with less noise.

### Validation plan

- repo search for duplicated first-screen link targets in panel `891` and `893`
- JSON validation for the dashboard
- targeted first-screen Grafana tests, especially link and structural contract
  checks
- optional manual screenshot or browser review if a live Grafana stack is
  available

### Risks and decisions

- removing the wrong link mechanism can unintentionally degrade click behavior
  on stat panels even if the JSON remains valid
- deleting the empty row is low risk technically, but if downstream tests or
  screenshots assume its presence they must be updated in the same change

## Issue 5

### Title

`CP-005 Add regression checks for Control Plane runbook, handoff, and CTA contracts`

### Suggested labels

- `enhancement`
- `test`
- `observability`

### Suggested scope

`Integration Tests / Dashboard Contracts`

### Problem

Current tests did not prevent the dashboard from drifting into:

- legacy external repo URLs
- missing local runbook targets
- replay-routing mismatch against alert annotations
- duplicate identical CTA links
- non-canonical Provider Health adapter fallback

Without dedicated regression checks, the same classes of defects can re-enter
the shipped dashboard after future edits.

### Proposed solution

Extend the existing Grafana integration test surface instead of adding an ad
hoc checker. The new assertions should validate the Control Plane dashboard as
an operator contract, not only as valid JSON.

### Scope

- extend `tests/integration/test_grafana_dashboard_links.py`
- extend `tests/integration/test_grafana_config.py` where config-level
  invariants are a better fit
- add checks for missing linked runbooks, stale legacy repo URLs, replay-family
  runbook mismatch, duplicate identical links, and Provider Health fallback
  drift

### Non-goals

- do not add a standalone CI script if the existing integration test surface is
  sufficient
- do not over-generalize the checks before the Control Plane invariants are
  stable

### Acceptance criteria

- tests fail when legacy external repo URLs are reintroduced
- tests fail when linked Control Plane runbooks do not exist locally
- tests fail when replay-family dashboard routing contradicts the alert
  baseline
- tests fail when Control Plane reintroduces duplicate identical CTA links or
  the non-canonical Provider Health adapter fallback
- the new checks run in the existing test workflow

### Dependencies

- should land after the behavioral decisions in `CP-001` through `CP-004`
- may reuse helpers that already exist in `tests/integration/_grafana_test_support.py`

### Detailed implementation plan

1. Review the current Grafana integration test surface to place each new
   invariant where it belongs:
   - link existence and URL-target checks in
     `tests/integration/test_grafana_dashboard_links.py`
   - config-level and structural invariants in
     `tests/integration/test_grafana_config.py`
1. Encode the final Control Plane contract as explicit assertions:
   - no legacy external repo URLs
   - all linked local runbooks exist
   - replay-family panels and alert annotations agree on runbook family
   - no duplicate identical CTA links on the first screen
   - Provider Health handoff does not use a non-canonical adapter fallback
1. Reuse shared dashboard walkers/helpers where possible so the checks survive
   nested panels and future layout changes.
1. Keep the checks narrow to Control Plane unless a stronger repo-wide contract
   is intentionally being introduced.
1. Wire the tests into the existing workflow by extending the current test
   files rather than creating a separate CI-only script.

### Validation plan

- run the new targeted tests in isolation first
- re-run the existing Control Plane Grafana test slice to check for unintended
  regressions
- if practical, run the broader file-level Grafana config suite after the new
  assertions are stable

### Risks and decisions

- over-generalizing the checks too early can create brittle repo-wide test
  failures unrelated to Control Plane
- if assertions depend on exact panel IDs or ordering, they should be justified
  and documented so small layout refactors do not create noisy churn
