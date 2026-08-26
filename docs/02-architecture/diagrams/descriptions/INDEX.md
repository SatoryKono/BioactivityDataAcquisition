# Diagram Descriptions Index

_Автогенерация: 2026-07-18T17:33:44+03:00_

- Карточек описаний: **325**
- Формат публикации: family-oriented index для derived description cards.
- Source of truth: individual description cards под `descriptions/<family>/`.

## Related Indexes

- [Class descriptions family index](./class/INDEX.md)
- [MMD diagram descriptions map](./class-summary.md)
- [Architecture bundle with descriptions](../bundles/architecture.bundle.md)
- [Class bundle with descriptions](../bundles/class.bundle.md)
- [Foundation bundle with descriptions](../bundles/foundation.bundle.md)
- [Views bundle with descriptions](../bundles/views.bundle.md)

## Family Overview

- Architecture cards: **89**
- Class cards: **16**
- Foundation cards: **55**
- View cards: **165** across **38** parent families

## Architecture Cards

- [01-high-level-hexagonal-simple](architecture/01-high-level-hexagonal-simple.md)
- [01-high-level-hexagonal](architecture/01-high-level-hexagonal.md)
- [01a-hexagonal-overview](architecture/01a-hexagonal-overview.md)
- [01b-hexagonal-domain-app](architecture/01b-hexagonal-domain-app.md)
- [01c-hexagonal-infra-comp](architecture/01c-hexagonal-infra-comp.md)
- [01d-hexagonal-overview-rounded](architecture/01d-hexagonal-overview-rounded.md)
- [02-layer-dependency-matrix](architecture/02-layer-dependency-matrix.md)
- [03-medallion-data-flow](architecture/03-medallion-data-flow.md)
- [03a-medallion-layers-overview](architecture/03a-medallion-layers-overview.md)
- [04-pipeline-execution-flow](architecture/04-pipeline-execution-flow.md)
- [05-provider-adapter-hierarchy](architecture/05-provider-adapter-hierarchy.md)
- [05a-adapter-hierarchy-base](architecture/05a-adapter-hierarchy-base.md)
- [05b-adapter-hierarchy-providers](architecture/05b-adapter-hierarchy-providers.md)
- [06-storage-layer](architecture/06-storage-layer.md)
- [06a-storage-writers](architecture/06a-storage-writers.md)
- [06b-storage-support](architecture/06b-storage-support.md)
- [07-dq-system](architecture/07-dq-system.md)
- [07a-dq-analysis](architecture/07a-dq-analysis.md)
- [07b-dq-pipeline](architecture/07b-dq-pipeline.md)
- [08-composite-pipeline](architecture/08-composite-pipeline.md)
- [08a-composite-config](architecture/08a-composite-config.md)
- [08b-composite-execution](architecture/08b-composite-execution.md)
- [09-observability-stack](architecture/09-observability-stack.md)
- [09a-observability-app](architecture/09a-observability-app.md)
- [09b-observability-infra](architecture/09b-observability-infra.md)
- [10-resilience-patterns](architecture/10-resilience-patterns.md)
- [11-configuration-system](architecture/11-configuration-system.md)
- [11a-config-loading](architecture/11a-config-loading.md)
- [11b-config-domain](architecture/11b-config-domain.md)
- [12-bootstrap-di-container](architecture/12-bootstrap-di-container.md)
- [12a-bootstrap-factories](architecture/12a-bootstrap-factories.md)
- [12b-bootstrap-wiring](architecture/12b-bootstrap-wiring.md)
- [13-port-protocol-contracts](architecture/13-port-protocol-contracts.md)
- [13a-data-storage-ports](architecture/13a-data-storage-ports.md)
- [13b-operational-ports](architecture/13b-operational-ports.md)
- [13c-validation-dq-ports](architecture/13c-validation-dq-ports.md)
- [13d-port-contracts-services](architecture/13d-port-contracts-services.md)
- [13e-operational-ports-domain](architecture/13e-operational-ports-domain.md)
- [13f-operational-ports-infra](architecture/13f-operational-ports-infra.md)
- [13g-port-contracts-data-sources](architecture/13g-port-contracts-data-sources.md)
- [13h-port-contracts-storage](architecture/13h-port-contracts-storage.md)
- [13i-port-contracts-observability](architecture/13i-port-contracts-observability.md)
- [14-cli-interface-layer](architecture/14-cli-interface-layer.md)
- [14a-cli-commands](architecture/14a-cli-commands.md)
- [14b-cli-routing](architecture/14b-cli-routing.md)
- [15-batch-executor-internals](architecture/15-batch-executor-internals.md)
- [16-transformer-hierarchy](architecture/16-transformer-hierarchy.md)
- [16a-transformer-base](architecture/16a-transformer-base.md)
- [16b-transformer-pub-other](architecture/16b-transformer-pub-other.md)
- [17-security-pii-audit](architecture/17-security-pii-audit.md)
- [18-lock-checkpoint-shutdown](architecture/18-lock-checkpoint-shutdown.md)
- [18a-lock-system](architecture/18a-lock-system.md)
- [18b-checkpoint-shutdown](architecture/18b-checkpoint-shutdown.md)
- [19-control-plane-artifacts](architecture/19-control-plane-artifacts.md)
- [20-data-traceability-runtime](architecture/20-data-traceability-runtime.md)
- [21-idempotent-processing-guards](architecture/21-idempotent-processing-guards.md)
- [22-data-operations-observability](architecture/22-data-operations-observability.md)
- [23-reproducible-run-contract](architecture/23-reproducible-run-contract.md)
- [24-control-plane-artifact-publication-pipeline](architecture/24-control-plane-artifact-publication-pipeline.md)
- [25-effective-execution-config-resolution-and-artifact-hashing](architecture/25-effective-execution-config-resolution-and-artifact-hashing.md)
- [26-reproducible-run-contract-across-manifest-ledger-and-output-metadata](architecture/26-reproducible-run-contract-across-manifest-ledger-and-output-metadata.md)
- [27-composite-preflight-field-priority-and-normalization-compatibility-resolution](architecture/27-composite-preflight-field-priority-and-normalization-compatibility-resolution.md)
- [28-historical-replay-universe-inventory-and-closure-report](architecture/28-historical-replay-universe-inventory-and-closure-report.md)
- [29-provider-registry-loading-to-data-source-creation](architecture/29-provider-registry-loading-to-data-source-creation.md)
- [30-postrun-retention-deduplication-and-vacuum-warning-path](architecture/30-postrun-retention-deduplication-and-vacuum-warning-path.md)
- [31-workflow-control-plane-manifest-and-ledger-publication](architecture/31-workflow-control-plane-manifest-and-ledger-publication.md)
- [32-lock-heartbeat-checkpoint-and-shutdown-collaboration](architecture/32-lock-heartbeat-checkpoint-and-shutdown-collaboration.md)
- [33-pipeline-service-bundle-and-runner-dependencies](architecture/33-pipeline-service-bundle-and-runner-dependencies.md)
- [34-pipelinerun-aggregate-stage-result-and-terminal-transition-model](architecture/34-pipelinerun-aggregate-stage-result-and-terminal-transition-model.md)
- [35-batch-aggregate-seal-write-commit-failure-lifecycle](architecture/35-batch-aggregate-seal-write-commit-failure-lifecycle.md)
- [36-quarantine-entry-review-resolution-and-discard-flow](architecture/36-quarantine-entry-review-resolution-and-discard-flow.md)
- [37-observability-bootstrap-bundle-from-settings-to-ports](architecture/37-observability-bootstrap-bundle-from-settings-to-ports.md)
- [38-chembl-bronze-activity-extraction-to-artifact-publication](architecture/38-chembl-bronze-activity-extraction-to-artifact-publication.md)
- [39-crossref-search-fallback-and-batch-doi-fetch-publications](architecture/39-crossref-search-fallback-and-batch-doi-fetch-publications.md)
- [40-pubmed-search-fetch-xml-parse-and-publication-mapping](architecture/40-pubmed-search-fetch-xml-parse-and-publication-mapping.md)
- [41-openalex-cursor-pagination-and-response-mapping-path](architecture/41-openalex-cursor-pagination-and-response-mapping-path.md)
- [42-semanticscholar-search-fallback-and-batch-request-flow](architecture/42-semanticscholar-search-fallback-and-batch-request-flow.md)
- [43-uniprot-mapping-job-to-protein-fetch-enrichment](architecture/43-uniprot-mapping-job-to-protein-fetch-enrichment.md)
- [44-pubchem-fetch-strategy-resolution-for-compounds](architecture/44-pubchem-fetch-strategy-resolution-for-compounds.md)
- [45-dq-contract-config-loading-and-policy-resolution](architecture/45-dq-contract-config-loading-and-policy-resolution.md)
- [46-filter-config-resolution-and-column-filter-evaluation](architecture/46-filter-config-resolution-and-column-filter-evaluation.md)
- [47-run-manifest-domain-model-and-serialization-surface](architecture/47-run-manifest-domain-model-and-serialization-surface.md)
- [48-effective-config-artifact-domain-model](architecture/48-effective-config-artifact-domain-model.md)
- [49-chembl-pipeline-activity-dataflow](architecture/49-chembl-pipeline-activity-dataflow.md)
- [50-chembl-pipeline-activity-filter-criteria](architecture/50-chembl-pipeline-activity-filter-criteria.md)
- [51a-chembl-pipeline-activity-silver-fields-1](architecture/51a-chembl-pipeline-activity-silver-fields-1.md)
- [51b-chembl-pipeline-activity-silver-fields-2](architecture/51b-chembl-pipeline-activity-silver-fields-2.md)
- [52a-chembl-pipeline-activity-gold-fields-1](architecture/52a-chembl-pipeline-activity-gold-fields-1.md)
- [52b-chembl-pipeline-activity-gold-fields-2](architecture/52b-chembl-pipeline-activity-gold-fields-2.md)

## Class Diagram Cards

- Dedicated family index: [class/INDEX.md](./class/INDEX.md)
- Narrative map for class-diagram families: [class-summary.md](./class-summary.md)

## Foundation Cards

- [01-full-system-component](foundation/01-full-system-component.md)
- [01-high-level](foundation/01-high-level.md)
- [02-full-medallion-data-flow](foundation/02-full-medallion-data-flow.md)
- [03-pipeline-execution-happy-path](foundation/03-pipeline-execution-happy-path.md)
- [04-domain-layer-class-diagram](foundation/04-domain-layer-class-diagram.md)
- [04-error-flow](foundation/04-error-flow.md)
- [05-layers-interaction](foundation/05-layers-interaction.md)
- [05-pipeline-lifecycle-states](foundation/05-pipeline-lifecycle-states.md)
- [06-application-layer-class-diagram](foundation/06-application-layer-class-diagram.md)
- [06-pipeline-execution](foundation/06-pipeline-execution.md)
- [07-circuit-breaker-states](foundation/07-circuit-breaker-states.md)
- [07-medallion-flow](foundation/07-medallion-flow.md)
- [08-complete-etl-workflow](foundation/08-complete-etl-workflow.md)
- [08-domain-ddd](foundation/08-domain-ddd.md)
- [09-full-er-diagram](foundation/09-full-er-diagram.md)
- [10-infrastructure-layer-class-diagram](foundation/10-infrastructure-layer-class-diagram.md)
- [11-lock-acquisition-sequence](foundation/11-lock-acquisition-sequence.md)
- [12-local-deployment-architecture](foundation/12-local-deployment-architecture.md)
- [13-domain-models-relationship](foundation/13-domain-models-relationship.md)
- [14-provider-health-states](foundation/14-provider-health-states.md)
- [15-dq-check-workflow](foundation/15-dq-check-workflow.md)
- [16-memory-lock-class](foundation/16-memory-lock-class.md)
- [17-pipeline-hierarchy](foundation/17-pipeline-hierarchy.md)
- [18-bronze-write-sequence](foundation/18-bronze-write-sequence.md)
- [19-delta-lake-write-sequence](foundation/19-delta-lake-write-sequence.md)
- [20-quarantine-record-states](foundation/20-quarantine-record-states.md)
- [21-activity-entity-data-flow](foundation/21-activity-entity-data-flow.md)
- [22-client-api-request-sequence](foundation/22-client-api-request-sequence.md)
- [23-silver-writer-class](foundation/23-silver-writer-class.md)
- [24-hash-service-class](foundation/24-hash-service-class.md)
- [25-circuit-breaker-observer-class](foundation/25-circuit-breaker-observer-class.md)
- [26-hexagonal-ports-adapters](foundation/26-hexagonal-ports-adapters.md)
- [27-import-matrix-enforcement](foundation/27-import-matrix-enforcement.md)
- [28-composition-root-di-graph](foundation/28-composition-root-di-graph.md)
- [29-composite-pipeline-workflow](foundation/29-composite-pipeline-workflow.md)
- [30-port-adapter-mapping](foundation/30-port-adapter-mapping.md)
- [31-pipeline-run-lifecycle](foundation/31-pipeline-run-lifecycle.md)
- [32-single-record-journey](foundation/32-single-record-journey.md)
- [33-cli-run-interaction](foundation/33-cli-run-interaction.md)
- [34-batch-processing-flow](foundation/34-batch-processing-flow.md)
- [35-bootstrap-sequence](foundation/35-bootstrap-sequence.md)
- [36-architecture-principles-mindmap](foundation/36-architecture-principles-mindmap.md)
- [37-cli-entry-full-chain](foundation/37-cli-entry-full-chain.md)
- [38-runtime-assembly-sequence](foundation/38-runtime-assembly-sequence.md)
- [39-medallion-invariants](foundation/39-medallion-invariants.md)
- [40-application-core-collaboration](foundation/40-application-core-collaboration.md)
- [41-error-classification-tree](foundation/41-error-classification-tree.md)
- [42-pipeline-runner-class](foundation/42-pipeline-runner-class.md)
- [43-fan-out-fan-in-pattern](foundation/43-fan-out-fan-in-pattern.md)
- [44-cross-provider-enrichment](foundation/44-cross-provider-enrichment.md)
- [46-yaml-config-resolution](foundation/46-yaml-config-resolution.md)
- [47-publication-merge-sources](foundation/47-publication-merge-sources.md)
- [48-composite-phase-lifecycle](foundation/48-composite-phase-lifecycle.md)
- [49-composite-runner-class](foundation/49-composite-runner-class.md)
- [50-exception-hierarchy](foundation/50-exception-hierarchy.md)

## View Families

- [00-legend](views/00-legend.md)
- [01-full-system-component](views/01-full-system-component-full.md) - 5 cards: dataflow, domain, full, infra, overview
- [01-high-level](views/01-high-level-full.md) - 5 cards: dataflow, domain, full, infra, overview
- [02-medallion](views/02-medallion-full.md) - 5 cards: dataflow, domain, full, infra, overview
- [03-medallion-data-flow](views/03-medallion-data-flow-full.md) - 2 cards: full, overview
- [04-domain-layer-class-diagram](views/04-domain-layer-class-diagram-full.md) - 5 cards: dataflow, domain, full, infra, overview
- [05-layers-interaction](views/05-layers-interaction-full.md) - 5 cards: dataflow, domain, full, infra, overview
- [05-pipeline-lifecycle-states](views/05-pipeline-lifecycle-states-full.md) - 5 cards: dataflow, domain, full, infra, overview
- [06-application-layer-class-diagram](views/06-application-layer-class-diagram-full.md) - 5 cards: dataflow, domain, full, infra, overview
- [07-circuit-breaker-states](views/07-circuit-breaker-states-full.md) - 5 cards: dataflow, domain, full, infra, overview
- [08-complete-etl-workflow](views/08-complete-etl-workflow-full.md) - 5 cards: dataflow, domain, full, infra, overview
- [08-domain-ddd](views/08-domain-ddd-full.md) - 5 cards: dataflow, domain, full, infra, overview
- [10-infrastructure-layer-class-diagram](views/10-infrastructure-layer-class-diagram-full.md) - 5 cards: dataflow, domain, full, infra, overview
- [12-local-deployment-architecture](views/12-local-deployment-architecture-full.md) - 5 cards: dataflow, domain, full, infra, overview
- [13-port-protocol-contracts](views/13-port-protocol-contracts-full.md) - 2 cards: full, overview
- [14-provider-health-states](views/14-provider-health-states-full.md) - 5 cards: dataflow, domain, full, infra, overview
- [15-dq-check-workflow](views/15-dq-check-workflow-full.md) - 5 cards: dataflow, domain, full, infra, overview
- [16-transformer-hierarchy](views/16-transformer-hierarchy-full.md) - 2 cards: full, overview
- [21-activity-entity-data-flow](views/21-activity-entity-data-flow-full.md) - 5 cards: dataflow, domain, full, infra, overview
- [21-idempotent-processing-guards-overview](views/21-idempotent-processing-guards-overview.md)
- [23-reproducible-run-contract-overview](views/23-reproducible-run-contract-overview.md)
- [24-data-runtime-quality-map-overview](views/24-data-runtime-quality-map-overview.md)
- [26-hexagonal-ports-adapters](views/26-hexagonal-ports-adapters-full.md) - 5 cards: dataflow, domain, full, infra, overview
- [28-composition-root-di-graph](views/28-composition-root-di-graph-full.md) - 5 cards: dataflow, domain, full, infra, overview
- [29-composite-pipeline-workflow](views/29-composite-pipeline-workflow-full.md) - 5 cards: dataflow, domain, full, infra, overview
- [30-port-adapter-mapping](views/30-port-adapter-mapping-full.md) - 5 cards: dataflow, domain, full, infra, overview
- [31-pipeline-run-lifecycle](views/31-pipeline-run-lifecycle-full.md) - 5 cards: dataflow, domain, full, infra, overview
- [32-single-record-journey](views/32-single-record-journey-full.md) - 5 cards: dataflow, domain, full, infra, overview
- [33-cli-run-interaction](views/33-cli-run-interaction-full.md) - 5 cards: dataflow, domain, full, infra, overview
- [34-batch-processing-flow](views/34-batch-processing-flow-full.md) - 5 cards: dataflow, domain, full, infra, overview
- [35-bootstrap-sequence](views/35-bootstrap-sequence-full.md) - 5 cards: dataflow, domain, full, infra, overview
- [36-architecture-principles-mindmap](views/36-architecture-principles-mindmap-full.md) - 5 cards: dataflow, domain, full, infra, overview
- [39-medallion-invariants](views/39-medallion-invariants-full.md) - 5 cards: dataflow, domain, full, infra, overview
- [41-error-classification-tree](views/41-error-classification-tree-full.md) - 5 cards: dataflow, domain, full, infra, overview
- [44-cross-provider-enrichment](views/44-cross-provider-enrichment-full.md) - 5 cards: dataflow, domain, full, infra, overview
- [46-yaml-config-resolution](views/46-yaml-config-resolution-full.md) - 5 cards: dataflow, domain, full, infra, overview
- [48-composite-phase-lifecycle](views/48-composite-phase-lifecycle-full.md) - 5 cards: dataflow, domain, full, infra, overview
- [50-exception-hierarchy](views/50-exception-hierarchy-full.md) - 5 cards: dataflow, domain, full, infra, overview
