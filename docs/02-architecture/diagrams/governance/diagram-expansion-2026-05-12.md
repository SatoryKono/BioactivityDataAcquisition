# Diagram Expansion Plan — 2026-05-12

## Baseline Notes

- Prompt alias files in `docs/00-project/01-domain-objects.md`, `02-etl-layers.md`, `03-data-flow.md`, `05-physical-layout.md` were already retired; canonical replacements were resolved through `docs/00-project/architecture-index.md`.
- Live ADR inventory currently contains `47` accepted/historical ADR files (`ADR-001`..`ADR-047`), not the older 38-file subset.
- Current measured diagram baseline was taken from `docs/02-architecture/diagrams/governance/policy.md`, `diagrams-index.md`, and `diagram-views-inventory.md`.

## Proposal Counts

- `Architecture`: `60`
- `DataFlow`: `60`
- `Pattern`: `50`
- `Component`: `50`
- `Interaction`: `50`
- `Lifecycle`: `40`
- `Provider`: `50`
- `Configuration`: `30`
- `DomainModel`: `30`
- `Composite`: `20`
- `Observability`: `20`
- `ErrorHandling`: `20`
- `Testing`: `10`
- `Security`: `5`
- `Performance`: `5`

## Part 1 — 500 New Diagram Proposals

| # | Title | Type | Category | Description |
|---|---|---|---|---|
| 1 | Control Plane Artifact Publication Pipeline | flowchart | Architecture | Maps how run manifests, effective config artifacts, and ledger references are published from runtime assembly into durable control-plane outputs. |
| 2 | Effective Execution Config Resolution And Artifact Hashing | sequenceDiagram | Architecture | Shows how runtime settings, pipeline config, DQ policy, and environment inputs converge into an effective execution config artifact with stable hashes. |
| 3 | Reproducible Run Contract Across Manifest Ledger And Output Metadata | flowchart | Architecture | Connects manifest, ledger, metadata, and medallion outputs into one end-to-end reproducibility contract. |
| 4 | Composite Preflight Field Priority And Normalization Compatibility Resolution | sequenceDiagram | Composite | Explains how composite preflight validates field priorities, source availability, schema agreement, and normalization compatibility overrides. |
| 5 | Historical Replay Universe Inventory And Closure Report | sequenceDiagram | Architecture | Shows how historical replay inventory and closure reports are assembled from manifests, ledger evidence, and external archive markers. |
| 6 | Provider Registry Loading To Data Source Creation | sequenceDiagram | Architecture | Traces registry readiness, provider config lookup, adapter creation, and final data-source construction. |
| 7 | Postrun Retention Deduplication And Vacuum Warning Path | sequenceDiagram | Interaction | Documents how postrun compaction invokes retention helpers, handles dedup timeouts, and degrades to warnings when allowed. |
| 8 | Workflow Control Plane Manifest And Ledger Publication | flowchart | Architecture | Visualizes workflow-level control-plane entities and their publication boundary relative to run-level artifacts. |
| 9 | Lock Heartbeat Checkpoint And Shutdown Collaboration | sequenceDiagram | Interaction | Shows the operational collaboration between lock ownership, heartbeat publication, checkpoint persistence, and shutdown signaling. |
| 10 | Pipeline Service Bundle And Runner Dependencies | classDiagram | Component | Captures the object graph around PipelineRunner, PipelineService, and the storage/quality/control-plane seams they depend on. |
| 11 | PipelineRun Aggregate Stage Result And Terminal Transition Model | stateDiagram | Lifecycle | Focuses on PipelineRun transitions, stage result capture, and terminal failure or cancellation behavior. |
| 12 | Batch Aggregate Seal Write Commit Failure Lifecycle | stateDiagram | Lifecycle | Explains the stateful progression of Batch aggregates from intake through write or failure. |
| 13 | Quarantine Entry Review Resolution And Discard Flow | stateDiagram | Lifecycle | Shows review-state transitions for quarantined records and the paths to resolution or discard. |
| 14 | Observability Bootstrap Bundle From Settings To Ports | flowchart | Observability | Documents how logger, metrics, tracer, DQ monitor, and optional metrics server are bootstrapped from runtime settings. |
| 15 | ChEMBL Activity Extraction To Bronze Artifact Publication | sequenceDiagram | Provider | Shows the concrete call path for ChEMBL activity fetch, related-entity expansion, and bronze artifact write. |
| 16 | CrossRef Publication Search Fallback And Batch DOI Fetch | sequenceDiagram | Provider | Explains the fallback-aware CrossRef publication path across search, DOI batching, and response mapping. |
| 17 | PubMed Search Fetch XML Parse And Publication Mapping | sequenceDiagram | Provider | Visualizes the PubMed publication flow from search through XML parsing into mapped publication entities. |
| 18 | OpenAlex Cursor Pagination And Response Mapping Path | sequenceDiagram | Provider | Shows how OpenAlex cursor pagination, query execution, fallback, and response mapping cooperate. |
| 19 | SemanticScholar Search Fallback And Batch Request Flow | sequenceDiagram | Provider | Maps the Semantic Scholar adapter stack across search fetch flow, batch requests, and fallback policy. |
| 20 | UniProt IDMapping To Protein Fetch Enrichment | flowchart | Provider | Documents the split UniProt path between idmapping jobs and protein feature retrieval. |
| 21 | PubChem Compound Fetch Strategy Resolution | flowchart | Provider | Shows how PubChem compound requests select fetch strategies, query builders, and response mappers. |
| 22 | DQ Contract Config Loading And Policy Resolution | flowchart | Configuration | Connects YAML DQ config, loaders, normalizers, and domain snapshots used by the DQ contract system. |
| 23 | Filter Config Resolution And Column Filter Evaluation | flowchart | Configuration | Shows how filter config is loaded and then evaluated by column and range filters across medallion stages. |
| 24 | Run Manifest Domain Model And Serialization Surface | classDiagram | Component | Focuses on the RunManifest model, nested refs, and serialization entrypoints. |
| 25 | Effective Config Artifact Domain Model | classDiagram | Component | Shows the nested domain models composing the effective config artifact published for reproducibility. |
| 26 | Workflow Manifest Step Serialization Surface | classDiagram | Component | Maps workflow manifest nesting and step serialization helpers. |
| 27 | Run Ledger Entry Replay Slice Model | classDiagram | Component | Explains the structure of ledger entries and replay slicing helpers. |
| 28 | Composite Dependency Join Planning And Join Key Resolution | flowchart | Composite | Shows how dependency joins are planned, normalized, and executed for composite datasets. |
| 29 | EnrichmentCoordinatorService Dependency Fan-Out And Result Reduction | sequenceDiagram | Interaction | Visualizes coordinator fan-out across enrichers and the reduction path back into one composite result. |
| 30 | DependencyJoinerService Composite Key Join And System Column Cleanup | flowchart | Component | Shows how dependency joins apply composite keys and then clean temporary system columns. |
| 31 | CompositePipelineRunner Stage State And Merge Boundaries | stateDiagram | Lifecycle | Documents the runner stage machine around seed, dependency, enrichment, merge, and terminal phases. |
| 32 | PipelineRunner Control Surface And Attached Ledger Service | classDiagram | Component | Focuses on PipelineRunner properties, service attachment, and execution diagnostics surfaces. |
| 33 | PipelineStorageProtocol And PipelineService Dependency Boundary | classDiagram | Component | Shows the protocol-driven storage dependency boundary used by application services. |
| 34 | Provider Health Monitor State Adaptation And Config Adjustment | stateDiagram | ErrorHandling | Explains how provider health state evolves and influences adaptive config decisions. |
| 35 | UnifiedHTTPClient Retry Policy And Circuit Breaker Interaction | sequenceDiagram | ErrorHandling | Shows the inner HTTP resilience stack around retry decisions, breaker checks, and request execution. |
| 36 | OpenTelemetryTracer And StructlogLogger Bootstrap Surfaces | classDiagram | Observability | Maps the main tracing and logging runtime surfaces exposed to the application layer. |
| 37 | Bootstrap Runtime Observability And Metrics Server Start Path | sequenceDiagram | Observability | Shows bootstrap-time sequencing around logger creation, tracer setup, metrics setup, and optional metrics server startup. |
| 38 | Runtime Builder Control Plane Inputs To Effective Config Artifact | flowchart | Architecture | Explains how runtime builders transform resolved inputs into control-plane artifacts. |
| 39 | Contract Registry Policy Resolution And Gold Contract Selection | flowchart | Architecture | Maps how contract registry helpers resolve gold contract policy and implementation selection. |
| 40 | Local Checkpoint Resume Decision Versus Workflow Ledger Replay | flowchart | ErrorHandling | Contrasts resume decisions derived from local checkpoints with replay decisions derived from workflow ledger state. |
| 41 | Publication Composite Merge Source Priority And Override Review Path | flowchart | DataFlow | Shows how publication sources compete for fields and where overrides are reviewed or normalized. |
| 42 | Control Plane Artifact Traceability From CLI To Run Manifest Inspection | sequenceDiagram | Interaction | Traces how CLI commands expose run manifests, histories, and control-plane diagnostics to operators. |
| 43 | Bronze Metadata To Silver Metadata To Gold Metadata Progression | sankey-beta | DataFlow | Summarizes how metadata references and lineage fragments progress across medallion layers. |
| 44 | Cached Bronze Snapshot And Exact Replay Input Resolution | flowchart | DataFlow | Shows how cached bronze snapshots feed exact replay input resolution in runtime builders. |
| 45 | Data Traceability Runtime Path For Manifest Effective Config And Lineage | flowchart | DataFlow | Connects traceability anchors across manifest, effective config, lineage graph, and metadata bundles. |
| 46 | Composite Lifecycle Observer Tracing And Metrics Publication | sequenceDiagram | Interaction | Shows how composite lifecycle observers publish traces and metrics during stage transitions. |
| 47 | Schema Domain Pair Governance From Domain Schemas To Gold Contract | flowchart | Configuration | Maps schema-domain pairing through canonical schema generation into gold contract governance. |
| 48 | Entity Normalization Services For DOI Title Abstract And Unit Surfaces | classDiagram | Pattern | Shows how normalization and validation services handle key publication and activity fields. |
| 49 | Factory Method Pipeline Assembly Across Construction Helpers | flowchart | Pattern | Explains the factory-method style assembly of pipeline runners from composition helpers and factories. |
| 50 | Decorator And Fallback Pattern Stack Around Provider Adapters | classDiagram | Pattern | Shows how adapters compose fallback policy, retry, and circuit-breaker decorators or mixins. |
| 51 | Port Capability Cluster For Runtime Services | classDiagram | Architecture | Groups the runtime ports (LockPort, CheckpointPort, ShutdownPort, HealthCheckPort) by responsibility and boundary semantics. |
| 52 | Port Capability Cluster For Storage Services | classDiagram | Architecture | Groups the storage ports (StoragePort, DeltaReaderPort, MetadataCoordinatorPort, MetadataPort) by responsibility and boundary semantics. |
| 53 | Port Capability Cluster For Quality Services | classDiagram | Architecture | Groups the quality ports (ValidationPort, DQMonitorPort, DQReportWriterPort, DQConfigLoaderPort) by responsibility and boundary semantics. |
| 54 | Port Capability Cluster For Observability Services | classDiagram | Architecture | Groups the observability ports (LoggerPort, MetricsPort, TracingPort, AuditPort) by responsibility and boundary semantics. |
| 55 | Port Capability Cluster For Source Services | classDiagram | Architecture | Groups the source ports (DataSourcePort, FilterableDataSourcePort, FilterConfigLoaderPort, PIIHasherPort) by responsibility and boundary semantics. |
| 56 | Run Manifest Inspection Surface | flowchart | Architecture | Shows the canonical BioETL architecture slice for run manifest inspection surface across the active layers. |
| 57 | Workflow Execution Orchestration | flowchart | Architecture | Shows the canonical BioETL architecture slice for workflow execution orchestration across the active layers. |
| 58 | Control Plane CLI Routing | flowchart | Architecture | Shows the canonical BioETL architecture slice for control plane cli routing across the active layers. |
| 59 | Artifact Lifecycle Governance | flowchart | Architecture | Shows the canonical BioETL architecture slice for artifact lifecycle governance across the active layers. |
| 60 | Contract Registry And Gold Policy | flowchart | Architecture | Shows the canonical BioETL architecture slice for contract registry and gold policy across the active layers. |
| 61 | Cached Bronze Replay Inputs | flowchart | Architecture | Shows the canonical BioETL architecture slice for cached bronze replay inputs across the active layers. |
| 62 | Runtime Builder Control Plane Assembly | flowchart | Architecture | Shows the canonical BioETL architecture slice for runtime builder control plane assembly across the active layers. |
| 63 | Lineage Graph Publication | flowchart | Architecture | Shows the canonical BioETL architecture slice for lineage graph publication across the active layers. |
| 64 | Metadata Bundle Publication | flowchart | Architecture | Shows the canonical BioETL architecture slice for metadata bundle publication across the active layers. |
| 65 | Local-Only Operations Boundary | flowchart | Architecture | Shows the canonical BioETL architecture slice for local-only operations boundary across the active layers. |
| 66 | DI Registry Expansion Paths | flowchart | Architecture | Shows the canonical BioETL architecture slice for di registry expansion paths across the active layers. |
| 67 | Health Server To Composition API Boundary | flowchart | Architecture | Shows the canonical BioETL architecture slice for health server to composition api boundary across the active layers. |
| 68 | Pipeline Registry Resolution | flowchart | Architecture | Shows the canonical BioETL architecture slice for pipeline registry resolution across the active layers. |
| 69 | Exact Replay Provenance Surface | flowchart | Architecture | Shows the canonical BioETL architecture slice for exact replay provenance surface across the active layers. |
| 70 | Workflow Ledger Recovery Boundary | flowchart | Architecture | Shows the canonical BioETL architecture slice for workflow ledger recovery boundary across the active layers. |
| 71 | Batch Execution Runtime Choreography | flowchart | Architecture | Shows the canonical BioETL architecture slice for batch execution runtime choreography across the active layers. |
| 72 | Config Loader Domain Resolver | flowchart | Architecture | Shows the canonical BioETL architecture slice for config loader domain resolver across the active layers. |
| 73 | Composite Runtime Wiring Contract | flowchart | Architecture | Shows the canonical BioETL architecture slice for composite runtime wiring contract across the active layers. |
| 74 | Publication Bridge Compatibility Layer | flowchart | Architecture | Shows the canonical BioETL architecture slice for publication bridge compatibility layer across the active layers. |
| 75 | Run Manifest Diagnostics Surface | flowchart | Architecture | Shows the canonical BioETL architecture slice for run manifest diagnostics surface across the active layers. |
| 76 | Historical Replay Inspection Surface | flowchart | Architecture | Shows the canonical BioETL architecture slice for historical replay inspection surface across the active layers. |
| 77 | Workflow Maintenance Command Boundary | flowchart | Architecture | Shows the canonical BioETL architecture slice for workflow maintenance command boundary across the active layers. |
| 78 | Storage Maintenance Composition Boundary | flowchart | Architecture | Shows the canonical BioETL architecture slice for storage maintenance composition boundary across the active layers. |
| 79 | Metrics Publication Control Surface | flowchart | Architecture | Shows the canonical BioETL architecture slice for metrics publication control surface across the active layers. |
| 80 | Anomaly Detection Publication Path | flowchart | Architecture | Shows the canonical BioETL architecture slice for anomaly detection publication path across the active layers. |
| 81 | Schema Governance Boundary | flowchart | Architecture | Shows the canonical BioETL architecture slice for schema governance boundary across the active layers. |
| 82 | Enum Loader To Domain Config Boundary | flowchart | Architecture | Shows the canonical BioETL architecture slice for enum loader to domain config boundary across the active layers. |
| 83 | Pipeline Inputs Resolution Surface | flowchart | Architecture | Shows the canonical BioETL architecture slice for pipeline inputs resolution surface across the active layers. |
| 84 | Manifest To Lineage Correlation Surface | flowchart | Architecture | Shows the canonical BioETL architecture slice for manifest to lineage correlation surface across the active layers. |
| 85 | Provider Registration Bootstrap Sequence | flowchart | Architecture | Shows the canonical BioETL architecture slice for provider registration bootstrap sequence across the active layers. |
| 86 | Composite Builder Support Surface | flowchart | Architecture | Shows the canonical BioETL architecture slice for composite builder support surface across the active layers. |
| 87 | Service Bundle Composition Graph | flowchart | Architecture | Shows the canonical BioETL architecture slice for service bundle composition graph across the active layers. |
| 88 | Run Ledger Publication Boundary | flowchart | Architecture | Shows the canonical BioETL architecture slice for run ledger publication boundary across the active layers. |
| 89 | Workflow Manifest Publication Boundary | flowchart | Architecture | Shows the canonical BioETL architecture slice for workflow manifest publication boundary across the active layers. |
| 90 | Execution Fingerprint Identity Surface | flowchart | Architecture | Shows the canonical BioETL architecture slice for execution fingerprint identity surface across the active layers. |
| 91 | DQ Contract Runtime Assembly | flowchart | Architecture | Shows the canonical BioETL architecture slice for dq contract runtime assembly across the active layers. |
| 92 | Filter Contract Runtime Assembly | flowchart | Architecture | Shows the canonical BioETL architecture slice for filter contract runtime assembly across the active layers. |
| 93 | Pipeline Contract Validation Surface | flowchart | Architecture | Shows the canonical BioETL architecture slice for pipeline contract validation surface across the active layers. |
| 94 | Composite Merge Dependency Assembly | flowchart | Architecture | Shows the canonical BioETL architecture slice for composite merge dependency assembly across the active layers. |
| 95 | Observability Preflight Enforcement | flowchart | Architecture | Shows the canonical BioETL architecture slice for observability preflight enforcement across the active layers. |
| 96 | Provider Config HTTP Surface | flowchart | Architecture | Shows the canonical BioETL architecture slice for provider config http surface across the active layers. |
| 97 | Checkpoint Policy Composition Boundary | flowchart | Architecture | Shows the canonical BioETL architecture slice for checkpoint policy composition boundary across the active layers. |
| 98 | Run Context Factory Boundary | flowchart | Architecture | Shows the canonical BioETL architecture slice for run context factory boundary across the active layers. |
| 99 | Artifact Provenance Hash Chain | flowchart | Architecture | Shows the canonical BioETL architecture slice for artifact provenance hash chain across the active layers. |
| 100 | CLI Diagnostics To Control Plane Boundary | flowchart | Architecture | Shows the canonical BioETL architecture slice for cli diagnostics to control plane boundary across the active layers. |
| 101 | Lineage Metadata Cross-Reference Surface | flowchart | Architecture | Shows the canonical BioETL architecture slice for lineage metadata cross-reference surface across the active layers. |
| 102 | Support Service Bundle Boundary | flowchart | Architecture | Shows the canonical BioETL architecture slice for support service bundle boundary across the active layers. |
| 103 | ChEMBL Activity Bronze To Silver Transformation With Metadata Carry-Over | flowchart | DataFlow | Traces the ChEMBL activity data path from raw ingestion into normalized silver outputs with metadata propagation. |
| 104 | ChEMBL Activity Silver To Gold Contract Validation Path | sequenceDiagram | DataFlow | Shows how ChEMBL activity rows traverse silver validation into gold contract enforcement and output publication. |
| 105 | ChEMBL Molecule Bronze To Silver Transformation With Metadata Carry-Over | flowchart | DataFlow | Traces the ChEMBL molecule data path from raw ingestion into normalized silver outputs with metadata propagation. |
| 106 | ChEMBL Molecule Silver To Gold Contract Validation Path | sequenceDiagram | DataFlow | Shows how ChEMBL molecule rows traverse silver validation into gold contract enforcement and output publication. |
| 107 | ChEMBL Target Bronze To Silver Transformation With Metadata Carry-Over | flowchart | DataFlow | Traces the ChEMBL target data path from raw ingestion into normalized silver outputs with metadata propagation. |
| 108 | ChEMBL Target Silver To Gold Contract Validation Path | sequenceDiagram | DataFlow | Shows how ChEMBL target rows traverse silver validation into gold contract enforcement and output publication. |
| 109 | ChEMBL Assay Bronze To Silver Transformation With Metadata Carry-Over | flowchart | DataFlow | Traces the ChEMBL assay data path from raw ingestion into normalized silver outputs with metadata propagation. |
| 110 | ChEMBL Assay Silver To Gold Contract Validation Path | sequenceDiagram | DataFlow | Shows how ChEMBL assay rows traverse silver validation into gold contract enforcement and output publication. |
| 111 | ChEMBL Publication Bronze To Silver Transformation With Metadata Carry-Over | flowchart | DataFlow | Traces the ChEMBL publication data path from raw ingestion into normalized silver outputs with metadata propagation. |
| 112 | ChEMBL Publication Silver To Gold Contract Validation Path | sequenceDiagram | DataFlow | Shows how ChEMBL publication rows traverse silver validation into gold contract enforcement and output publication. |
| 113 | ChEMBL Compound-Record Bronze To Silver Transformation With Metadata Carry-Over | flowchart | DataFlow | Traces the ChEMBL compound-record data path from raw ingestion into normalized silver outputs with metadata propagation. |
| 114 | ChEMBL Compound-Record Silver To Gold Contract Validation Path | sequenceDiagram | DataFlow | Shows how ChEMBL compound-record rows traverse silver validation into gold contract enforcement and output publication. |
| 115 | ChEMBL Cell-Line Bronze To Silver Transformation With Metadata Carry-Over | flowchart | DataFlow | Traces the ChEMBL cell-line data path from raw ingestion into normalized silver outputs with metadata propagation. |
| 116 | ChEMBL Cell-Line Silver To Gold Contract Validation Path | sequenceDiagram | DataFlow | Shows how ChEMBL cell-line rows traverse silver validation into gold contract enforcement and output publication. |
| 117 | PubChem Compound Bronze To Silver Transformation With Metadata Carry-Over | flowchart | DataFlow | Traces the PubChem compound data path from raw ingestion into normalized silver outputs with metadata propagation. |
| 118 | PubChem Compound Silver To Gold Contract Validation Path | sequenceDiagram | DataFlow | Shows how PubChem compound rows traverse silver validation into gold contract enforcement and output publication. |
| 119 | UniProt Protein Bronze To Silver Transformation With Metadata Carry-Over | flowchart | DataFlow | Traces the UniProt protein data path from raw ingestion into normalized silver outputs with metadata propagation. |
| 120 | UniProt Protein Silver To Gold Contract Validation Path | sequenceDiagram | DataFlow | Shows how UniProt protein rows traverse silver validation into gold contract enforcement and output publication. |
| 121 | UniProt Idmapping Bronze To Silver Transformation With Metadata Carry-Over | flowchart | DataFlow | Traces the UniProt idmapping data path from raw ingestion into normalized silver outputs with metadata propagation. |
| 122 | UniProt Idmapping Silver To Gold Contract Validation Path | sequenceDiagram | DataFlow | Shows how UniProt idmapping rows traverse silver validation into gold contract enforcement and output publication. |
| 123 | CrossRef Publication Bronze To Silver Transformation With Metadata Carry-Over | flowchart | DataFlow | Traces the CrossRef publication data path from raw ingestion into normalized silver outputs with metadata propagation. |
| 124 | CrossRef Publication Silver To Gold Contract Validation Path | sequenceDiagram | DataFlow | Shows how CrossRef publication rows traverse silver validation into gold contract enforcement and output publication. |
| 125 | PubMed Publication Bronze To Silver Transformation With Metadata Carry-Over | flowchart | DataFlow | Traces the PubMed publication data path from raw ingestion into normalized silver outputs with metadata propagation. |
| 126 | PubMed Publication Silver To Gold Contract Validation Path | sequenceDiagram | DataFlow | Shows how PubMed publication rows traverse silver validation into gold contract enforcement and output publication. |
| 127 | OpenAlex Publication Bronze To Silver Transformation With Metadata Carry-Over | flowchart | DataFlow | Traces the OpenAlex publication data path from raw ingestion into normalized silver outputs with metadata propagation. |
| 128 | OpenAlex Publication Silver To Gold Contract Validation Path | sequenceDiagram | DataFlow | Shows how OpenAlex publication rows traverse silver validation into gold contract enforcement and output publication. |
| 129 | SemanticScholar Publication Bronze To Silver Transformation With Metadata Carry-Over | flowchart | DataFlow | Traces the SemanticScholar publication data path from raw ingestion into normalized silver outputs with metadata propagation. |
| 130 | SemanticScholar Publication Silver To Gold Contract Validation Path | sequenceDiagram | DataFlow | Shows how SemanticScholar publication rows traverse silver validation into gold contract enforcement and output publication. |
| 131 | ChEMBL Bronze ingestion | sankey-beta | DataFlow | Summarizes how ChEMBL records and metadata move through bronze ingestion in BioETL. |
| 132 | PubChem Bronze ingestion | sankey-beta | DataFlow | Summarizes how PubChem records and metadata move through bronze ingestion in BioETL. |
| 133 | UniProt Bronze ingestion | sankey-beta | DataFlow | Summarizes how UniProt records and metadata move through bronze ingestion in BioETL. |
| 134 | CrossRef Bronze ingestion | sankey-beta | DataFlow | Summarizes how CrossRef records and metadata move through bronze ingestion in BioETL. |
| 135 | PubMed Bronze ingestion | sankey-beta | DataFlow | Summarizes how PubMed records and metadata move through bronze ingestion in BioETL. |
| 136 | OpenAlex Bronze ingestion | sankey-beta | DataFlow | Summarizes how OpenAlex records and metadata move through bronze ingestion in BioETL. |
| 137 | SemanticScholar Bronze ingestion | sankey-beta | DataFlow | Summarizes how SemanticScholar records and metadata move through bronze ingestion in BioETL. |
| 138 | ChEMBL Silver normalization | sankey-beta | DataFlow | Summarizes how ChEMBL records and metadata move through silver normalization in BioETL. |
| 139 | PubChem Silver normalization | sankey-beta | DataFlow | Summarizes how PubChem records and metadata move through silver normalization in BioETL. |
| 140 | UniProt Silver normalization | sankey-beta | DataFlow | Summarizes how UniProt records and metadata move through silver normalization in BioETL. |
| 141 | CrossRef Silver normalization | sankey-beta | DataFlow | Summarizes how CrossRef records and metadata move through silver normalization in BioETL. |
| 142 | PubMed Silver normalization | sankey-beta | DataFlow | Summarizes how PubMed records and metadata move through silver normalization in BioETL. |
| 143 | OpenAlex Silver normalization | sankey-beta | DataFlow | Summarizes how OpenAlex records and metadata move through silver normalization in BioETL. |
| 144 | SemanticScholar Silver normalization | sankey-beta | DataFlow | Summarizes how SemanticScholar records and metadata move through silver normalization in BioETL. |
| 145 | ChEMBL Gold validation | sankey-beta | DataFlow | Summarizes how ChEMBL records and metadata move through gold validation in BioETL. |
| 146 | PubChem Gold validation | sankey-beta | DataFlow | Summarizes how PubChem records and metadata move through gold validation in BioETL. |
| 147 | UniProt Gold validation | sankey-beta | DataFlow | Summarizes how UniProt records and metadata move through gold validation in BioETL. |
| 148 | CrossRef Gold validation | sankey-beta | DataFlow | Summarizes how CrossRef records and metadata move through gold validation in BioETL. |
| 149 | PubMed Gold validation | sankey-beta | DataFlow | Summarizes how PubMed records and metadata move through gold validation in BioETL. |
| 150 | OpenAlex Gold validation | sankey-beta | DataFlow | Summarizes how OpenAlex records and metadata move through gold validation in BioETL. |
| 151 | SemanticScholar Gold validation | sankey-beta | DataFlow | Summarizes how SemanticScholar records and metadata move through gold validation in BioETL. |
| 152 | ChEMBL Quarantine routing | sankey-beta | DataFlow | Summarizes how ChEMBL records and metadata move through quarantine routing in BioETL. |
| 153 | PubChem Quarantine routing | sankey-beta | DataFlow | Summarizes how PubChem records and metadata move through quarantine routing in BioETL. |
| 154 | UniProt Quarantine routing | sankey-beta | DataFlow | Summarizes how UniProt records and metadata move through quarantine routing in BioETL. |
| 155 | CrossRef Quarantine routing | sankey-beta | DataFlow | Summarizes how CrossRef records and metadata move through quarantine routing in BioETL. |
| 156 | PubMed Quarantine routing | sankey-beta | DataFlow | Summarizes how PubMed records and metadata move through quarantine routing in BioETL. |
| 157 | OpenAlex Quarantine routing | sankey-beta | DataFlow | Summarizes how OpenAlex records and metadata move through quarantine routing in BioETL. |
| 158 | SemanticScholar Quarantine routing | sankey-beta | DataFlow | Summarizes how SemanticScholar records and metadata move through quarantine routing in BioETL. |
| 159 | Template Method Across Transformers | classDiagram | Pattern | Illustrates how BioETL applies the template method across transformers in concrete modules rather than as a generic textbook pattern. |
| 160 | Template Method Across Transformers Execution Path | flowchart | Pattern | Shows the runtime path where the template method across transformers is exercised. |
| 161 | Factory Method Across Pipeline Builders | classDiagram | Pattern | Illustrates how BioETL applies the factory method across pipeline builders in concrete modules rather than as a generic textbook pattern. |
| 162 | Factory Method Across Pipeline Builders Execution Path | flowchart | Pattern | Shows the runtime path where the factory method across pipeline builders is exercised. |
| 163 | Builder Pattern In Runtime Assembly | classDiagram | Pattern | Illustrates how BioETL applies the builder pattern in runtime assembly in concrete modules rather than as a generic textbook pattern. |
| 164 | Builder Pattern In Runtime Assembly Execution Path | flowchart | Pattern | Shows the runtime path where the builder pattern in runtime assembly is exercised. |
| 165 | Strategy Pattern In Join Key Resolution | classDiagram | Pattern | Illustrates how BioETL applies the strategy pattern in join key resolution in concrete modules rather than as a generic textbook pattern. |
| 166 | Strategy Pattern In Join Key Resolution Execution Path | flowchart | Pattern | Shows the runtime path where the strategy pattern in join key resolution is exercised. |
| 167 | Observer Pattern In Lifecycle Observability | classDiagram | Pattern | Illustrates how BioETL applies the observer pattern in lifecycle observability in concrete modules rather than as a generic textbook pattern. |
| 168 | Observer Pattern In Lifecycle Observability Execution Path | flowchart | Pattern | Shows the runtime path where the observer pattern in lifecycle observability is exercised. |
| 169 | Decorator Stack Around HTTP Adapters | classDiagram | Pattern | Illustrates how BioETL applies the decorator stack around http adapters in concrete modules rather than as a generic textbook pattern. |
| 170 | Decorator Stack Around HTTP Adapters Execution Path | flowchart | Pattern | Shows the runtime path where the decorator stack around http adapters is exercised. |
| 171 | Facade Pattern At Bootstrap Package Root | classDiagram | Pattern | Illustrates how BioETL applies the facade pattern at bootstrap package root in concrete modules rather than as a generic textbook pattern. |
| 172 | Facade Pattern At Bootstrap Package Root Execution Path | flowchart | Pattern | Shows the runtime path where the facade pattern at bootstrap package root is exercised. |
| 173 | Protocol Adapter Pattern Around Storage Writers | classDiagram | Pattern | Illustrates how BioETL applies the protocol adapter pattern around storage writers in concrete modules rather than as a generic textbook pattern. |
| 174 | Protocol Adapter Pattern Around Storage Writers Execution Path | flowchart | Pattern | Shows the runtime path where the protocol adapter pattern around storage writers is exercised. |
| 175 | State Pattern In Aggregates | classDiagram | Pattern | Illustrates how BioETL applies the state pattern in aggregates in concrete modules rather than as a generic textbook pattern. |
| 176 | State Pattern In Aggregates Execution Path | flowchart | Pattern | Shows the runtime path where the state pattern in aggregates is exercised. |
| 177 | Fallback Chain For Publication Providers | classDiagram | Pattern | Illustrates how BioETL applies the fallback chain for publication providers in concrete modules rather than as a generic textbook pattern. |
| 178 | Fallback Chain For Publication Providers Execution Path | flowchart | Pattern | Shows the runtime path where the fallback chain for publication providers is exercised. |
| 179 | Anti-Corruption Layer For Provider Response Mapping | classDiagram | Pattern | Illustrates how BioETL applies the anti-corruption layer for provider response mapping in concrete modules rather than as a generic textbook pattern. |
| 180 | Anti-Corruption Layer For Provider Response Mapping Execution Path | flowchart | Pattern | Shows the runtime path where the anti-corruption layer for provider response mapping is exercised. |
| 181 | Policy Object Pattern In Config Resolution | classDiagram | Pattern | Illustrates how BioETL applies the policy object pattern in config resolution in concrete modules rather than as a generic textbook pattern. |
| 182 | Policy Object Pattern In Config Resolution Execution Path | flowchart | Pattern | Shows the runtime path where the policy object pattern in config resolution is exercised. |
| 183 | Retry Policy Strategy For HTTP Client | classDiagram | Pattern | Illustrates how BioETL applies the retry policy strategy for http client in concrete modules rather than as a generic textbook pattern. |
| 184 | Retry Policy Strategy For HTTP Client Execution Path | flowchart | Pattern | Shows the runtime path where the retry policy strategy for http client is exercised. |
| 185 | NoOp Observability Substitution Pattern | classDiagram | Pattern | Illustrates how BioETL applies the noop observability substitution pattern in concrete modules rather than as a generic textbook pattern. |
| 186 | NoOp Observability Substitution Pattern Execution Path | flowchart | Pattern | Shows the runtime path where the noop observability substitution pattern is exercised. |
| 187 | Serializer Boundary Pattern For Control Plane | classDiagram | Pattern | Illustrates how BioETL applies the serializer boundary pattern for control plane in concrete modules rather than as a generic textbook pattern. |
| 188 | Serializer Boundary Pattern For Control Plane Execution Path | flowchart | Pattern | Shows the runtime path where the serializer boundary pattern for control plane is exercised. |
| 189 | Mixin Decomposition Pattern In Composite Runner | classDiagram | Pattern | Illustrates how BioETL applies the mixin decomposition pattern in composite runner in concrete modules rather than as a generic textbook pattern. |
| 190 | Mixin Decomposition Pattern In Composite Runner Execution Path | flowchart | Pattern | Shows the runtime path where the mixin decomposition pattern in composite runner is exercised. |
| 191 | Read Model Projection Pattern In PipelineRun | classDiagram | Pattern | Illustrates how BioETL applies the read model projection pattern in pipelinerun in concrete modules rather than as a generic textbook pattern. |
| 192 | Read Model Projection Pattern In PipelineRun Execution Path | flowchart | Pattern | Shows the runtime path where the read model projection pattern in pipelinerun is exercised. |
| 193 | Compatibility Alias Pattern In Bootstrap Facades | classDiagram | Pattern | Illustrates how BioETL applies the compatibility alias pattern in bootstrap facades in concrete modules rather than as a generic textbook pattern. |
| 194 | Compatibility Alias Pattern In Bootstrap Facades Execution Path | flowchart | Pattern | Shows the runtime path where the compatibility alias pattern in bootstrap facades is exercised. |
| 195 | Threshold Policy Pattern In DQ Rules | classDiagram | Pattern | Illustrates how BioETL applies the threshold policy pattern in dq rules in concrete modules rather than as a generic textbook pattern. |
| 196 | Threshold Policy Pattern In DQ Rules Execution Path | flowchart | Pattern | Shows the runtime path where the threshold policy pattern in dq rules is exercised. |
| 197 | Join Planner Delegation Pattern | classDiagram | Pattern | Illustrates how BioETL applies the join planner delegation pattern in concrete modules rather than as a generic textbook pattern. |
| 198 | Join Planner Delegation Pattern Execution Path | flowchart | Pattern | Shows the runtime path where the join planner delegation pattern is exercised. |
| 199 | Cursor Pagination Template Pattern | classDiagram | Pattern | Illustrates how BioETL applies the cursor pagination template pattern in concrete modules rather than as a generic textbook pattern. |
| 200 | Cursor Pagination Template Pattern Execution Path | flowchart | Pattern | Shows the runtime path where the cursor pagination template pattern is exercised. |
| 201 | Batch Request Aggregator Pattern | classDiagram | Pattern | Illustrates how BioETL applies the batch request aggregator pattern in concrete modules rather than as a generic textbook pattern. |
| 202 | Batch Request Aggregator Pattern Execution Path | flowchart | Pattern | Shows the runtime path where the batch request aggregator pattern is exercised. |
| 203 | Checksum And Content Identity Pattern | classDiagram | Pattern | Illustrates how BioETL applies the checksum and content identity pattern in concrete modules rather than as a generic textbook pattern. |
| 204 | Checksum And Content Identity Pattern Execution Path | flowchart | Pattern | Shows the runtime path where the checksum and content identity pattern is exercised. |
| 205 | Control Plane Artifact Builder Pattern | classDiagram | Pattern | Illustrates how BioETL applies the control plane artifact builder pattern in concrete modules rather than as a generic textbook pattern. |
| 206 | Port Call-Site Map For Runtime Services | classDiagram | Component | Maps concrete application or composition call-sites that depend on the runtime port cluster. |
| 207 | Port Call-Site Map For Storage Services | classDiagram | Component | Maps concrete application or composition call-sites that depend on the storage port cluster. |
| 208 | Port Call-Site Map For Quality Services | classDiagram | Component | Maps concrete application or composition call-sites that depend on the quality port cluster. |
| 209 | Port Call-Site Map For Observability Services | classDiagram | Component | Maps concrete application or composition call-sites that depend on the observability port cluster. |
| 210 | Port Call-Site Map For Source Services | classDiagram | Component | Maps concrete application or composition call-sites that depend on the source port cluster. |
| 211 | BatchTransformer Streaming Surface | classDiagram | Component | Details the internal component structure and key collaborators for batchtransformer streaming surface. |
| 212 | BatchTransformer Streaming Surface Runtime Choreography | flowchart | Component | Shows the execution choreography through batchtransformer streaming surface during a normal pipeline run. |
| 213 | BatchWriter IO And Tracing Mixins | classDiagram | Component | Details the internal component structure and key collaborators for batchwriter io and tracing mixins. |
| 214 | BatchWriter IO And Tracing Mixins Runtime Choreography | flowchart | Component | Shows the execution choreography through batchwriter io and tracing mixins during a normal pipeline run. |
| 215 | RecordProcessor Normalization Pipeline | classDiagram | Component | Details the internal component structure and key collaborators for recordprocessor normalization pipeline. |
| 216 | RecordProcessor Normalization Pipeline Runtime Choreography | flowchart | Component | Shows the execution choreography through recordprocessor normalization pipeline during a normal pipeline run. |
| 217 | QuarantineManager Decision Surface | classDiagram | Component | Details the internal component structure and key collaborators for quarantinemanager decision surface. |
| 218 | QuarantineManager Decision Surface Runtime Choreography | flowchart | Component | Shows the execution choreography through quarantinemanager decision surface during a normal pipeline run. |
| 219 | PreflightService Dependency Boundary | classDiagram | Component | Details the internal component structure and key collaborators for preflightservice dependency boundary. |
| 220 | PreflightService Dependency Boundary Runtime Choreography | flowchart | Component | Shows the execution choreography through preflightservice dependency boundary during a normal pipeline run. |
| 221 | PostrunService Maintenance Surface | classDiagram | Component | Details the internal component structure and key collaborators for postrunservice maintenance surface. |
| 222 | PostrunService Maintenance Surface Runtime Choreography | flowchart | Component | Shows the execution choreography through postrunservice maintenance surface during a normal pipeline run. |
| 223 | BatchMetrics Publication Surface | classDiagram | Component | Details the internal component structure and key collaborators for batchmetrics publication surface. |
| 224 | BatchMetrics Publication Surface Runtime Choreography | flowchart | Component | Shows the execution choreography through batchmetrics publication surface during a normal pipeline run. |
| 225 | CheckpointManager Persistence Surface | classDiagram | Component | Details the internal component structure and key collaborators for checkpointmanager persistence surface. |
| 226 | CheckpointManager Persistence Surface Runtime Choreography | flowchart | Component | Shows the execution choreography through checkpointmanager persistence surface during a normal pipeline run. |
| 227 | LockManager Ownership Surface | classDiagram | Component | Details the internal component structure and key collaborators for lockmanager ownership surface. |
| 228 | LockManager Ownership Surface Runtime Choreography | flowchart | Component | Shows the execution choreography through lockmanager ownership surface during a normal pipeline run. |
| 229 | FilteredDataSource Adapter Surface | classDiagram | Component | Details the internal component structure and key collaborators for filtereddatasource adapter surface. |
| 230 | FilteredDataSource Adapter Surface Runtime Choreography | flowchart | Component | Shows the execution choreography through filtereddatasource adapter surface during a normal pipeline run. |
| 231 | Pipeline Processing Components Builder | classDiagram | Component | Details the internal component structure and key collaborators for pipeline processing components builder. |
| 232 | Pipeline Processing Components Builder Runtime Choreography | flowchart | Component | Shows the execution choreography through pipeline processing components builder during a normal pipeline run. |
| 233 | Composite Merger Collaborator Surface | classDiagram | Component | Details the internal component structure and key collaborators for composite merger collaborator surface. |
| 234 | Composite Merger Collaborator Surface Runtime Choreography | flowchart | Component | Shows the execution choreography through composite merger collaborator surface during a normal pipeline run. |
| 235 | Composite Column Service And Priority Orderers | classDiagram | Component | Details the internal component structure and key collaborators for composite column service and priority orderers. |
| 236 | Composite Column Service And Priority Orderers Runtime Choreography | flowchart | Component | Shows the execution choreography through composite column service and priority orderers during a normal pipeline run. |
| 237 | Composite Conflict Resolver Surface | classDiagram | Component | Details the internal component structure and key collaborators for composite conflict resolver surface. |
| 238 | Composite Conflict Resolver Surface Runtime Choreography | flowchart | Component | Shows the execution choreography through composite conflict resolver surface during a normal pipeline run. |
| 239 | Composite Join Planner Support Package | classDiagram | Component | Details the internal component structure and key collaborators for composite join planner support package. |
| 240 | Composite Join Planner Support Package Runtime Choreography | flowchart | Component | Shows the execution choreography through composite join planner support package during a normal pipeline run. |
| 241 | Provider Registry Protocol And Store | classDiagram | Component | Details the internal component structure and key collaborators for provider registry protocol and store. |
| 242 | Provider Registry Protocol And Store Runtime Choreography | flowchart | Component | Shows the execution choreography through provider registry protocol and store during a normal pipeline run. |
| 243 | Storage Factory Layer Writers Bundle | classDiagram | Component | Details the internal component structure and key collaborators for storage factory layer writers bundle. |
| 244 | Storage Factory Layer Writers Bundle Runtime Choreography | flowchart | Component | Shows the execution choreography through storage factory layer writers bundle during a normal pipeline run. |
| 245 | DataSource Factory CrossRef Branch | classDiagram | Component | Details the internal component structure and key collaborators for datasource factory crossref branch. |
| 246 | DataSource Factory CrossRef Branch Runtime Choreography | flowchart | Component | Shows the execution choreography through datasource factory crossref branch during a normal pipeline run. |
| 247 | DQ Context Resolver Factory | classDiagram | Component | Details the internal component structure and key collaborators for dq context resolver factory. |
| 248 | CLI Run Command To Bootstrap Runner | sequenceDiagram | Interaction | Shows the concrete participant interaction sequence for cli run command to bootstrap runner. |
| 249 | CLI Run Command To Bootstrap Runner Timing Landmarks | timeline | Interaction | Summarizes the timing landmarks and ordering constraints for cli run command to bootstrap runner. |
| 250 | CLI Run Composite Command To Composite Runner | sequenceDiagram | Interaction | Shows the concrete participant interaction sequence for cli run composite command to composite runner. |
| 251 | CLI Run Composite Command To Composite Runner Timing Landmarks | timeline | Interaction | Summarizes the timing landmarks and ordering constraints for cli run composite command to composite runner. |
| 252 | CLI Health Command To Provider Probes | sequenceDiagram | Interaction | Shows the concrete participant interaction sequence for cli health command to provider probes. |
| 253 | CLI Health Command To Provider Probes Timing Landmarks | timeline | Interaction | Summarizes the timing landmarks and ordering constraints for cli health command to provider probes. |
| 254 | BatchExecutor To BatchTransformer To BatchWriter | sequenceDiagram | Interaction | Shows the concrete participant interaction sequence for batchexecutor to batchtransformer to batchwriter. |
| 255 | BatchExecutor To BatchTransformer To BatchWriter Timing Landmarks | timeline | Interaction | Summarizes the timing landmarks and ordering constraints for batchexecutor to batchtransformer to batchwriter. |
| 256 | PipelineRunner To PreflightService And PostrunService | sequenceDiagram | Interaction | Shows the concrete participant interaction sequence for pipelinerunner to preflightservice and postrunservice. |
| 257 | PipelineRunner To PreflightService And PostrunService Timing Landmarks | timeline | Interaction | Summarizes the timing landmarks and ordering constraints for pipelinerunner to preflightservice and postrunservice. |
| 258 | Composite Runner To Coordinator And Merger | sequenceDiagram | Interaction | Shows the concrete participant interaction sequence for composite runner to coordinator and merger. |
| 259 | Composite Runner To Coordinator And Merger Timing Landmarks | timeline | Interaction | Summarizes the timing landmarks and ordering constraints for composite runner to coordinator and merger. |
| 260 | Retention Manager To Delta Reader | sequenceDiagram | Interaction | Shows the concrete participant interaction sequence for retention manager to delta reader. |
| 261 | Retention Manager To Delta Reader Timing Landmarks | timeline | Interaction | Summarizes the timing landmarks and ordering constraints for retention manager to delta reader. |
| 262 | Health Monitor To Provider Adapter | sequenceDiagram | Interaction | Shows the concrete participant interaction sequence for health monitor to provider adapter. |
| 263 | Health Monitor To Provider Adapter Timing Landmarks | timeline | Interaction | Summarizes the timing landmarks and ordering constraints for health monitor to provider adapter. |
| 264 | DQ Monitor To Metrics And Logger | sequenceDiagram | Interaction | Shows the concrete participant interaction sequence for dq monitor to metrics and logger. |
| 265 | DQ Monitor To Metrics And Logger Timing Landmarks | timeline | Interaction | Summarizes the timing landmarks and ordering constraints for dq monitor to metrics and logger. |
| 266 | Run Manifest Command To Inspection Output | sequenceDiagram | Interaction | Shows the concrete participant interaction sequence for run manifest command to inspection output. |
| 267 | Run Manifest Command To Inspection Output Timing Landmarks | timeline | Interaction | Summarizes the timing landmarks and ordering constraints for run manifest command to inspection output. |
| 268 | Workflow Command To Workflow Control Plane | sequenceDiagram | Interaction | Shows the concrete participant interaction sequence for workflow command to workflow control plane. |
| 269 | Workflow Command To Workflow Control Plane Timing Landmarks | timeline | Interaction | Summarizes the timing landmarks and ordering constraints for workflow command to workflow control plane. |
| 270 | Bootstrap Logger To Metrics Server Startup | sequenceDiagram | Interaction | Shows the concrete participant interaction sequence for bootstrap logger to metrics server startup. |
| 271 | Bootstrap Logger To Metrics Server Startup Timing Landmarks | timeline | Interaction | Summarizes the timing landmarks and ordering constraints for bootstrap logger to metrics server startup. |
| 272 | Provider Adapter To UnifiedHTTPClient | sequenceDiagram | Interaction | Shows the concrete participant interaction sequence for provider adapter to unifiedhttpclient. |
| 273 | Provider Adapter To UnifiedHTTPClient Timing Landmarks | timeline | Interaction | Summarizes the timing landmarks and ordering constraints for provider adapter to unifiedhttpclient. |
| 274 | PubMed Adapter To XML Processor | sequenceDiagram | Interaction | Shows the concrete participant interaction sequence for pubmed adapter to xml processor. |
| 275 | PubMed Adapter To XML Processor Timing Landmarks | timeline | Interaction | Summarizes the timing landmarks and ordering constraints for pubmed adapter to xml processor. |
| 276 | CrossRef Adapter To Fallback Fetch Service | sequenceDiagram | Interaction | Shows the concrete participant interaction sequence for crossref adapter to fallback fetch service. |
| 277 | CrossRef Adapter To Fallback Fetch Service Timing Landmarks | timeline | Interaction | Summarizes the timing landmarks and ordering constraints for crossref adapter to fallback fetch service. |
| 278 | OpenAlex Adapter To Cursor Flow | sequenceDiagram | Interaction | Shows the concrete participant interaction sequence for openalex adapter to cursor flow. |
| 279 | OpenAlex Adapter To Cursor Flow Timing Landmarks | timeline | Interaction | Summarizes the timing landmarks and ordering constraints for openalex adapter to cursor flow. |
| 280 | UniProt Adapter To IdMapping Client | sequenceDiagram | Interaction | Shows the concrete participant interaction sequence for uniprot adapter to idmapping client. |
| 281 | UniProt Adapter To IdMapping Client Timing Landmarks | timeline | Interaction | Summarizes the timing landmarks and ordering constraints for uniprot adapter to idmapping client. |
| 282 | SemanticScholar Adapter To Batch Request Mixin | sequenceDiagram | Interaction | Shows the concrete participant interaction sequence for semanticscholar adapter to batch request mixin. |
| 283 | SemanticScholar Adapter To Batch Request Mixin Timing Landmarks | timeline | Interaction | Summarizes the timing landmarks and ordering constraints for semanticscholar adapter to batch request mixin. |
| 284 | PubChem Adapter To Fetch Strategies | sequenceDiagram | Interaction | Shows the concrete participant interaction sequence for pubchem adapter to fetch strategies. |
| 285 | PubChem Adapter To Fetch Strategies Timing Landmarks | timeline | Interaction | Summarizes the timing landmarks and ordering constraints for pubchem adapter to fetch strategies. |
| 286 | ChEMBL Adapter To Entity Mapper | sequenceDiagram | Interaction | Shows the concrete participant interaction sequence for chembl adapter to entity mapper. |
| 287 | ChEMBL Adapter To Entity Mapper Timing Landmarks | timeline | Interaction | Summarizes the timing landmarks and ordering constraints for chembl adapter to entity mapper. |
| 288 | Contract Registry Service To Gold Contract Loader | sequenceDiagram | Interaction | Shows the concrete participant interaction sequence for contract registry service to gold contract loader. |
| 289 | Contract Registry Service To Gold Contract Loader Timing Landmarks | timeline | Interaction | Summarizes the timing landmarks and ordering constraints for contract registry service to gold contract loader. |
| 290 | Effective Config Builder To Environment Snapshot | sequenceDiagram | Interaction | Shows the concrete participant interaction sequence for effective config builder to environment snapshot. |
| 291 | Effective Config Builder To Environment Snapshot Timing Landmarks | timeline | Interaction | Summarizes the timing landmarks and ordering constraints for effective config builder to environment snapshot. |
| 292 | Historical Replay Service To Manifest Reader | sequenceDiagram | Interaction | Shows the concrete participant interaction sequence for historical replay service to manifest reader. |
| 293 | PipelineRun Aggregate Lifecycle | stateDiagram | Lifecycle | Models the lifecycle states and transitions for pipelinerun aggregate in BioETL. |
| 294 | PipelineRun Aggregate Timeline | timeline | Lifecycle | Shows the temporal ordering and milestone edges in the pipelinerun aggregate lifecycle. |
| 295 | Batch Aggregate Lifecycle | stateDiagram | Lifecycle | Models the lifecycle states and transitions for batch aggregate in BioETL. |
| 296 | Batch Aggregate Timeline | timeline | Lifecycle | Shows the temporal ordering and milestone edges in the batch aggregate lifecycle. |
| 297 | QuarantineEntry Aggregate Lifecycle | stateDiagram | Lifecycle | Models the lifecycle states and transitions for quarantineentry aggregate in BioETL. |
| 298 | QuarantineEntry Aggregate Timeline | timeline | Lifecycle | Shows the temporal ordering and milestone edges in the quarantineentry aggregate lifecycle. |
| 299 | Circuit Breaker Lifecycle | stateDiagram | Lifecycle | Models the lifecycle states and transitions for circuit breaker in BioETL. |
| 300 | Circuit Breaker Timeline | timeline | Lifecycle | Shows the temporal ordering and milestone edges in the circuit breaker lifecycle. |
| 301 | Provider Health Monitor Lifecycle | stateDiagram | Lifecycle | Models the lifecycle states and transitions for provider health monitor in BioETL. |
| 302 | Provider Health Monitor Timeline | timeline | Lifecycle | Shows the temporal ordering and milestone edges in the provider health monitor lifecycle. |
| 303 | CompositePipelineRunner Lifecycle | stateDiagram | Lifecycle | Models the lifecycle states and transitions for compositepipelinerunner in BioETL. |
| 304 | CompositePipelineRunner Timeline | timeline | Lifecycle | Shows the temporal ordering and milestone edges in the compositepipelinerunner lifecycle. |
| 305 | WorkflowExecutionState Lifecycle | stateDiagram | Lifecycle | Models the lifecycle states and transitions for workflowexecutionstate in BioETL. |
| 306 | WorkflowExecutionState Timeline | timeline | Lifecycle | Shows the temporal ordering and milestone edges in the workflowexecutionstate lifecycle. |
| 307 | Run Ledger Entry Publication Lifecycle | stateDiagram | Lifecycle | Models the lifecycle states and transitions for run ledger entry publication in BioETL. |
| 308 | Run Ledger Entry Publication Timeline | timeline | Lifecycle | Shows the temporal ordering and milestone edges in the run ledger entry publication lifecycle. |
| 309 | Historical Replay Inventory Closure Lifecycle | stateDiagram | Lifecycle | Models the lifecycle states and transitions for historical replay inventory closure in BioETL. |
| 310 | Historical Replay Inventory Closure Timeline | timeline | Lifecycle | Shows the temporal ordering and milestone edges in the historical replay inventory closure lifecycle. |
| 311 | DQ Contract Enforcement Lifecycle | stateDiagram | Lifecycle | Models the lifecycle states and transitions for dq contract enforcement in BioETL. |
| 312 | DQ Contract Enforcement Timeline | timeline | Lifecycle | Shows the temporal ordering and milestone edges in the dq contract enforcement lifecycle. |
| 313 | Retention Dedup Timeout Budget Lifecycle | stateDiagram | Lifecycle | Models the lifecycle states and transitions for retention dedup timeout budget in BioETL. |
| 314 | Retention Dedup Timeout Budget Timeline | timeline | Lifecycle | Shows the temporal ordering and milestone edges in the retention dedup timeout budget lifecycle. |
| 315 | Cached Bronze Snapshot Refresh Lifecycle | stateDiagram | Lifecycle | Models the lifecycle states and transitions for cached bronze snapshot refresh in BioETL. |
| 316 | Cached Bronze Snapshot Refresh Timeline | timeline | Lifecycle | Shows the temporal ordering and milestone edges in the cached bronze snapshot refresh lifecycle. |
| 317 | Metrics Server Startup Lifecycle | stateDiagram | Lifecycle | Models the lifecycle states and transitions for metrics server startup in BioETL. |
| 318 | Metrics Server Startup Timeline | timeline | Lifecycle | Shows the temporal ordering and milestone edges in the metrics server startup lifecycle. |
| 319 | OpenAlex Cursor Session Lifecycle | stateDiagram | Lifecycle | Models the lifecycle states and transitions for openalex cursor session in BioETL. |
| 320 | OpenAlex Cursor Session Timeline | timeline | Lifecycle | Shows the temporal ordering and milestone edges in the openalex cursor session lifecycle. |
| 321 | UniProt IdMapping Job Lifecycle | stateDiagram | Lifecycle | Models the lifecycle states and transitions for uniprot idmapping job in BioETL. |
| 322 | UniProt IdMapping Job Timeline | timeline | Lifecycle | Shows the temporal ordering and milestone edges in the uniprot idmapping job lifecycle. |
| 323 | PubMed Search Session Lifecycle | stateDiagram | Lifecycle | Models the lifecycle states and transitions for pubmed search session in BioETL. |
| 324 | PubMed Search Session Timeline | timeline | Lifecycle | Shows the temporal ordering and milestone edges in the pubmed search session lifecycle. |
| 325 | CrossRef DOI Batch Window Lifecycle | stateDiagram | Lifecycle | Models the lifecycle states and transitions for crossref doi batch window in BioETL. |
| 326 | CrossRef DOI Batch Window Timeline | timeline | Lifecycle | Shows the temporal ordering and milestone edges in the crossref doi batch window lifecycle. |
| 327 | ChEMBL Related Entity Expansion Lifecycle | stateDiagram | Lifecycle | Models the lifecycle states and transitions for chembl related entity expansion in BioETL. |
| 328 | ChEMBL Related Entity Expansion Timeline | timeline | Lifecycle | Shows the temporal ordering and milestone edges in the chembl related entity expansion lifecycle. |
| 329 | ChEMBL Activity Request Build Fetch Parse Map Loop | sequenceDiagram | Provider | Documents the provider-specific request, fetch, parse, and mapping cycle for ChEMBL activity. |
| 330 | ChEMBL Activity Health Fallback And Retry Decision Tree | flowchart | Provider | Explains provider-specific health, retry, and fallback decisions for ChEMBL activity fetches. |
| 331 | ChEMBL Molecule Request Build Fetch Parse Map Loop | sequenceDiagram | Provider | Documents the provider-specific request, fetch, parse, and mapping cycle for ChEMBL molecule. |
| 332 | ChEMBL Molecule Health Fallback And Retry Decision Tree | flowchart | Provider | Explains provider-specific health, retry, and fallback decisions for ChEMBL molecule fetches. |
| 333 | ChEMBL Target Request Build Fetch Parse Map Loop | sequenceDiagram | Provider | Documents the provider-specific request, fetch, parse, and mapping cycle for ChEMBL target. |
| 334 | ChEMBL Target Health Fallback And Retry Decision Tree | flowchart | Provider | Explains provider-specific health, retry, and fallback decisions for ChEMBL target fetches. |
| 335 | ChEMBL Assay Request Build Fetch Parse Map Loop | sequenceDiagram | Provider | Documents the provider-specific request, fetch, parse, and mapping cycle for ChEMBL assay. |
| 336 | ChEMBL Assay Health Fallback And Retry Decision Tree | flowchart | Provider | Explains provider-specific health, retry, and fallback decisions for ChEMBL assay fetches. |
| 337 | ChEMBL Publication Request Build Fetch Parse Map Loop | sequenceDiagram | Provider | Documents the provider-specific request, fetch, parse, and mapping cycle for ChEMBL publication. |
| 338 | ChEMBL Publication Health Fallback And Retry Decision Tree | flowchart | Provider | Explains provider-specific health, retry, and fallback decisions for ChEMBL publication fetches. |
| 339 | ChEMBL Compound-Record Request Build Fetch Parse Map Loop | sequenceDiagram | Provider | Documents the provider-specific request, fetch, parse, and mapping cycle for ChEMBL compound-record. |
| 340 | ChEMBL Compound-Record Health Fallback And Retry Decision Tree | flowchart | Provider | Explains provider-specific health, retry, and fallback decisions for ChEMBL compound-record fetches. |
| 341 | ChEMBL Cell-Line Request Build Fetch Parse Map Loop | sequenceDiagram | Provider | Documents the provider-specific request, fetch, parse, and mapping cycle for ChEMBL cell-line. |
| 342 | ChEMBL Cell-Line Health Fallback And Retry Decision Tree | flowchart | Provider | Explains provider-specific health, retry, and fallback decisions for ChEMBL cell-line fetches. |
| 343 | PubChem Compound Request Build Fetch Parse Map Loop | sequenceDiagram | Provider | Documents the provider-specific request, fetch, parse, and mapping cycle for PubChem compound. |
| 344 | PubChem Compound Health Fallback And Retry Decision Tree | flowchart | Provider | Explains provider-specific health, retry, and fallback decisions for PubChem compound fetches. |
| 345 | UniProt Protein Request Build Fetch Parse Map Loop | sequenceDiagram | Provider | Documents the provider-specific request, fetch, parse, and mapping cycle for UniProt protein. |
| 346 | UniProt Protein Health Fallback And Retry Decision Tree | flowchart | Provider | Explains provider-specific health, retry, and fallback decisions for UniProt protein fetches. |
| 347 | UniProt Idmapping Request Build Fetch Parse Map Loop | sequenceDiagram | Provider | Documents the provider-specific request, fetch, parse, and mapping cycle for UniProt idmapping. |
| 348 | UniProt Idmapping Health Fallback And Retry Decision Tree | flowchart | Provider | Explains provider-specific health, retry, and fallback decisions for UniProt idmapping fetches. |
| 349 | CrossRef Publication Request Build Fetch Parse Map Loop | sequenceDiagram | Provider | Documents the provider-specific request, fetch, parse, and mapping cycle for CrossRef publication. |
| 350 | CrossRef Publication Health Fallback And Retry Decision Tree | flowchart | Provider | Explains provider-specific health, retry, and fallback decisions for CrossRef publication fetches. |
| 351 | PubMed Publication Request Build Fetch Parse Map Loop | sequenceDiagram | Provider | Documents the provider-specific request, fetch, parse, and mapping cycle for PubMed publication. |
| 352 | PubMed Publication Health Fallback And Retry Decision Tree | flowchart | Provider | Explains provider-specific health, retry, and fallback decisions for PubMed publication fetches. |
| 353 | OpenAlex Publication Request Build Fetch Parse Map Loop | sequenceDiagram | Provider | Documents the provider-specific request, fetch, parse, and mapping cycle for OpenAlex publication. |
| 354 | OpenAlex Publication Health Fallback And Retry Decision Tree | flowchart | Provider | Explains provider-specific health, retry, and fallback decisions for OpenAlex publication fetches. |
| 355 | SemanticScholar Publication Request Build Fetch Parse Map Loop | sequenceDiagram | Provider | Documents the provider-specific request, fetch, parse, and mapping cycle for SemanticScholar publication. |
| 356 | SemanticScholar Publication Health Fallback And Retry Decision Tree | flowchart | Provider | Explains provider-specific health, retry, and fallback decisions for SemanticScholar publication fetches. |
| 357 | ChEMBL Request Headers And Auth Surface | classDiagram | Provider | Details the provider-specific runtime component surface for ChEMBL request headers and auth surface. |
| 358 | ChEMBL Pagination / Cursor Progression | classDiagram | Provider | Details the provider-specific runtime component surface for ChEMBL pagination / cursor progression. |
| 359 | ChEMBL Response Model Normalization | classDiagram | Provider | Details the provider-specific runtime component surface for ChEMBL response model normalization. |
| 360 | ChEMBL Source Metadata Capability Publication | classDiagram | Provider | Details the provider-specific runtime component surface for ChEMBL source metadata capability publication. |
| 361 | ChEMBL Health Probe And Adaptive Params | classDiagram | Provider | Details the provider-specific runtime component surface for ChEMBL health probe and adaptive params. |
| 362 | ChEMBL Fallback Policy Escalation | classDiagram | Provider | Details the provider-specific runtime component surface for ChEMBL fallback policy escalation. |
| 363 | ChEMBL Batch Request Optimization | classDiagram | Provider | Details the provider-specific runtime component surface for ChEMBL batch request optimization. |
| 364 | ChEMBL Entity Mapper And Model Bridge | classDiagram | Provider | Details the provider-specific runtime component surface for ChEMBL entity mapper and model bridge. |
| 365 | PubChem Request Headers And Auth Surface | classDiagram | Provider | Details the provider-specific runtime component surface for PubChem request headers and auth surface. |
| 366 | PubChem Pagination / Cursor Progression | classDiagram | Provider | Details the provider-specific runtime component surface for PubChem pagination / cursor progression. |
| 367 | PubChem Response Model Normalization | classDiagram | Provider | Details the provider-specific runtime component surface for PubChem response model normalization. |
| 368 | PubChem Source Metadata Capability Publication | classDiagram | Provider | Details the provider-specific runtime component surface for PubChem source metadata capability publication. |
| 369 | PubChem Health Probe And Adaptive Params | classDiagram | Provider | Details the provider-specific runtime component surface for PubChem health probe and adaptive params. |
| 370 | PubChem Fallback Policy Escalation | classDiagram | Provider | Details the provider-specific runtime component surface for PubChem fallback policy escalation. |
| 371 | PubChem Batch Request Optimization | classDiagram | Provider | Details the provider-specific runtime component surface for PubChem batch request optimization. |
| 372 | Pipeline YAML Resolution | flowchart | Configuration | Shows how pipeline yaml resolution moves from YAML or policy inputs into domain-validated configuration objects. |
| 373 | Pipeline YAML Resolution Block Layout | block-beta | Configuration | Provides a block-level view of the moving pieces involved in pipeline yaml resolution. |
| 374 | DQ Config Merge Layers | flowchart | Configuration | Shows how dq config merge layers moves from YAML or policy inputs into domain-validated configuration objects. |
| 375 | DQ Config Merge Layers Block Layout | block-beta | Configuration | Provides a block-level view of the moving pieces involved in dq config merge layers. |
| 376 | Filter Config Merge Layers | flowchart | Configuration | Shows how filter config merge layers moves from YAML or policy inputs into domain-validated configuration objects. |
| 377 | Filter Config Merge Layers Block Layout | block-beta | Configuration | Provides a block-level view of the moving pieces involved in filter config merge layers. |
| 378 | Enum Externalization Loader | flowchart | Configuration | Shows how enum externalization loader moves from YAML or policy inputs into domain-validated configuration objects. |
| 379 | Enum Externalization Loader Block Layout | block-beta | Configuration | Provides a block-level view of the moving pieces involved in enum externalization loader. |
| 380 | Composite Config Parsing | flowchart | Configuration | Shows how composite config parsing moves from YAML or policy inputs into domain-validated configuration objects. |
| 381 | Composite Config Parsing Block Layout | block-beta | Configuration | Provides a block-level view of the moving pieces involved in composite config parsing. |
| 382 | Composite Config Validation | flowchart | Configuration | Shows how composite config validation moves from YAML or policy inputs into domain-validated configuration objects. |
| 383 | Composite Config Validation Block Layout | block-beta | Configuration | Provides a block-level view of the moving pieces involved in composite config validation. |
| 384 | Composite Runtime Config Projection | flowchart | Configuration | Shows how composite runtime config projection moves from YAML or policy inputs into domain-validated configuration objects. |
| 385 | Composite Runtime Config Projection Block Layout | block-beta | Configuration | Provides a block-level view of the moving pieces involved in composite runtime config projection. |
| 386 | Field Group Loader Resolution | flowchart | Configuration | Shows how field group loader resolution moves from YAML or policy inputs into domain-validated configuration objects. |
| 387 | Field Group Loader Resolution Block Layout | block-beta | Configuration | Provides a block-level view of the moving pieces involved in field group loader resolution. |
| 388 | Publication Type Classification Loader | flowchart | Configuration | Shows how publication type classification loader moves from YAML or policy inputs into domain-validated configuration objects. |
| 389 | Publication Type Classification Loader Block Layout | block-beta | Configuration | Provides a block-level view of the moving pieces involved in publication type classification loader. |
| 390 | Domain Config Resolver | flowchart | Configuration | Shows how domain config resolver moves from YAML or policy inputs into domain-validated configuration objects. |
| 391 | Domain Config Resolver Block Layout | block-beta | Configuration | Provides a block-level view of the moving pieces involved in domain config resolver. |
| 392 | Source Config Loader | flowchart | Configuration | Shows how source config loader moves from YAML or policy inputs into domain-validated configuration objects. |
| 393 | Source Config Loader Block Layout | block-beta | Configuration | Provides a block-level view of the moving pieces involved in source config loader. |
| 394 | Pipeline Normalizers | flowchart | Configuration | Shows how pipeline normalizers moves from YAML or policy inputs into domain-validated configuration objects. |
| 395 | Pipeline Normalizers Block Layout | block-beta | Configuration | Provides a block-level view of the moving pieces involved in pipeline normalizers. |
| 396 | Contract Policy Loader | flowchart | Configuration | Shows how contract policy loader moves from YAML or policy inputs into domain-validated configuration objects. |
| 397 | Contract Policy Loader Block Layout | block-beta | Configuration | Provides a block-level view of the moving pieces involved in contract policy loader. |
| 398 | DQ Contract Config Loader | flowchart | Configuration | Shows how dq contract config loader moves from YAML or policy inputs into domain-validated configuration objects. |
| 399 | Publication Entity Family | classDiagram | DomainModel | Provides a structural domain-model view for publication entity family with concrete BioETL types. |
| 400 | Publication Entity Family Relationship View | erDiagram | DomainModel | Highlights the key relationships and identity anchors inside publication entity family. |
| 401 | Activity Entity Family | classDiagram | DomainModel | Provides a structural domain-model view for activity entity family with concrete BioETL types. |
| 402 | Activity Entity Family Relationship View | erDiagram | DomainModel | Highlights the key relationships and identity anchors inside activity entity family. |
| 403 | Protein Entity Family | classDiagram | DomainModel | Provides a structural domain-model view for protein entity family with concrete BioETL types. |
| 404 | Protein Entity Family Relationship View | erDiagram | DomainModel | Highlights the key relationships and identity anchors inside protein entity family. |
| 405 | Compound Identity Value Objects | classDiagram | DomainModel | Provides a structural domain-model view for compound identity value objects with concrete BioETL types. |
| 406 | Compound Identity Value Objects Relationship View | erDiagram | DomainModel | Highlights the key relationships and identity anchors inside compound identity value objects. |
| 407 | Run Context Value Objects | classDiagram | DomainModel | Provides a structural domain-model view for run context value objects with concrete BioETL types. |
| 408 | Run Context Value Objects Relationship View | erDiagram | DomainModel | Highlights the key relationships and identity anchors inside run context value objects. |
| 409 | DQ Metrics Value Objects | classDiagram | DomainModel | Provides a structural domain-model view for dq metrics value objects with concrete BioETL types. |
| 410 | DQ Metrics Value Objects Relationship View | erDiagram | DomainModel | Highlights the key relationships and identity anchors inside dq metrics value objects. |
| 411 | Lineage Graph Models | classDiagram | DomainModel | Provides a structural domain-model view for lineage graph models with concrete BioETL types. |
| 412 | Lineage Graph Models Relationship View | erDiagram | DomainModel | Highlights the key relationships and identity anchors inside lineage graph models. |
| 413 | Metadata Models Across Layers | classDiagram | DomainModel | Provides a structural domain-model view for metadata models across layers with concrete BioETL types. |
| 414 | Metadata Models Across Layers Relationship View | erDiagram | DomainModel | Highlights the key relationships and identity anchors inside metadata models across layers. |
| 415 | Control Plane Artifact Models | classDiagram | DomainModel | Provides a structural domain-model view for control plane artifact models with concrete BioETL types. |
| 416 | Control Plane Artifact Models Relationship View | erDiagram | DomainModel | Highlights the key relationships and identity anchors inside control plane artifact models. |
| 417 | Workflow Manifest Models | classDiagram | DomainModel | Provides a structural domain-model view for workflow manifest models with concrete BioETL types. |
| 418 | Workflow Manifest Models Relationship View | erDiagram | DomainModel | Highlights the key relationships and identity anchors inside workflow manifest models. |
| 419 | Gold Contract Models | classDiagram | DomainModel | Provides a structural domain-model view for gold contract models with concrete BioETL types. |
| 420 | Gold Contract Models Relationship View | erDiagram | DomainModel | Highlights the key relationships and identity anchors inside gold contract models. |
| 421 | Composite Result Models | classDiagram | DomainModel | Provides a structural domain-model view for composite result models with concrete BioETL types. |
| 422 | Composite Result Models Relationship View | erDiagram | DomainModel | Highlights the key relationships and identity anchors inside composite result models. |
| 423 | Cross Validation Result Models | classDiagram | DomainModel | Provides a structural domain-model view for cross validation result models with concrete BioETL types. |
| 424 | Cross Validation Result Models Relationship View | erDiagram | DomainModel | Highlights the key relationships and identity anchors inside cross validation result models. |
| 425 | Normalization Policy Models | classDiagram | DomainModel | Provides a structural domain-model view for normalization policy models with concrete BioETL types. |
| 426 | Normalization Policy Models Relationship View | erDiagram | DomainModel | Highlights the key relationships and identity anchors inside normalization policy models. |
| 427 | Health Status And Runtime Types | classDiagram | DomainModel | Provides a structural domain-model view for health status and runtime types with concrete BioETL types. |
| 428 | Health Status And Runtime Types Relationship View | erDiagram | DomainModel | Highlights the key relationships and identity anchors inside health status and runtime types. |
| 429 | Composite Seed Dependency Planning | flowchart | Composite | Shows the composite-specific control flow for seed dependency planning. |
| 430 | Composite Seed Dependency Planning Interaction | sequenceDiagram | Composite | Details participant interaction around composite seed dependency planning. |
| 431 | Composite Dependency Progress Tracking | flowchart | Composite | Shows the composite-specific control flow for dependency progress tracking. |
| 432 | Composite Dependency Progress Tracking Interaction | sequenceDiagram | Composite | Details participant interaction around composite dependency progress tracking. |
| 433 | Composite Join Key Normalization | flowchart | Composite | Shows the composite-specific control flow for join key normalization. |
| 434 | Composite Join Key Normalization Interaction | sequenceDiagram | Composite | Details participant interaction around composite join key normalization. |
| 435 | Composite Join Key Resolution | flowchart | Composite | Shows the composite-specific control flow for join key resolution. |
| 436 | Composite Join Key Resolution Interaction | sequenceDiagram | Composite | Details participant interaction around composite join key resolution. |
| 437 | Composite Column Priority Ordering | flowchart | Composite | Shows the composite-specific control flow for column priority ordering. |
| 438 | Composite Column Priority Ordering Interaction | sequenceDiagram | Composite | Details participant interaction around composite column priority ordering. |
| 439 | Composite Cross Validation Result Routing | flowchart | Composite | Shows the composite-specific control flow for cross validation result routing. |
| 440 | Composite Cross Validation Result Routing Interaction | sequenceDiagram | Composite | Details participant interaction around composite cross validation result routing. |
| 441 | Composite Merger Metrics Publication | flowchart | Composite | Shows the composite-specific control flow for merger metrics publication. |
| 442 | Composite Merger Metrics Publication Interaction | sequenceDiagram | Composite | Details participant interaction around composite merger metrics publication. |
| 443 | Composite Merger Input And Output Mixins | flowchart | Composite | Shows the composite-specific control flow for merger input and output mixins. |
| 444 | Composite Merger Input And Output Mixins Interaction | sequenceDiagram | Composite | Details participant interaction around composite merger input and output mixins. |
| 445 | Composite Checkpoint Persistence For Composite Runs | flowchart | Composite | Shows the composite-specific control flow for checkpoint persistence for composite runs. |
| 446 | Composite Checkpoint Persistence For Composite Runs Interaction | sequenceDiagram | Composite | Details participant interaction around composite checkpoint persistence for composite runs. |
| 447 | Structlog Binding And Context Propagation | flowchart | Observability | Shows the observability-oriented signal path for structlog binding and context propagation. |
| 448 | Structlog Binding And Context Propagation Component View | classDiagram | Observability | Maps the concrete classes or functions involved in structlog binding and context propagation. |
| 449 | OpenTelemetry Span Publication | flowchart | Observability | Shows the observability-oriented signal path for opentelemetry span publication. |
| 450 | OpenTelemetry Span Publication Component View | classDiagram | Observability | Maps the concrete classes or functions involved in opentelemetry span publication. |
| 451 | Prometheus Metrics Port Publication | flowchart | Observability | Shows the observability-oriented signal path for prometheus metrics port publication. |
| 452 | Prometheus Metrics Port Publication Component View | classDiagram | Observability | Maps the concrete classes or functions involved in prometheus metrics port publication. |
| 453 | Anomaly Detector Alert Path | flowchart | Observability | Shows the observability-oriented signal path for anomaly detector alert path. |
| 454 | Anomaly Detector Alert Path Component View | classDiagram | Observability | Maps the concrete classes or functions involved in anomaly detector alert path. |
| 455 | Run Manifest Diagnostics Reporting | flowchart | Observability | Shows the observability-oriented signal path for run manifest diagnostics reporting. |
| 456 | Run Manifest Diagnostics Reporting Component View | classDiagram | Observability | Maps the concrete classes or functions involved in run manifest diagnostics reporting. |
| 457 | Health Check Summary Recording | flowchart | Observability | Shows the observability-oriented signal path for health check summary recording. |
| 458 | Health Check Summary Recording Component View | classDiagram | Observability | Maps the concrete classes or functions involved in health check summary recording. |
| 459 | Composite Lifecycle Metrics | flowchart | Observability | Shows the observability-oriented signal path for composite lifecycle metrics. |
| 460 | Composite Lifecycle Metrics Component View | classDiagram | Observability | Maps the concrete classes or functions involved in composite lifecycle metrics. |
| 461 | Provider Request Count Reporting | flowchart | Observability | Shows the observability-oriented signal path for provider request count reporting. |
| 462 | Provider Request Count Reporting Component View | classDiagram | Observability | Maps the concrete classes or functions involved in provider request count reporting. |
| 463 | Metadata Write Completion Signals | flowchart | Observability | Shows the observability-oriented signal path for metadata write completion signals. |
| 464 | HTTP Retry Exhaustion | flowchart | ErrorHandling | Documents the BioETL error-handling path for http retry exhaustion. |
| 465 | HTTP Retry Exhaustion Recovery Sequence | sequenceDiagram | ErrorHandling | Shows the recovery or degradation sequence for http retry exhaustion. |
| 466 | Circuit Breaker Open Recovery | flowchart | ErrorHandling | Documents the BioETL error-handling path for circuit breaker open recovery. |
| 467 | Circuit Breaker Open Recovery Recovery Sequence | sequenceDiagram | ErrorHandling | Shows the recovery or degradation sequence for circuit breaker open recovery. |
| 468 | Provider Health Degradation | flowchart | ErrorHandling | Documents the BioETL error-handling path for provider health degradation. |
| 469 | Provider Health Degradation Recovery Sequence | sequenceDiagram | ErrorHandling | Shows the recovery or degradation sequence for provider health degradation. |
| 470 | DQ Hard Threshold Escalation | flowchart | ErrorHandling | Documents the BioETL error-handling path for dq hard threshold escalation. |
| 471 | DQ Hard Threshold Escalation Recovery Sequence | sequenceDiagram | ErrorHandling | Shows the recovery or degradation sequence for dq hard threshold escalation. |
| 472 | Validation Quarantine Routing | flowchart | ErrorHandling | Documents the BioETL error-handling path for validation quarantine routing. |
| 473 | Validation Quarantine Routing Recovery Sequence | sequenceDiagram | ErrorHandling | Shows the recovery or degradation sequence for validation quarantine routing. |
| 474 | Checkpoint Resume Rejection | flowchart | ErrorHandling | Documents the BioETL error-handling path for checkpoint resume rejection. |
| 475 | Checkpoint Resume Rejection Recovery Sequence | sequenceDiagram | ErrorHandling | Shows the recovery or degradation sequence for checkpoint resume rejection. |
| 476 | Workflow Ledger Resume Conflict | flowchart | ErrorHandling | Documents the BioETL error-handling path for workflow ledger resume conflict. |
| 477 | Workflow Ledger Resume Conflict Recovery Sequence | sequenceDiagram | ErrorHandling | Shows the recovery or degradation sequence for workflow ledger resume conflict. |
| 478 | Composite Normalization Compatibility Mismatch | flowchart | ErrorHandling | Documents the BioETL error-handling path for composite normalization compatibility mismatch. |
| 479 | Composite Normalization Compatibility Mismatch Recovery Sequence | sequenceDiagram | ErrorHandling | Shows the recovery or degradation sequence for composite normalization compatibility mismatch. |
| 480 | Join Key Missing Source | flowchart | ErrorHandling | Documents the BioETL error-handling path for join key missing source. |
| 481 | Architecture Import Matrix Enforcement | flowchart | Testing | Summarizes the main test surfaces and assertions around architecture import matrix enforcement. |
| 482 | Compatibility Freeze Guard Inventory | flowchart | Testing | Summarizes the main test surfaces and assertions around compatibility freeze guard inventory. |
| 483 | VCR Cassette Placement Governance | flowchart | Testing | Summarizes the main test surfaces and assertions around vcr cassette placement governance. |
| 484 | Reproducibility Contract Suite Coverage | flowchart | Testing | Summarizes the main test surfaces and assertions around reproducibility contract suite coverage. |
| 485 | Diagram Lint And Visual Smoke Gate | flowchart | Testing | Summarizes the main test surfaces and assertions around diagram lint and visual smoke gate. |
| 486 | Provider Contract Regression Pack | flowchart | Testing | Summarizes the main test surfaces and assertions around provider contract regression pack. |
| 487 | Debt Scorecard Governance Tests | flowchart | Testing | Summarizes the main test surfaces and assertions around debt scorecard governance tests. |
| 488 | Composite Preflight Regression Matrix | flowchart | Testing | Summarizes the main test surfaces and assertions around composite preflight regression matrix. |
| 489 | Control Plane Artifact Regression Pack | flowchart | Testing | Summarizes the main test surfaces and assertions around control plane artifact regression pack. |
| 490 | Workflow CLI Stability Matrix | flowchart | Testing | Summarizes the main test surfaces and assertions around workflow cli stability matrix. |
| 491 | PII Hashing And Salt Rotation | flowchart | Security | Shows the security-sensitive surface around pii hashing and salt rotation in local-only BioETL runtime. |
| 492 | Audit Trail File Publication | flowchart | Security | Shows the security-sensitive surface around audit trail file publication in local-only BioETL runtime. |
| 493 | Secret Redaction In Logs | flowchart | Security | Shows the security-sensitive surface around secret redaction in logs in local-only BioETL runtime. |
| 494 | Local-Only Deployment Trust Boundary | flowchart | Security | Shows the security-sensitive surface around local-only deployment trust boundary in local-only BioETL runtime. |
| 495 | Config Provenance Hash Chain | flowchart | Security | Shows the security-sensitive surface around config provenance hash chain in local-only BioETL runtime. |
| 496 | Batch Memory Budget Adjustment | xychart-beta | Performance | Provides a performance-oriented view of batch memory budget adjustment and its tuning surface. |
| 497 | Cached Bronze Snapshot Reuse | xychart-beta | Performance | Provides a performance-oriented view of cached bronze snapshot reuse and its tuning surface. |
| 498 | Delta Dedup Timeout Clamp | xychart-beta | Performance | Provides a performance-oriented view of delta dedup timeout clamp and its tuning surface. |
| 499 | Retry Reduction Policy | xychart-beta | Performance | Provides a performance-oriented view of retry reduction policy and its tuning surface. |
| 500 | Adaptive Provider Batch Size | xychart-beta | Performance | Provides a performance-oriented view of adaptive provider batch size and its tuning surface. |

## Part 2 / 3 — TOP-50 Priority Table

| # | Title | Type | Category | Priority | Arch | Doc | Freq | Complex | Coverage | Obosnovanie vazhnosti | Classes/Components |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---|---|
| 1 | Control Plane Artifact Publication Pipeline | flowchart | Architecture | 9.69 | 10 | 10 | 9 | 10 | 9 | This diagram resolves one of the hardest modern BioETL onboarding gaps: how control-plane artifacts are produced and connected. It is critical for platform engineers, reproducibility work, and any contributor touching manifest or ledger paths. | `build_postrun_service`, `RunManifest`, `EffectiveConfigArtifact`, `RunLedgerEntry`, `PipelineRunner`, `historical_replay_universe_service.py` |
| 2 | Effective Execution Config Resolution And Artifact Hashing | sequenceDiagram | Architecture | 9.50 | 10 | 10 | 8 | 10 | 9 | Config resolution is central to reproducibility and difficult to infer from scattered builders and domain models. The diagram is most useful for maintainers touching config loaders, runtime assembly, or exact replay guarantees. | `EffectiveConfigArtifact`, `EffectiveConfigHashes`, `ResolvedConfigSnapshot`, `ExecutionEnvironmentSnapshot`, `composite.py`, `assembly.py` |
| 3 | Reproducible Run Contract Across Manifest Ledger And Output Metadata | flowchart | Architecture | 9.44 | 10 | 9 | 8 | 10 | 10 | BioETL now has multiple traceability artifacts; without a unifying view it is easy to miss contract boundaries. This diagram gives reviewers and operators a single checkpoint for exact-run reasoning. | `RunManifest`, `RunLedgerEntry`, `chembl_activity_metadata.yaml`, `MetadataWriter`, `bronze_writer.py`, `silver_writer.py`, `gold_writer.py` |
| 4 | Historical Replay Universe Inventory And Closure Report | sequenceDiagram | Architecture | 9.00 | 10 | 9 | 7 | 10 | 8 | Historical replay is a newer control-plane surface with dense policy semantics and little visual documentation. The diagram helps platform, audit, and operations contributors validate replay readiness and closure gaps. | `HistoricalReplayUniverseService`, `HistoricalReplayUniverseInventorySnapshot`, `HistoricalReplayUniverseClosureReportRecord`, `build_universe_inventory`, `build_universe_closure_report` |
| 5 | Composite Preflight Field Priority And Normalization Compatibility Resolution | sequenceDiagram | Composite | 8.94 | 9 | 9 | 8 | 10 | 8 | Composite preflight is subtle and currently spread across validator mixins and reporting helpers. This view is especially valuable for engineers working on publication merge semantics or schema-governance regressions. | `CompositePreflightValidationService`, `PreflightValidationReportingMixin`, `PreflightSchemaOrchestrationMixin`, `preflight_validator.py`, `memory-py-doc-bot.md` |
| 6 | Pipeline Service Bundle And Runner Dependencies | classDiagram | Component | 8.69 | 9 | 9 | 8 | 9 | 8 | The runner bundle is the main application composition surface and reading it from code is expensive. This diagram is most helpful for maintainers touching execution orchestration or storage integration. | `PipelineRunner`, `PipelineService`, `PipelineStorageProtocol`, `BatchExecutor`, `RecordProcessor`, `BatchWriter` |
| 7 | Provider Registry Loading To Data Source Creation | sequenceDiagram | Architecture | 8.69 | 9 | 9 | 8 | 9 | 8 | Composition-time provider wiring is a common extension point and a common source of confusion. This diagram is highly useful for anyone adding providers or debugging missing registry entries. | `ProviderRegistry`, `ensure_provider_registry_ready`, `create_provider_registry`, `create_adapter`, `create_data_source`, `data_source_factory.py` |
| 8 | Workflow Control Plane Manifest And Ledger Publication | flowchart | Architecture | 8.56 | 10 | 8 | 7 | 9 | 8 | Workflow-level control-plane surfaces add a second orchestration plane above single pipeline runs. This diagram is important for contributors implementing workflow CLI or runbook support. | `WorkflowManifest`, `WorkflowManifestStep`, `workflow_execution_state.py`, `WorkflowLedger`, `workflow.py` |
| 9 | Lock Heartbeat Checkpoint And Shutdown Collaboration | sequenceDiagram | Interaction | 8.56 | 9 | 9 | 8 | 9 | 7 | These runtime guardrails are central to safe incremental execution but distributed across layers and services. The visual path is useful to runtime engineers and reviewers of lifecycle changes. | `MemoryLock`, `LocalCheckpointPort`, `PipelineRunner`, `ShutdownPort`, `heartbeat.py`, `shutdown.py` |
| 10 | Postrun Retention Deduplication And Vacuum Warning Path | sequenceDiagram | Interaction | 8.56 | 9 | 9 | 8 | 9 | 7 | The postrun path mixes maintenance policy, retention helpers, and operational guardrails that are not obvious from unit tests alone. It is most valuable for storage maintainers and incident response work. | `build_postrun_service`, `RetentionPolicy`, `retention.py`, `postrun_assembly.py`, `test_postrun_compact_orchestrator.py` |
| 11 | Observability Bootstrap Bundle From Settings To Ports | flowchart | Observability | 8.31 | 9 | 9 | 8 | 8 | 7 | Observability wiring spans runtime assembly and infrastructure implementations and is easy to misread from bootstrap helpers alone. This diagram gives both platform and app engineers a stable reference. | `bootstrap_logger`, `bootstrap_tracer`, `bootstrap_metrics`, `bootstrap_dq_monitor`, `bootstrap_observability_bundle`, `maybe_start_metrics_server` |
| 12 | PipelineRun Aggregate Stage Result And Terminal Transition Model | stateDiagram | Lifecycle | 8.25 | 9 | 9 | 7 | 9 | 6 | The PipelineRun aggregate is foundational but its real transition semantics are hidden behind mixins and read-model helpers. This view is particularly valuable for domain and architecture reviews. | `PipelineRun`, `pipeline_run_stage_result.py`, `pipeline_run_state.py`, `events.py`, `PipelineRunState` |
| 13 | Composite Dependency Join Planning And Join Key Resolution | flowchart | Composite | 8.19 | 9 | 8 | 7 | 9 | 7 | Dependency join planning is one of the most complicated composite subsystems and lacks a small mental model. This diagram is especially useful when debugging publication merges and cross-source enrichment. | `DependencyJoinerService`, `join_planner.py`, `join_key_resolution.py`, `dependency_join_execution.py`, `dependency_result_mapper.py` |
| 14 | CompositePipelineRunner Stage State And Merge Boundaries | stateDiagram | Lifecycle | 8.19 | 9 | 8 | 7 | 9 | 7 | Composite runner state is one of the densest execution surfaces in the repository. This diagram helps both architecture review and incident debugging. | `CompositePipelineRunner`, `runner_stage_state_flow.py`, `runner_merge_stage_runtime.py`, `runner_stage_dependency_flow.py` |
| 15 | ChEMBL Activity Extraction To Bronze Artifact Publication | sequenceDiagram | Provider | 8.12 | 8 | 8 | 8 | 9 | 7 | ChEMBL activity is a flagship pipeline and still one of the most operationally important flows. The diagram is highly useful for provider-specific debugging and onboarding. | `ChemblAdapter`, `activity_transformer.py`, `BronzeWriter`, `BatchExecutor`, `UnifiedHTTPClient`, `TokenBucketRateLimiter` |
| 16 | DQ Contract Config Loading And Policy Resolution | flowchart | Configuration | 7.94 | 9 | 8 | 7 | 8 | 7 | The DQ contract system is policy-heavy and spans both config and domain layers. This visual is helpful for governance work and for contributors externalizing new DQ rules. | `DQConfigLoaderPort`, `dq_config_loader.py`, `DQPolicySnapshot`, `ADR-045-dq-contract-system.md` |
| 17 | UnifiedHTTPClient Retry Policy And Circuit Breaker Interaction | sequenceDiagram | ErrorHandling | 7.81 | 9 | 8 | 7 | 8 | 6 | HTTP resilience is a cross-cutting mechanism that affects every provider. This sequence helps adapter maintainers and incident responders understand the exact order of protections. | `UnifiedHTTPClient`, `TokenBucketRateLimiter`, `CircuitBreaker`, `client_retry_mixin.py`, `_client_retry_policy.py` |
| 18 | CrossRef Publication Search Fallback And Batch DOI Fetch | sequenceDiagram | Provider | 7.81 | 8 | 8 | 7 | 9 | 6 | CrossRef behavior includes fallback policy and batching details that are easy to miss. This view is useful for publication-pipeline maintainers and troubleshooting failed enrichment. | `CrossRefAdapter`, `fallback.py`, `batch.py`, `query_builder.py`, `response_mapper.py` |
| 19 | EnrichmentCoordinatorService Dependency Fan-Out And Result Reduction | sequenceDiagram | Interaction | 7.81 | 8 | 8 | 7 | 9 | 6 | The coordinator is concurrency-heavy and not trivial to reconstruct from code alone. This sequence is valuable for contributors changing composite execution or observability. | `EnrichmentCoordinatorService`, `coordinator_result_mixin.py`, `dependency_coordinator.py`, `aggregator.py` |
| 20 | OpenAlex Cursor Pagination And Response Mapping Path | sequenceDiagram | Provider | 7.81 | 8 | 8 | 7 | 9 | 6 | OpenAlex brings cursor-style pagination and a different enrichment posture than the biomedical providers. This diagram is useful for adapter maintainers and pagination debugging. | `OpenAlexAdapter`, `cursor_flow.py`, `query_execution.py`, `response_mapping.py`, `fallback_orchestrator.py` |
| 21 | PubMed Search Fetch XML Parse And Publication Mapping | sequenceDiagram | Provider | 7.81 | 8 | 8 | 7 | 9 | 6 | PubMed has a materially different fetch and parse pipeline from the JSON-first providers. A focused sequence view helps new contributors avoid treating it like CrossRef or OpenAlex. | `PubMedClient`, `PubMedAdapter`, `xml_processor.py`, `_search.py`, `_fetch.py` |
| 22 | UniProt IDMapping To Protein Fetch Enrichment | flowchart | Provider | 7.81 | 8 | 8 | 7 | 9 | 6 | UniProt is structurally different from most other providers because idmapping and protein fetch are distinct behaviors. This view is useful for scientific-data contributors and adapter reviewers. | `UniProtAdapter`, `UniProtIdMappingClient`, `idmapping_client.py`, `protein_fetch_adapter_mixin.py`, `feature_sequence_adapter_mixin.py` |
| 23 | Data Traceability Runtime Path For Manifest Effective Config And Lineage | flowchart | DataFlow | 7.75 | 9 | 8 | 6 | 8 | 7 | This cross-cutting path is vital during audits and replay analysis. The diagram gives one view that unifies several otherwise disconnected artifacts. | `run_manifest.py`, `effective_config_artifact.py`, `lineage/graph.py`, `lineage/metadata_bundle.py` |
| 24 | Runtime Builder Control Plane Inputs To Effective Config Artifact | flowchart | Architecture | 7.75 | 9 | 8 | 6 | 8 | 7 | This diagram closes the gap between builder modules and published artifacts. It is particularly helpful for contributors extending run-level provenance. | `effective_config_artifact_builder.py`, `inputs_resolver.py`, `control_plane.py`, `effective_config_artifact.py` |
| 25 | SemanticScholar Search Fallback And Batch Request Flow | sequenceDiagram | Provider | 7.62 | 8 | 8 | 6 | 9 | 6 | Semantic Scholar is one of the less frequently touched providers, which makes its control flow easier to forget. A dedicated diagram lowers the barrier to safe maintenance. | `SemanticScholarAdapter`, `_search_fetch_flow.py`, `batch_request_mixin.py`, `fallback.py` |
| 26 | Batch Aggregate Seal Write Commit Failure Lifecycle | stateDiagram | Lifecycle | 7.56 | 8 | 8 | 7 | 8 | 6 | Batch lifecycle bugs can corrupt medallion semantics and are hard to reason about from helper mixins. The diagram gives engineers a clear contract for batch terminal states. | `Batch`, `_batch_lifecycle.py`, `_batch_record.py`, `_batch_status.py`, `BatchRecord` |
| 27 | DependencyJoinerService Composite Key Join And System Column Cleanup | flowchart | Component | 7.56 | 8 | 8 | 7 | 8 | 6 | The service is a critical merge seam and its cleanup behavior is easy to forget. The diagram helps explain why intermediate columns appear and disappear during composite assembly. | `DependencyJoinerService`, `apply_dependency_joins`, `apply_composite_key_dependency_join`, `drop_system_columns` |
| 28 | Effective Config Artifact Domain Model | classDiagram | Component | 7.56 | 8 | 8 | 7 | 8 | 6 | The effective config artifact carries dense provenance and hash surfaces that are easy to misuse without a structural map. The diagram helps both config and control-plane maintainers. | `EffectiveConfigArtifact`, `EffectiveConfigHashes`, `ConfigSourceRef`, `ResolvedConfigSnapshot`, `RuntimeOverrideSnapshot`, `ExecutionEnvironmentSnapshot` |
| 29 | Filter Config Resolution And Column Filter Evaluation | flowchart | Configuration | 7.56 | 8 | 8 | 7 | 8 | 6 | Filtering is externally configured and easy to misunderstand when debugging missing records. The diagram is useful for both pipeline implementers and data-quality operators. | `FilterConfigLoaderPort`, `filter_config_loader.py`, `column_filter.py`, `silver_config.py`, `gold_config.py` |
| 30 | PipelineRunner Control Surface And Attached Ledger Service | classDiagram | Component | 7.56 | 8 | 8 | 7 | 8 | 6 | PipelineRunner is a core application facade with a large dependency footprint. This diagram is useful for reviewers who need the runtime surface quickly without reading multiple support mixins. | `PipelineRunner`, `attach_run_ledger_service`, `execution_metrics`, `execution_diagnostics`, `services` |
| 31 | PubChem Compound Fetch Strategy Resolution | flowchart | Provider | 7.56 | 8 | 8 | 7 | 8 | 6 | PubChem is strategically important and uses a mix of strategy helpers that are non-obvious from the adapter shell alone. The diagram makes this extension surface significantly easier to understand. | `PubChemAdapter`, `fetch_strategies.py`, `query_builder.py`, `response_mapper.py`, `client_builders.py` |
| 32 | Publication Composite Merge Source Priority And Override Review Path | flowchart | DataFlow | 7.56 | 8 | 8 | 7 | 8 | 6 | Publication merge semantics are important and subtle, especially around normalization mismatches. This view is highly useful for bibliographic pipeline work. | `CompositePreflightValidationService`, `merger.py`, `column_priority_orderer.py`, `cross_validator.py` |
| 33 | Run Manifest Domain Model And Serialization Surface | classDiagram | Component | 7.56 | 8 | 8 | 7 | 8 | 6 | Run manifest payload shape is critical for downstream tooling, but its nested models are not easy to reconstruct mentally. This class view is most useful for control-plane and CLI work. | `RunManifest`, `RunInputSnapshotRef`, `RunSourceRef`, `RunArtifactRef`, `RunCodeProvenance` |
| 34 | Quarantine Entry Review Resolution And Discard Flow | stateDiagram | Lifecycle | 7.44 | 8 | 8 | 7 | 8 | 5 | Quarantine semantics matter for quality operations but are usually understood only through tests. This view is especially useful for DQ maintainers and support engineers. | `QuarantineEntry`, `_quarantine_aggregate.py`, `_quarantine_entry_transitions_mixin.py`, `unified.py` |
| 35 | Contract Registry Policy Resolution And Gold Contract Selection | flowchart | Architecture | 7.38 | 8 | 8 | 6 | 8 | 6 | Gold contract policy is a governance-sensitive area that benefits from explicit visualization. This view is useful for architecture, schema, and contract maintainers. | `contract_registry.py`, `contract_registry_service.py`, `gold_contract.py`, `contract_registry_helpers.py` |
| 36 | PipelineStorageProtocol And PipelineService Dependency Boundary | classDiagram | Component | 7.25 | 8 | 8 | 6 | 8 | 5 | The protocol seam is central to hexagonal enforcement but can disappear inside type aliases and bundles. This view is useful for application and infrastructure contributors alike. | `PipelineStorageProtocol`, `PipelineService`, `BronzeStoragePort`, `SilverStoragePort`, `GoldStoragePort`, `MergedStoragePort` |
| 37 | Provider Health Monitor State Adaptation And Config Adjustment | stateDiagram | ErrorHandling | 7.25 | 8 | 8 | 6 | 8 | 5 | Adaptive provider health is operationally important but easy to miss because state and config logic live together. This diagram is especially useful for resilience tuning. | `ProviderHealthMonitor`, `ProviderHealthState`, `record_health_check_result`, `get_adjusted_config` |
| 38 | Cached Bronze Snapshot And Exact Replay Input Resolution | flowchart | DataFlow | 7.19 | 8 | 7 | 6 | 8 | 6 | Exact replay support is one of the newer and less intuitive runtime paths. This view is especially useful for reproducibility diagnostics and storage reasoning. | `cached_bronze_snapshot_support.py`, `inputs_resolver.py`, `context_cached_bronze.py`, `effective_config_artifact_builder.py` |
| 39 | Composite Lifecycle Observer Tracing And Metrics Publication | sequenceDiagram | Interaction | 7.19 | 8 | 7 | 6 | 8 | 6 | Composite observability is a dense mix of stage logic and telemetry hooks. This diagram is useful for debugging missing lifecycle signals. | `lifecycle_observer_service.py`, `_lifecycle_observer_tracing_mixin.py`, `CompositePipelineRunner`, `MetricsPort`, `TracingPort` |
| 40 | Local Checkpoint Resume Decision Versus Workflow Ledger Replay | flowchart | ErrorHandling | 7.19 | 8 | 7 | 6 | 8 | 6 | This is a nuanced operational distinction introduced by newer control-plane work. The diagram helps maintainers avoid blending two similar but different recovery mechanisms. | `LocalCheckpointPort`, `run_ledger_replay.py`, `workflow_execution_state.py`, `checkpoint_manager.py` |
| 41 | Schema Domain Pair Governance From Domain Schemas To Gold Contract | flowchart | Configuration | 7.19 | 8 | 7 | 6 | 8 | 6 | Schema governance spans multiple ADRs and is not trivial to connect mentally. This view helps data-contract and validation contributors reason about enforcement boundaries. | `domain/schemas/base.py`, `ADR-034-schema-domain-pairs.md`, `ADR-037-canonical-schema-generation.md`, `gold_contract.py` |
| 42 | Control Plane Artifact Traceability From CLI To Run Manifest Inspection | sequenceDiagram | Interaction | 7.12 | 8 | 8 | 6 | 7 | 6 | Operators often need to inspect artifacts without understanding the full runtime. This sequence bridges CLI entrypoints and control-plane surfaces. | `run_manifest.py`, `diagnostics.py`, `domains/shared/inspection_output.py`, `HistoricalReplayUniverseService` |
| 43 | Decorator And Fallback Pattern Stack Around Provider Adapters | classDiagram | Pattern | 7.06 | 8 | 7 | 6 | 7 | 7 | The provider stack demonstrates several applied patterns at once, which is easy to miss when reading one adapter at a time. This diagram is valuable for adapter and resilience work. | `FallbackPolicyMixin`, `CircuitBreakerDecorator`, `RetryDecorator`, `BaseHttpAdapter`, `CrossRefAdapter`, `OpenAlexAdapter` |
| 44 | Factory Method Pipeline Assembly Across Construction Helpers | flowchart | Pattern | 7.06 | 8 | 7 | 6 | 7 | 7 | Pipeline assembly is a classic extension point and a recurring source of accidental coupling. The diagram is useful for any engineer modifying composition or registry code. | `construction.py`, `runner_constructor.py`, `transformer_builder.py`, `pipeline_builder.py`, `registry.py` |
| 45 | Bootstrap Runtime Observability And Metrics Server Start Path | sequenceDiagram | Observability | 7.00 | 8 | 8 | 6 | 7 | 5 | This path is frequently touched during environment-specific debugging and observability rollout. It is useful for both platform and local-ops contributors. | `bootstrap_logger`, `bootstrap_tracer`, `bootstrap_metrics`, `maybe_start_metrics_server`, `start_metrics_server` |
| 46 | Bronze Metadata To Silver Metadata To Gold Metadata Progression | sankey-beta | DataFlow | 6.94 | 8 | 7 | 6 | 7 | 6 | Metadata progression is critical to traceability but difficult to summarize textually. A sankey view provides a compact and intuitive operator-facing summary. | `metadata_writer.py`, `MetadataCoordinatorPort`, `lineage_fragment_id`, `dataset_ref`, `MetadataWriter` |
| 47 | Entity Normalization Services For DOI Title Abstract And Unit Surfaces | classDiagram | Pattern | 6.94 | 7 | 7 | 6 | 8 | 6 | Normalization logic is scattered across services and helper modules; this diagram turns it into a coherent design surface. It is useful for domain and publication-model contributors. | `DataNormalizationService`, `IdentityService`, `UnitConverter`, `ValueValidator`, `dataset_content_identity.py` |
| 48 | Run Ledger Entry Replay Slice Model | classDiagram | Component | 6.81 | 8 | 7 | 6 | 7 | 5 | Replay logic depends on subtle ledger slicing behavior. This view is useful for control-plane maintainers and reproducibility testing. | `RunLedgerEntry`, `slice_ledger_entries_after`, `canonicalize_run_ledger_stage_name`, `run_ledger.py` |
| 49 | Workflow Manifest Step Serialization Surface | classDiagram | Component | 6.81 | 8 | 7 | 6 | 7 | 5 | Workflow manifests are less common than run manifests but increasingly relevant for control-plane orchestration. This diagram helps CLI and workflow contributors reason about payload shape quickly. | `WorkflowManifest`, `WorkflowManifestStep`, `to_dict`, `from_dict`, `workflow_manifest.py` |
| 50 | OpenTelemetryTracer And StructlogLogger Bootstrap Surfaces | classDiagram | Observability | 6.75 | 7 | 8 | 6 | 7 | 5 | The observability adapter layer is compact but widely reused. This diagram is useful when reviewing telemetry consistency or changing bootstrap contracts. | `OpenTelemetryTracer`, `StructlogLogger`, `_TracerAdapter`, `_SpanHandle`, `create_logger` |

## Part 4 — Render Targets For TOP-25

| Rank | Diagram | Canonical `.mmd` file | Planned PNG export |
|---|---|---|---|
| 1 | Control Plane Artifact Publication Pipeline | `architecture/24-control-plane-artifact-publication-pipeline.mmd` | `png/24-control-plane-artifact-publication-pipeline.png` |
| 2 | Effective Execution Config Resolution And Artifact Hashing | `architecture/25-effective-execution-config-resolution-and-artifact-hashing.mmd` | `png/25-effective-execution-config-resolution-and-artifact-hashing.png` |
| 3 | Reproducible Run Contract Across Manifest Ledger And Output Metadata | `architecture/26-reproducible-run-contract-across-manifest-ledger-and-output-metadata.mmd` | `png/26-reproducible-run-contract-across-manifest-ledger-and-output-metadata.png` |
| 4 | Historical Replay Universe Inventory And Closure Report | `architecture/28-historical-replay-universe-inventory-and-closure-report.mmd` | `png/28-historical-replay-universe-inventory-and-closure-report.png` |
| 5 | Composite Preflight Field Priority And Normalization Compatibility Resolution | `architecture/27-composite-preflight-field-priority-and-normalization-compatibility-resolution.mmd` | `png/27-composite-preflight-field-priority-and-normalization-compatibility-resolution.png` |
| 6 | Pipeline Service Bundle And Runner Dependencies | `architecture/33-pipeline-service-bundle-and-runner-dependencies.mmd` | `png/33-pipeline-service-bundle-and-runner-dependencies.png` |
| 7 | Provider Registry Loading To Data Source Creation | `architecture/29-provider-registry-loading-to-data-source-creation.mmd` | `png/29-provider-registry-loading-to-data-source-creation.png` |
| 8 | Workflow Control Plane Manifest And Ledger Publication | `architecture/31-workflow-control-plane-manifest-and-ledger-publication.mmd` | `png/31-workflow-control-plane-manifest-and-ledger-publication.png` |
| 9 | Lock Heartbeat Checkpoint And Shutdown Collaboration | `architecture/32-lock-heartbeat-checkpoint-and-shutdown-collaboration.mmd` | `png/32-lock-heartbeat-checkpoint-and-shutdown-collaboration.png` |
| 10 | Postrun Retention Deduplication And Vacuum Warning Path | `architecture/30-postrun-retention-deduplication-and-vacuum-warning-path.mmd` | `png/30-postrun-retention-deduplication-and-vacuum-warning-path.png` |
| 11 | Observability Bootstrap Bundle From Settings To Ports | `architecture/37-observability-bootstrap-bundle-from-settings-to-ports.mmd` | `png/37-observability-bootstrap-bundle-from-settings-to-ports.png` |
| 12 | PipelineRun Aggregate Stage Result And Terminal Transition Model | `architecture/34-pipelinerun-aggregate-stage-result-and-terminal-transition-model.mmd` | `png/34-pipelinerun-aggregate-stage-result-and-terminal-transition-model.png` |
| 13 | Composite Dependency Join Planning And Join Key Resolution | `` | `(not generated)` |
| 14 | CompositePipelineRunner Stage State And Merge Boundaries | `` | `(not generated)` |
| 15 | ChEMBL Activity Extraction To Bronze Artifact Publication | `architecture/38-chembl-bronze-activity-extraction-to-artifact-publication.mmd` | `png/38-chembl-bronze-activity-extraction-to-artifact-publication.png` |
| 16 | DQ Contract Config Loading And Policy Resolution | `architecture/45-dq-contract-config-loading-and-policy-resolution.mmd` | `png/45-dq-contract-config-loading-and-policy-resolution.png` |
| 17 | UnifiedHTTPClient Retry Policy And Circuit Breaker Interaction | `` | `(not generated)` |
| 18 | CrossRef Publication Search Fallback And Batch DOI Fetch | `architecture/39-crossref-search-fallback-and-batch-doi-fetch-publications.mmd` | `png/39-crossref-search-fallback-and-batch-doi-fetch-publications.png` |
| 19 | EnrichmentCoordinatorService Dependency Fan-Out And Result Reduction | `` | `(not generated)` |
| 20 | OpenAlex Cursor Pagination And Response Mapping Path | `architecture/41-openalex-cursor-pagination-and-response-mapping-path.mmd` | `png/41-openalex-cursor-pagination-and-response-mapping-path.png` |
| 21 | PubMed Search Fetch XML Parse And Publication Mapping | `architecture/40-pubmed-search-fetch-xml-parse-and-publication-mapping.mmd` | `png/40-pubmed-search-fetch-xml-parse-and-publication-mapping.png` |
| 22 | UniProt IDMapping To Protein Fetch Enrichment | `architecture/43-uniprot-mapping-job-to-protein-fetch-enrichment.mmd` | `png/43-uniprot-mapping-job-to-protein-fetch-enrichment.png` |
| 23 | Data Traceability Runtime Path For Manifest Effective Config And Lineage | `` | `(not generated)` |
| 24 | Runtime Builder Control Plane Inputs To Effective Config Artifact | `` | `(not generated)` |
| 25 | SemanticScholar Search Fallback And Batch Request Flow | `architecture/42-semanticscholar-search-fallback-and-batch-request-flow.mmd` | `png/42-semanticscholar-search-fallback-and-batch-request-flow.png` |
