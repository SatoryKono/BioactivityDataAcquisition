# 500 New Mermaid Diagram Proposals for BioETL

*Generated: 2026-02-17 | Based on: RULES.md v5.20, 34 ADRs, 534 Python files*

This document proposes 500 new unique Mermaid diagrams that do not duplicate the 34 existing diagrams in `docs/02-architecture/diagrams/`.

## Existing Diagrams (NOT duplicated)

The following 34 diagrams already exist and are explicitly excluded:
- 01: Full system component (C4), High-level overview
- 02: Medallion data flow (detailed + simplified)
- 03: Pipeline execution happy path, Pipeline sequence
- 04: Domain layer classes, Error flow
- 05: Layers interaction, Locking mechanism, Pipeline lifecycle states
- 06: Application layer classes, Pipeline execution flow
- 07: Circuit breaker states, Medallion flow
- 08: Complete ETL workflow, DDD diagram
- 09: Full ER diagram
- 10: Infrastructure layer classes
- 11: Lock acquisition sequence
- 12: AWS deployment
- 13: Domain model relationships
- 14: Provider health states
- 15: DQ check workflow
- 16: MemoryLock class
- 17: Pipeline/Transformer hierarchy
- 18: Bronze write sequence
- 19: Delta Lake write sequence
- 20: Quarantine record states
- 21: Activity entity data flow
- 22: Client API request sequence
- 23: Silver writer class
- 24: Hash service class
- 25: CircuitBreaker observer class

---

## Category Distribution

| Category | Count | Diagrams |
|----------|-------|----------|
| Architecture | 60 | 1–60 |
| DataFlow | 60 | 61–120 |
| Pattern | 50 | 121–170 |
| Component | 50 | 171–220 |
| Interaction | 50 | 221–270 |
| Lifecycle | 40 | 271–310 |
| Provider | 50 | 311–360 |
| Configuration | 30 | 361–390 |
| DomainModel | 30 | 391–420 |
| Composite | 20 | 421–440 |
| Observability | 20 | 441–460 |
| ErrorHandling | 20 | 461–480 |
| Testing | 10 | 481–490 |
| Security | 5 | 491–495 |
| Performance | 5 | 496–500 |

---

## Architecture (1–60)

| # | Name | Type | Description |
|---|------|------|-------------|
| 1 | Five-Layer Import Matrix Enforcement | flowchart | Shows ARCH-001 import rules between domain/application/infrastructure/composition/interfaces with allowed and forbidden import paths |
| 2 | C4 Container Diagram — BioETL Internal Containers | C4Container | Detailed C4 Level 2 showing CLI, PipelineRunner, Storage Writers, HTTP Adapters, MemoryLock, and Checkpoint containers |
| 3 | C4 Component — Application Layer Internal Components | C4Component | C4 Level 3 decomposition of application layer into Runner, BatchExecutor, Transformers, Services |
| 4 | C4 Component — Infrastructure Layer Internal Components | C4Component | C4 Level 3 decomposition of infrastructure: HTTP client stack, storage writers, observability adapters |
| 5 | C4 Component — Composition Layer Factories and Bootstrap | C4Component | C4 Level 3 showing GenericPipelineFactory, RunnerFactory, ServicesFactory, StorageFactory, DataSourceFactory |
| 6 | Hexagonal Architecture — Ports and Adapters Overview | flowchart | Shows all 24 domain ports on the inner hexagon with their infrastructure adapter implementations on the outer ring |
| 7 | Domain Layer Internal Package Structure | flowchart | Package-level dependency graph: ports, entities, value-objects, schemas, config, services, aggregates, exceptions, composite |
| 8 | Application Layer Internal Package Structure | flowchart | Package-level view: core/, pipelines/, composite/, observability/ with internal dependencies |
| 9 | Infrastructure Layer Internal Package Structure | flowchart | Package-level view: adapters/, storage/, locking/, checkpoint/, quarantine/, observability/, validation/, security/, config/ |
| 10 | Composition Layer Bootstrap Sequence | flowchart | Step-by-step flow from CLI invocation through bootstrap-pipeline() to fully assembled PipelineRunner |
| 11 | Interfaces Layer CLI Command Tree | flowchart | Click command group hierarchy: main → run, run-all, run-composite, health, export, quarantine, maintenance |
| 12 | Local-Only Deployment Architecture (ADR-010) | flowchart | Single-process architecture with MemoryLock, local file system storage, local checkpoints — no Redis/S3 |
| 13 | Domain Purity Boundary — Allowed vs Forbidden Imports | flowchart | What domain layer CAN import (typing, dataclasses, abc) vs what it MUST NOT (requests, httpx, structlog, open) |
| 14 | Port-to-Adapter Mapping Table Diagram | flowchart | All 24 ports mapped to their concrete adapter implementations with module paths |
| 15 | Composition Root Wiring Diagram — Full DI Graph | flowchart | Complete dependency injection graph showing how composition wires all ports to adapters |
| 16 | YAML Configuration Resolution Chain | flowchart | How pipeline configs resolve: -base.yaml → provider.yaml → entity.yaml → dq overrides → filter rules |
| 17 | Architecture Test Coverage Map | flowchart | Map of architecture tests: import boundary, random prohibition, datetime prohibition, structlog prohibition |
| 18 | Layer Responsibility Matrix | flowchart | What each layer IS responsible for vs what it MUST NOT do, based on RULES.md §1.1 |
| 19 | Data Contract Publication Flow | flowchart | Gold schemas → JSON Schema export → docs/contracts/ → Consumer notification → Slack channel |
| 20 | Schema Evolution Workflow — Minor vs Major Changes | flowchart | Decision tree for schema changes: additive (minor) vs breaking (major) with deprecation period |
| 21 | Rollback Strategy Decision Tree | flowchart | Infrastructure rollback (auto at >10% error rate) vs Data DQ rollback (manual analysis + replay) |
| 22 | Environment Isolation — Dev/Staging/Prod | flowchart | Three environments with separate storage dirs, config sources, and access controls |
| 23 | Module File Count Per Layer | pie | Distribution of 534 Python files across domain, application, infrastructure, composition, interfaces layers |
| 24 | ADR Decision Timeline | timeline | Chronological timeline of all 34 ADRs from ADR-001 to ADR-034 showing evolution of architecture |
| 25 | ADR Category Distribution | pie | ADR distribution: Storage, Pipeline, Observability, Configuration, Naming, Security, Resilience categories |
| 26 | Single Instance Policy Enforcement | flowchart | How MemoryLock prevents multiple pipeline instances — lock key generation, TTL, heartbeat validation |
| 27 | Dependency Injection Flow — Constructor Injection Pattern | sequenceDiagram | Sequence showing Composition creating adapters then injecting them into Application services via constructor |
| 28 | Import Linter Configuration and Enforcement | flowchart | How import-linter rules map to ARCH-001 matrix and block PRs on violations |
| 29 | GenericPipelineFactory Declarative Registration | flowchart | How pipeline-factories.py declares provider/entity/transformer/schema → factory auto-generates pipeline |
| 30 | Runtime Assembly Sequence — bootstrap/runtime/assembly.py | sequenceDiagram | Step-by-step assembly: create logger → create storage → create HTTP client → create adapter → create services → create runner |
| 31 | DataSourceRegistry Lookup Flow | flowchart | Registry.get(provider) → creator function → adapter instantiation with HTTP client, rate limiter, circuit breaker |
| 32 | StorageFactory Assembly — Bronze + Silver + Gold Writers | flowchart | StorageFactory combining BronzeWriter, SilverWriter, GoldWriter into unified StoragePort implementation |
| 33 | HttpClientFactory Configuration Per Provider | flowchart | HttpClientFactory creating UnifiedHTTPClient with provider-specific rate limits, timeouts, circuit breaker thresholds |
| 34 | TransformerFactory Registration and Resolution | flowchart | register-transformer() / create-transformer() flow with provider→entity→class mapping |
| 35 | Pipeline Name Convention Resolution | flowchart | {provider}-{entity} → config path, storage paths, lock keys, checkpoint file — all derived from naming |
| 36 | ProviderRegistry vs DataSourceRegistry Relationship | classDiagram | ProviderRegistry as primary, DataSourceRegistry as backward-compatible facade, delegation pattern |
| 37 | CLI Entry Point to Pipeline Execution Full Chain | flowchart | click command → parse args → bootstrap → assemble → runner.run() → finalize → exit code |
| 38 | Health Server HTTP Endpoints Architecture | flowchart | /health (liveness), /ready (readiness with storage + lock checks), /metrics (Prometheus scrape) |
| 39 | Makefile Commands Architecture | flowchart | make install, make test, make lint, make run-local, make quarantine-inspect — full command map |
| 40 | Pre-commit Hook Pipeline | flowchart | ruff → mypy → import-linter → security scan → terminology lint → commit |
| 41 | CI/CD Pipeline Architecture | flowchart | Push → lint → type-check → unit tests → integration tests (VCR) → architecture tests → coverage gate → deploy |
| 42 | Python Package Structure — pyproject.toml Groups | flowchart | Base deps → [tests] group → [dev] group → [tracing] group → [docs] group with dependency relationships |
| 43 | Domain Types Enum Hierarchy | classDiagram | HealthStatus, RunType, SilverWriteMode, GoldWriteMode, EntityType, LoadingStrategy enum classes and their values |
| 44 | Exception Hierarchy Full Tree | classDiagram | BioETLError → NetworkError, ValidationError, StorageError, ConfigError, LockError with all subclasses |
| 45 | Medallion Architecture Invariants | flowchart | REBUILD→clear both, BACKFILL→clear both, INCREMENTAL→clear neither — enforcement via MedallionLifecycleService |
| 46 | Convention-Based Path Resolution | flowchart | From pipeline-name=chembl-activity → auto-computed source, dq, filter, sink paths without explicit config |
| 47 | Architecture Principles Mind Map | mindmap | Central: Hexagonal Architecture → Ports&Adapters, DI, Medallion, DDD Aggregates, Composition Root, Local-Only |
| 48 | RULES.md Section Dependency Graph | flowchart | How RULES.md sections cross-reference: §1→§2 (layers→data flow), §3 (errors), §4 (code), §5 (ops) |
| 49 | BasePipeline Decomposition (ADR-020) | flowchart | Original monolith → decomposed: BatchExecutor, BatchTransformer, BatchWriter, PreflightService, PostrunService |
| 50 | Five-Layer Architecture With Allowed Dependencies | block-beta | Visual block diagram showing 5 layers stacked with arrows only for allowed dependency directions |
| 51 | Composition Bootstrap — Composite vs Standard Pipeline | flowchart | Decision: is composite? → bootstrap-composite-runner() : bootstrap-pipeline() with different wiring |
| 52 | Interface Layer — CLI vs HTTP Server Boundary | flowchart | CLI (click commands) for batch execution, HTTP server for health/metrics — two interface types |
| 53 | Domain Ports Grouped By Concern | mindmap | Ports organized: Data (DataSource, Storage), Coordination (Lock, Checkpoint), Observability (Logger, Metrics, Tracing), Quality (Validation, Quarantine, DQ), Resilience (CircuitBreaker, HealthCheck) |
| 54 | Infrastructure Adapter Inheritance Hierarchy | classDiagram | BaseHttpAdapter → ChemblAdapter, UniProtAdapter, CrossRefAdapter, OpenAlexAdapter; BaseSyncAdapter → PubChemAdapter |
| 55 | Storage Writer Inheritance Hierarchy | classDiagram | BaseDeltaWriter → SilverWriter, GoldWriter; BronzeWriter (standalone); DeltaReader (standalone) |
| 56 | Application Core Component Collaboration | flowchart | PipelineRunner orchestrates LockManager, PreflightService, BatchExecutor, PostrunService, CheckpointManager |
| 57 | Transformer DI Pattern — Template Method with Injection | flowchart | BaseTransformer (abstract -transform-impl) → BaseChemblTransformer → ActivityTransformer injected into BatchTransformer |
| 58 | Factory Method vs Abstract Factory in Composition | flowchart | GenericPipelineFactory (Factory Method) vs HttpClientFactory (Abstract Factory) usage comparison |
| 59 | Service Locator Anti-Pattern vs Constructor Injection | flowchart | Why ServiceLocator/Container.resolve is forbidden (DI-003) vs proper constructor injection pattern |
| 60 | Architecture Quality Gate Checks | flowchart | mypy --strict → import-linter → pytest tests/architecture/ → coverage ≥85% — all must pass for merge |

## DataFlow (61–120)

| # | Name | Type | Description |
|---|------|------|-------------|
| 61 | ChEMBL Activity Bronze→Silver Transformation Including Field Mapping and Content Hash | sequenceDiagram | Detailed sequence: raw JSON → ActivityTransformer.-transform-impl() → normalize values → compute hash → Silver DataFrame |
| 62 | ChEMBL Molecule Bronze→Silver Field Mapping | flowchart | Raw molecule JSON fields → MoleculeTransformer mapping → Silver columns with type coercions and null handling |
| 63 | PubChem Compound Bronze→Silver Transformation Flow | sequenceDiagram | pubchempy response → PubChemCompoundTransformer → normalize CID, SMILES, InChI → Silver write |
| 64 | UniProt Protein Bronze→Silver Data Normalization | flowchart | UniProt XML/JSON → UniProtProteinTransformer → sequence extraction, organism mapping → Silver table |
| 65 | PubMed Publication Bronze→Silver Metadata Extraction | flowchart | E-utilities XML → PubMedPublicationTransformer → title, authors, abstract, MeSH terms → Silver |
| 66 | CrossRef Publication Bronze→Silver DOI Resolution | flowchart | CrossRef /works response → CrossRefPublicationTransformer → DOI, title, ISSN, citation count → Silver |
| 67 | OpenAlex Publication Bronze→Silver Enrichment | flowchart | OpenAlex response → OpenAlexPublicationTransformer → concepts, institutions, cited-by-count → Silver |
| 68 | SemanticScholar Publication Bronze→Silver Processing | flowchart | S2 API response → SemanticScholarPublicationTransformer → paper-id, tldr, embedding → Silver |
| 69 | Content Hash Calculation Pipeline | flowchart | Raw record → exclude META-FIELDS → canonical JSON → NaN/Inf→null, floats→round(10), dates→ISO → sha256 |
| 70 | Bronze Write Atomic Operation Detail | sequenceDiagram | BronzeWriter: create temp file → write JSONL → zstd compress → compute checksum → atomic rename → update manifest |
| 71 | Silver Merge/Upsert Decision Logic | flowchart | SilverWriter: check write-mode → MERGE: upsert by PK → APPEND: insert → DELETE: truncate+insert |
| 72 | Gold Write Mode Selection — OVERWRITE vs SCD2 vs APPEND | flowchart | GoldWriter: check gold-write-mode → OVERWRITE: full replace → SCD2: history tracking → APPEND: partition add |
| 73 | SCD Type 2 Record Versioning in Gold | sequenceDiagram | Existing Gold record + updated Silver record → compare content-hash → create new version with valid-from/valid-to |
| 74 | Data Lineage Tracking — Bronze batch-id to Silver -source-batch-id | flowchart | Bronze file → batch-id generated → passed through transform → stored as -source-batch-id in Silver → lineage-log entry |
| 75 | Quarantine Record Creation and Routing | sequenceDiagram | Pandera validation fail → QuarantineEntry created → payload truncated to 64KB → payload-hash computed → write to quarantine table |
| 76 | DQ Metrics Calculation Per Batch | flowchart | Batch records → null-rate per column, unique-count, schema-violations → DQMetrics value object → Prometheus export |
| 77 | Schema Drift Detection Flow | flowchart | Incoming record → compare with expected schema → new fields: Info → missing required: Critical → SLA 48h owner assignment |
| 78 | Record Processing Pipeline — Single Record Journey | flowchart | API response → Bronze JSONL → RecordProcessor.process() → transform → validate → route (Silver or Quarantine) → Gold |
| 79 | Batch Processing Flow — Extract to Write | sequenceDiagram | BatchExecutor: fetch-batch() → BatchTransformer.transform() → validate() → BatchWriter.write() → update metrics |
| 80 | Metadata Fields Injection Timeline | flowchart | PipelineContext.started-at → -ingestion-ts; RunContext → -run-id, -run-type; BatchID → -source-batch-id; HashService → -content-hash |
| 81 | NULL Handling Strategy Per Layer | flowchart | Source missing value → Bronze: as-is → Silver: explicit NULL with nullable=True → Gold: NaN for nullable ints |
| 82 | Int→Float Coercion Path for Nullable Integers | flowchart | Domain: Series[int] → Silver: pa.int64() → Gold: Series[float]+coerce=True → downstream: handle NaN as missing |
| 83 | Bronze File Naming Convention and Path Structure | flowchart | bronze/{provider}/{entity}/{YYYY-MM-DD}/batch-{NNN}.jsonl.zst + -manifest.json with checksums |
| 84 | Silver Delta Lake Table Structure | flowchart | silver/{provider}/{entity}/ → -delta-log/ (transaction log) + parquet data files + partition dirs |
| 85 | Gold Delta Lake Table Structure with Partitioning | flowchart | gold/{provider}/{entity}/ → optional partition-by columns → -delta-log/ + data files |
| 86 | Checkpoint Save and Restore Flow | sequenceDiagram | Pipeline: save-checkpoint(last-id, batch-num) → JSON file → restart: load-checkpoint() → resume from last-id+1 |
| 87 | Data Freshness Monitoring Pipeline | flowchart | Gold table → max(updated-at) → now() - max → data-freshness-seconds metric → alert if >24h (warning) or >72h (critical) |
| 88 | Backfill Data Flow — Full Reload Path | flowchart | CLI --run-type=backfill → acquire exclusive lock → clear Silver+Gold → full API fetch → Bronze → Silver → Gold |
| 89 | Incremental Data Flow — Delta Update Path | flowchart | CLI --run-type=incremental → standard lock → load watermark → fetch since watermark → Bronze append → Silver merge → Gold merge |
| 90 | Rebuild Data Flow — Clean Slate Path | flowchart | CLI --run-type=rebuild → acquire exclusive lock → clear all layers → full extraction → rebuild all layers |
| 91 | Cross-Provider Data Enrichment Flow — Publication | flowchart | ChEMBL document → extract DOIs/PMIDs → fan-out to CrossRef+PubMed+OpenAlex+SemanticScholar → merge into Gold |
| 92 | Filtered Data Source — ID-Based Extraction | flowchart | FilteredDataSource: load filter-ids from file → deduplicate → chunk into batches → DataSourcePort.fetch(filter-ids=chunk) |
| 93 | ID Mapping Data Source — UniProt Cross-References | flowchart | IDMappingDataSource: submit ID mapping job → poll status → download results → yield mapped records |
| 94 | Bronze Cleanup Flow — Retention Policy | flowchart | CleanupService: scan bronze dirs → check age against 90-day retention → delete expired → log cleanup stats |
| 95 | Delta Lake VACUUM Execution Flow | flowchart | PostrunService → SilverWriter.vacuum(retention=7d) → GoldWriter.vacuum(retention=7d) → log stats |
| 96 | Batch Size Adaptive Calculation | flowchart | Provider health status → HEALTHY: full batch-size → DEGRADED: batch-size/2 → UNHEALTHY: pause pipeline |
| 97 | Sort-Before-Write Pipeline for Deterministic Output | flowchart | DataFrame → sort by primary-keys (Silver) or business-keys (Gold) → then write to Delta Lake → deterministic file content |
| 98 | Gold Schema Validation Pipeline (ADR-018) | flowchart | Silver records → transform-for-gold() → exclude JSON fields → Pandera strict=True validation → write or fail batch |
| 99 | JSONL+Zstd Compression Pipeline in BronzeWriter | sequenceDiagram | Records → json.dumps per record → join with newlines → zstd.compress() → write temp file → rename to final |
| 100 | Manifest File Generation for Bronze Batches | flowchart | After batch write → compute file hash → record file-path, size, record-count, checksum → write -manifest.json |
| 101 | ChEMBL Target→TargetComponent→ProteinClass Chained Data Flow | flowchart | Target entity → extract component-ids → fetch target-components → extract protein-class-ids → fetch protein-classes |
| 102 | Publication Composite — Seed DOI Extraction | flowchart | ChEMBL document Silver table → extract DOI and PMID columns → deduplicate → create enrichment key lists |
| 103 | Publication Composite — CrossRef Enrichment Path | sequenceDiagram | Key list (DOIs) → CrossRefAdapter.fetch(filter-ids=DOIs) → Bronze → CrossRefTransformer → Silver |
| 104 | Publication Composite — Merge All Sources | flowchart | Seed Silver + CrossRef Silver + PubMed Silver + OpenAlex Silver + S2 Silver → MergeService LEFT OUTER JOIN → Gold |
| 105 | Column Group Ordering in Gold Output | flowchart | FieldGroupRegistry: ID-AND-STATUS → BIBLIOGRAPHY → AUTHOR → TERMS → CITATIONS → DATES → PUB-TYPES; TRASH excluded |
| 106 | Qualified Column Naming — preserve-all-sources=true | flowchart | Base field "title" → chembl.publication.title, crossref.publication.title, openalex.publication.title |
| 107 | Coalesce Conflict Resolution Strategy | flowchart | Multiple source values for same field → iterate by provider-order → take first non-null → write single column |
| 108 | Silver Rename Chain — Original→Silver→Gold Column Names | flowchart | entity-id → document-id (Silver rename) → publication-id (Gold rename) — chain resolution |
| 109 | DQ Flag Routing Decision Tree | flowchart | Record → validate → all pass: clean → warning <5%: -dq-warn=true → error: quarantine → >20% errors: batch fail |
| 110 | Bronze→Silver→Gold Complete Transformation for ChEMBL Assay | flowchart | Assay JSON → AssayTransformer → normalize assay-type, confidence-score → Silver → Gold (strict validation) |
| 111 | Target Entity Full Data Flow — ChEMBL and UniProt Sources | flowchart | ChEMBL /target API → Bronze → TargetTransformer → Silver | UniProt /protein API → Bronze → UniProtTransformer → Silver → Cross-reference |
| 112 | Cell Line Entity Data Flow | flowchart | ChEMBL /cell-line → Bronze → CellLineTransformer → cell-chembl-id, cell-name, organism → Silver → Gold |
| 113 | Compound Record Entity Data Flow | flowchart | ChEMBL /compound-record → Bronze → CompoundRecordTransformer → molecule-document linkage → Silver |
| 114 | Tissue Entity Data Flow | flowchart | ChEMBL /tissue → Bronze → TissueTransformer → tissue-chembl-id, pref-name, BTO → Silver |
| 115 | Subcellular Fraction Entity Data Flow | flowchart | ChEMBL → Bronze → SubcellularFractionTransformer → GO terms, cellular component → Silver |
| 116 | Assay Parameters Entity Data Flow | flowchart | ChEMBL /assay → parameters extraction → AssayParametersTransformer → parameter-type, value → Silver |
| 117 | Watermark-Based vs Full-Scan Loading Strategy | flowchart | LoadingStrategy enum → WATERMARK-BASED: use last checkpoint → FULL-SCAN-ONLY: ignore watermark, fetch all |
| 118 | Partition Strategy Per Medallion Layer | flowchart | Bronze: by ingestion-date → Silver: by source-date or entity-type → Gold: by business key or date |
| 119 | Data Quality Anomaly Detection Baseline | flowchart | Days 1-7: silence (training) → Days 8-30: warning only → Days 30+: full alerting with z-score thresholds |
| 120 | Duplicate Detection via Content Hash in Silver Upsert | sequenceDiagram | New record → compute content-hash → check existing by entity-id → same hash: skip → different hash: upsert new version |

## Pattern (121–170)

| # | Name | Type | Description |
|---|------|------|-------------|
| 121 | Template Method Pattern — BaseTransformer.-transform-impl() | classDiagram | BaseTransformer defines transform() skeleton; subclasses override -transform-impl() for provider-specific logic |
| 122 | Null Object Pattern — NoOpMetrics and NoOpTracing | classDiagram | MetricsPort/TracingPort → NoOpMetrics/NoOpTracing implementations that silently accept all calls |
| 123 | Strategy Pattern — SilverWriteMode Selection | classDiagram | SilverWriter uses SilverWriteMode enum (MERGE, APPEND, DELETE) to select write strategy at runtime |
| 124 | Strategy Pattern — GoldWriteMode Selection | classDiagram | GoldWriter uses GoldWriteMode enum (OVERWRITE, APPEND, SCD2) to select gold output strategy |
| 125 | Strategy Pattern — Conflict Resolution in Merge | classDiagram | MergeService uses ConflictResolution enum (seed-priority, enricher-priority, coalesce, explicit-rules) |
| 126 | Observer Pattern — PipelineObserver Lifecycle Events | sequenceDiagram | PipelineRunner → PipelineObserver.enter() → metrics.started → execute → PipelineObserver.exit() → metrics.completed |
| 127 | Facade Pattern — domain.ports.--init--.py Re-exports | flowchart | All 24 port protocols re-exported from domain.ports facade → enforced by ARCH-008 |
| 128 | Builder Pattern — ServicesBuilder for PipelineServices | sequenceDiagram | ServicesBuilder.with-storage().with-lock().with-logger().with-metrics().build() → frozen PipelineServices |
| 129 | Registry Pattern — ProviderRegistry and DataSourceRegistry | classDiagram | ProviderRegistry stores provider→config mapping; DataSourceRegistry is legacy facade delegating to ProviderRegistry |
| 130 | Frozen Dataclass Pattern — Immutable Configuration Objects | classDiagram | PipelineConfig, RuntimeConfig, DQConfig, CompositeConfig — all @dataclass(frozen=True) for thread safety |
| 131 | Mixin Pattern — PaginatedFetcherMixin for HTTP Adapters | classDiagram | PaginatedFetcherMixin provides pagination logic; mixed into UniProtAdapter, CrossRefAdapter, OpenAlexAdapter, SemanticScholarAdapter |
| 132 | Mixin Pattern — NotSupportedMultiFilterMixin for PubChem | classDiagram | NotSupportedMultiFilterMixin raises error for unsupported multi-ID filter operations |
| 133 | Token Bucket Pattern — Rate Limiting Implementation | stateDiagram | TokenBucket states: tokens-available → consume-token → check-refill → wait-if-empty → tokens-available |
| 134 | Decorator Pattern — FilteredDataSource Wrapping DataSourcePort | classDiagram | FilteredDataSource wraps DataSourcePort, adds filter-ids logic, delegates fetch() to inner source |
| 135 | Aggregate Pattern (DDD) — PipelineRun as Aggregate Root | classDiagram | PipelineRun aggregate: root entity with Batch children, QuarantineEntry children, domain events |
| 136 | Value Object Pattern — Activity, DQMetrics, RunContext | classDiagram | Frozen dataclass value objects: Activity (pchembl-value, standard-value), DQMetrics, RunContext — equality by value |
| 137 | Domain Event Pattern — PipelineStarted, BatchCompleted, PipelineFailed Events | classDiagram | DomainEvent base → PipelineStarted, BatchCompleted, PipelineFailed with timestamps and metadata |
| 138 | Context Manager Pattern — PipelineServices async with | sequenceDiagram | async with services → --aenter--: init resources → yield → --aexit--: aclose() all components |
| 139 | Fencing Token Pattern — owner-id in MemoryLock | sequenceDiagram | Lock acquire with owner-id → heartbeat validates owner-id → write validates owner-id → prevents split-brain |
| 140 | Circuit Breaker Pattern — State Transitions Detail | stateDiagram | CLOSED→(5 failures)→OPEN→(5 min timeout)→HALF-OPEN→(success)→CLOSED, (failure)→OPEN |
| 141 | Retry with Exponential Backoff Pattern | flowchart | Attempt 1 → fail → wait 1s+jitter → Attempt 2 → fail → wait 2s+jitter → Attempt 3 → fail → give up |
| 142 | Deterministic Jitter Calculation via MD5 Hash | flowchart | Input: attempt+url+seed → MD5 hash → take first 8 hex chars → normalize to [0,1] → multiply by max-jitter |
| 143 | Safety Guard Pattern — Lock Validation Before Write | sequenceDiagram | Before Silver write → validate lock still held → if not held → abort (no partial write) → if held → proceed |
| 144 | Idempotent Write Pattern — Content Hash Deduplication | flowchart | Compute content-hash → query Silver by entity-id → same hash exists: skip → different: upsert → guarantees idempotency |
| 145 | At-Least-Once Delivery + Silver Deduplication | flowchart | Network retry → possible duplicate Bronze writes → Silver merge by content-hash → exactly-once semantics at Silver |
| 146 | Atomic Rename Pattern — Bronze File Write Safety | sequenceDiagram | Write to temp-file.tmp → fsync → rename temp-file.tmp → final-file.jsonl.zst → atomic visibility |
| 147 | Composition Root Pattern — Assembly.py as Single Wiring Point | flowchart | All object creation happens in composition/ → application and domain never create concrete implementations |
| 148 | Double-Check Locking — Metrics Server Startup Idempotency | flowchart | Check if metrics started → if not: acquire lock → check again → if still not: start server → release lock |
| 149 | Graceful Degradation Pattern — Missing DQ Config | flowchart | Load DQ config → file exists: apply rules → file missing: log warning → continue without DQ validation → no crash |
| 150 | Backward Compatibility Re-export Pattern | classDiagram | application/core/medallion-policy.py re-exports from domain/policies for backward compatibility — 19 LOC shim |
| 151 | Protocol-Based Structural Subtyping | classDiagram | DataSourcePort(Protocol) → ChemblAdapter satisfies via structural subtyping (duck typing) — no explicit inheritance |
| 152 | Runtime Checkable Protocol for Boundary Validation | flowchart | @runtime-checkable on DataSourcePort → isinstance(adapter, DataSourcePort) check in composition layer |
| 153 | Frozen Bundle Pattern — PipelineServices as Immutable DI Container | classDiagram | PipelineServices frozen dataclass: all ports as fields, no mutation after creation, passed through call chain |
| 154 | Heartbeat Renewal Pattern for Lock TTL Extension | sequenceDiagram | Heartbeat timer fires every 30s → MemoryLock.renew(owner-id) → extends TTL by 90s → prevents expiration during long batches |
| 155 | Fan-Out/Fan-In Pattern — Composite Pipeline Enrichment | flowchart | Seed → extract keys → fan-out to N enrichers (asyncio.gather) → collect results → fan-in via MergeService |
| 156 | Canonical JSON Serialization for Hash Stability | flowchart | Record → sort-keys=True → separators=(',',':') → ensure-ascii=True → round floats → NaN→null → stable hash input |
| 157 | Error Classification Strategy Pattern | flowchart | ErrorClassifier: HTTP status → Critical (401, schema) vs Recoverable (429, 502) vs DataQuality (invalid SMILES) |
| 158 | Layered Validation Strategy (5 Levels) | flowchart | Level 1: Base (Pandera) → Level 2: Structural (cross-field) → Level 3: External (API verify) → Level 4: Logical (ranges) → Level 5: Semantic (NLP) |
| 159 | Threshold-Based Batch Failure Pattern | flowchart | Count errors per batch → <5%: warn → 5-20%: alert → >20%: fail entire batch → circuit breaker may trip |
| 160 | Entity Mapper Pattern — ChEMBL entity-type to API Resource | flowchart | EntityMapper: entity-type="activity" → resource="activity", entity-type="compound" → resource="molecule" |
| 161 | Async Context Manager Pattern — Resource Lifecycle | sequenceDiagram | async with resource → --aenter--: open connection → use resource → --aexit--: close connection (idempotent) |
| 162 | Convention Over Configuration — Auto-Computed Paths | flowchart | pipeline-name → split provider-entity → derive: source-file, dq-config, filter-config, sink paths |
| 163 | Schema-Domain Configuration Pairs (ADR-034) | classDiagram | Each domain entity paired with its Pandera schema: Activity↔ActivitySchema, Molecule↔MoleculeSchema |
| 164 | Output Metadata Unification Pattern (ADR-029) | classDiagram | BaseOutputMetadata → BronzeOutputMetadata, SilverOutputMetadata, GoldOutputMetadata — unified contract |
| 165 | Column Filter Pattern — Gold Layer Field Exclusion | flowchart | Gold record → check FieldGroupRegistry → TRASH group fields → exclude from output → write only business columns |
| 166 | Loading Strategy Formalization (ADR-031) | stateDiagram | LoadingStrategy.FULL-SCAN-ONLY → always full load | WATERMARK-BASED → incremental when watermark available, else full |
| 167 | Publication Pagination Strategy (ADR-030) | flowchart | PubMed: E-utilities retstart/retmax → CrossRef: cursor-based → OpenAlex: per-page → S2: token-based |
| 168 | DQ Rules Externalization (ADR-027) | flowchart | Inline Python DQ rules → extracted to configs/quality/entities/{provider}/{entity}.yaml → loaded by DQConfigLoader |
| 169 | Filter Rules Externalization (ADR-028) | flowchart | Inline filter logic → extracted to configs/filters/entities/{provider}/{entity}.yaml → loaded by FilterConfigLoader |
| 170 | Pipeline Config Unification (ADR-025) | flowchart | Per-provider configs → unified schema: pipeline-name, provider, entity-type, sink, dq-overrides → validated by Pydantic |

## Component (171–220)

| # | Name | Type | Description |
|---|------|------|-------------|
| 171 | PipelineRunner Internal Component Diagram | classDiagram | PipelineRunner with -lock-manager, -preflight, -batch-executor, -postrun, -checkpoint, -observer — all injected |
| 172 | BatchExecutor Internal Structure — 786 LOC Decomposition | classDiagram | BatchExecutor with -transformer, -writer, -metrics-recorder, -tracing-manager methods: execute-batch(), -extract(), -transform(), -write() |
| 173 | BatchTransformer Component — Transform Orchestration | classDiagram | BatchTransformer coordinates: BaseTransformer, DataNormalizationService, IdentityService for each batch |
| 174 | BatchWriter Component — Medallion Write Orchestration | classDiagram | BatchWriter with -bronze-writer, -silver-writer, -gold-writer, -quarantine — writes to all layers per batch |
| 175 | PreflightService Component — 818 LOC with 21 Methods | classDiagram | PreflightService: check-config(), check-storage(), check-data-source(), check-lock(), check-health() — single responsibility: pre-run validation |
| 176 | PostrunService Component — Cleanup and Finalization | classDiagram | PostrunService: run-dq-checks(), execute-vacuum(), write-dq-report(), cleanup-temp-files(), publish-final-metrics() |
| 177 | LockManager Component — Lock Lifecycle Coordination | classDiagram | LockManager wraps LockPort: acquire-with-timeout(), release-safely(), validate-ownership(), generate-lock-key() |
| 178 | CheckpointManager Component — State Persistence | classDiagram | CheckpointManager: save(last-id, batch-num), load() → CheckpointState, delete(), exists(), is-stale() |
| 179 | QuarantineManager Component — Failed Record Handling | classDiagram | QuarantineManager: route-failed-records(), create-entry(), compute-payload-hash(), truncate-payload(64KB) |
| 180 | HeartbeatTask Component — TTL Renewal Worker | classDiagram | HeartbeatTask: start(), stop(), -heartbeat-loop() — async task running every 30s to renew lock TTL |
| 181 | ShutdownHandler Component — Signal Handling | classDiagram | ShutdownHandler: register-signals(), handle-sigterm(), handle-sigint(), is-shutting-down(), wait-for-current-batch() |
| 182 | CleanupService Component — Bronze Retention | classDiagram | CleanupService: cleanup-expired-bronze(retention-days=90), scan-directories(), delete-old-batches(), log-cleanup-stats() |
| 183 | FilteredDataSource Component — ID Filter Wrapper | classDiagram | FilteredDataSource wrapping DataSourcePort: load-filter-ids(), deduplicate-ids(), chunk-ids(), fetch-filtered() |
| 184 | UnifiedHTTPClient Component — Full Internal Architecture | classDiagram | UnifiedHTTPClient: -httpx-client, -rate-limiter(TokenBucket), -circuit-breaker, -retry-config, -metrics methods: get(), post(), health-check() |
| 185 | TokenBucket Component — Rate Limiting Algorithm | classDiagram | TokenBucket: -capacity, -tokens, -refill-rate, -last-refill methods: acquire(), try-acquire(), -refill(), wait-for-token() |
| 186 | CircuitBreaker Component — State Machine Implementation | classDiagram | CircuitBreaker: -state(CLOSED/OPEN/HALF-OPEN), -failure-count, -last-failure-time, -recovery-timeout methods: call(), record-success(), record-failure(), -check-state() |
| 187 | HealthMonitor Component — Provider Health Tracking | classDiagram | HealthMonitor: -provider-states(dict), -error-counts methods: record-result(), get-status(), update-health(), calculate-adaptive-params() |
| 188 | PaginatedFetcherMixin Component — Generic Pagination | classDiagram | PaginatedFetcherMixin: -fetch-page(), -extract-next-cursor(), -has-more-pages(), fetch() async generator yielding pages |
| 189 | BronzeWriter Internal Structure | classDiagram | BronzeWriter: -base-path, -compressor methods: write-bronze(), -create-batch-file(), -write-jsonl(), -compress-zstd(), -write-manifest() |
| 190 | SilverWriter Internal Structure | classDiagram | SilverWriter(BaseDeltaWriter): -table-path, -primary-keys methods: write-silver(), -merge-upsert(), -append(), -delete-and-insert(), vacuum() |
| 191 | GoldWriter Internal Structure — 946 LOC | classDiagram | GoldWriter(BaseDeltaWriter): -csv-exporter, -audit-port methods: write-gold(), -overwrite(), -scd2(), -append(), -validate-strict(), export-csv() |
| 192 | BaseDeltaWriter Internal Structure | classDiagram | BaseDeltaWriter: -table-uri, -arrow-converter methods: -write-delta(), -read-delta(), -get-schema(), -sort-dataframe(), vacuum() |
| 193 | DeltaReader Component — Query Interface | classDiagram | DeltaReader: read-table(), read-with-filter(), get-table-info(), list-partitions(), get-schema(), count-rows() |
| 194 | MetadataWriter Component — Output Metadata | classDiagram | MetadataWriter: write-metadata(), build-metadata(), -compute-stats() for each medallion layer output |
| 195 | RetentionManager Component — Data Lifecycle | classDiagram | RetentionManager: enforce-retention(), -check-bronze-age(), -check-quarantine-age(), -vacuum-delta-tables() |
| 196 | MemoryLock Internal State Machine | classDiagram | MemoryLock: -locks(dict), -owners(dict), -ttls(dict) methods: acquire(), release(), renew(), is-locked(), validate-owner() |
| 197 | LocalCheckpoint Component — File-Based State | classDiagram | LocalCheckpoint: -checkpoint-dir methods: save(), load(), delete(), exists(), -read-json(), -write-json-atomic() |
| 198 | UnifiedQuarantine Component | classDiagram | UnifiedQuarantine: -base-path methods: write(), read-sample(), count(), purge(), replay(), -build-entry() |
| 199 | StructlogLogger Component — LoggerPort Implementation | classDiagram | StructlogLogger implementing LoggerPort: info(), warning(), error(), debug(), bind(), unbind() — JSON output |
| 200 | PrometheusMetrics Component — MetricsPort Implementation | classDiagram | PrometheusMetrics: -counters, -histograms, -gauges methods: increment-counter(), observe-histogram(), set-gauge(), start-server() |
| 201 | NoOpTracing Component — TracingPort Null Object | classDiagram | NoOpTracing: get-tracer()→NoOpTracer, start-span()→NoOpSpan — all methods are no-ops, zero overhead |
| 202 | PanderaValidator Component — ValidationPort Implementation | classDiagram | PanderaValidator: validate-silver(), validate-gold(), -apply-schema(), -collect-errors(), -build-report() |
| 203 | PIIHasher Component — SecurityPort Implementation | classDiagram | PIIHasher: hash-field(), hash-email(), hash-name(), -sha256-with-salt() — RULES.md §5.4 compliance |
| 204 | PipelineConfigLoader Component — YAML to Domain Config | classDiagram | PipelineConfigLoader: load(), -resolve-paths(), -merge-base(), -validate(), -apply-defaults() → PipelineConfig |
| 205 | DQConfigLoader Component — DQ Rules from YAML | classDiagram | DQConfigLoader: load(), -parse-field-validations(), -parse-thresholds(), -merge-overrides() → DQConfig |
| 206 | FilterConfigLoader Component — Filter Rules from YAML | classDiagram | FilterConfigLoader: load(), -parse-column-filters(), -parse-row-filters() → FilterConfig |
| 207 | GenericPipelineFactory Component | classDiagram | GenericPipelineFactory: -pipeline-name, -pipeline-class, -transformer-class, -gold-schema methods: create(), -assemble-pipeline() |
| 208 | RunnerFactory Component | classDiagram | RunnerFactory: create-runner() → PipelineRunner with all services injected via ServicesFactory |
| 209 | ServicesFactory/ServicesBuilder Component | classDiagram | ServicesBuilder: progressive builder → creates PipelineServices bundle with all required and optional ports |
| 210 | StorageFactory Component | classDiagram | StorageFactory: create() → StoragePort from BronzeWriter + SilverWriter + GoldWriter + config |
| 211 | HttpClientFactory Component | classDiagram | HttpClientFactory: create(provider) → UnifiedHTTPClient configured with provider-specific rate limits and circuit breaker |
| 212 | DataSourceFactory Component | classDiagram | DataSourceFactory: create(provider, config) → DataSourcePort implementation for the given provider |
| 213 | DQServicesFactory Component | classDiagram | DQServicesFactory: create() → DQ analyzers (Bronze, Silver, Gold), DQ monitor, DQ report writer, DQ report service |
| 214 | EnrichmentCoordinator Component | classDiagram | EnrichmentCoordinator: run-enrichers() → asyncio.gather(enricher1, enricher2, ...) with timeout per enricher |
| 215 | MergeService Component | classDiagram | MergeService: merge() → LEFT OUTER JOIN seed+enrichers, conflict-resolution, column-ordering, trash-filtering |
| 216 | CompositePipelineRunner Component | classDiagram | CompositePipelineRunner: run() → seed-pipeline → dependency-pipelines → enrichment-coordinator → merge-service → gold-write |
| 217 | KeyExtractorService Component | classDiagram | KeyExtractorService: extract-keys(seed-silver-table, join-keys) → list of key values for enricher filtering |
| 218 | DependencyCoordinator Component | classDiagram | DependencyCoordinator: run-dependencies() → sequential execution of dependency pipelines with chained key extraction |
| 219 | CrossValidator Component — Composite Data Quality | classDiagram | CrossValidator: validate-merge() → check join coverage, detect orphan records, verify merge completeness |
| 220 | AnomalyDetector Component — DQ Anomaly Detection | classDiagram | AnomalyDetector: detect() → z-score calculation vs 30-day baseline, severity classification, alert generation |

## Interaction (221–270)

| # | Name | Type | Description |
|---|------|------|-------------|
| 221 | CLI Run Command → PipelineRunner Full Interaction | sequenceDiagram | CLI run → parse args → load config → bootstrap-pipeline → runner.run() → observer → executor → finalize |
| 222 | CLI Run-All Command — Sequential Multi-Pipeline Execution | sequenceDiagram | CLI run-all → iterate pipeline-names → for each: bootstrap → run → report → aggregate results |
| 223 | CLI Run-Composite Command — Composite Pipeline Invocation | sequenceDiagram | CLI run-composite → load CompositeConfig → bootstrap-composite-runner → seed → enrich → merge → report |
| 224 | CLI Health Command — Provider Health Check Aggregation | sequenceDiagram | CLI health → for each provider: create adapter → health-check() → collect statuses → display table |
| 225 | CLI Export Command — Gold to CSV Export Flow | sequenceDiagram | CLI export → DeltaReader.read-table(gold) → GoldWriter.export-csv() → write CSV file |
| 226 | CLI Quarantine Inspect — Error Sample Display | sequenceDiagram | CLI quarantine inspect → UnifiedQuarantine.read-sample(pipeline, limit) → format table → display |
| 227 | CLI Quarantine Replay — Reprocess Failed Records | sequenceDiagram | CLI quarantine replay → read entries → re-validate → pass: move to Silver → fail: update status |
| 228 | CLI Maintenance — VACUUM and Cleanup | sequenceDiagram | CLI maintenance → RetentionManager.enforce-retention() → BronzeCleanup → SilverVACUUM → GoldVACUUM |
| 229 | PipelineRunner ↔ LockManager Interaction Detail | sequenceDiagram | Runner: request lock → LockManager: generate key → MemoryLock.acquire(key, owner, ttl) → success/fail → HeartbeatTask.start() |
| 230 | PipelineRunner ↔ PreflightService Interaction | sequenceDiagram | Runner: run-preflight() → Preflight: check-config → check-storage-paths → check-data-source-health → check-lock-availability → report |
| 231 | PipelineRunner ↔ BatchExecutor Interaction | sequenceDiagram | Runner: execute() → BatchExecutor: iterate batches → for each: extract → transform → validate → write → update checkpoint |
| 232 | PipelineRunner ↔ PostrunService Interaction | sequenceDiagram | Runner: run-postrun() → PostrunService: run-dq-checks → vacuum → write-dq-report → cleanup → publish-metrics |
| 233 | BatchExecutor ↔ DataSourcePort Fetch Interaction | sequenceDiagram | BatchExecutor: async for page in data-source.fetch() → create batch → BatchTransformer.transform(batch) → BatchWriter.write() |
| 234 | BatchTransformer ↔ BaseTransformer Interaction | sequenceDiagram | BatchTransformer: transform(batch) → BaseTransformer.transform() → -transform-impl() → normalize → add metadata → hash |
| 235 | BatchWriter ↔ Storage Writers Interaction | sequenceDiagram | BatchWriter: write(batch) → BronzeWriter.write-bronze() → SilverWriter.write-silver() → GoldWriter.write-gold() |
| 236 | BatchWriter ↔ QuarantineManager Interaction | sequenceDiagram | BatchWriter: validate records → failures → QuarantineManager.route-failed-records() → UnifiedQuarantine.write() |
| 237 | DataSourcePort ↔ UnifiedHTTPClient Request Flow | sequenceDiagram | Adapter.fetch() → HTTPClient.get(url, params) → RateLimiter.acquire() → CircuitBreaker.call() → httpx.get() → response |
| 238 | UnifiedHTTPClient ↔ RateLimiter ↔ CircuitBreaker Triple Interaction | sequenceDiagram | HTTPClient: request → RateLimiter.wait() → CircuitBreaker.before-call() → httpx.request() → CircuitBreaker.record-result() → return |
| 239 | CircuitBreaker ↔ HealthMonitor State Sync | sequenceDiagram | CircuitBreaker trips → HealthMonitor.update(UNHEALTHY) → adaptive batch-size reduction → CircuitBreaker recovers → HealthMonitor.update(DEGRADED→HEALTHY) |
| 240 | PipelineObserver ↔ MetricsPort ↔ PrometheusMetrics Chain | sequenceDiagram | Observer.enter() → MetricsPort.increment(started) → PrometheusMetrics.inc(bioetl-pipeline-runs-total) |
| 241 | HeartbeatTask ↔ MemoryLock Renewal Cycle | sequenceDiagram | HeartbeatTask.-loop: sleep(30s) → MemoryLock.renew(key, owner-id) → success: continue → fail: shutdown handler |
| 242 | ShutdownHandler ↔ PipelineRunner Signal Propagation | sequenceDiagram | SIGTERM received → ShutdownHandler.handle() → set -shutting-down=True → BatchExecutor checks flag → finish current batch → save checkpoint → exit(0) |
| 243 | PanderaValidator ↔ Domain Schemas Interaction | sequenceDiagram | Validator.validate-silver(df) → load ActivitySilverSchema → schema.validate(df) → collect errors → return ValidationResult |
| 244 | PIIHasher ↔ SilverWriter PII Processing | sequenceDiagram | SilverWriter.write-silver() → check PII fields → PIIHasher.hash-field(value, salt) → sha256 → replace in DataFrame → write |
| 245 | PipelineConfigLoader ↔ DQConfigLoader ↔ FilterConfigLoader Assembly | sequenceDiagram | PipelineConfigLoader.load() → resolve dq-config-file → DQConfigLoader.load() → resolve filter-config-file → FilterConfigLoader.load() |
| 246 | CompositeRunner ↔ EnrichmentCoordinator Fan-Out | sequenceDiagram | CompositePipelineRunner → EnrichmentCoordinator.run-enrichers([crossref, pubmed, openalex]) → asyncio.gather → collect results |
| 247 | MergeService ↔ FieldGroupRegistry Column Ordering | sequenceDiagram | MergeService.merge() → FieldGroupRegistry.get-ordered-columns() → exclude TRASH → sort by group priority → apply to output |
| 248 | DependencyCoordinator ↔ KeyExtractor Chained Key Flow | sequenceDiagram | DependencyCoordinator: run dep1 → KeyExtractor.extract-keys(dep1-silver) → run dep2(keys-from-dep1) → KeyExtractor.extract-keys(dep2-silver) |
| 249 | CLI ↔ Bootstrap ↔ Factory Triple-Layer Wiring | sequenceDiagram | CLI.run() → entrypoints.bootstrap-pipeline(name, config) → Factories.create-all() → assemble PipelineRunner → return |
| 250 | Bronze→Silver Batch Processing Interaction | sequenceDiagram | Read Bronze JSONL → decompress zstd → parse records → BatchTransformer → validate → SilverWriter.merge-upsert() |
| 251 | Silver→Gold Transformation Interaction | sequenceDiagram | Read Silver Delta → transform-for-gold() → exclude JSON fields → Pandera strict validate → GoldWriter.write() |
| 252 | ErrorClassifier ↔ RetryConfig Decision | sequenceDiagram | HTTP error → ErrorClassifier.classify(status-code) → RECOVERABLE → RetryConfig.calculate-delay(attempt) → wait → retry |
| 253 | ChemblAdapter ↔ EntityMapper URL Construction | sequenceDiagram | ChemblAdapter.fetch(entity-type) → EntityMapper.get-resource-url(entity-type) → build params → HTTPClient.get(url, params) |
| 254 | Provider Adapter Registration in Composition | sequenceDiagram | App startup → registration.py → ProviderRegistry.register("chembl", ChemblAdapter, config) → repeat for all 7 providers |
| 255 | RunType-Based Clear Policy Interaction | sequenceDiagram | Runner: check run-type → REBUILD/BACKFILL: MedallionLifecycle.clear-silver() + clear-gold() → INCREMENTAL: skip clearing |
| 256 | Checkpoint Resume Flow After Shutdown | sequenceDiagram | Pipeline restart → CheckpointManager.load() → found: log "Resuming from X" → BatchExecutor.start-from(checkpoint.last-id + 1) |
| 257 | Data Source Health Check → Pipeline Pause Decision | sequenceDiagram | HealthMonitor.check-all() → provider UNHEALTHY → pause pipeline → wait → re-check → DEGRADED → resume with reduced batch size |
| 258 | Anomaly Detection ↔ Alerting Chain | sequenceDiagram | AnomalyDetector.detect(current-metrics, baseline) → anomaly found → AlertChannel.send(alert) → webhook or logger |
| 259 | BronzeWriter ↔ LineageLog Recording | sequenceDiagram | BronzeWriter.write-bronze() → generate batch-id → record file-paths → write lineage-log entry → return batch-id for Silver FK |
| 260 | Delta Lake Time Travel Query Sequence | sequenceDiagram | DeltaReader.read-table(as-of-version=N) → Delta Log → resolve version N → read only relevant parquet files → return DataFrame |
| 261 | MedallionLifecycleService Clear+Rebuild Sequence | sequenceDiagram | MedallionLifecycle: validate run-type → clear-silver(table) → clear-gold(table) → log cleared → proceed with pipeline |
| 262 | Filtered ID Loading and Deduplication | sequenceDiagram | FilteredDataSource: read filter-file → parse IDs → deduplicate → log stats (loaded, duplicates) → chunk for batched fetch |
| 263 | CompositePipelineRunner Checkpoint Save/Resume | sequenceDiagram | Composite: seed completed → save checkpoint(phase=enrichment) → enricher3 fails → restart → load checkpoint → skip seed → resume enricher3 |
| 264 | GoldWriter SCD2 History Management | sequenceDiagram | New version detected → existing record: set valid-to=now → insert new record: valid-from=now, valid-to=null → Delta merge |
| 265 | Config Inheritance — -base.yaml to Entity Config | sequenceDiagram | Load -base.yaml → load entity.yaml → merge (entity overrides base) → apply dq-overrides → resolve convention paths → final PipelineConfig |
| 266 | Publication Validation Strategy 5-Level Pipeline (ADR-033) | sequenceDiagram | Record → L1:Pandera → L2:CrossField (page-start<page-end) → L3:DOI verify → L4:Year range → L5:Title similarity |
| 267 | Metrics Collection — Request to Prometheus Scrape | sequenceDiagram | Pipeline event → MetricsPort.observe() → PrometheusMetrics.observe-histogram() → /metrics endpoint → Prometheus scrape |
| 268 | Lock Contention Handling — Wait vs Fail | sequenceDiagram | Request lock → already held → check --wait-for-lock → if set: poll with timeout → if not: fail immediately with LockError |
| 269 | Composite Pipeline Cross-Validation After Merge | sequenceDiagram | MergeService.merge() → CrossValidator.validate() → check join rates → check orphans → check coverage → report quality |
| 270 | Deduplication Service in Composite Merge | sequenceDiagram | After merge → DeduplicationService.deduplicate() → identify duplicate DOIs/PMIDs → keep highest-quality source → remove duplicates |

## Lifecycle (271–310)

| # | Name | Type | Description |
|---|------|------|-------------|
| 271 | Pipeline Run Lifecycle — From Config to Completion | stateDiagram | CONFIGURED→LOCKED→PREFLIGHT→EXTRACTING→TRANSFORMING→VALIDATING→LOADING→POSTRUN→COMPLETED or FAILED |
| 272 | Batch Lifecycle States | stateDiagram | CREATED→EXTRACTING→EXTRACTED→TRANSFORMING→TRANSFORMED→VALIDATING→VALIDATED→WRITING→WRITTEN→COMMITTED |
| 273 | Lock Lifecycle States | stateDiagram | AVAILABLE→ACQUIRED(owner-id)→HEARTBEAT-RENEWED→RELEASED or EXPIRED(TTL) or FORCED-RELEASE(max-duration) |
| 274 | Checkpoint Lifecycle | stateDiagram | NONE→CREATED(first-batch)→UPDATED(each-batch)→STALE(detected)→RESUMED(--resume)→DELETED(success) |
| 275 | QuarantineEntry DQ Status Lifecycle | stateDiagram | NEW→UNDER-REVIEW→{IGNORED or REPROCESSED or EXPIRED} with transitions and triggers for each |
| 276 | Provider Health Status Transitions | stateDiagram | HEALTHY→(1-2 errors)→DEGRADED→(≥3 errors)→UNHEALTHY→(1 success)→DEGRADED→(0 errors 5min)→HEALTHY |
| 277 | Circuit Breaker Recovery Cycle Detail | stateDiagram | CLOSED(normal)→(threshold failures)→OPEN(reject all)→(timeout)→HALF-OPEN(probe 1 request)→(success)→CLOSED or (fail)→OPEN |
| 278 | Composite Pipeline Phase Lifecycle | stateDiagram | INIT→SEED-RUNNING→SEED-COMPLETE→DEPS-RUNNING→DEPS-COMPLETE→ENRICHING→ENRICHMENT-DONE→MERGING→MERGED→GOLD-WRITING→DONE |
| 279 | Enricher Lifecycle Within Composite | stateDiagram | PENDING→RUNNING→{COMPLETED or FAILED(timeout) or SKIPPED(not-required)} |
| 280 | Schema Drift Event Lifecycle | stateDiagram | DETECTED→CLASSIFIED(info/critical)→OWNER-ASSIGNED(critical)→{RESOLVED(48h) or BLOCKED(>48h→blocks release)} |
| 281 | Data Retention Lifecycle — Bronze | stateDiagram | ACTIVE(0-90 days)→ARCHIVED(after 90 days)→DELETED(after archive period) |
| 282 | Delta Lake Table Version Lifecycle | stateDiagram | V0(initial)→V1(first write)→VN(merge/append)→VACUUMED(old versions cleaned) with Time Travel window |
| 283 | Pipeline Services Async Lifecycle | stateDiagram | CREATED→ENTERED(async with --aenter--)→ACTIVE→EXITING(--aexit--)→CLOSED(aclose all) — idempotent |
| 284 | HTTP Request Lifecycle Through Adapter Stack | stateDiagram | QUEUED→RATE-LIMITED(waiting)→SENT→{SUCCESS or RETRY(backoff)→SENT or CB-OPEN(rejected) or TIMEOUT(error)} |
| 285 | Alert Lifecycle — Detection to Resolution | stateDiagram | DETECTED→SENT(webhook/logger)→ACKNOWLEDGED→{RESOLVED or ESCALATED} with cooldown between repeated alerts |
| 286 | DQ Report Lifecycle | stateDiagram | GENERATED(per batch)→AGGREGATED(per run)→WRITTEN(to file)→PUBLISHED(metrics) |
| 287 | Gold SCD2 Record Lifecycle | stateDiagram | CURRENT(valid-to=null)→SUPERSEDED(valid-to=update-time, new record created with valid-from=update-time) |
| 288 | Token Bucket Refill Lifecycle | stateDiagram | FULL(capacity tokens)→DRAINING(requests consume)→EMPTY(wait for refill)→REFILLING(rate-based)→FULL |
| 289 | Pipeline Error Recovery Lifecycle | stateDiagram | RUNNING→ERROR→CLASSIFIED→{RETRY(recoverable) or QUARANTINE(dq) or FAIL(critical)} retry→RUNNING or FAIL |
| 290 | Heartbeat Monitor Lifecycle | stateDiagram | STARTED→TICKING(every 30s)→RENEWED(lock TTL extended)→{STOPPED(normal) or FAILED(lock lost→crash)} |
| 291 | Configuration Loading Lifecycle | stateDiagram | RAW-YAML→PARSED→VALIDATED(Pydantic)→MERGED(base+entity)→RESOLVED(convention paths)→FROZEN(immutable) |
| 292 | Graceful Shutdown Lifecycle | stateDiagram | RUNNING→SIGNAL-RECEIVED(SIGTERM/SIGINT)→DRAINING(finish batch)→CHECKPOINT-SAVED→LOCK-RELEASED→EXIT(0) |
| 293 | Bronze File Lifecycle | stateDiagram | TEMP-CREATED→WRITTEN→COMPRESSED(zstd)→SYNCED(fsync)→RENAMED(atomic)→MANIFESTED→AGED→EXPIRED→DELETED |
| 294 | Composite Checkpoint Lifecycle | stateDiagram | NONE→SEED-CHECKPOINT→DEPS-CHECKPOINT→ENRICHMENT-CHECKPOINT→MERGE-CHECKPOINT→COMPLETED→DELETED |
| 295 | PipelineRun Aggregate Lifecycle (DDD) | stateDiagram | CREATED(new PipelineRun)→BATCHES-ADDED→EVENTS-RECORDED→COMPLETED or FAILED — aggregate tracks all state |
| 296 | Batch Aggregate Lifecycle (DDD) | stateDiagram | CREATED(new Batch)→RECORDS-ADDED→PROCESSED→{COMMITTED or PARTIALLY-FAILED}→FINALIZED |
| 297 | Filter ID Loading Lifecycle | stateDiagram | FILE-READ→IDS-PARSED→DEDUPLICATED→CHUNKED→FETCHING→{ALL-FETCHED or PARTIAL-FAIL} |
| 298 | Dependency Pipeline Lifecycle in Composite | stateDiagram | PENDING→KEY-EXTRACTION→KEYS-READY→RUNNING→{COMPLETED(silver written) or FAILED}→NEXT-DEPENDENCY |
| 299 | Data Contract Version Lifecycle | stateDiagram | DRAFT→PUBLISHED(JSON Schema)→ACTIVE→DEPRECATED(14 days)→REMOVED(major version bump) |
| 300 | Silver Write Mode Decision Lifecycle | stateDiagram | CONFIG-LOADED→MODE-SELECTED(MERGE/APPEND/DELETE)→VALIDATED(no OVERWRITE allowed)→EXECUTED→COMMITTED |
| 301 | Gold Write Mode Decision Lifecycle | stateDiagram | CONFIG-LOADED→MODE-SELECTED(OVERWRITE/APPEND/SCD2)→SCD2-CONFIG-LOADED(if SCD2)→EXECUTED→COMMITTED |
| 302 | Architecture Review Lifecycle (REQ-ARCH-040) | stateDiagram | DISCOVERED→FIRST-VERIFICATION(grep, wc)→CONFIRMED/REJECTED→SECOND-VERIFICATION(documentation)→REPORTED |
| 303 | ADR Lifecycle | stateDiagram | PROPOSED→DISCUSSED→{ACCEPTED or REJECTED or DEFERRED}→SUPERSEDED(by newer ADR) |
| 304 | Game Day DR Exercise Lifecycle | stateDiagram | PLANNED→SCHEDULED→EXECUTED(simulate failure)→RECOVERED(within RTO)→REVIEWED→DOCUMENTED |
| 305 | Schema Evolution Lifecycle | stateDiagram | CHANGE-PROPOSED→CLASSIFIED(minor/major)→{MINOR:add-nullable or MAJOR:deprecation-period}→DEPLOYED→OLD-REMOVED |
| 306 | Metrics Server Lifecycle | stateDiagram | NOT-STARTED→STARTING(double-check lock)→RUNNING(port bound)→SCRAPE-READY→SHUTDOWN(graceful) |
| 307 | Environment Promotion Lifecycle | stateDiagram | DEV(local fixtures)→STAGING(prod-like data)→PROD(CI/CD deploy only) with gates at each transition |
| 308 | Retry Attempt Lifecycle | stateDiagram | ATTEMPT-1→FAILED→BACKOFF(1s+jitter)→ATTEMPT-2→FAILED→BACKOFF(2s+jitter)→ATTEMPT-3→{SUCCESS or GIVE-UP} |
| 309 | Publication Composite Enrichment Lifecycle | stateDiagram | SEED-DONE→KEYS-EXTRACTED(DOIs,PMIDs)→CROSSREF-ENRICHING→PUBMED-ENRICHING→OPENALEX-ENRICHING→S2-ENRICHING→ALL-DONE→MERGING |
| 310 | Pipeline Warmup and Cooldown Lifecycle | stateDiagram | COLD-START→CONFIG-LOAD→HEALTH-CHECK→LOCK-ACQUIRE→WARM→RUNNING→COOLDOWN→METRICS-FLUSH→LOCK-RELEASE→STOPPED |

## Provider (311–360)

| # | Name | Type | Description |
|---|------|------|-------------|
| 311 | ChEMBL Adapter — 14 Entity Types Supported | flowchart | ChemblAdapter with entity-mapper routing to 14 endpoints: activity, assay, molecule, target, document, cell-line, etc. |
| 312 | ChEMBL API Pagination — Offset-Based | sequenceDiagram | fetch(offset=0, limit=1000) → response(total-count, results) → offset+=limit → repeat until offset≥total-count |
| 313 | ChEMBL Entity Mapper — entity-type to API Resource Mapping | flowchart | activity→activity, compound→molecule, publication→document, protein-class→protein-classification — full mapping table |
| 314 | ChEMBL Query Parameter Construction | flowchart | -build-params(): format=json + limit + offset + optional {field}--in=ID1,ID2 for filter-ids |
| 315 | ChEMBL Health Check — /status Endpoint Probe | sequenceDiagram | ChemblAdapter.health-check() → GET /chembl/api/data/status → parse response time → <5s:HEALTHY, >5s:DEGRADED, error:UNHEALTHY |
| 316 | ChEMBL Rate Limiting Strategy — No Explicit Limit | flowchart | ChEMBL has no explicit rate limit → TokenBucket(capacity=high) → polite delay between requests → adaptive on errors |
| 317 | ChEMBL Activity Entity — Field Map from API to Silver | flowchart | API fields: activity-id, assay-chembl-id, molecule-chembl-id, standard-value → Silver columns with types |
| 318 | ChEMBL Molecule Entity — Nested JSON Handling | flowchart | API: molecule-properties(nested), molecule-structures(nested) → flatten for Silver → exclude nested for Gold |
| 319 | ChEMBL Assay Entity — Confidence Score Processing | flowchart | API: assay-chembl-id, assay-type, confidence-score → normalize → Silver with confidence-score as int (nullable) |
| 320 | ChEMBL Target Entity — Component Relationship | flowchart | Target → has many TargetComponents → each has ProteinClass → hierarchical entity resolution |
| 321 | ChEMBL Publication Entity — Document to Publication Mapping | flowchart | API endpoint /document → domain entity ChemblPublication → extract DOI and PMID for composite enrichment |
| 322 | PubChem Adapter — Sync Library Wrapper Architecture | flowchart | PubChemAdapter(BaseSyncAdapter) → pubchempy sync call → ThreadPoolExecutor → async wrapper → yield results |
| 323 | PubChem Compound CID Resolution | flowchart | Input CIDs → PUG REST /compound/cid/{cid}/property → batch request → parse response → yield compound records |
| 324 | PubChem Rate Limiting — 5 req/sec TokenBucket | flowchart | TokenBucket(capacity=5, refill-rate=5/sec) → acquire before each request → wait if empty → respect NCBI policy |
| 325 | PubChem Health Check — Lightweight Property Query | sequenceDiagram | PubChemAdapter.health-check() → GET /rest/pug/compound/cid/2244/property/MolecularFormula/JSON → parse → status |
| 326 | UniProt Adapter — REST API with PaginatedFetcherMixin | flowchart | UniProtAdapter(BaseHttpAdapter + PaginatedFetcherMixin) → cursor-based pagination → 100 req/sec with API key |
| 327 | UniProt ID Mapping — Cross-Reference Resolution | sequenceDiagram | Submit mapping job (from=UniProtKB, to=ChEMBL) → job-id → poll /idmapping/status/{id} → download results |
| 328 | UniProt Protein Entity — Sequence and Annotation Extraction | flowchart | UniProt JSON → extract sequence, organism, organism-id, function-description → Silver protein record |
| 329 | UniProt Health Check — Search Probe | sequenceDiagram | UniProtAdapter.health-check() → GET /uniprot/search?query=test&size=1 → response time → status classification |
| 330 | PubMed Adapter — E-utilities Integration | flowchart | PubMedAdapter → esearch(term) → get PMIDs → efetch(PMIDs) → parse XML → yield publication records |
| 331 | PubMed Pagination — retstart/retmax Pattern | sequenceDiagram | esearch(retstart=0, retmax=500) → count → efetch(retstart=0) → increment retstart → repeat |
| 332 | PubMed Rate Limiting — 3 req/sec (10 with API key) | flowchart | Check NCBI-API-KEY → present: TokenBucket(10/sec) → absent: TokenBucket(3/sec) → respect E-utilities policy |
| 333 | PubMed Health Check — E-info Probe | sequenceDiagram | PubMedAdapter.health-check() → einfo(db="pubmed") → parse response → status |
| 334 | PubMed MeSH Terms Extraction Pipeline | flowchart | XML MeshHeadingList → extract DescriptorName, QualifierName → normalize → Silver mesh-terms column |
| 335 | CrossRef Adapter — Works API with Cursor Pagination | flowchart | CrossRefAdapter(BaseHttpAdapter + PaginatedFetcherMixin) → GET /works?filter=doi:{doi} → cursor-based pagination |
| 336 | CrossRef DOI Resolution Flow | sequenceDiagram | Input DOIs → CrossRefAdapter.fetch(filter-ids=DOIs) → /works?filter=doi:10.1234/... → parse → yield records |
| 337 | CrossRef Rate Limiting — Polite Pool with Email | flowchart | Include mailto: header → get polite pool access (50 req/sec) → TokenBucket(50/sec) → respect Crossref policy |
| 338 | CrossRef Health Check — Root Endpoint Probe | sequenceDiagram | CrossRefAdapter.health-check() → GET /works?rows=1 → response time → status |
| 339 | CrossRef Publication Fields Mapping | flowchart | API: DOI, title, author, container-title, issued, is-referenced-by-count → Silver column mapping |
| 340 | OpenAlex Adapter — Works API Integration | flowchart | OpenAlexAdapter(BaseHttpAdapter + PaginatedFetcherMixin) → GET /works?filter=doi:{doi} → per-page pagination |
| 341 | OpenAlex Rate Limiting — 10 req/sec Polite Pool | flowchart | Include email in config → polite pool → TokenBucket(10/sec) → OpenAlex fair usage |
| 342 | OpenAlex Health Check — Generic Probe | sequenceDiagram | OpenAlexAdapter.health-check() → GET /works?per-page=1 → response time → status |
| 343 | OpenAlex Concepts and Institutions Extraction | flowchart | API: concepts[{id, display-name, score}], authorships[{institutions}] → flatten → Silver columns |
| 344 | SemanticScholar Adapter — Paper API Integration | flowchart | SemanticScholarAdapter(BaseHttpAdapter + PaginatedFetcherMixin) → GET /paper/{id} → token-based pagination |
| 345 | SemanticScholar Rate Limiting — 100 req/5min | flowchart | TokenBucket(rate=100/300sec) → very conservative → with API key: 1 req/sec → sliding window |
| 346 | SemanticScholar Health Check — Generic Probe | sequenceDiagram | SemanticScholarAdapter.health-check() → GET /paper/search?query=test&limit=1 → response time → status |
| 347 | SemanticScholar TLDR and Embedding Fields | flowchart | API: tldr{text}, embedding{vector} → Silver: tldr-text(string), embedding(array) |
| 348 | Provider Comparison — Authentication Methods | flowchart | ChEMBL: Public → PubChem: Public → UniProt: API Key → PubMed: API Key → CrossRef: Email → OpenAlex: Email → S2: API Key |
| 349 | Provider Comparison — Rate Limit Strategies | flowchart | ChEMBL: none → PubChem: 5/s → UniProt: 100/s → PubMed: 3-10/s → CrossRef: 50/s → OpenAlex: 10/s → S2: 0.33/s |
| 350 | Provider Comparison — Pagination Methods | flowchart | ChEMBL: offset → PubChem: chunked CIDs → UniProt: cursor → PubMed: retstart → CrossRef: cursor → OpenAlex: per-page → S2: token |
| 351 | Provider Comparison — Entity Coverage Matrix | flowchart | ChEMBL: 14 entities → PubChem: 1 → UniProt: 2 (protein + idmapping) → PubMed: 1 → CrossRef: 1 → OpenAlex: 1 → S2: 1 |
| 352 | Provider Error Response Handling Comparison | flowchart | 429: all providers → retry-after → 403: auth issue → 500/502/504: server error → retry with backoff |
| 353 | Provider-Specific Transformer Class Hierarchy | classDiagram | BaseTransformer → BaseChemblTransformer → Activity/Assay/Molecule/Target; BasePublicationTransformer → PubMed/CrossRef/OpenAlex/S2 |
| 354 | ChEMBL Multi-Entity Pipeline Graph | flowchart | 14 ChEMBL pipelines with shared adapter, independent transformers and configs, common storage factory |
| 355 | Publication Provider Coverage Overlap Analysis | flowchart | DOI coverage: CrossRef (highest) → OpenAlex → ChEMBL → S2; PMID coverage: PubMed → ChEMBL → S2 |
| 356 | Provider Adapter Factory Wiring | sequenceDiagram | DataSourceFactory.create("chembl") → HttpClientFactory.create("chembl") → ChemblAdapter(http-client, logger) |
| 357 | Provider-Specific Config Loading | flowchart | configs/sources/{provider}.yaml → rate-limit, base-url, auth-type, health-check-endpoint per provider |
| 358 | Provider Response Normalization — Heterogeneous API Formats | flowchart | ChEMBL: JSON {results:[]} → PubChem: JSON {PropertyTable:{}} → UniProt: JSON-LD → PubMed: XML → all → dict records |
| 359 | Provider Silver Table Naming Convention | flowchart | silver/{provider}/{entity}/ — chembl/activity, pubchem/compound, uniprot/protein, pubmed/publication |
| 360 | Provider Gold Schema Mapping — Domain to Pandera | flowchart | Per provider: domain entity fields → Pandera DataFrameModel → Series[type] with nullable, coerce, regex constraints |

## Configuration (361–390)

| # | Name | Type | Description |
|---|------|------|-------------|
| 361 | Pipeline Config YAML Structure | flowchart | pipeline-name, provider, entity-type, version, primary-keys, silver-table, gold-table, sink{silver, gold}, dq-overrides |
| 362 | -base.yaml Inheritance Mechanism | flowchart | configs/pipelines/-base.yaml → defaults for all pipelines → entity.yaml overrides specific fields → merged config |
| 363 | Source Config YAML Structure | flowchart | configs/sources/{provider}.yaml: base-url, rate-limit, auth-type, health-check-endpoint, load-strategy |
| 364 | DQ Config YAML Structure (ADR-027) | flowchart | configs/quality/entities/{provider}/{entity}.yaml: field-validations[{field, type, min, max, nullable}], thresholds |
| 365 | Filter Config YAML Structure (ADR-028) | flowchart | configs/filters/entities/{provider}/{entity}.yaml: column-filters, row-filters, include/exclude patterns |
| 366 | Composite Pipeline Config YAML Structure | flowchart | configs/pipelines/composite/{name}.yaml: seed, dependencies[], enrichers[], merge{strategy, conflict-resolution} |
| 367 | Data Schema Config YAML Structure (ADR-034) | flowchart | configs/schemas/{provider}/{entity}.yaml: column-groups, silver{include-groups, rename-fields}, gold{include-groups, exclude-fields, rename-fields} |
| 368 | Field Groups Config YAML Structure | flowchart | configs/composite/field-groups/publication.yaml: groups with name, fields, provider-order — 106 base fields |
| 369 | RuntimeConfig Parameters Map | flowchart | RuntimeConfig: batch-size, heartbeat-interval(30s), lock-ttl(90s), max-lock-duration(4h), resume flag, run-type |
| 370 | PipelineConfig to Runtime Resolution | flowchart | YAML → PipelineConfig(frozen) → merge with CLI args → RuntimeConfig → passed to PipelineRunner |
| 371 | DQ Override Merge Strategy | flowchart | Entity DQ config (base rules) + Pipeline dq-overrides (field-specific) → merged DQConfig → applied during validation |
| 372 | Sink Configuration — Silver and Gold Write Settings | flowchart | sink.silver: primary-key, sort-by, write-mode, partition-by → sink.gold: sort-by, write-mode, scd-config |
| 373 | Convention-Based Path Resolution Algorithm | flowchart | pipeline-name → split by - → provider + entity → derive: source-file, dq-config, filter-config, sink paths automatically |
| 374 | Environment Variable Configuration | flowchart | BIOETL-{PROVIDER}-{KEY} pattern: BIOETL-PUBCHEM-API-KEY, BIOETL-PUBMED-API-KEY, BIOETL-METRICS-PORT |
| 375 | Config Validation Pipeline | flowchart | YAML → parse → Pydantic model validation → type coercion → constraint checks → frozen dataclass → ready |
| 376 | ChEMBL Pipeline Configs — 14 Entity Configurations | flowchart | configs/pipelines/chembl/: activity.yaml, assay.yaml, molecule.yaml, target.yaml, ... — 14 files with shared base |
| 377 | Composite Config Dependencies Section | flowchart | dependencies: [{pipeline, join-keys, key-source, filter-field, required, timeout-seconds, silver-table}] — chained resolution |
| 378 | MergeConfig Parameters | flowchart | MergeConfig: strategy(left-outer/inner/union), conflict-resolution, preserve-all-sources, column-groups |
| 379 | SCD Config Parameters for Gold | flowchart | scd-config: key-columns, valid-from-column, valid-to-column, current-flag-column — for SCD Type 2 |
| 380 | Config File Discovery and Loading Order | flowchart | Working dir → configs/ → scan providers → load -base → load entities → resolve references → validate all |
| 381 | Silver Partition Configuration | flowchart | partition-by: [] (none) → ["year", "month"] → ["organism"] → Silver table directory structure per config |
| 382 | Gold Sort Configuration | flowchart | sort-by: {columns: ["activity-id"], ascending: [true]} → deterministic write order → stable Delta files |
| 383 | Provider Registration Configuration | flowchart | composition/providers/registration.py → register-all-providers() → ProviderRegistry populated with creator functions |
| 384 | Logging Configuration — structlog Setup | flowchart | structlog config: JSON renderer, ISO timestamps, log level from env, run-id context binding |
| 385 | Metrics Configuration — Prometheus Port Setup | flowchart | BIOETL-METRICS-PORT env → default 8000 → PrometheusMetrics.start-server(port) → /metrics endpoint |
| 386 | DQ Thresholds Configuration | flowchart | soft-threshold: 5% → warning; hard-threshold: 20% → batch fail; configured per entity in DQ YAML |
| 387 | Circuit Breaker Configuration | flowchart | failure-threshold: 5, recovery-timeout: 300s, half-open-max-calls: 1 — per provider in source config |
| 388 | Retry Configuration | flowchart | max-attempts: 3, multiplier: 2.0, jitter: random(0.1,0.5), deterministic: true/false — in RetryConfig |
| 389 | Lock Configuration | flowchart | heartbeat-interval: 30s, lock-ttl: 90s (3x heartbeat), max-lock-duration: 4h — in RuntimeConfig |
| 390 | Health Check Configuration | flowchart | cache-duration: 30s, timeout: 5s, probe-type: lightweight GET — per provider adapter configuration |

## DomainModel (391–420)

| # | Name | Type | Description |
|---|------|------|-------------|
| 391 | Activity Value Object — Internal Structure | classDiagram | Activity: activity-id, assay-chembl-id, molecule-chembl-id, standard-value, standard-units, pchembl-value — frozen |
| 392 | DQMetrics Value Object — Quality Metrics Bundle | classDiagram | DQMetrics: null-rates(dict), unique-counts(dict), schema-violations(int), record-count(int), error-rate(float) |
| 393 | RunContext Value Object — Pipeline Execution Context | classDiagram | RunContext: run-id(UUID), run-type(RunType), started-at(datetime), pipeline-name(str) — immutable |
| 394 | CompoundIDs Value Object — Chemical Identifiers | classDiagram | CompoundIDs: chembl-id, pubchem-cid, inchi, inchi-key, smiles, canonical-smiles — value equality |
| 395 | TaxonomyID Value Object — Organism Classification | classDiagram | TaxonomyID: tax-id(int), organism-name(str), strain(str|None) — validated, immutable |
| 396 | PipelineRun Aggregate — Complete Structure | classDiagram | PipelineRun(root): run-id, pipeline-name, run-type, status, batches:list[Batch], events:list[DomainEvent], started-at, completed-at |
| 397 | Batch Aggregate — Record Container | classDiagram | Batch: batch-id, batch-number, records:list[dict], record-count, error-count, start-time, end-time, status |
| 398 | QuarantineEntry Aggregate — Failed Record Details | classDiagram | QuarantineEntry: -pipeline-name, -error-code, -payload(truncated 64KB), -payload-hash, -batch-id, -created-at, -dq-status |
| 399 | Domain Events Class Hierarchy | classDiagram | DomainEvent → PipelineStarted, PipelineCompleted, PipelineFailed, BatchStarted, BatchCompleted, RecordQuarantined |
| 400 | ChEMBL Activity Entity — Full Field Map | classDiagram | ChemblActivity entity: 20+ fields from activity-id to pchembl-value with types and nullable flags |
| 401 | PubChem Compound Entity — CID-Based Structure | classDiagram | PubchemMolecule entity: cid, molecular-formula, molecular-weight, canonical-smiles, inchi, iupac-name |
| 402 | UniProt Protein Entity — Sequence and Annotations | classDiagram | UniprotTarget entity: accession, entry-name, protein-name, organism, organism-id, sequence, sequence-length |
| 403 | CrossRef Publication Entity — DOI Metadata | classDiagram | CrossRefPublicationEntity: doi, title, authors[], container-title, issued-date, is-referenced-by-count |
| 404 | PubMed Publication Entity — NCBI Metadata | classDiagram | PubMedPublication entity: pmid, title, abstract, authors[], journal, pub-date, mesh-terms[], keywords[] |
| 405 | Base Entity — Common Fields and Behavior | classDiagram | BaseEntity: -entity-id, -content-hash, -ingestion-ts, -run-id, -run-type — shared metadata interface |
| 406 | DataSourcePort Protocol — Complete Method Signatures | classDiagram | DataSourcePort(Protocol): fetch(entity-type, limit, query, filter-ids, filter-field)→AsyncIterator, health-check()→HealthStatus |
| 407 | StoragePort Protocol — Complete Method Signatures | classDiagram | StoragePort: write-bronze(), write-silver(), write-gold(), clear-silver(), clear-gold(), read-silver(), vacuum() |
| 408 | LockPort Protocol — Complete Method Signatures | classDiagram | LockPort: acquire(key, owner-id, ttl)→bool, release(key, owner-id)→bool, renew(key, owner-id, ttl)→bool, is-locked(key)→bool |
| 409 | CheckpointPort Protocol — Complete Method Signatures | classDiagram | CheckpointPort: save(state), load()→CheckpointState|None, delete(), exists()→bool |
| 410 | QuarantinePort Protocol — Complete Method Signatures | classDiagram | QuarantinePort: write(entry), read-sample(limit)→list, count()→int, purge(before-date)→int, replay()→int |
| 411 | MetricsPort Protocol — Counter, Histogram, Gauge | classDiagram | MetricsPort: increment-counter(name, labels), observe-histogram(name, value, labels), set-gauge(name, value, labels) |
| 412 | LoggerPort Protocol — Structured Logging Interface | classDiagram | LoggerPort: info(msg, **kw), warning(msg, **kw), error(msg, **kw), debug(msg, **kw), bind(**kw)→LoggerPort |
| 413 | TracingPort Protocol — OTel-Modeled Tracing | classDiagram | TracingPort: get-tracer(name)→Tracer; Tracer: start-as-current-span(name)→Span; Span: set-attribute(), end() |
| 414 | ValidationPort Protocol — Schema Validation Interface | classDiagram | ValidationPort: validate(df, schema)→ValidationResult with errors:list, warnings:list, passed:bool |
| 415 | Domain Services Dependency Map | flowchart | DataNormalizationService (pure), IdentityService (pure), UnitConverter (pure), ValueValidator (pure) — no I/O, no ports |
| 416 | IdentityService — Content Hash Generation Logic | flowchart | IdentityService: normalize(record) → canonical-json(sort-keys, round-floats, NaN→null) → sha256 → content-hash |
| 417 | DataNormalizationService — Field Normalization Rules | flowchart | NaN→null, Inf→null, strip strings, dates→ISO, floats→round(10), exclude META-FIELDS — per RULES.md §2.8.1 |
| 418 | UnitConverter — Standard Unit Conversion | flowchart | UnitConverter: convert-to-standard(value, from-unit, to-unit) → normalized standard-value with standard-units |
| 419 | ActivityAggregator — pChEMBL Value Processing | flowchart | Activities by target → filter valid pchembl-value → compute mean, median, min, max → aggregated activity profile |
| 420 | ErrorClassifier — HTTP Status to Error Category | flowchart | ErrorClassifier: 401→CRITICAL, 429→RECOVERABLE, 500/502/504→RECOVERABLE, invalid data→DATA-QUALITY, other→UNKNOWN |

## Composite (421–440)

| # | Name | Type | Description |
|---|------|------|-------------|
| 421 | Composite Pipeline Full Workflow — Seed to Gold | flowchart | Seed(ChEMBL docs) → Extract Keys(DOIs, PMIDs) → Dependencies → Fan-Out Enrichers → Collect → Merge → Validate → Gold Write |
| 422 | Composite Config Dataclass Structure | classDiagram | CompositeConfig: seed(SeedConfig), dependencies[DependencyConfig], enrichers[EnricherConfig], merge(MergeConfig), gold-schema |
| 423 | SeedConfig Dataclass | classDiagram | SeedConfig: pipeline-name, provider, entity-type, silver-table — defines primary data source |
| 424 | EnricherConfig Dataclass | classDiagram | EnricherConfig: pipeline-name, provider, entity-type, join-keys[], filter-field, required(bool), timeout-seconds |
| 425 | DependencyConfig Dataclass — Chained Dependencies | classDiagram | DependencyConfig: pipeline, join-keys[], key-source(str|None), filter-field, required, timeout-seconds, silver-table |
| 426 | MergeConfig Dataclass — All Parameters | classDiagram | MergeConfig: strategy, conflict-resolution, preserve-all-sources, column-groups[], field-group-registry |
| 427 | CompositeState Tracking Object | classDiagram | CompositeState: phase(enum), seed-result, dependency-results[], enrichment-results[], merge-result, errors[] |
| 428 | CompositeStrategy — Execution Order Determination | flowchart | CompositeStrategy: analyze-dependencies() → topological sort → determine execution order → parallel groups |
| 429 | CompositeLineage — Cross-Source Data Provenance | flowchart | Lineage tracking: seed-batch-id → enricher-batch-ids[] → merge-timestamp → Gold record -lineage metadata |
| 430 | Enrichment Fan-Out — asyncio.gather Parallel Execution | flowchart | EnrichmentCoordinator: create tasks per enricher → asyncio.gather(*tasks, return-exceptions=True) → collect results |
| 431 | Enricher Failure Handling — Required vs Optional | flowchart | Enricher fails → check required flag → required=true: abort composite → required=false: skip, continue with available data |
| 432 | Key Extraction — Seed Silver to Enricher Filter IDs | flowchart | KeyExtractor: read seed Silver table → select join-key columns → unique values → return list for enricher filtering |
| 433 | Chained Dependency Key Resolution | flowchart | Dep1: keys from seed → run dep1 → Dep2: key-source=dep1 → extract keys from dep1's Silver → run dep2 |
| 434 | Merge JOIN Strategy — Left Outer vs Inner vs Union | flowchart | left-outer: keep all seed records → inner: only matched → union: combine all unique records from all sources |
| 435 | Conflict Resolution Strategies Comparison | flowchart | seed-priority: prefer seed → enricher-priority: prefer enricher → coalesce: first non-null → explicit-rules: per-field config |
| 436 | Qualified Column Name Generation | flowchart | Base field "title" + provider "crossref" + entity "publication" → "crossref.publication.title" when preserve-all-sources=true |
| 437 | TRASH Group Filtering in Gold Output | flowchart | FieldGroupRegistry → identify TRASH group fields → remove from merged DataFrame before Gold write → cleaner analytics |
| 438 | Composite Pipeline Bootstrap vs Standard Bootstrap | flowchart | Standard: bootstrap-pipeline() → single runner | Composite: bootstrap-composite-runner() → CompositePipelineRunner with coordinator |
| 439 | Composite Aggregator — Multi-Source Metric Aggregation | flowchart | Per enricher: record-count, error-rate, duration → Aggregator: combine into composite-level metrics → publish |
| 440 | Cross-Validation Checks After Merge | flowchart | Check join rate (>80% expected), orphan records (<5%), duplicate DOIs (0 expected), coverage per provider → quality report |

## Observability (441–460)

| # | Name | Type | Description |
|---|------|------|-------------|
| 441 | Three Pillars of Observability in BioETL | flowchart | Logging (StructlogLogger→LoggerPort) + Metrics (PrometheusMetrics→MetricsPort) + Tracing (NoOpTracing→TracingPort) |
| 442 | Prometheus Metric Naming Convention | flowchart | prefix: bioetl- → type: pipeline/records/errors/batch → suffix: -total/-seconds/-records → labels: pipeline, stage, run-type |
| 443 | Full Prometheus Metrics Catalog | flowchart | pipeline-duration-seconds, records-processed-total, errors-total, batch-size-records, filter-ids-loaded-total, circuit-breaker-state |
| 444 | Structured Log Schema — Required and Optional Fields | flowchart | MUST: timestamp, level, run-id, pipeline, stage → SHOULD: dataset, record-count → conditional: error-type, error-code |
| 445 | Tracing Span Hierarchy — Pipeline to HTTP Request | flowchart | PipelineRun span → Batch span → Transform span → Write span → HTTP Request span (nested spans) |
| 446 | NoOp Tracing Implementation (ADR-022) | classDiagram | NoOpTracing → NoOpTracer → NoOpSpan — zero overhead, satisfies TracingPort contract, swappable with OTel |
| 447 | OTel Integration Path — NoOp to Real Tracing | flowchart | Default: NoOpTracing → install .[tracing] → OpenTelemetryTracing → same TracingPort interface → no code changes |
| 448 | Observability Port Enforcement (ADR-019) | flowchart | Application MUST NOT import structlog → MUST use LoggerPort → Architecture test blocks direct imports |
| 449 | PipelineObserver Context Manager — Lifecycle Metrics | sequenceDiagram | with PipelineObserver(metrics, logger) → enter: log started, inc counter → body: pipeline runs → exit: log completed/failed, observe duration |
| 450 | BatchMetricsRecorder — Per-Batch Instrumentation | sequenceDiagram | BatchMetricsRecorder: record(batch-size, duration, errors) → observe-histogram(batch-size) → inc-counter(records) → inc-counter(errors) |
| 451 | BatchTracingManager — Span Management | sequenceDiagram | BatchTracingManager: start-span("batch") → set-attribute(batch-num) → execute batch → end-span(status) |
| 452 | Alert Severity Classification | flowchart | CRITICAL: system down, data loss → ERROR: pipeline fail → WARNING: DQ anomaly, degraded → INFO: schema drift (new fields) |
| 453 | DQ Anomaly Z-Score Calculation | flowchart | Current null-rate → historical mean (30 days) → standard deviation → z-score = (current - mean) / std → compare thresholds |
| 454 | Anomaly Detection Cold Start Handling | flowchart | Days 1-7: accumulate baselines, silence alerts → Days 8-30: warning-only alerts → Days 30+: full alerting with configurable thresholds |
| 455 | Metrics Export to /metrics Endpoint | sequenceDiagram | Prometheus scraper → GET /metrics → PrometheusMetrics renders all counters/histograms/gauges → text/plain response |
| 456 | Run ID Correlation Across All Observability Channels | flowchart | run-id (UUID) → bound to logger → included in metrics labels → set as trace attribute → correlates logs, metrics, traces |
| 457 | Dataset Label in Metrics and Logs | flowchart | Pipeline may write to multiple tables → dataset label (e.g., chembl/activity) → added to every metric and log entry |
| 458 | Provider Health Metric — provider-health-status Gauge | flowchart | 0=UNHEALTHY, 1=DEGRADED, 2=HEALTHY → set per provider → monitored for alerting → if stuck at 0 for >10min → P2 alert |
| 459 | Circuit Breaker Metric — State and Trip Count | flowchart | circuit-breaker-state{provider} gauge (0/1/2) + trips-total{provider} counter → alert if Open >10min |
| 460 | Graceful Degradation for Observability Failures | flowchart | Metrics server fails to start → log warning → continue pipeline → metrics data lost but pipeline runs normally |

## ErrorHandling (461–480)

| # | Name | Type | Description |
|---|------|------|-------------|
| 461 | Error Classification Decision Tree — Full Logic | flowchart | HTTP error → 401/403→CRITICAL → 429→RECOVERABLE → 500/502/504→RECOVERABLE → schema mismatch→CRITICAL → invalid data→DQ |
| 462 | Retry Strategy — Exponential Backoff with Deterministic Jitter | flowchart | Attempt N → base-delay = multiplier^N → jitter = MD5(attempt:url:seed) → total = base-delay + jitter → wait → retry |
| 463 | Circuit Breaker Integration with Retry | flowchart | Request → CB check state → CLOSED: proceed → OPEN: fail fast (no retry) → HALF-OPEN: allow probe → result updates CB |
| 464 | Batch Error Threshold Enforcement | flowchart | Count errors per batch → <5%: write with -dq-warn → 5-20%: WARNING log → >20%: FAIL batch → increment errors-total metric |
| 465 | Error Recovery Playbook — Auth Failure | flowchart | 401 detected → check BIOETL-{PROVIDER}-API-KEY → expired: rotate key → missing: configure → retry → success |
| 466 | Error Recovery Playbook — Rate Limit Exhaustion | flowchart | 429 detected → check Retry-After header → reduce requests-per-second in config → wait → retry → monitor |
| 467 | Error Recovery Playbook — Schema Mismatch in Gold | flowchart | Gold validation fails → check API changes → update Gold schema → create ADR → rebuild affected tables |
| 468 | Error Recovery Playbook — Stale Checkpoint | flowchart | Warning at startup → --resume: continue from checkpoint → no --resume: delete checkpoint + --run-type rebuild |
| 469 | Error Recovery Playbook — Lock Timeout | flowchart | Lock expired alert → check for zombie processes → kill zombie → release-lock → restart pipeline |
| 470 | Exception Propagation Through Layers | flowchart | Infrastructure error → wrapped in domain exception → Application catches → classify → retry/quarantine/fail → CLI reports |
| 471 | Data Quality Error Isolation — Per-Record vs Per-Batch | flowchart | Single invalid record → quarantine record, continue batch → >20% records invalid → fail entire batch → don't corrupt Silver |
| 472 | Network Error Retry vs Circuit Breaker Interaction | stateDiagram | NetworkError → retry-count < max → retry with backoff → retry-count >= max → record failure → CB failure-count → CB trip |
| 473 | Lock Lost Safety Guard — Abort Before Write | flowchart | About to write Silver → validate-lock() → lock valid: proceed → lock expired: ABORT immediately → no partial write → data integrity |
| 474 | Cascading Failure Prevention — Provider Isolation | flowchart | Provider A fails → CB opens for A → Provider B unaffected → Pipelines using B continue normally → no cascade |
| 475 | Error Severity to SLA Mapping | flowchart | P0: system down (15min react, 1h recover) → P1: critical pipeline (1h, 4h) → P2: secondary (8h, 24h) → P3: warning (24h, next sprint) |
| 476 | Quarantine Error Pattern Analysis | flowchart | Quarantine entries → group by error-code → SCHEMA-VIOLATION: fix transformer → INVALID-VALUE: fix DQ rules → NETWORK: transient |
| 477 | Error Handling in Composite Pipeline — Enricher Failure | flowchart | Enricher fails → required=true: abort composite → required=false: log warning → merge without that source → degraded but functional |
| 478 | Split-Brain Prevention via Fencing Token | sequenceDiagram | Worker A holds lock → A stalls → lock expires → Worker B acquires → A resumes → A tries write → fencing token mismatch → A rejected |
| 479 | Transient vs Permanent Error Classification | flowchart | Transient: 429, 502, timeout, DNS → retry → Permanent: 401, 403, 404, schema error → fail fast, no retry |
| 480 | Error Metrics Dashboard — Key Error Indicators | flowchart | errors-total by error-code → record-error-rate → entity-error-rate → circuit-breaker-state → quarantine-count-total |

## Testing (481–490)

| # | Name | Type | Description |
|---|------|------|-------------|
| 481 | Test Pyramid — Unit, Integration, E2E, Contract | flowchart | Unit tests (domain logic, fast) → Integration (VCR cassettes) → E2E (full pipeline, local FS) → Contract (monthly, live API) |
| 482 | VCR Cassette Recording and Playback Flow | sequenceDiagram | First run: record mode → real HTTP → save cassette → CI run: playback mode → cassette → no network → fast, deterministic |
| 483 | VCR Secret Sanitization — before-record Callback | flowchart | before-record: intercept request → remove Authorization header → redact X-API-Key → sanitize PII → save clean cassette |
| 484 | Architecture Test Suite Overview | flowchart | test-import-boundaries → test-no-random-in-writers → test-no-datetime-now → test-no-structlog-in-app → test-port-suffixes |
| 485 | Test Fixture Organization | flowchart | tests/fixtures/: vcr/{provider}/ → bronze-samples/ → silver-samples/ → config-fixtures/ → per-entity test data |
| 486 | Coverage Gate Enforcement — 85% Minimum | flowchart | pytest --cov=src/bioetl --cov-fail-under=85 → generate report → <85%: CI fails → ≥85%: CI passes |
| 487 | E2E Test Architecture — Local-Only Full Pipeline | flowchart | create-test-context() → run pipeline (fixture data) → assert-bronze-files-exist() → assert-silver-table-has-records() → assert Gold |
| 488 | Property-Based Testing with Hypothesis | flowchart | Hypothesis generates random Activity records → test IdentityService.hash() stability → same input always same hash |
| 489 | Snapshot Testing with Syrupy | flowchart | Transform sample data → capture output schema/format → save snapshot → next run: compare → changed: update or fail |
| 490 | Contract Test — Monthly Live API Validation | flowchart | Monthly CI job → real API calls to each provider → validate response schema → detect breaking changes → alert team |

## Security (491–495)

| # | Name | Type | Description |
|---|------|------|-------------|
| 491 | PII Data Flow Through Medallion Layers | flowchart | Bronze: PII stored as-is → Silver: PIIHasher.hash(value, salt) → sha256 → Gold: PII excluded or aggregated |
| 492 | Secret Management — Environment Variable Pattern | flowchart | BIOETL-{PROVIDER}-{KEY} → os.environ → never hardcoded → .env files never in git → CI secrets via vault |
| 493 | Security Scan Pipeline — pip-audit Integration | flowchart | CI job → pip-audit scan → CVE severity ≥ HIGH → block merge → CVE < HIGH → warning only |
| 494 | Sensitive Data Classification | flowchart | Public (Gold analytics) → Internal (Silver normalized, Bronze raw) → Restricted (PII fields, API keys) |
| 495 | VCR Cassette Secret Sanitization Pipeline | sequenceDiagram | Record HTTP interaction → before-record hook → check headers for Authorization/API-Key → replace with REDACTED → save cassette |

## Performance (496–500)

| # | Name | Type | Description |
|---|------|------|-------------|
| 496 | Adaptive Batch Size Based on Provider Health | flowchart | HEALTHY: batch-size=1000 → DEGRADED: batch-size=500 (÷2), timeout×2 → UNHEALTHY: pause → recover → ramp up |
| 497 | Memory Monitoring During Pipeline Execution | flowchart | Monitor RSS memory per batch → log memory-stats → if approaching limit: reduce batch-size → graceful degradation |
| 498 | TokenBucket Rate Limiter Performance Characteristics | flowchart | Burst capacity (full bucket) → sustained rate (refill rate) → backpressure when empty (wait) → throughput graph |
| 499 | Delta Lake VACUUM Impact on Query Performance | flowchart | Before VACUUM: many small files → slow reads → VACUUM(7d retention) → compact files → faster reads → weekly schedule |
| 500 | Zstd Compression Ratio for Bronze JSONL | flowchart | Raw JSONL size → zstd compression → typical ratio 5:1-10:1 → storage savings → decompression speed for Silver reads |

---

## Diagram Type Distribution

| Type | Count | Percentage |
|------|-------|------------|
| flowchart | 258 | 51.6% |
| classDiagram | 94 | 18.8% |
| sequenceDiagram | 77 | 15.4% |
| stateDiagram | 29 | 5.8% |
| pie | 3 | 0.6% |
| mindmap | 3 | 0.6% |
| timeline | 1 | 0.2% |
| C4Container | 1 | 0.2% |
| C4Component | 3 | 0.6% |
| block-beta | 1 | 0.2% |
| **Total** | **500** | **100%** |

*10 distinct diagram types used.*

---

## Implementation Priority

### TOP-25 Recommended for Immediate Implementation

| Priority | Diagram # | Name | Rationale |
|----------|-----------|------|-----------|
| 1 | 6 | Hexagonal Architecture — Ports and Adapters Overview | Core architecture visualization missing from existing set |
| 2 | 2 | C4 Container Diagram — Internal Containers | C4 Level 2 gap |
| 3 | 421 | Composite Pipeline Full Workflow | Most complex feature needs detailed diagram |
| 4 | 1 | Five-Layer Import Matrix Enforcement | Critical ARCH-001 rule visualization |
| 5 | 271 | Pipeline Run Lifecycle — Full States | Extends existing lifecycle diagram with all states |
| 6 | 69 | Content Hash Calculation Pipeline | Core deduplication mechanism undocumented |
| 7 | 14 | Port-to-Adapter Mapping Table | Essential reference for developers |
| 8 | 79 | Batch Processing Flow — Extract to Write | Core data processing sequence |
| 9 | 15 | Composition Root Wiring — Full DI Graph | Shows complete dependency injection |
| 10 | 184 | UnifiedHTTPClient Full Internal Architecture | Complex component needs detailed view |
| 11 | 221 | CLI Run Command → PipelineRunner Full Interaction | End-to-end user journey |
| 12 | 10 | Composition Layer Bootstrap Sequence | Key initialization flow |
| 13 | 61 | ChEMBL Activity Bronze→Silver Transformation | Most used pipeline transformation detail |
| 14 | 441 | Three Pillars of Observability | Observability architecture overview |
| 15 | 311 | ChEMBL Adapter — 14 Entity Types | Most complex adapter documentation |
| 16 | 461 | Error Classification Decision Tree | Error handling reference |
| 17 | 44 | Exception Hierarchy Full Tree | Developer reference for error types |
| 18 | 158 | Layered Validation Strategy (5 Levels) | Complex validation system |
| 19 | 121 | Template Method Pattern — BaseTransformer | Core design pattern |
| 20 | 353 | Provider-Specific Transformer Hierarchy | Shows all 23 transformers |
| 21 | 155 | Fan-Out/Fan-In — Composite Enrichment | Parallel execution pattern |
| 22 | 292 | Graceful Shutdown Lifecycle | Critical operational flow |
| 23 | 361 | Pipeline Config YAML Structure | Configuration reference |
| 24 | 396 | PipelineRun Aggregate Structure | DDD aggregate documentation |
| 25 | 481 | Test Pyramid Overview | Testing strategy visualization |

---

*Document generated based on analysis of 534 Python source files, 34 ADRs, RULES.md v5.20, and all architecture documentation.*
