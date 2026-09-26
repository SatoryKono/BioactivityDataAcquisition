______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Diagram Decomposition Plan

| Parent Diagram                                | Status     | Nodes | Overview | Domain-Focus | Infrastructure-Mapping | Data-Flow |
| --------------------------------------------- | ---------- | ----: | -------: | -----------: | ---------------------: | --------: |
| 01-full-system-component.mermaid              | CRITICAL   |    60 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 01-high-level.mermaid                         | OVERLOADED |    20 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 04-domain-layer-class-diagram.mermaid         | OVERLOADED |    26 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 05-layers-interaction.mermaid                 | OVERLOADED |    24 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 05-pipeline-lifecycle-states.mermaid          | CRITICAL   |    51 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 06-application-layer-class-diagram.mermaid    | OVERLOADED |    22 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 07-circuit-breaker-states.mermaid             | OVERLOADED |    21 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 08-complete-etl-workflow.mermaid              | CRITICAL   |    62 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 08-domain-ddd.mermaid                         | OVERLOADED |    26 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 10-infrastructure-layer-class-diagram.mermaid | OVERLOADED |    28 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 12-local-deployment-architecture.mermaid      | OVERLOADED |    21 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 14-provider-health-states.mermaid             | OVERLOADED |    21 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 15-dq-check-workflow.mermaid                  | OVERLOADED |    26 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 21-activity-entity-data-flow.mermaid          | OVERLOADED |    31 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 26-hexagonal-ports-adapters.mermaid           | CRITICAL   |    48 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 28-composition-root-di-graph.mermaid          | OVERLOADED |    28 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 29-composite-pipeline-workflow.mermaid        | OVERLOADED |    33 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 31-pipeline-run-lifecycle.mermaid             | OVERLOADED |    22 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 32-single-record-journey.mermaid              | OVERLOADED |    20 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 33-cli-run-interaction.mermaid                | OVERLOADED |    23 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 34-batch-processing-flow.mermaid              | OVERLOADED |    23 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 36-architecture-principles-mindmap.mermaid    | CRITICAL   |    81 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 39-medallion-invariants.mermaid               | OVERLOADED |    22 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 41-error-classification-tree.mermaid          | OVERLOADED |    24 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 44-cross-provider-enrichment.mermaid          | OVERLOADED |    30 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 46-yaml-config-resolution.mermaid             | OVERLOADED |    30 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 48-composite-phase-lifecycle.mermaid          | OVERLOADED |    22 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
| 50-exception-hierarchy.mermaid                | CRITICAL   |    82 |      ≤15 |          ≤20 |                    ≤20 |       ≤12 |
