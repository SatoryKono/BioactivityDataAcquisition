# Diagram Rendering Improvement Plan (Actual State)

Updated: 2026-02-26
Owner: Docs/Architecture tooling
Scope: Mermaid diagram workflow in `docs/**`

## Goal

Bring diagram rendering and visual quality workflow to a single, enforceable, CI-stable pipeline aligned with ADR-040.

## Current State Snapshot

### Already implemented (in working tree)

- `docs.yml` now validates Mermaid via `scripts/validate_mermaid_syntax.sh` instead of inline loop.
- `docs.yml` drift check already includes both `docs/**/*.mmd` and `docs/**/*.mermaid` (excluding `docs/99-archive/**`).
- `render.sh` now scans `docs/**` (not only `mmd-diagrams/*`) and supports exclusion paths.
- `render.sh` already applies SVG post-processing via `scripts/inject_svg_styles.py`.
- `lint_diagrams.py` already scans full `docs/` and excludes `docs/99-archive/**`.

### Gaps vs ADR-040 / docs policy

- Large amount of manual `&nbsp;` padding remains in source diagrams.
- No image-based visual regression gate in CI.

## Execution Plan

## Phase 0: Policy-Grade Gates (High priority)

- [x] Add missing lint rules in `scripts/lint_diagrams.py`:
  - `COLOUR-001`: non-canonical palette usage in `style`/`classDef`.
  - `COLOUR-002`: emoji in subgraph labels.
  - `SIZE-001`: `@nodes > 35` -> `ERROR`.
  - `SIZE-002`: `@nodes > 20` -> `WARNING`.
- [x] Confirm thresholds/exemptions policy for `*-full.mermaid` reference views and align with ADR text.
- [x] Add/adjust tests for new lint behavior (target: `tests/` policy/architecture area).
- [x] Execute new tests in project runtime (`pytest`) and record result in this plan.

Acceptance:
- `lint_diagrams.py` output matches ADR-040 rule set.
- CI fails on canonical-policy violations, not only syntax errors.

## Phase 1: Single Render Pipeline (High priority)

- [x] Mark legacy pipeline deprecated:
  - `scripts/render_diagrams.py` (deprecation notice; keep temporary compatibility).
  - `.github/workflows/project-automation.yml` diagram render step disabled.
- [x] Keep canonical pipeline:
  - `docs/02-architecture/mmd-diagrams/render.sh`
  - `.github/workflows/docs.yml`

Acceptance:
- One authoritative render path documented and used in CI.

## Phase 2: Runtime Stability (Medium priority)

- [x] Add explicit preflight guidance for `mmdc` browser runtime:
  - required Chrome/Chromium setup for Puppeteer.
  - fallback/diagnostics in `scripts/validate_mermaid_syntax.sh`.
- [x] Update runbook text in `docs/02-architecture/mmd-diagrams/README.md`.

Acceptance:
- Local validation failures clearly distinguish content errors from missing browser runtime.

## Phase 3: Visual Quality Cleanup (Medium priority)

- [x] Add baseline hotspot report for manual padding density:
  - `scripts/report_diagram_padding.py`
  - `make report-diagram-padding`
- [x] Run pilot normalization on one hotspot (`foundation/30-port-adapter-mapping.mmd`) to confirm tooling flow.
- [x] Implement grouped-width normalization strategy in `uniform_diagram_sizes.py`:
  - new directive: `%% @uniform-width group`
  - metadata now records `width_strategy` and per-group `width`
  - idempotency covered by `tests/architecture/test_uniform_diagram_group_width.py`
- [x] Apply grouped-width mode to top class-diagram hotspots:
  - `class-diagrams/04-types-enums.mmd`
  - `class-diagrams/06-config-classes.mmd`
  - `class-diagrams/07-application-core-services.mmd`
  - `class-diagrams/08-application-services.mmd`
  - `class-diagrams/09-transformers.mmd`
  - `class-diagrams/10-adapters.mmd`
- [x] Apply grouped-width mode to highest flowchart hotspot pair:
  - `foundation/30-port-adapter-mapping.mmd`
  - `diagrams/mermaid/30-port-adapter-mapping-full.mermaid`
- [x] Reduce manual `&nbsp;` in `foundation/04` and `foundation/13` families:
  - `foundation/04-domain-layer-class-diagram.mmd`
  - `diagrams/mermaid/04-domain-layer-class-diagram-full.mermaid`
  - `foundation/13-domain-models-relationship.mmd`
  - approach used: remove manual `&nbsp;` padding directly (grouped-width was regressive for these files due very long signature lines)
- [x] Reduce manual `&nbsp;` in class-diagram hotspots:
  - `class-diagrams/07-application-core-services.mmd`
  - `class-diagrams/10-adapters.mmd`
  - approach used: remove manual inline `&nbsp;` fillers; preserve semantic class content and relations
- [x] Continue class-diagram hotspot cleanup:
  - `class-diagrams/06-config-classes.mmd`
  - `class-diagrams/08-application-services.mmd`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for remaining top files:
  - `foundation/30-port-adapter-mapping.mmd`
  - `diagrams/mermaid/30-port-adapter-mapping-full.mermaid`
  - `class-diagrams/09-transformers.mmd`
  - `class-diagrams/04-types-enums.mmd`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for next top files:
  - `diagrams/mermaid/46-yaml-config-resolution-full.mermaid`
  - `foundation/49-composite-runner-class.mmd`
  - `class-diagrams/01-domain-ports.mmd`
  - `class-diagrams/03-value-objects.mmd`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for top foundation/architecture pair:
  - `foundation/01-full-system-component.mmd`
  - `diagrams/mermaid/01-full-system-component-full.mermaid`
  - `foundation/46-yaml-config-resolution.mmd`
  - `architecture/08-composite-pipeline.mmd`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for top full-view package:
  - `diagrams/mermaid/26-hexagonal-ports-adapters-full.mermaid`
  - `diagrams/mermaid/35-bootstrap-sequence-full.mermaid`
  - `diagrams/mermaid/44-cross-provider-enrichment-full.mermaid`
  - `diagrams/mermaid/28-composition-root-di-graph-full.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for mixed architecture/class package:
  - `class-diagrams/02-entities-aggregates.mmd`
  - `architecture/05-provider-adapter-hierarchy.mmd`
  - `class-diagrams/14-observability.mmd`
  - `architecture/10-resilience-patterns.mmd`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for architecture/foundation package:
  - `architecture/13-port-protocol-contracts.mmd`
  - `foundation/44-cross-provider-enrichment.mmd`
  - `foundation/26-hexagonal-ports-adapters.mmd`
  - `architecture/18-lock-checkpoint-shutdown.mmd`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
  - note: `architecture/13` still has existing policy debt `SIZE-001` (`@nodes=68`), unrelated to padding cleanup
- [x] Continue hotspot cleanup for pipeline/bootstrapping package:
  - `foundation/35-bootstrap-sequence.mmd`
  - `diagrams/mermaid/29-composite-pipeline-workflow-full.mermaid`
  - `foundation/25-circuit-breaker-observer-class.mmd`
  - `architecture/11-configuration-system.mmd`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
  - note: `architecture/11` has expected `SIZE-002` warning (`@nodes=29`)
- [x] Continue hotspot cleanup for composite/infra package:
  - `foundation/29-composite-pipeline-workflow.mmd`
  - `diagrams/mermaid/10-infrastructure-layer-class-diagram-full.mermaid`
  - `foundation/10-infrastructure-layer-class-diagram.mmd`
  - `architecture/01b-hexagonal-domain-app.mmd`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for activity/application package:
  - `foundation/43-fan-out-fan-in-pattern.mmd`
  - `diagrams/mermaid/21-activity-entity-data-flow-full.mermaid`
  - `diagrams/mermaid/06-application-layer-class-diagram-full.mermaid`
  - `foundation/06-application-layer-class-diagram.mmd`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for record/template/dq package:
  - `diagrams/mermaid/32-single-record-journey-full.mermaid`
  - `foundation/45-template-method-transformer.mmd`
  - `diagrams/mermaid/15-dq-check-workflow-full.mermaid`
  - `foundation/15-dq-check-workflow.mmd`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for architecture/core package:
  - `foundation/28-composition-root-di-graph.mmd`
  - `architecture/01-high-level-hexagonal.mmd`
  - `architecture/16-transformer-hierarchy.mmd`
  - `architecture/06-storage-layer.mmd`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
  - notes:
    - `architecture/01` has existing policy debt `SIZE-001` (`@nodes=39`)
    - `architecture/06` has expected `SIZE-002` warning (`@nodes=21`)
    - `architecture/16` has expected `SIZE-002` warning (`@nodes=35`)
- [x] Continue hotspot cleanup for hierarchy/security/dataflow package:
  - `foundation/17-pipeline-hierarchy.mmd`
  - `foundation/32-single-record-journey.mmd`
  - `architecture/17-security-pii-audit.mmd`
  - `diagrams/mermaid/48-composite-phase-lifecycle-dataflow.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for medallion/observability package:
  - `foundation/21-activity-entity-data-flow.mmd`
  - `foundation/07-medallion-flow.mmd`
  - `foundation/23-silver-writer-class.mmd`
  - `architecture/09-observability-stack.mmd`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
  - note: `architecture/09` has expected `SIZE-002` warning (`@nodes=24`)
- [x] Continue hotspot cleanup for medallion/bootstrap package:
  - `architecture/12b-bootstrap-wiring.mmd`
  - `diagrams/mermaid/39-medallion-invariants-full.mermaid`
  - `foundation/39-medallion-invariants.mmd`
  - `architecture/03-medallion-data-flow.mmd`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
  - note: `architecture/03` has existing policy debt `SIZE-001` (`@nodes=36`)
- [x] Continue hotspot cleanup for decomposed domain/infra package:
  - `diagrams/mermaid/04-domain-layer-class-diagram-domain.mermaid`
  - `diagrams/mermaid/48-composite-phase-lifecycle-domain.mermaid`
  - `diagrams/mermaid/48-composite-phase-lifecycle-infra.mermaid`
  - `diagrams/mermaid/10-infrastructure-layer-class-diagram-domain.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [ ] Expand ELK/layout + differentiated `linkStyle` usage for overloaded flowcharts.

Progress metric (2026-02-26):
- Total `&nbsp;` across scanned Mermaid sources reduced from **56,971** to **14,023** (`-42,948`, ~`-75.4%`).

Acceptance:
- Fewer padding artifacts in source files.
- Better edge routing/readability in dense diagrams.

## Phase 4: Visual Regression Guard (Lower priority)

- [ ] Add smoke visual regression in CI for selected reference diagrams:
  - render deterministic SVG set.
  - compare against checked-in baseline (or artifact diff report).

Acceptance:
- Style/layout regressions are visible in PR checks.

## Implementation Order (next actions)

1. Continue hotspot cleanup for remaining high-padding files (`diagrams/mermaid/36-architecture-principles-mindmap-domain`, `architecture/07-dq-system`, `architecture/14-cli-interface-layer`, `foundation/37-cli-entry-full-chain`).
2. Expand ELK/layout + differentiated `linkStyle` on overloaded flowcharts.
3. Add CI smoke visual regression set (Phase 4).

## Notes

- Working tree currently contains substantial unrelated changes; implementation should be scoped strictly to files listed per phase.
- Do not auto-reformat unrelated docs/diagram files during this workstream.
