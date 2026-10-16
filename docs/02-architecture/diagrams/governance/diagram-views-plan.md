______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-10-15'

______________________________________________________________________

# Diagram Decomposition Plan

| Parent Diagram                                | Status     | Nodes | Overview | Domain-Focus | Infrastructure-Mapping | Data-Flow |
| --------------------------------------------- | ---------- | ----: | -------: | -----------: | ---------------------: | --------: |
| 01-full-system-component.mmd              | CRITICAL   |    60 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 01-high-level.mmd                         | OVERLOADED |    20 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 04-domain-layer-class-diagram.mmd         | OVERLOADED |    26 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 05-layers-interaction.mmd                 | OVERLOADED |    24 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 05-pipeline-lifecycle-states.mmd          | CRITICAL   |    51 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 06-application-layer-class-diagram.mmd    | OVERLOADED |    22 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 07-circuit-breaker-states.mmd             | OVERLOADED |    21 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 08-complete-etl-workflow.mmd              | CRITICAL   |    62 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 08-domain-ddd.mmd                         | OVERLOADED |    26 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 10-infrastructure-layer-class-diagram.mmd | OVERLOADED |    28 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 12-local-deployment-architecture.mmd      | OVERLOADED |    21 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 14-provider-health-states.mmd             | OVERLOADED |    21 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 15-dq-check-workflow.mmd                  | OVERLOADED |    26 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 21-activity-entity-data-flow.mmd          | OVERLOADED |    31 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 26-hexagonal-ports-adapters.mmd           | CRITICAL   |    48 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 28-composition-root-di-graph.mmd          | OVERLOADED |    28 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 29-composite-pipeline-workflow.mmd        | OVERLOADED |    33 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 31-pipeline-run-lifecycle.mmd             | OVERLOADED |    22 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 32-single-record-journey.mmd              | OVERLOADED |    20 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 33-cli-run-interaction.mmd                | OVERLOADED |    23 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 34-batch-processing-flow.mmd              | OVERLOADED |    23 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 36-architecture-principles-mindmap.mmd    | CRITICAL   |    81 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 39-medallion-invariants.mmd               | OVERLOADED |    22 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 41-error-classification-tree.mmd          | OVERLOADED |    24 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 44-cross-provider-enrichment.mmd          | OVERLOADED |    30 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 46-yaml-config-resolution.mmd             | OVERLOADED |    30 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 48-composite-phase-lifecycle.mmd          | OVERLOADED |    22 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 50-exception-hierarchy.mmd                | CRITICAL   |    82 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
