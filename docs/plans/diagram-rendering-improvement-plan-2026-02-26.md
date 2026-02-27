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

- Manual `&nbsp;` padding cleanup is complete and guarded by lint rule `NBSP-001`.
- Smoke-level visual regression gate exists in CI with expanded baseline coverage (27 SVGs).

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
- [x] Continue hotspot cleanup for mindmap/dq/cli package:
  - `diagrams/mermaid/36-architecture-principles-mindmap-domain.mermaid`
  - `architecture/07-dq-system.mmd`
  - `architecture/14-cli-interface-layer.mmd`
  - `foundation/37-cli-entry-full-chain.mmd`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
  - notes:
    - `architecture/07` has expected `SIZE-002` warning (`@nodes=22`)
    - `architecture/14` has expected `SIZE-002` warning (`@nodes=24`)
- [x] Continue hotspot cleanup for complete-etl/storage package:
  - `diagrams/mermaid/08-complete-etl-workflow-full.mermaid`
  - `foundation/08-complete-etl-workflow.mmd`
  - `diagrams/mermaid/04-domain-layer-class-diagram-infra.mermaid`
  - `class-diagrams/11-storage.mmd`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for bootstrap/exceptions package:
  - `class-diagrams/05-exceptions.mmd`
  - `diagrams/mermaid/36-architecture-principles-mindmap-infra.mermaid`
  - `diagrams/mermaid/04-domain-layer-class-diagram-overview.mermaid`
  - `architecture/12-bootstrap-di-container.mmd`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
  - note: `architecture/12` has expected `SIZE-002` warning (`@nodes=29`)
- [x] Continue hotspot cleanup for provider-health/exception package:
  - `diagrams/mermaid/14-provider-health-states-domain.mermaid`
  - `diagrams/mermaid/14-provider-health-states-infra.mermaid`
  - `foundation/02-full-medallion-data-flow.mmd`
  - `diagrams/mermaid/50-exception-hierarchy-infra.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for infra/enrichment decomposed package:
  - `diagrams/mermaid/44-cross-provider-enrichment-domain.mermaid`
  - `diagrams/mermaid/44-cross-provider-enrichment-infra.mermaid`
  - `diagrams/mermaid/10-infrastructure-layer-class-diagram-overview.mermaid`
  - `diagrams/mermaid/10-infrastructure-layer-class-diagram-infra.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for batch/yaml/lifecycle domain package:
  - `diagrams/mermaid/34-batch-processing-flow-infra.mermaid`
  - `diagrams/mermaid/46-yaml-config-resolution-domain.mermaid`
  - `diagrams/mermaid/01-high-level-full.mermaid`
  - `diagrams/mermaid/31-pipeline-run-lifecycle-domain.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for domain-flow/memory package:
  - `diagrams/mermaid/05-pipeline-lifecycle-states-domain.mermaid`
  - `foundation/16-memory-lock-class.mmd`
  - `diagrams/mermaid/08-domain-ddd-infra.mermaid`
  - `diagrams/mermaid/34-batch-processing-flow-domain.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for infra/domain lifecycle package:
  - `diagrams/mermaid/46-yaml-config-resolution-infra.mermaid`
  - `diagrams/mermaid/31-pipeline-run-lifecycle-infra.mermaid`
  - `diagrams/mermaid/08-domain-ddd-domain.mermaid`
  - `diagrams/mermaid/05-layers-interaction-full.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for layers/medallion package:
  - `foundation/05-layers-interaction.mmd`
  - `diagrams/mermaid/02-medallion-domain.mermaid`
  - `diagrams/mermaid/02-medallion-infra.mermaid`
  - `diagrams/mermaid/05-layers-interaction-domain.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for layers/state/dataflow package:
  - `diagrams/mermaid/05-layers-interaction-infra.mermaid`
  - `diagrams/mermaid/05-pipeline-lifecycle-states-infra.mermaid`
  - `diagrams/mermaid/04-domain-layer-class-diagram-dataflow.mermaid`
  - `diagrams/mermaid/07-circuit-breaker-states-domain.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for circuit/deployment/domain-ddd package:
  - `diagrams/mermaid/07-circuit-breaker-states-infra.mermaid`
  - `diagrams/mermaid/12-local-deployment-architecture-domain.mermaid`
  - `diagrams/mermaid/08-domain-ddd-full.mermaid`
  - `foundation/08-domain-ddd.mmd`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for mindmap/exception/deployment package:
  - `diagrams/mermaid/36-architecture-principles-mindmap-overview.mermaid`
  - `diagrams/mermaid/50-exception-hierarchy-overview.mermaid`
  - `diagrams/mermaid/12-local-deployment-architecture-infra.mermaid`
  - `foundation/40-application-core-collaboration.mmd`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for infra/deployment/exception package:
  - `diagrams/mermaid/10-infrastructure-layer-class-diagram-dataflow.mermaid`
  - `diagrams/mermaid/12-local-deployment-architecture-full.mermaid`
  - `diagrams/mermaid/50-exception-hierarchy-domain.mermaid`
  - `architecture/05a-adapter-hierarchy-base.mmd`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for domain-ddd/deployment package:
  - `diagrams/mermaid/08-domain-ddd-overview.mermaid`
  - `foundation/12-local-deployment-architecture.mmd`
  - `architecture/13d-port-contracts-services.mmd`
  - `architecture/01c-hexagonal-infra-comp.mmd`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for activity/medallion/package:
  - `diagrams/mermaid/21-activity-entity-data-flow-domain.mermaid`
  - `diagrams/mermaid/02-medallion-full.mermaid`
  - `foundation/42-pipeline-runner-class.mmd`
  - `diagrams/mermaid/01-high-level-domain.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for high-level/lifecycle package:
  - `diagrams/mermaid/01-high-level-infra.mermaid`
  - `diagrams/mermaid/31-pipeline-run-lifecycle-overview.mermaid`
  - `diagrams/mermaid/12-local-deployment-architecture-overview.mermaid`
  - `architecture/15-batch-executor-internals.mmd`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for infra overview package:
  - `diagrams/mermaid/06-application-layer-class-diagram-infra.mermaid`
  - `diagrams/mermaid/14-provider-health-states-overview.mermaid`
  - `diagrams/mermaid/21-activity-entity-data-flow-infra.mermaid`
  - `diagrams/mermaid/41-error-classification-tree-infra.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for layers/bootstrap/hash package:
  - `diagrams/mermaid/05-layers-interaction-overview.mermaid`
  - `architecture/12a-bootstrap-factories.mmd`
  - `diagrams/mermaid/01-full-system-component-domain.mermaid`
  - `foundation/24-hash-service-class.mmd`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for overview/cli package:
  - `architecture/01a-hexagonal-overview.mmd`
  - `diagrams/mermaid/06-application-layer-class-diagram-domain.mermaid`
  - `diagrams/mermaid/34-batch-processing-flow-overview.mermaid`
  - `diagrams/mermaid/33-cli-run-interaction-full.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for system/lifecycle overview package:
  - `diagrams/mermaid/01-full-system-component-infra.mermaid`
  - `diagrams/mermaid/48-composite-phase-lifecycle-overview.mermaid`
  - `diagrams/mermaid/41-error-classification-tree-domain.mermaid`
  - `diagrams/mermaid/44-cross-provider-enrichment-overview.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for adapter/medallion/circuit overview package:
  - `architecture/05b-adapter-hierarchy-providers.mmd`
  - `diagrams/mermaid/02-medallion-overview.mermaid`
  - `diagrams/mermaid/07-circuit-breaker-states-overview.mermaid`
  - `diagrams/mermaid/05-pipeline-lifecycle-states-overview.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for dataflow/cli/yaml package:
  - `diagrams/mermaid/05-layers-interaction-dataflow.mermaid`
  - `diagrams/mermaid/08-domain-ddd-dataflow.mermaid`
  - `diagrams/mermaid/33-cli-run-interaction-domain.mermaid`
  - `diagrams/mermaid/46-yaml-config-resolution-overview.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for cli/high-level/deployment package:
  - `diagrams/mermaid/33-cli-run-interaction-infra.mermaid`
  - `foundation/01-high-level.mmd`
  - `diagrams/mermaid/12-local-deployment-architecture-dataflow.mermaid`
  - `diagrams/mermaid/31-pipeline-run-lifecycle-dataflow.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for invariants/yaml/application package:
  - `diagrams/mermaid/39-medallion-invariants-domain.mermaid`
  - `diagrams/mermaid/39-medallion-invariants-infra.mermaid`
  - `diagrams/mermaid/46-yaml-config-resolution-dataflow.mermaid`
  - `diagrams/mermaid/06-application-layer-class-diagram-overview.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for full/dataflow/governance package:
  - `diagrams/mermaid/34-batch-processing-flow-full.mermaid`
  - `foundation/27-import-matrix-enforcement.mmd`
  - `diagrams/mermaid/01-full-system-component-dataflow.mermaid`
  - `diagrams/mermaid/50-exception-hierarchy-dataflow.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for medallion/circuit/cli dataflow package:
  - `diagrams/mermaid/02-medallion-dataflow.mermaid`
  - `diagrams/mermaid/07-circuit-breaker-states-dataflow.mermaid`
  - `diagrams/mermaid/44-cross-provider-enrichment-dataflow.mermaid`
  - `diagrams/mermaid/33-cli-run-interaction-overview.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for provider/error/system overview package:
  - `diagrams/mermaid/14-provider-health-states-dataflow.mermaid`
  - `diagrams/mermaid/41-error-classification-tree-overview.mermaid`
  - `diagrams/mermaid/01-full-system-component-overview.mermaid`
  - `diagrams/mermaid/36-architecture-principles-mindmap-dataflow.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for class/extractor/dataflow package:
  - `class-diagrams/16-factories-bootstrap.mmd`
  - `diagrams/mermaid/06-application-layer-class-diagram-dataflow.mermaid`
  - `diagrams/mermaid/34-batch-processing-flow-dataflow.mermaid`
  - `diagrams/mermaid/41-error-classification-tree-dataflow.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for extractors/ports/hexagonal package:
  - `class-diagrams/15-extractors.mmd`
  - `architecture/13c-port-contracts-observability.mmd`
  - `diagrams/mermaid/26-hexagonal-ports-adapters-domain.mermaid`
  - `diagrams/mermaid/05-pipeline-lifecycle-states-dataflow.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for single-record/high-level package:
  - `diagrams/mermaid/32-single-record-journey-domain.mermaid`
  - `diagrams/mermaid/32-single-record-journey-infra.mermaid`
  - `diagrams/mermaid/01-high-level-overview.mermaid`
  - `diagrams/mermaid/01-high-level-dataflow.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for workflow/invariants/full package:
  - `diagrams/mermaid/08-complete-etl-workflow-overview.mermaid`
  - `diagrams/mermaid/39-medallion-invariants-overview.mermaid`
  - `diagrams/mermaid/50-exception-hierarchy-full.mermaid`
  - `diagrams/mermaid/33-cli-run-interaction-dataflow.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for composite/single-record dataflow package:
  - `diagrams/mermaid/29-composite-pipeline-workflow-dataflow.mermaid`
  - `diagrams/mermaid/32-single-record-journey-overview.mermaid`
  - `diagrams/mermaid/39-medallion-invariants-dataflow.mermaid`
  - `diagrams/mermaid/32-single-record-journey-dataflow.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for composition matrix package:
  - `architecture/02-layer-dependency-matrix.mmd`
  - `diagrams/mermaid/28-composition-root-di-graph-domain.mermaid`
  - `diagrams/mermaid/28-composition-root-di-graph-infra.mermaid`
  - `diagrams/mermaid/29-composite-pipeline-workflow-domain.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for composite/ports/exception package:
  - `diagrams/mermaid/29-composite-pipeline-workflow-infra.mermaid`
  - `architecture/13b-port-contracts-storage.mmd`
  - `foundation/50-exception-hierarchy.mmd`
  - `diagrams/mermaid/29-composite-pipeline-workflow-overview.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for composition/etl domain package:
  - `diagrams/mermaid/28-composition-root-di-graph-overview.mermaid`
  - `architecture/13a-port-contracts-data-sources.mmd`
  - `diagrams/mermaid/08-complete-etl-workflow-domain.mermaid`
  - `diagrams/mermaid/08-complete-etl-workflow-infra.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for mapping/error hierarchy package:
  - `diagrams/mermaid/30-port-adapter-mapping-domain.mermaid`
  - `diagrams/mermaid/30-port-adapter-mapping-infra.mermaid`
  - `diagrams/mermaid/41-error-classification-tree-full.mermaid`
  - `foundation/41-error-classification-tree.mmd`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for dq/composition activity package:
  - `diagrams/mermaid/15-dq-check-workflow-domain.mermaid`
  - `diagrams/mermaid/15-dq-check-workflow-infra.mermaid`
  - `diagrams/mermaid/28-composition-root-di-graph-dataflow.mermaid`
  - `diagrams/mermaid/21-activity-entity-data-flow-overview.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Continue hotspot cleanup for dq/hexagonal dataflow package:
  - `diagrams/mermaid/26-hexagonal-ports-adapters-infra.mermaid`
  - `diagrams/mermaid/15-dq-check-workflow-overview.mermaid`
  - `diagrams/mermaid/21-activity-entity-data-flow-dataflow.mermaid`
  - `diagrams/mermaid/15-dq-check-workflow-dataflow.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Final hotspot cleanup package:
  - `diagrams/mermaid/26-hexagonal-ports-adapters-overview.mermaid`
  - `class-diagrams/13-domain-services.mmd`
  - `diagrams/mermaid/26-hexagonal-ports-adapters-dataflow.mermaid`
  - approach used: remove manual inline `&nbsp;` fillers; preserve metadata and relationships
- [x] Complete manual padding cleanup across scanned Mermaid sources (`total &nbsp; = 0`).
- [x] Add lint guard against manual spacing entity regressions:
  - `scripts/lint_diagrams.py`: `NBSP-001` (ERROR on `&nbsp;`)
  - `tests/architecture/test_diagram_lint_policy_rules.py`: coverage for `NBSP-001`
- [x] Expand ELK/layout + differentiated `linkStyle` usage for overloaded flowcharts:
  - lifecycle package: `diagrams/mermaid/31-pipeline-run-lifecycle-{domain,overview,infra}.mermaid`
  - single-record package: `diagrams/mermaid/32-single-record-journey-{domain,overview,infra,dataflow}.mermaid`
  - cli-interaction package: `diagrams/mermaid/33-cli-run-interaction-{domain,overview,infra,dataflow}.mermaid`
  - approach used: add ELK renderer init + semantic `linkStyle` groups (`primary`, `quarantine`, `shutdown`/`routing`, `failure`)
- [x] Include `harmonize_link_styles.py` in verification contour:
  - `src/tools/harmonize_link_styles.py`: added `--fail-on-errors` mode
  - `.github/workflows/docs.yml`: added CI step `python3 src/tools/harmonize_link_styles.py --dry-run --fail-on-errors`
  - purpose: ensure post-render harmonizer itself remains valid and error-free

Progress metric (2026-02-26):
- Total `&nbsp;` across scanned Mermaid sources reduced from **56,971** to **0** (`-56,971`, `100%`).

Acceptance:
- Fewer padding artifacts in source files.
- Better edge routing/readability in dense diagrams.

## Phase 4: Visual Regression Guard (Lower priority)

- [x] Add smoke visual regression in CI for selected reference diagrams:
  - baseline manifest: `docs/02-architecture/mmd-diagrams/visual-smoke-manifest.txt`
  - checker script: `scripts/check_diagram_visual_smoke.py`
  - workflow integration: `.github/workflows/docs.yml` (`render-diagrams` job)
  - strategy: compare selected baseline SVG files against working tree after render; fail on drift
  - coverage: 27 baseline SVGs across `foundation/`, `architecture/`, `class-diagrams/`

Acceptance:
- Style/layout regressions are visible in PR checks.

## Implementation Order (next actions)

1. Validate updated ruleset in docs CI and document rollout notes.
2. Broaden ELK/semantic-linkStyle rollout to additional dense flowcharts as needed.
3. Define manifest maintenance policy (which diagrams stay in smoke baseline set).

## Notes

- Working tree currently contains substantial unrelated changes; implementation should be scoped strictly to files listed per phase.
- Do not auto-reformat unrelated docs/diagram files during this workstream.

## Rollout Notes (2026-02-26)

- Local checks completed:
  - `python3 scripts/report_diagram_padding.py --top 5` → `total &nbsp;=0`
  - `python3 scripts/check_diagram_visual_smoke.py --manifest docs/02-architecture/mmd-diagrams/visual-smoke-manifest.txt` → pass (`27 baseline SVGs unchanged`)
  - `python3 src/tools/harmonize_link_styles.py --dry-run --fail-on-errors` → pass (`Errors: 0`)
  - `python3 scripts/lint_diagrams.py <updated files>` → pass
  - `pytest tests/architecture/test_diagram_lint_policy_rules.py -q` → pass
- CI-only confirmation point:
  - Full `docs.yml` run (including `render.sh` + Puppeteer runtime) remains the final merge gate for render-time determinism.

## Rollout Notes (2026-02-27)

- Layout strategy clarified and aligned in tooling:
  - `src/tools/apply_elk_layout.py` now uses `POLYLINE` by default.
  - Optional dense override added: `--dense-orthogonal-from N` (recommended start: `60`).
  - Default ELK auto-apply threshold adjusted to `@nodes > 15` for new flowcharts.
- Template guidance aligned to policy:
  - `docs/02-architecture/mmd-diagrams/_template.mmd` now documents `POLYLINE` as default route.
  - `ORTHOGONAL` documented as opt-in for very dense diagrams only.
- Adaptive policy applied to canonical architecture sources:
  - Removed explicit ELK init from 13 files with `@nodes <= 15` in `docs/02-architecture/mmd-diagrams/architecture/*.mmd`.
  - Post-state audit:
    - `<=15 nodes`: `ELK=0`, non-ELK=13
    - `16-40 nodes`: `ELK=14`
    - `>40 nodes`: `ELK=1`
  - Full re-render for `architecture/` completed: `29/29` OK (SVG + PNG).
- Verification:
  - `python3 -m py_compile src/tools/apply_elk_layout.py` → pass
