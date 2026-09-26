______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Diagram Views Inventory

Measured inventory for `docs/02-architecture/diagrams/views/*.mermaid`.

Current baseline reviewed on `2026-03-19`:

- `34` parent view families
- `31` foundation families with the full five-view set
- `3` architecture-derived families with reduced `full + overview` slices
- `1` service legend file (`00-legend.mermaid`)
- `162` tracked `.mermaid` files total

Parent-source truth stays in the canonical `.mmd` files under
`docs/02-architecture/diagrams/foundation/` and
`docs/02-architecture/diagrams/architecture/`.

| View family                             | Parent source                                                                        | Variants                                  | Files |
| --------------------------------------- | ------------------------------------------------------------------------------------ | ----------------------------------------- | ----: |
| `00-legend`                             | `(root legend)`                                                                      | `legend`                                  |     1 |
| `01-full-system-component`              | `docs/02-architecture/diagrams/foundation/01-full-system-component.mmd`              | `dataflow, domain, full, infra, overview` |     5 |
| `01-high-level`                         | `docs/02-architecture/diagrams/foundation/01-high-level.mmd`                         | `dataflow, domain, full, infra, overview` |     5 |
| `02-medallion`                          | `docs/02-architecture/diagrams/foundation/02-full-medallion-data-flow.mmd`           | `dataflow, domain, full, infra, overview` |     5 |
| `03-medallion-data-flow`                | `docs/02-architecture/diagrams/architecture/03-medallion-data-flow.mmd`              | `full, overview`                          |     2 |
| `04-domain-layer-class-diagram`         | `docs/02-architecture/diagrams/foundation/04-domain-layer-class-diagram.mmd`         | `dataflow, domain, full, infra, overview` |     5 |
| `05-layers-interaction`                 | `docs/02-architecture/diagrams/foundation/05-layers-interaction.mmd`                 | `dataflow, domain, full, infra, overview` |     5 |
| `05-pipeline-lifecycle-states`          | `docs/02-architecture/diagrams/foundation/05-pipeline-lifecycle-states.mmd`          | `dataflow, domain, full, infra, overview` |     5 |
| `06-application-layer-class-diagram`    | `docs/02-architecture/diagrams/foundation/06-application-layer-class-diagram.mmd`    | `dataflow, domain, full, infra, overview` |     5 |
| `07-circuit-breaker-states`             | `docs/02-architecture/diagrams/foundation/07-circuit-breaker-states.mmd`             | `dataflow, domain, full, infra, overview` |     5 |
| `08-complete-etl-workflow`              | `docs/02-architecture/diagrams/foundation/08-complete-etl-workflow.mmd`              | `dataflow, domain, full, infra, overview` |     5 |
| `08-domain-ddd`                         | `docs/02-architecture/diagrams/foundation/08-domain-ddd.mmd`                         | `dataflow, domain, full, infra, overview` |     5 |
| `10-infrastructure-layer-class-diagram` | `docs/02-architecture/diagrams/foundation/10-infrastructure-layer-class-diagram.mmd` | `dataflow, domain, full, infra, overview` |     5 |
| `12-local-deployment-architecture`      | `docs/02-architecture/diagrams/foundation/12-local-deployment-architecture.mmd`      | `dataflow, domain, full, infra, overview` |     5 |
| `13-port-protocol-contracts`            | `docs/02-architecture/diagrams/architecture/13-port-protocol-contracts.mmd`          | `full, overview`                          |     2 |
| `14-provider-health-states`             | `docs/02-architecture/diagrams/foundation/14-provider-health-states.mmd`             | `dataflow, domain, full, infra, overview` |     5 |
| `15-dq-check-workflow`                  | `docs/02-architecture/diagrams/foundation/15-dq-check-workflow.mmd`                  | `dataflow, domain, full, infra, overview` |     5 |
| `16-transformer-hierarchy`              | `docs/02-architecture/diagrams/architecture/16-transformer-hierarchy.mmd`            | `full, overview`                          |     2 |
| `21-activity-entity-data-flow`          | `docs/02-architecture/diagrams/foundation/21-activity-entity-data-flow.mmd`          | `dataflow, domain, full, infra, overview` |     5 |
| `26-hexagonal-ports-adapters`           | `docs/02-architecture/diagrams/foundation/26-hexagonal-ports-adapters.mmd`           | `dataflow, domain, full, infra, overview` |     5 |
| `28-composition-root-di-graph`          | `docs/02-architecture/diagrams/foundation/28-composition-root-di-graph.mmd`          | `dataflow, domain, full, infra, overview` |     5 |
| `29-composite-pipeline-workflow`        | `docs/02-architecture/diagrams/foundation/29-composite-pipeline-workflow.mmd`        | `dataflow, domain, full, infra, overview` |     5 |
| `30-port-adapter-mapping`               | `docs/02-architecture/diagrams/foundation/30-port-adapter-mapping.mmd`               | `dataflow, domain, full, infra, overview` |     5 |
| `31-pipeline-run-lifecycle`             | `docs/02-architecture/diagrams/foundation/31-pipeline-run-lifecycle.mmd`             | `dataflow, domain, full, infra, overview` |     5 |
| `32-single-record-journey`              | `docs/02-architecture/diagrams/foundation/32-single-record-journey.mmd`              | `dataflow, domain, full, infra, overview` |     5 |
| `33-cli-run-interaction`                | `docs/02-architecture/diagrams/foundation/33-cli-run-interaction.mmd`                | `dataflow, domain, full, infra, overview` |     5 |
| `34-batch-processing-flow`              | `docs/02-architecture/diagrams/foundation/34-batch-processing-flow.mmd`              | `dataflow, domain, full, infra, overview` |     5 |
| `35-bootstrap-sequence`                 | `docs/02-architecture/diagrams/foundation/35-bootstrap-sequence.mmd`                 | `dataflow, domain, full, infra, overview` |     5 |
| `36-architecture-principles-mindmap`    | `docs/02-architecture/diagrams/foundation/36-architecture-principles-mindmap.mmd`    | `dataflow, domain, full, infra, overview` |     5 |
| `39-medallion-invariants`               | `docs/02-architecture/diagrams/foundation/39-medallion-invariants.mmd`               | `dataflow, domain, full, infra, overview` |     5 |
| `41-error-classification-tree`          | `docs/02-architecture/diagrams/foundation/41-error-classification-tree.mmd`          | `dataflow, domain, full, infra, overview` |     5 |
| `44-cross-provider-enrichment`          | `docs/02-architecture/diagrams/foundation/44-cross-provider-enrichment.mmd`          | `dataflow, domain, full, infra, overview` |     5 |
| `46-yaml-config-resolution`             | `docs/02-architecture/diagrams/foundation/46-yaml-config-resolution.mmd`             | `dataflow, domain, full, infra, overview` |     5 |
| `48-composite-phase-lifecycle`          | `docs/02-architecture/diagrams/foundation/48-composite-phase-lifecycle.mmd`          | `dataflow, domain, full, infra, overview` |     5 |
| `50-exception-hierarchy`                | `docs/02-architecture/diagrams/foundation/50-exception-hierarchy.mmd`                | `dataflow, domain, full, infra, overview` |     5 |
