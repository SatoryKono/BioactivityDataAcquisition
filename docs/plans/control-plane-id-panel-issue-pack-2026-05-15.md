# Control Plane ID Panel Refactoring Plan And Issue Pack 2026-05-15

*Status: Working planning artifact (non-normative)*
*Created: 2026-05-15*
*Scope: `0. Control Plane` ID/identity-graph refactor and implementation backlog*

## Purpose

This plan converts the current `0. Control Plane` `ID` audit gap into a
bounded implementation program with dependency-ordered GitHub issues.

The goal is not a generic dashboard redesign. The goal is to turn the current
minimal local identity table into an operator-usable control-plane identity
graph surface that:

- preserves `run_id` and `manifest_id` as P0 anchors;
- exposes replay, checkpoint, contract, config, and input-snapshot anchors
  without adding high-cardinality Prometheus labels;
- reuses the existing run-manifest / replay-bundle / checkpoint-compatibility
  evidence that already exists in the repository;
- preserves the shared `run_id` shell semantics on other primary dashboards.

## Audit Summary

### Current shipped state

- `grafana/dashboards/bioetl-control-plane-v1.json` panel `9402` is a compact
  HTTP-backed `ID` table sourced from
  `/ops/control-plane/identity-table?pipeline=${pipeline}&run_type=${run_type:csv}&run_id=${run_id}`.
- `src/bioetl/interfaces/http/_health_server_identity_support.py` returns only
  nine coarse rows:
  `manifest_id`, `run_id`, `pipeline name`, `pipelineversion`,
  `git commit hash`, `config hash`, `execution fingerprint`,
  `schema contract`, `version`.
- `docs/03-guides/dashboards/design-system.md` and `grafana/README.md`
  define `9402` as part of the shared operator shell across primary dashboards,
  not as a Control Plane-only deep evidence surface.
- `src/bioetl/application/services/control_plane/_run_manifest_identity_graph_builder.py`
  already assembles a much richer identity graph with replay, snapshot,
  artifact, and exact-replay anchors.
- `src/bioetl/application/services/checkpoint_compatibility_service_v2.py`
  already models current-vs-checkpoint identity anchors, including
  `composite_run_identity`, `effective_config_artifact_id`,
  `input_snapshot_fingerprint`, `manifest_id`, and `execution_fingerprint`.
- `docs/05-operations/runbooks/run-manifest-inspection.md` already defines the
  operator-facing manifest/replay-bundle inspection surface.

### Gap to the target spec

The current dashboard cannot yet satisfy the requested spec because it lacks:

- P0/P1/P2 identity tiering;
- missing-anchor severity rendering;
- short-vs-full rendering split for IDs and hashes;
- copyable artifact/value handoffs for identity fields;
- replay parentage and exact-replay eligibility on the dashboard first path;
- checkpoint anchor comparison (`OK / MISMATCH / MISSING / PARTIAL`);
- composite execution identity exposure;
- explicit identity-gap status for config/contract/input closure;
- dedicated deep evidence layout for manifest/config/contract/input/replay/composite/checkpoint surfaces.

### Constraints that must remain true

- `run_id`, `manifest_id`, `execution_fingerprint`, config hashes, contract
  hashes, artifact refs, snapshot IDs, checkpoint file IDs, and similar
  forensic identifiers MUST NOT become Prometheus labels.
- The current shared `$run_id` variable remains local identity context only;
  it must not start filtering Prometheus queries or cross-dashboard links.
- The shared shell contract for primary dashboards must either stay intact, or
  any Control Plane exception must be documented and test-covered explicitly.
- Deep evidence can be HTTP-backed or CLI/runbook-backed; it must not be faked
  via synthetic PromQL.

## Recommended Refactoring Strategy

### Phase 1: Decouple Control Plane deep identity from the shared shell

Do **not** inflate the shared `9402` shell contract across Runtime, DQ,
Provider Health, and Workflow.

Instead:

- keep `/ops/control-plane/identity-table` backward-compatible for the shared
  shell;
- introduce a dedicated Control Plane identity-graph evidence contract for the
  richer surface;
- either:
  - keep `9402` as the compact shell table and add a new Control Plane-only
    identity band below it, or
  - formally document a Control Plane exception if `9402` itself is repurposed.

The first option is lower risk and better aligned with the current design
system.

### Phase 2: Ship a P0-first operator path

The first always-visible identity surface on `0. Control Plane` should answer:

- which exact run/manifest are we looking at;
- which pipeline/provider/entity/runtime mode produced it;
- whether the execution/config/contract/input anchors are complete enough to
  trust replay/resume decisions;
- whether checkpoint anchors match the current runtime anchors.

### Phase 3: Move deep evidence below fold

The requested “details tabs” should be mapped to Grafana-safe structures:

- either row-based detail sections;
- or HTTP-backed tables/text panels grouped by section.

Do not force a fake tab widget if the shipped dashboard stack does not already
use one.

### Phase 4: Prefer CLI/runbook/artifact handoffs over synthetic UI invention

For full-value copy/drilldown behavior:

- use short forms only in cards and compact summary tables;
- use full values in HTTP detail tables and/or `data:text/plain` copy links;
- hand off to maintained manifest inspection, replay bundle, checkpoint
  inspection, contract docs, and artifact references instead of inventing
  Prometheus-only proofs.

## Suggested Dependency Order

1. Add the dedicated Control Plane identity-graph evidence endpoint and freeze
   compatibility rules for the old shared shell endpoint.
2. Refactor the Control Plane first screen to a P0 identity overview.
3. Add replay / composite / checkpoint compare deep evidence sections.
4. Wire copyable full-value handoffs and drilldowns for config / contract /
   input / artifact anchors.
5. Add regression tests and docs/contracts so the surface does not drift back.

## GitHub Issue Set

## Issue 1

### Title

`CP-ID-001 Introduce a dedicated Control Plane identity-graph evidence endpoint while preserving shared shell compatibility`

### Suggested labels

- `enhancement`
- `observability`
- `control-plane`
- `interfaces`
- `backend`
- `replay-safety`
- `reproducibility`
- `P1`
- `priority:high`

### Problem

The current `/ops/control-plane/identity-table` endpoint is intentionally
minimal and shared across multiple dashboards. It cannot satisfy the requested
identity-graph contract without either breaking the shared shell or forcing the
other dashboards to absorb Control Plane-specific deep evidence.

### Evidence

- `src/bioetl/interfaces/http/_health_server_identity_support.py`
- `src/bioetl/interfaces/http/_health_server_routing_support.py`
- `docs/03-guides/dashboards/design-system.md`
- `grafana/README.md`
- `src/bioetl/application/services/control_plane/_run_manifest_identity_graph_builder.py`
- `src/bioetl/application/services/checkpoint_compatibility_service_v2.py`

### Proposed solution

Add a new HTTP evidence surface for Control Plane identity graph data and keep
the existing identity-table endpoint backward-compatible for the shared shell.

The new payload should expose, at minimum:

- P0 / P1 / P2 sections;
- `name`, `label`, `priority`, `source`, `render_short`, `render_full`,
  `copy_mode`, `drilldown`, `missing_severity`;
- explicit aggregate-scope behavior for `pipeline=$__all`;
- replay parentage, replay eligibility, input-snapshot closure, contract/config
  anchors, and checkpoint/runtime anchor comparisons;
- `identity_graph_complete` and gap classification metadata.

### Scope

- `src/bioetl/interfaces/http/_health_server_routing_support.py`
- `src/bioetl/interfaces/http/_health_server_identity_support.py`
- new supporting helper module(s) under `src/bioetl/interfaces/http/` as needed
- reuse of manifest inspection / replay bundle / checkpoint compatibility
  service outputs
- unit tests for the new HTTP contract

### Non-goals

- do not add high-cardinality Prometheus labels;
- do not remove `/ops/control-plane/identity-table`;
- do not redesign other dashboards yet;
- do not invent checkpoint-age or replay-duplicate metrics in this issue.

### Acceptance criteria

- `/ops/control-plane/identity-table` remains stable for the shared shell.
- A new Control Plane identity evidence endpoint returns P0/P1/P2 anchor data.
- The new payload includes replay parentage, exact-replay eligibility, input
  snapshot identity, contract/config anchors, and checkpoint compare status.
- Aggregate pipeline scope fail-closes unless exact `run_id` is supplied.
- No returned field contract implies Prometheus label filtering by forensic IDs.
- Unit tests cover concrete pipeline scope, aggregate scope, replay runs,
  composite runs, and missing-anchor severity.

### Dependencies

- none

### Validation plan

- `python3 -m json.tool` is not applicable; this is backend-only
- `uv run python -m pytest -q tests/unit/interfaces/http/test_health_server.py -k 'control_plane and identity'`
- targeted unit tests for any new identity payload helpers

## Issue 2

### Title

`CP-ID-002 Refactor 0. Control Plane first-screen identity surface to a P0 overview`

### Suggested labels

- `enhancement`
- `observability`
- `dashboard`
- `grafana`
- `control-plane`
- `ux`
- `P1`
- `priority:high`

### Problem

The current Control Plane first screen shows the generic shared-shell `ID`
table, but it does not answer the Control Plane-specific operator question:
whether the run identity, replay, config, contract, snapshot, and checkpoint
anchors are trustworthy enough for replay/resume decisions.

### Evidence

- `grafana/dashboards/bioetl-control-plane-v1.json` panel `9402`
- `docs/03-guides/dashboards/design-system.md`
- `grafana/dashboards/bioetl-control-plane-v1.json` known-gap row `905`

### Proposed solution

Introduce a Control Plane-specific P0 overview band that surfaces:

- `run_id`
- `manifest_id`
- `pipeline_name`
- `provider / entity`
- `runtime_mode`
- `execution_fingerprint`
- `effective_config_hash`
- `contract_ref / contract_version`
- `input_snapshot_identity_fingerprint`
- `replay_mode / replay parentage summary`
- `checkpoint_anchor_status`
- `identity_graph_complete`

This issue should also decide and codify one of two layout models:

- preserve `9402` as the shared shell table and add a new Control Plane-only
  identity overview band; or
- formally document and test a Control Plane exception for `9402`.

### Scope

- `grafana/dashboards/bioetl-control-plane-v1.json`
- dashboard design-system / selector docs if the shared-shell contract changes
- first-screen layout only

### Non-goals

- do not implement all P1/P2 deep tables in this issue;
- do not add artifact/config/contract drilldown tables yet;
- do not change Runtime/DQ/Provider/Workflow shared shell unless required by
  the chosen contract decision.

### Acceptance criteria

- Control Plane first screen exposes a dedicated P0 identity overview.
- Long UUID/hash values are shortened only in overview cards.
- Full values are not lost; they are deferred to details surfaces.
- Missing `run_id` and terminal-run missing `manifest_id` render failing state.
- Missing config/contract/input anchors render explicit identity-gap state.
- No Prometheus query on the dashboard starts filtering by `run_id`,
  `manifest_id`, or hash fields.
- The final `9402` contract decision is encoded in docs and tests.

### Dependencies

- depends on `CP-ID-001`

### Validation plan

- `uv run python -m json.tool grafana/dashboards/bioetl-control-plane-v1.json`
- `uv run python -m pytest -q tests/integration/test_grafana_config.py`
- targeted Control Plane slices under:
  - `tests/integration/test_grafana_dashboard_links.py`
  - `tests/integration/test_grafana_dashboard_metric_semantics.py`
  - `tests/integration/test_grafana_layout_and_metadata.py`

## Issue 3

### Title

`CP-ID-003 Add replay, composite, and checkpoint-compare detail sections for Control Plane identity evidence`

### Suggested labels

- `enhancement`
- `observability`
- `dashboard`
- `control-plane`
- `replay-safety`
- `reproducibility`
- `composite`
- `P1`
- `priority:high`

### Problem

The requested spec requires deep evidence for replay parentage, exact replay
eligibility, `composite_run_identity`, and checkpoint-vs-runtime anchor
comparison. The current dashboard does not surface those details even though
the repository already models them in application services.

### Evidence

- `src/bioetl/application/services/control_plane/_run_manifest_identity_graph_builder.py`
- `src/bioetl/application/services/checkpoint_compatibility_service_v2.py`
- `docs/05-operations/runbooks/run-manifest-inspection.md`

### Proposed solution

Add Control Plane detail sections for:

- replay / resume / backfill / rebuild summary;
- parent `run_id` / `manifest_id`;
- exact replay blockers and support boundary;
- `composite_run_identity` and component-run evidence for composite flows;
- checkpoint compare with `OK / MISMATCH / MISSING / PARTIAL`;
- current runtime anchors vs persisted checkpoint anchors.

The implementation should prefer HTTP-backed tables and text panels over fake
PromQL approximations.

### Scope

- Control Plane dashboard deep rows / detail sections
- HTTP payload fields required for replay/composite/checkpoint evidence
- checkpoint compare rendering semantics

### Non-goals

- do not add checkpoint-age metrics;
- do not add replay-duplicate-record metrics;
- do not redesign unrelated incident drilldown rows.

### Acceptance criteria

- Replay runs show parent run/manifest anchors when available.
- Missing replay parentage is not silently ignored.
- Composite runs expose `composite_run_identity` and component run evidence.
- Checkpoint detail surfaces compare current and persisted anchors and classify
  them as `OK`, `MISMATCH`, `MISSING`, or `PARTIAL`.
- Exact replay blockers appear as explicit operator-facing evidence.
- Tests cover replay, composite, and checkpoint mismatch cases.

### Dependencies

- depends on `CP-ID-001`
- should follow `CP-ID-002`

### Validation plan

- dashboard JSON validation
- targeted unit tests for checkpoint/replay payload shaping
- Grafana integration slices covering Control Plane deep surfaces

## Issue 4

### Title

`CP-ID-004 Add copyable full-value handoffs and stable drilldowns for manifest, config, contract, input, and artifact anchors`

### Suggested labels

- `enhancement`
- `observability`
- `dashboard`
- `control-plane`
- `docs`
- `runbook`
- `P2`
- `priority:medium`

### Problem

The requested operator workflow requires copyable full values and drilldowns for
UUID/hash/artifact anchors. The current Control Plane dashboard mainly routes
operators to runbooks and does not provide a stable full-value handoff model for
manifest/config/contract/input evidence.

### Evidence

- `docs/05-operations/runbooks/run-manifest-inspection.md`
- `grafana/dashboards/bioetl-silver-reject-explorer.json` demonstrates the
  existing `data:text/plain` copy-link pattern
- current Control Plane dashboard uses runbook links heavily but not copyable
  identity evidence

### Proposed solution

Wire copy/drilldown behavior so that:

- cards and summary tables render short values only;
- details surfaces render full values;
- UUID/hash/artifact refs expose copyable handoffs;
- simple enum/status badges do not get fake copy affordances;
- drilldowns route to maintained targets:
  - run manifest inspection
  - replay bundle / checkpoint runbook path
  - effective config artifact evidence
  - contract registry / contract docs
  - input snapshot details
  - published artifact / lineage evidence

Where Grafana lacks a native clipboard action, use `data:text/plain` links or
copy-friendly CLI handoffs explicitly.

### Scope

- Control Plane dashboard links / dataLinks
- supporting docs for operator handoff semantics
- any HTTP payload metadata needed to drive the links cleanly

### Non-goals

- do not invent a new general-purpose artifact explorer UI unless required;
- do not convert every runbook link into a custom HTTP view.

### Acceptance criteria

- Full values are copyable from detail surfaces.
- Short values remain limited to first-screen summary surfaces.
- Copy links exist for UUID/hash/artifact anchors and are absent for simple
  badges.
- Drilldowns target maintained docs / CLI / artifact surfaces and not stale
  legacy URLs.
- Monitoring docs describe the final handoff model.

### Dependencies

- depends on `CP-ID-001`
- should follow `CP-ID-002` and `CP-ID-003`

### Validation plan

- targeted dashboard link tests
- repo search for stale/non-canonical drilldown targets
- docs link validation if docs are changed

## Issue 5

### Title

`CP-ID-005 Add regression contracts for Control Plane identity evidence, forbidden labels, rendering split, and docs alignment`

### Suggested labels

- `enhancement`
- `testing`
- `observability`
- `dashboard`
- `control-plane`
- `cardinality`
- `docs`
- `P1`
- `priority:high`

### Problem

The current test suite only guards the minimal shared-shell identity-table URL
and the broad “no `run_id` in Prometheus labels” rule. It does not yet lock the
new identity-graph behaviors that the refactor requires.

### Evidence

- `tests/integration/test_grafana_config.py`
- `tests/integration/test_grafana_dashboard_links.py`
- `tests/unit/interfaces/http/test_health_server.py`
- `docs/03-guides/dashboards/design-system.md`
- `docs/03-guides/dashboards/variable-reference.md`

### Proposed solution

Add explicit regression checks for:

- shared-shell compatibility of `/ops/control-plane/identity-table`;
- new identity-graph endpoint contract;
- forbidden high-cardinality labels in Prometheus queries;
- short-value vs full-value rendering split;
- missing-anchor severity semantics;
- replay parentage, composite identity, and checkpoint mismatch rendering;
- final docs/design-system contract for the Control Plane identity surface;
- removal or update of the stale “Known Missing Replay-Safety Signals” note for
  fields that are now provided by the HTTP evidence path.

### Scope

- unit tests for HTTP payloads
- integration tests for dashboard JSON/layout/links
- docs contract tests

### Non-goals

- do not broaden the scope to unrelated dashboard families before the Control
  Plane contract is stable.

### Acceptance criteria

- Tests fail if high-cardinality identity fields leak into Prometheus queries.
- Tests fail if Control Plane drops the short/full rendering split.
- Tests fail if replay/composite/checkpoint identity evidence regresses.
- Docs and dashboard contracts stay aligned.
- The dashboard no longer documents missing signals that are already available
  through the shipped HTTP evidence surface.

### Dependencies

- depends on `CP-ID-001`
- should land after `CP-ID-002`, `CP-ID-003`, and `CP-ID-004`

### Validation plan

- `uv run python -m pytest -q tests/unit/interfaces/http/test_health_server.py`
- targeted Grafana integration and docs/architecture tests
- `uv run python -m scripts.docs check-drift --runtime-mirrors --freshness` if
  docs/design-system contracts change materially

## Out of scope for this issue pack

These may deserve separate backlog items, but they should not block the ID
panel refactor:

- introducing `checkpoint_age` metrics;
- introducing replay duplicate-record metrics;
- adding high-cardinality Prometheus projections for manifest or artifact IDs;
- repo-wide redesign of the shared shell on non-Control-Plane dashboards.
