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
| 7 | Domain Layer Internal Package Structure | flowchart | Package-level dependency graph: ports, entities, value_objects, schemas, config, services, aggregates, exceptions, composite |
| 8 | Application Layer Internal Package Structure | flowchart | Package-level view: core/, pipelines/, composite/, observability/ with internal dependencies |
| 9 | Infrastructure Layer Internal Package Structure | flowchart | Package-level view: adapters/, storage/, locking/, checkpoint/, quarantine/, observability/, validation/, security/, config/ |
| 10 | Composition Layer Bootstrap Sequence | flowchart | Step-by-step flow from CLI invocation through bootstrap_pipeline() to fully assembled PipelineRunner |
| 11 | Interfaces Layer CLI Command Tree | flowchart | Click command group hierarchy: main → run, run-all, run-composite, health, export, quarantine, maintenance |
| 12 | Local-Only Deployment Architecture (ADR-010) | flowchart | Single-process architecture with MemoryLock, local file system storage, local checkpoints — no Redis/S3 |
| 13 | Domain Purity Boundary — Allowed vs Forbidden Imports | flowchart | What domain layer CAN import (typing, dataclasses, abc) vs what it MUST NOT (requests, httpx, structlog, open) |
| 14 | Port-to-Adapter Mapping Table Diagram | flowchart | All 24 ports mapped to their concrete adapter implementations with module paths |
| 15 | Composition Root Wiring Diagram — Full DI Graph | flowchart | Complete dependency injection graph showing how composition wires all ports to adapters |
| 16 | YAML Configuration Resolution Chain | flowchart | How pipeline configs resolve: _base.yaml → provider.yaml → entity.yaml → dq overrides → filter rules |
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
| 29 | GenericPipelineFactory Declarative Registration | flowchart | How pipeline_factories.py declares provider/entity/transformer/schema → factory auto-generates pipeline |
| 30 | Runtime Assembly Sequence — bootstrap/runtime/assembly.py | sequenceDiagram | Step-by-step assembly: create logger → create storage → create HTTP client → create adapter → create services → create runner |
| 31 | DataSourceRegistry Lookup Flow | flowchart | Registry.get(provider) → creator function → adapter instantiation with HTTP client, rate limiter, circuit breaker |
| 32 | StorageFactory Assembly — Bronze + Silver + Gold Writers | flowchart | StorageFactory combining BronzeWriter, SilverWriter, GoldWriter into unified StoragePort implementation |
| 33 | HttpClientFactory Configuration Per Provider | flowchart | HttpClientFactory creating UnifiedHTTPClient with provider-specific rate limits, timeouts, circuit breaker thresholds |
| 34 | TransformerFactory Registration and Resolution | flowchart | register_transformer() / create_transformer() flow with provider→entity→class mapping |
| 35 | Pipeline Name Convention Resolution | flowchart | {provider}_{entity} → config path, storage paths, lock keys, checkpoint file — all derived from naming |
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
| 46 | Convention-Based Path Resolution | flowchart | From pipeline_name=chembl_activity → auto-computed source, dq, filter, sink paths without explicit config |
| 47 | Architecture Principles Mind Map | mindmap | Central: Hexagonal Architecture → Ports&Adapters, DI, Medallion, DDD Aggregates, Composition Root, Local-Only |
| 48 | RULES.md Section Dependency Graph | flowchart | How RULES.md sections cross-reference: §1→§2 (layers→data flow), §3 (errors), §4 (code), §5 (ops) |
| 49 | BasePipeline Decomposition (ADR-020) | flowchart | Original monolith → decomposed: BatchExecutor, BatchTransformer, BatchWriter, PreflightService, PostrunService |
| 50 | Five-Layer Architecture With Allowed Dependencies | block-beta | Visual block diagram showing 5 layers stacked with arrows only for allowed dependency directions |
| 51 | Composition Bootstrap — Composite vs Standard Pipeline | flowchart | Decision: is composite? → bootstrap_composite_runner() : bootstrap_pipeline() with different wiring |
| 52 | Interface Layer — CLI vs HTTP Server Boundary | flowchart | CLI (click commands) for batch execution, HTTP server for health/metrics — two interface types |
| 53 | Domain Ports Grouped By Concern | mindmap | Ports organized: Data (DataSource, Storage), Coordination (Lock, Checkpoint), Observability (Logger, Metrics, Tracing), Quality (Validation, Quarantine, DQ), Resilience (CircuitBreaker, HealthCheck) |
| 54 | Infrastructure Adapter Inheritance Hierarchy | classDiagram | BaseHttpAdapter → ChemblAdapter, UniProtAdapter, CrossRefAdapter, OpenAlexAdapter; BaseSyncAdapter → PubChemAdapter |
| 55 | Storage Writer Inheritance Hierarchy | classDiagram | BaseDeltaWriter → SilverWriter, GoldWriter; BronzeWriter (standalone); DeltaReader (standalone) |
| 56 | Application Core Component Collaboration | flowchart | PipelineRunner orchestrates LockManager, PreflightService, BatchExecutor, PostrunService, CheckpointManager |
| 57 | Transformer DI Pattern — Template Method with Injection | flowchart | BaseTransformer (abstract _transform_impl) → BaseChemblTransformer → ActivityTransformer injected into BatchTransformer |
| 58 | Factory Method vs Abstract Factory in Composition | flowchart | GenericPipelineFactory (Factory Method) vs HttpClientFactory (Abstract Factory) usage comparison |
| 59 | Service Locator Anti-Pattern vs Constructor Injection | flowchart | Why ServiceLocator/Container.resolve is forbidden (DI-003) vs proper constructor injection pattern |
| 60 | Architecture Quality Gate Checks | flowchart | mypy --strict → import-linter → pytest tests/architecture/ → coverage ≥85% — all must pass for merge |

## DataFlow (61–120)

| # | Name | Type | Description |
|---|------|------|-------------|
| 61 | ChEMBL Activity Bronze→Silver Transformation Including Field Mapping and Content Hash | sequenceDiagram | Detailed sequence: raw JSON → ActivityTransformer._transform_impl() → normalize values → compute hash → Silver DataFrame |
| 62 | ChEMBL Molecule Bronze→Silver Field Mapping | flowchart | Raw molecule JSON fields → MoleculeTransformer mapping → Silver columns with type coercions and null handling |
| 63 | PubChem Compound Bronze→Silver Transformation Flow | sequenceDiagram | pubchempy response → PubChemCompoundTransformer → normalize CID, SMILES, InChI → Silver write |
| 64 | UniProt Protein Bronze→Silver Data Normalization | flowchart | UniProt XML/JSON → UniProtProteinTransformer → sequence extraction, organism mapping → Silver table |
| 65 | PubMed Publication Bronze→Silver Metadata Extraction | flowchart | E-utilities XML → PubMedPublicationTransformer → title, authors, abstract, MeSH terms → Silver |
| 66 | CrossRef Publication Bronze→Silver DOI Resolution | flowchart | CrossRef /works response → CrossRefPublicationTransformer → DOI, title, ISSN, citation count → Silver |
| 67 | OpenAlex Publication Bronze→Silver Enrichment | flowchart | OpenAlex response → OpenAlexPublicationTransformer → concepts, institutions, cited_by_count → Silver |
| 68 | SemanticScholar Publication Bronze→Silver Processing | flowchart | S2 API response → SemanticScholarPublicationTransformer → paper_id, tldr, embedding → Silver |
| 69 | Content Hash Calculation Pipeline | flowchart | Raw record → exclude META_FIELDS → canonical JSON → NaN/Inf→null, floats→round(10), dates→ISO → sha256 |
| 70 | Bronze Write Atomic Operation Detail | sequenceDiagram | BronzeWriter: create temp file → write JSONL → zstd compress → compute checksum → atomic rename → update manifest |
| 71 | Silver Merge/Upsert Decision Logic | flowchart | SilverWriter: check write_mode → MERGE: upsert by PK → APPEND: insert → DELETE: truncate+insert |
| 72 | Gold Write Mode Selection — OVERWRITE vs SCD2 vs APPEND | flowchart | GoldWriter: check gold_write_mode → OVERWRITE: full replace → SCD2: history tracking → APPEND: partition add |
| 73 | SCD Type 2 Record Versioning in Gold | sequenceDiagram | Existing Gold record + updated Silver record → compare content_hash → create new version with valid_from/valid_to |
| 74 | Data Lineage Tracking — Bronze batch_id to Silver _source_batch_id | flowchart | Bronze file → batch_id generated → passed through transform → stored as _source_batch_id in Silver → lineage_log entry |
| 75 | Quarantine Record Creation and Routing | sequenceDiagram | Pandera validation fail → QuarantineEntry created → payload truncated to 64KB → payload_hash computed → write to quarantine table |
| 76 | DQ Metrics Calculation Per Batch | flowchart | Batch records → null_rate per column, unique_count, schema_violations → DQMetrics value object → Prometheus export |
| 77 | Schema Drift Detection Flow | flowchart | Incoming record → compare with expected schema → new fields: Info → missing required: Critical → SLA 48h owner assignment |
| 78 | Record Processing Pipeline — Single Record Journey | flowchart | API response → Bronze JSONL → RecordProcessor.process() → transform → validate → route (Silver or Quarantine) → Gold |
| 79 | Batch Processing Flow — Extract to Write | sequenceDiagram | BatchExecutor: fetch_batch() → BatchTransformer.transform() → validate() → BatchWriter.write() → update metrics |
| 80 | Metadata Fields Injection Timeline | flowchart | PipelineContext.started_at → _ingestion_ts; RunContext → _run_id, _run_type; BatchID → _source_batch_id; HashService → _content_hash |
| 81 | NULL Handling Strategy Per Layer | flowchart | Source missing value → Bronze: as-is → Silver: explicit NULL with nullable=True → Gold: NaN for nullable ints |
| 82 | Int→Float Coercion Path for Nullable Integers | flowchart | Domain: Series[int] → Silver: pa.int64() → Gold: Series[float]+coerce=True → downstream: handle NaN as missing |
| 83 | Bronze File Naming Convention and Path Structure | flowchart | bronze/{provider}/{entity}/{YYYY-MM-DD}/batch_{NNN}.jsonl.zst + _manifest.json with checksums |
| 84 | Silver Delta Lake Table Structure | flowchart | silver/{provider}/{entity}/ → _delta_log/ (transaction log) + parquet data files + partition dirs |
| 85 | Gold Delta Lake Table Structure with Partitioning | flowchart | gold/{provider}/{entity}/ → optional partition_by columns → _delta_log/ + data files |
| 86 | Checkpoint Save and Restore Flow | sequenceDiagram | Pipeline: save_checkpoint(last_id, batch_num) → JSON file → restart: load_checkpoint() → resume from last_id+1 |
| 87 | Data Freshness Monitoring Pipeline | flowchart | Gold table → max(updated_at) → now() - max → data_freshness_seconds metric → alert if >24h (warning) or >72h (critical) |
| 88 | Backfill Data Flow — Full Reload Path | flowchart | CLI --run-type=backfill → acquire exclusive lock → clear Silver+Gold → full API fetch → Bronze → Silver → Gold |
| 89 | Incremental Data Flow — Delta Update Path | flowchart | CLI --run-type=incremental → standard lock → load watermark → fetch since watermark → Bronze append → Silver merge → Gold merge |
| 90 | Rebuild Data Flow — Clean Slate Path | flowchart | CLI --run-type=rebuild → acquire exclusive lock → clear all layers → full extraction → rebuild all layers |
| 91 | Cross-Provider Data Enrichment Flow — Publication | flowchart | ChEMBL document → extract DOIs/PMIDs → fan-out to CrossRef+PubMed+OpenAlex+SemanticScholar → merge into Gold |
| 92 | Filtered Data Source — ID-Based Extraction | flowchart | FilteredDataSource: load filter_ids from file → deduplicate → chunk into batches → DataSourcePort.fetch(filter_ids=chunk) |
| 93 | ID Mapping Data Source — UniProt Cross-References | flowchart | IDMappingDataSource: submit ID mapping job → poll status → download results → yield mapped records |
| 94 | Bronze Cleanup Flow — Retention Policy | flowchart | CleanupService: scan bronze dirs → check age against 90-day retention → delete expired → log cleanup stats |
| 95 | Delta Lake VACUUM Execution Flow | flowchart | PostrunService → SilverWriter.vacuum(retention=7d) → GoldWriter.vacuum(retention=7d) → log stats |
| 96 | Batch Size Adaptive Calculation | flowchart | Provider health status → HEALTHY: full batch_size → DEGRADED: batch_size/2 → UNHEALTHY: pause pipeline |
| 97 | Sort-Before-Write Pipeline for Deterministic Output | flowchart | DataFrame → sort by primary_keys (Silver) or business_keys (Gold) → then write to Delta Lake → deterministic file content |
| 98 | Gold Schema Validation Pipeline (ADR-018) | flowchart | Silver records → transform_for_gold() → exclude JSON fields → Pandera strict=True validation → write or fail batch |
| 99 | JSONL+Zstd Compression Pipeline in BronzeWriter | sequenceDiagram | Records → json.dumps per record → join with newlines → zstd.compress() → write temp file → rename to final |
| 100 | Manifest File Generation for Bronze Batches | flowchart | After batch write → compute file hash → record file_path, size, record_count, checksum → write _manifest.json |
| 101 | ChEMBL Target→TargetComponent→ProteinClass Chained Data Flow | flowchart | Target entity → extract component_ids → fetch target_components → extract protein_class_ids → fetch protein_classes |
| 102 | Publication Composite — Seed DOI Extraction | flowchart | ChEMBL document Silver table → extract DOI and PMID columns → deduplicate → create enrichment key lists |
| 103 | Publication Composite — CrossRef Enrichment Path | sequenceDiagram | Key list (DOIs) → CrossRefAdapter.fetch(filter_ids=DOIs) → Bronze → CrossRefTransformer → Silver |
| 104 | Publication Composite — Merge All Sources | flowchart | Seed Silver + CrossRef Silver + PubMed Silver + OpenAlex Silver + S2 Silver → MergeService LEFT OUTER JOIN → Gold |
| 105 | Column Group Ordering in Gold Output | flowchart | FieldGroupRegistry: ID_AND_STATUS → BIBLIOGRAPHY → AUTHOR → TERMS → CITATIONS → DATES → PUB_TYPES; TRASH excluded |
| 106 | Qualified Column Naming — preserve_all_sources=true | flowchart | Base field "title" → chembl.publication.title, crossref.publication.title, openalex.publication.title |
| 107 | Coalesce Conflict Resolution Strategy | flowchart | Multiple source values for same field → iterate by provider_order → take first non-null → write single column |
| 108 | Silver Rename Chain — Original→Silver→Gold Column Names | flowchart | entity_id → document_id (Silver rename) → publication_id (Gold rename) — chain resolution |
| 109 | DQ Flag Routing Decision Tree | flowchart | Record → validate → all pass: clean → warning <5%: _dq_warn=true → error: quarantine → >20% errors: batch fail |
| 110 | Bronze→Silver→Gold Complete Transformation for ChEMBL Assay | flowchart | Assay JSON → AssayTransformer → normalize assay_type, confidence_score → Silver → Gold (strict validation) |
| 111 | Target Entity Full Data Flow — ChEMBL and UniProt Sources | flowchart | ChEMBL /target API → Bronze → TargetTransformer → Silver | UniProt /protein API → Bronze → UniProtTransformer → Silver → Cross-reference |
| 112 | Cell Line Entity Data Flow | flowchart | ChEMBL /cell_line → Bronze → CellLineTransformer → cell_chembl_id, cell_name, organism → Silver → Gold |
| 113 | Compound Record Entity Data Flow | flowchart | ChEMBL /compound_record → Bronze → CompoundRecordTransformer → molecule-document linkage → Silver |
| 114 | Tissue Entity Data Flow | flowchart | ChEMBL /tissue → Bronze → TissueTransformer → tissue_chembl_id, pref_name, BTO → Silver |
| 115 | Subcellular Fraction Entity Data Flow | flowchart | ChEMBL → Bronze → SubcellularFractionTransformer → GO terms, cellular component → Silver |
| 116 | Assay Parameters Entity Data Flow | flowchart | ChEMBL /assay → parameters extraction → AssayParametersTransformer → parameter_type, value → Silver |
| 117 | Watermark-Based vs Full-Scan Loading Strategy | flowchart | LoadingStrategy enum → WATERMARK_BASED: use last checkpoint → FULL_SCAN_ONLY: ignore watermark, fetch all |
| 118 | Partition Strategy Per Medallion Layer | flowchart | Bronze: by ingestion_date → Silver: by source_date or entity_type → Gold: by business key or date |
| 119 | Data Quality Anomaly Detection Baseline | flowchart | Days 1-7: silence (training) → Days 8-30: warning only → Days 30+: full alerting with z-score thresholds |
| 120 | Duplicate Detection via Content Hash in Silver Upsert | sequenceDiagram | New record → compute content_hash → check existing by entity_id → same hash: skip → different hash: upsert new version |

## Pattern (121–170)

| # | Name | Type | Description |
|---|------|------|-------------|
| 121 | Template Method Pattern — BaseTransformer._transform_impl() | classDiagram | BaseTransformer defines transform() skeleton; subclasses override _transform_impl() for provider-specific logic |
| 122 | Null Object Pattern — NoOpMetrics and NoOpTracing | classDiagram | MetricsPort/TracingPort → NoOpMetrics/NoOpTracing implementations that silently accept all calls |
| 123 | Strategy Pattern — SilverWriteMode Selection | classDiagram | SilverWriter uses SilverWriteMode enum (MERGE, APPEND, DELETE) to select write strategy at runtime |
| 124 | Strategy Pattern — GoldWriteMode Selection | classDiagram | GoldWriter uses GoldWriteMode enum (OVERWRITE, APPEND, SCD2) to select gold output strategy |
| 125 | Strategy Pattern — Conflict Resolution in Merge | classDiagram | MergeService uses ConflictResolution enum (seed_priority, enricher_priority, coalesce, explicit_rules) |
| 126 | Observer Pattern — PipelineObserver Lifecycle Events | sequenceDiagram | PipelineRunner → PipelineObserver.enter() → metrics.started → execute → PipelineObserver.exit() → metrics.completed |
| 127 | Facade Pattern — domain.ports.__init__.py Re-exports | flowchart | All 24 port protocols re-exported from domain.ports facade → enforced by ARCH-008 |
| 128 | Builder Pattern — ServicesBuilder for PipelineServices | sequenceDiagram | ServicesBuilder.with_storage().with_lock().with_logger().with_metrics().build() → frozen PipelineServices |
| 129 | Registry Pattern — ProviderRegistry and DataSourceRegistry | classDiagram | ProviderRegistry stores provider→config mapping; DataSourceRegistry is legacy facade delegating to ProviderRegistry |
| 130 | Frozen Dataclass Pattern — Immutable Configuration Objects | classDiagram | PipelineConfig, RuntimeConfig, DQConfig, CompositeConfig — all @dataclass(frozen=True) for thread safety |
| 131 | Mixin Pattern — PaginatedFetcherMixin for HTTP Adapters | classDiagram | PaginatedFetcherMixin provides pagination logic; mixed into UniProtAdapter, CrossRefAdapter, OpenAlexAdapter, SemanticScholarAdapter |
| 132 | Mixin Pattern — NotSupportedMultiFilterMixin for PubChem | classDiagram | NotSupportedMultiFilterMixin raises error for unsupported multi-ID filter operations |
| 133 | Token Bucket Pattern — Rate Limiting Implementation | stateDiagram | TokenBucket states: tokens_available → consume_token → check_refill → wait_if_empty → tokens_available |
| 134 | Decorator Pattern — FilteredDataSource Wrapping DataSourcePort | classDiagram | FilteredDataSource wraps DataSourcePort, adds filter_ids logic, delegates fetch() to inner source |
| 135 | Aggregate Pattern (DDD) — PipelineRun as Aggregate Root | classDiagram | PipelineRun aggregate: root entity with Batch children, QuarantineEntry children, domain events |
| 136 | Value Object Pattern — Activity, DQMetrics, RunContext | classDiagram | Frozen dataclass value objects: Activity (pchembl_value, standard_value), DQMetrics, RunContext — equality by value |
| 137 | Domain Event Pattern — PipelineStarted, BatchCompleted, PipelineFailed Events | classDiagram | DomainEvent base → PipelineStarted, BatchCompleted, PipelineFailed with timestamps and metadata |
| 138 | Context Manager Pattern — PipelineServices async with | sequenceDiagram | async with services → __aenter__: init resources → yield → __aexit__: aclose() all components |
| 139 | Fencing Token Pattern — owner_id in MemoryLock | sequenceDiagram | Lock acquire with owner_id → heartbeat validates owner_id → write validates owner_id → prevents split-brain |
| 140 | Circuit Breaker Pattern — State Transitions Detail | stateDiagram | CLOSED→(5 failures)→OPEN→(5 min timeout)→HALF_OPEN→(success)→CLOSED, (failure)→OPEN |
| 141 | Retry with Exponential Backoff Pattern | flowchart | Attempt 1 → fail → wait 1s+jitter → Attempt 2 → fail → wait 2s+jitter → Attempt 3 → fail → give up |
| 142 | Deterministic Jitter Calculation via MD5 Hash | flowchart | Input: attempt+url+seed → MD5 hash → take first 8 hex chars → normalize to [0,1] → multiply by max_jitter |
| 143 | Safety Guard Pattern — Lock Validation Before Write | sequenceDiagram | Before Silver write → validate lock still held → if not held → abort (no partial write) → if held → proceed |
| 144 | Idempotent Write Pattern — Content Hash Deduplication | flowchart | Compute content_hash → query Silver by entity_id → same hash exists: skip → different: upsert → guarantees idempotency |
| 145 | At-Least-Once Delivery + Silver Deduplication | flowchart | Network retry → possible duplicate Bronze writes → Silver merge by content_hash → exactly-once semantics at Silver |
| 146 | Atomic Rename Pattern — Bronze File Write Safety | sequenceDiagram | Write to temp_file.tmp → fsync → rename temp_file.tmp → final_file.jsonl.zst → atomic visibility |
| 147 | Composition Root Pattern — Assembly.py as Single Wiring Point | flowchart | All object creation happens in composition/ → application and domain never create concrete implementations |
| 148 | Double-Check Locking — Metrics Server Startup Idempotency | flowchart | Check if metrics started → if not: acquire lock → check again → if still not: start server → release lock |
| 149 | Graceful Degradation Pattern — Missing DQ Config | flowchart | Load DQ config → file exists: apply rules → file missing: log warning → continue without DQ validation → no crash |
| 150 | Backward Compatibility Re-export Pattern | classDiagram | application/core/medallion_policy.py re-exports from domain/policies for backward compatibility — 19 LOC shim |
| 151 | Protocol-Based Structural Subtyping | classDiagram | DataSourcePort(Protocol) → ChemblAdapter satisfies via structural subtyping (duck typing) — no explicit inheritance |
| 152 | Runtime Checkable Protocol for Boundary Validation | flowchart | @runtime_checkable on DataSourcePort → isinstance(adapter, DataSourcePort) check in composition layer |
| 153 | Frozen Bundle Pattern — PipelineServices as Immutable DI Container | classDiagram | PipelineServices frozen dataclass: all ports as fields, no mutation after creation, passed through call chain |
| 154 | Heartbeat Renewal Pattern for Lock TTL Extension | sequenceDiagram | Heartbeat timer fires every 30s → MemoryLock.renew(owner_id) → extends TTL by 90s → prevents expiration during long batches |
| 155 | Fan-Out/Fan-In Pattern — Composite Pipeline Enrichment | flowchart | Seed → extract keys → fan-out to N enrichers (asyncio.gather) → collect results → fan-in via MergeService |
| 156 | Canonical JSON Serialization for Hash Stability | flowchart | Record → sort_keys=True → separators=(',',':') → ensure_ascii=True → round floats → NaN→null → stable hash input |
| 157 | Error Classification Strategy Pattern | flowchart | ErrorClassifier: HTTP status → Critical (401, schema) vs Recoverable (429, 502) vs DataQuality (invalid SMILES) |
| 158 | Layered Validation Strategy (5 Levels) | flowchart | Level 1: Base (Pandera) → Level 2: Structural (cross-field) → Level 3: External (API verify) → Level 4: Logical (ranges) → Level 5: Semantic (NLP) |
| 159 | Threshold-Based Batch Failure Pattern | flowchart | Count errors per batch → <5%: warn → 5-20%: alert → >20%: fail entire batch → circuit breaker may trip |
| 160 | Entity Mapper Pattern — ChEMBL entity_type to API Resource | flowchart | EntityMapper: entity_type="activity" → resource="activity", entity_type="compound" → resource="molecule" |
| 161 | Async Context Manager Pattern — Resource Lifecycle | sequenceDiagram | async with resource → __aenter__: open connection → use resource → __aexit__: close connection (idempotent) |
| 162 | Convention Over Configuration — Auto-Computed Paths | flowchart | pipeline_name → split provider_entity → derive: source_file, dq_config, filter_config, sink paths |
| 163 | Schema-Domain Configuration Pairs (ADR-034) | classDiagram | Each domain entity paired with its Pandera schema: Activity↔ActivitySchema, Molecule↔MoleculeSchema |
| 164 | Output Metadata Unification Pattern (ADR-029) | classDiagram | BaseOutputMetadata → BronzeOutputMetadata, SilverOutputMetadata, GoldOutputMetadata — unified contract |
| 165 | Column Filter Pattern — Gold Layer Field Exclusion | flowchart | Gold record → check FieldGroupRegistry → TRASH group fields → exclude from output → write only business columns |
| 166 | Loading Strategy Formalization (ADR-031) | stateDiagram | LoadingStrategy.FULL_SCAN_ONLY → always full load | WATERMARK_BASED → incremental when watermark available, else full |
| 167 | Publication Pagination Strategy (ADR-030) | flowchart | PubMed: E-utilities retstart/retmax → CrossRef: cursor-based → OpenAlex: per-page → S2: token-based |
| 168 | DQ Rules Externalization (ADR-027) | flowchart | Inline Python DQ rules → extracted to configs/quality/entities/{provider}/{entity}.yaml → loaded by DQConfigLoader |
| 169 | Filter Rules Externalization (ADR-028) | flowchart | Inline filter logic → extracted to configs/filters/entities/{provider}/{entity}.yaml → loaded by FilterConfigLoader |
| 170 | Pipeline Config Unification (ADR-025) | flowchart | Per-provider configs → unified schema: pipeline_name, provider, entity_type, sink, dq_overrides → validated by Pydantic |

## Component (171–220)

| # | Name | Type | Description |
|---|------|------|-------------|
| 171 | PipelineRunner Internal Component Diagram | classDiagram | PipelineRunner with _lock_manager, _preflight, _batch_executor, _postrun, _checkpoint, _observer — all injected |
| 172 | BatchExecutor Internal Structure — 786 LOC Decomposition | classDiagram | BatchExecutor with _transformer, _writer, _metrics_recorder, _tracing_manager methods: execute_batch(), _extract(), _transform(), _write() |
| 173 | BatchTransformer Component — Transform Orchestration | classDiagram | BatchTransformer coordinates: BaseTransformer, DataNormalizationService, IdentityService for each batch |
| 174 | BatchWriter Component — Medallion Write Orchestration | classDiagram | BatchWriter with _bronze_writer, _silver_writer, _gold_writer, _quarantine — writes to all layers per batch |
| 175 | PreflightService Component — 818 LOC with 21 Methods | classDiagram | PreflightService: check_config(), check_storage(), check_data_source(), check_lock(), check_health() — single responsibility: pre-run validation |
| 176 | PostrunService Component — Cleanup and Finalization | classDiagram | PostrunService: run_dq_checks(), execute_vacuum(), write_dq_report(), cleanup_temp_files(), publish_final_metrics() |
| 177 | LockManager Component — Lock Lifecycle Coordination | classDiagram | LockManager wraps LockPort: acquire_with_timeout(), release_safely(), validate_ownership(), generate_lock_key() |
| 178 | CheckpointManager Component — State Persistence | classDiagram | CheckpointManager: save(last_id, batch_num), load() → CheckpointState, delete(), exists(), is_stale() |
| 179 | QuarantineManager Component — Failed Record Handling | classDiagram | QuarantineManager: route_failed_records(), create_entry(), compute_payload_hash(), truncate_payload(64KB) |
| 180 | HeartbeatTask Component — TTL Renewal Worker | classDiagram | HeartbeatTask: start(), stop(), _heartbeat_loop() — async task running every 30s to renew lock TTL |
| 181 | ShutdownHandler Component — Signal Handling | classDiagram | ShutdownHandler: register_signals(), handle_sigterm(), handle_sigint(), is_shutting_down(), wait_for_current_batch() |
| 182 | CleanupService Component — Bronze Retention | classDiagram | CleanupService: cleanup_expired_bronze(retention_days=90), scan_directories(), delete_old_batches(), log_cleanup_stats() |
| 183 | FilteredDataSource Component — ID Filter Wrapper | classDiagram | FilteredDataSource wrapping DataSourcePort: load_filter_ids(), deduplicate_ids(), chunk_ids(), fetch_filtered() |
| 184 | UnifiedHTTPClient Component — Full Internal Architecture | classDiagram | UnifiedHTTPClient: _httpx_client, _rate_limiter(TokenBucket), _circuit_breaker, _retry_config, _metrics methods: get(), post(), health_check() |
| 185 | TokenBucket Component — Rate Limiting Algorithm | classDiagram | TokenBucket: _capacity, _tokens, _refill_rate, _last_refill methods: acquire(), try_acquire(), _refill(), wait_for_token() |
| 186 | CircuitBreaker Component — State Machine Implementation | classDiagram | CircuitBreaker: _state(CLOSED/OPEN/HALF_OPEN), _failure_count, _last_failure_time, _recovery_timeout methods: call(), record_success(), record_failure(), _check_state() |
| 187 | HealthMonitor Component — Provider Health Tracking | classDiagram | HealthMonitor: _provider_states(dict), _error_counts methods: record_result(), get_status(), update_health(), calculate_adaptive_params() |
| 188 | PaginatedFetcherMixin Component — Generic Pagination | classDiagram | PaginatedFetcherMixin: _fetch_page(), _extract_next_cursor(), _has_more_pages(), fetch() async generator yielding pages |
| 189 | BronzeWriter Internal Structure | classDiagram | BronzeWriter: _base_path, _compressor methods: write_bronze(), _create_batch_file(), _write_jsonl(), _compress_zstd(), _write_manifest() |
| 190 | SilverWriter Internal Structure | classDiagram | SilverWriter(BaseDeltaWriter): _table_path, _primary_keys methods: write_silver(), _merge_upsert(), _append(), _delete_and_insert(), vacuum() |
| 191 | GoldWriter Internal Structure — 946 LOC | classDiagram | GoldWriter(BaseDeltaWriter): _csv_exporter, _audit_port methods: write_gold(), _overwrite(), _scd2(), _append(), _validate_strict(), export_csv() |
| 192 | BaseDeltaWriter Internal Structure | classDiagram | BaseDeltaWriter: _table_uri, _arrow_converter methods: _write_delta(), _read_delta(), _get_schema(), _sort_dataframe(), vacuum() |
| 193 | DeltaReader Component — Query Interface | classDiagram | DeltaReader: read_table(), read_with_filter(), get_table_info(), list_partitions(), get_schema(), count_rows() |
| 194 | MetadataWriter Component — Output Metadata | classDiagram | MetadataWriter: write_metadata(), build_metadata(), _compute_stats() for each medallion layer output |
| 195 | RetentionManager Component — Data Lifecycle | classDiagram | RetentionManager: enforce_retention(), _check_bronze_age(), _check_quarantine_age(), _vacuum_delta_tables() |
| 196 | MemoryLock Internal State Machine | classDiagram | MemoryLock: _locks(dict), _owners(dict), _ttls(dict) methods: acquire(), release(), renew(), is_locked(), validate_owner() |
| 197 | LocalCheckpoint Component — File-Based State | classDiagram | LocalCheckpoint: _checkpoint_dir methods: save(), load(), delete(), exists(), _read_json(), _write_json_atomic() |
| 198 | UnifiedQuarantine Component | classDiagram | UnifiedQuarantine: _base_path methods: write(), read_sample(), count(), purge(), replay(), _build_entry() |
| 199 | StructlogLogger Component — LoggerPort Implementation | classDiagram | StructlogLogger implementing LoggerPort: info(), warning(), error(), debug(), bind(), unbind() — JSON output |
| 200 | PrometheusMetrics Component — MetricsPort Implementation | classDiagram | PrometheusMetrics: _counters, _histograms, _gauges methods: increment_counter(), observe_histogram(), set_gauge(), start_server() |
| 201 | NoOpTracing Component — TracingPort Null Object | classDiagram | NoOpTracing: get_tracer()→NoOpTracer, start_span()→NoOpSpan — all methods are no-ops, zero overhead |
| 202 | PanderaValidator Component — ValidationPort Implementation | classDiagram | PanderaValidator: validate_silver(), validate_gold(), _apply_schema(), _collect_errors(), _build_report() |
| 203 | PIIHasher Component — SecurityPort Implementation | classDiagram | PIIHasher: hash_field(), hash_email(), hash_name(), _sha256_with_salt() — RULES.md §5.4 compliance |
| 204 | PipelineConfigLoader Component — YAML to Domain Config | classDiagram | PipelineConfigLoader: load(), _resolve_paths(), _merge_base(), _validate(), _apply_defaults() → PipelineConfig |
| 205 | DQConfigLoader Component — DQ Rules from YAML | classDiagram | DQConfigLoader: load(), _parse_field_validations(), _parse_thresholds(), _merge_overrides() → DQConfig |
| 206 | FilterConfigLoader Component — Filter Rules from YAML | classDiagram | FilterConfigLoader: load(), _parse_column_filters(), _parse_row_filters() → FilterConfig |
| 207 | GenericPipelineFactory Component | classDiagram | GenericPipelineFactory: _pipeline_name, _pipeline_class, _transformer_class, _gold_schema methods: create(), _assemble_pipeline() |
| 208 | RunnerFactory Component | classDiagram | RunnerFactory: create_runner() → PipelineRunner with all services injected via ServicesFactory |
| 209 | ServicesFactory/ServicesBuilder Component | classDiagram | ServicesBuilder: progressive builder → creates PipelineServices bundle with all required and optional ports |
| 210 | StorageFactory Component | classDiagram | StorageFactory: create() → StoragePort from BronzeWriter + SilverWriter + GoldWriter + config |
| 211 | HttpClientFactory Component | classDiagram | HttpClientFactory: create(provider) → UnifiedHTTPClient configured with provider-specific rate limits and circuit breaker |
| 212 | DataSourceFactory Component | classDiagram | DataSourceFactory: create(provider, config) → DataSourcePort implementation for the given provider |
| 213 | DQServicesFactory Component | classDiagram | DQServicesFactory: create() → DQ analyzers (Bronze, Silver, Gold), DQ monitor, DQ report writer, DQ report service |
| 214 | EnrichmentCoordinator Component | classDiagram | EnrichmentCoordinator: run_enrichers() → asyncio.gather(enricher1, enricher2, ...) with timeout per enricher |
| 215 | MergeService Component | classDiagram | MergeService: merge() → LEFT OUTER JOIN seed+enrichers, conflict_resolution, column_ordering, trash_filtering |
| 216 | CompositePipelineRunner Component | classDiagram | CompositePipelineRunner: run() → seed_pipeline → dependency_pipelines → enrichment_coordinator → merge_service → gold_write |
| 217 | KeyExtractorService Component | classDiagram | KeyExtractorService: extract_keys(seed_silver_table, join_keys) → list of key values for enricher filtering |
| 218 | DependencyCoordinator Component | classDiagram | DependencyCoordinator: run_dependencies() → sequential execution of dependency pipelines with chained key extraction |
| 219 | CrossValidator Component — Composite Data Quality | classDiagram | CrossValidator: validate_merge() → check join coverage, detect orphan records, verify merge completeness |
| 220 | AnomalyDetector Component — DQ Anomaly Detection | classDiagram | AnomalyDetector: detect() → z-score calculation vs 30-day baseline, severity classification, alert generation |

## Interaction (221–270)

| # | Name | Type | Description |
|---|------|------|-------------|
| 221 | CLI Run Command → PipelineRunner Full Interaction | sequenceDiagram | CLI run → parse args → load config → bootstrap_pipeline → runner.run() → observer → executor → finalize |
| 222 | CLI Run-All Command — Sequential Multi-Pipeline Execution | sequenceDiagram | CLI run-all → iterate pipeline_names → for each: bootstrap → run → report → aggregate results |
| 223 | CLI Run-Composite Command — Composite Pipeline Invocation | sequenceDiagram | CLI run-composite → load CompositeConfig → bootstrap_composite_runner → seed → enrich → merge → report |
| 224 | CLI Health Command — Provider Health Check Aggregation | sequenceDiagram | CLI health → for each provider: create adapter → health_check() → collect statuses → display table |
| 225 | CLI Export Command — Gold to CSV Export Flow | sequenceDiagram | CLI export → DeltaReader.read_table(gold) → GoldWriter.export_csv() → write CSV file |
| 226 | CLI Quarantine Inspect — Error Sample Display | sequenceDiagram | CLI quarantine inspect → UnifiedQuarantine.read_sample(pipeline, limit) → format table → display |
| 227 | CLI Quarantine Replay — Reprocess Failed Records | sequenceDiagram | CLI quarantine replay → read entries → re-validate → pass: move to Silver → fail: update status |
| 228 | CLI Maintenance — VACUUM and Cleanup | sequenceDiagram | CLI maintenance → RetentionManager.enforce_retention() → BronzeCleanup → SilverVACUUM → GoldVACUUM |
| 229 | PipelineRunner ↔ LockManager Interaction Detail | sequenceDiagram | Runner: request lock → LockManager: generate key → MemoryLock.acquire(key, owner, ttl) → success/fail → HeartbeatTask.start() |
| 230 | PipelineRunner ↔ PreflightService Interaction | sequenceDiagram | Runner: run_preflight() → Preflight: check_config → check_storage_paths → check_data_source_health → check_lock_availability → report |
| 231 | PipelineRunner ↔ BatchExecutor Interaction | sequenceDiagram | Runner: execute() → BatchExecutor: iterate batches → for each: extract → transform → validate → write → update checkpoint |
| 232 | PipelineRunner ↔ PostrunService Interaction | sequenceDiagram | Runner: run_postrun() → PostrunService: run_dq_checks → vacuum → write_dq_report → cleanup → publish_metrics |
| 233 | BatchExecutor ↔ DataSourcePort Fetch Interaction | sequenceDiagram | BatchExecutor: async for page in data_source.fetch() → create batch → BatchTransformer.transform(batch) → BatchWriter.write() |
| 234 | BatchTransformer ↔ BaseTransformer Interaction | sequenceDiagram | BatchTransformer: transform(batch) → BaseTransformer.transform() → _transform_impl() → normalize → add metadata → hash |
| 235 | BatchWriter ↔ Storage Writers Interaction | sequenceDiagram | BatchWriter: write(batch) → BronzeWriter.write_bronze() → SilverWriter.write_silver() → GoldWriter.write_gold() |
| 236 | BatchWriter ↔ QuarantineManager Interaction | sequenceDiagram | BatchWriter: validate records → failures → QuarantineManager.route_failed_records() → UnifiedQuarantine.write() |
| 237 | DataSourcePort ↔ UnifiedHTTPClient Request Flow | sequenceDiagram | Adapter.fetch() → HTTPClient.get(url, params) → RateLimiter.acquire() → CircuitBreaker.call() → httpx.get() → response |
| 238 | UnifiedHTTPClient ↔ RateLimiter ↔ CircuitBreaker Triple Interaction | sequenceDiagram | HTTPClient: request → RateLimiter.wait() → CircuitBreaker.before_call() → httpx.request() → CircuitBreaker.record_result() → return |
| 239 | CircuitBreaker ↔ HealthMonitor State Sync | sequenceDiagram | CircuitBreaker trips → HealthMonitor.update(UNHEALTHY) → adaptive batch_size reduction → CircuitBreaker recovers → HealthMonitor.update(DEGRADED→HEALTHY) |
| 240 | PipelineObserver ↔ MetricsPort ↔ PrometheusMetrics Chain | sequenceDiagram | Observer.enter() → MetricsPort.increment(started) → PrometheusMetrics.inc(bioetl_pipeline_runs_total) |
| 241 | HeartbeatTask ↔ MemoryLock Renewal Cycle | sequenceDiagram | HeartbeatTask._loop: sleep(30s) → MemoryLock.renew(key, owner_id) → success: continue → fail: shutdown handler |
| 242 | ShutdownHandler ↔ PipelineRunner Signal Propagation | sequenceDiagram | SIGTERM received → ShutdownHandler.handle() → set _shutting_down=True → BatchExecutor checks flag → finish current batch → save checkpoint → exit(0) |
| 243 | PanderaValidator ↔ Domain Schemas Interaction | sequenceDiagram | Validator.validate_silver(df) → load ActivitySilverSchema → schema.validate(df) → collect errors → return ValidationResult |
| 244 | PIIHasher ↔ SilverWriter PII Processing | sequenceDiagram | SilverWriter.write_silver() → check PII fields → PIIHasher.hash_field(value, salt) → sha256 → replace in DataFrame → write |
| 245 | PipelineConfigLoader ↔ DQConfigLoader ↔ FilterConfigLoader Assembly | sequenceDiagram | PipelineConfigLoader.load() → resolve dq_config_file → DQConfigLoader.load() → resolve filter_config_file → FilterConfigLoader.load() |
| 246 | CompositeRunner ↔ EnrichmentCoordinator Fan-Out | sequenceDiagram | CompositePipelineRunner → EnrichmentCoordinator.run_enrichers([crossref, pubmed, openalex]) → asyncio.gather → collect results |
| 247 | MergeService ↔ FieldGroupRegistry Column Ordering | sequenceDiagram | MergeService.merge() → FieldGroupRegistry.get_ordered_columns() → exclude TRASH → sort by group priority → apply to output |
| 248 | DependencyCoordinator ↔ KeyExtractor Chained Key Flow | sequenceDiagram | DependencyCoordinator: run dep1 → KeyExtractor.extract_keys(dep1_silver) → run dep2(keys_from_dep1) → KeyExtractor.extract_keys(dep2_silver) |
| 249 | CLI ↔ Bootstrap ↔ Factory Triple-Layer Wiring | sequenceDiagram | CLI.run() → entrypoints.bootstrap_pipeline(name, config) → Factories.create_all() → assemble PipelineRunner → return |
| 250 | Bronze→Silver Batch Processing Interaction | sequenceDiagram | Read Bronze JSONL → decompress zstd → parse records → BatchTransformer → validate → SilverWriter.merge_upsert() |
| 251 | Silver→Gold Transformation Interaction | sequenceDiagram | Read Silver Delta → transform_for_gold() → exclude JSON fields → Pandera strict validate → GoldWriter.write() |
| 252 | ErrorClassifier ↔ RetryConfig Decision | sequenceDiagram | HTTP error → ErrorClassifier.classify(status_code) → RECOVERABLE → RetryConfig.calculate_delay(attempt) → wait → retry |
| 253 | ChemblAdapter ↔ EntityMapper URL Construction | sequenceDiagram | ChemblAdapter.fetch(entity_type) → EntityMapper.get_resource_url(entity_type) → build params → HTTPClient.get(url, params) |
| 254 | Provider Adapter Registration in Composition | sequenceDiagram | App startup → registration.py → ProviderRegistry.register("chembl", ChemblAdapter, config) → repeat for all 7 providers |
| 255 | RunType-Based Clear Policy Interaction | sequenceDiagram | Runner: check run_type → REBUILD/BACKFILL: MedallionLifecycle.clear_silver() + clear_gold() → INCREMENTAL: skip clearing |
| 256 | Checkpoint Resume Flow After Shutdown | sequenceDiagram | Pipeline restart → CheckpointManager.load() → found: log "Resuming from X" → BatchExecutor.start_from(checkpoint.last_id + 1) |
| 257 | Data Source Health Check → Pipeline Pause Decision | sequenceDiagram | HealthMonitor.check_all() → provider UNHEALTHY → pause pipeline → wait → re-check → DEGRADED → resume with reduced batch size |
| 258 | Anomaly Detection ↔ Alerting Chain | sequenceDiagram | AnomalyDetector.detect(current_metrics, baseline) → anomaly found → AlertChannel.send(alert) → webhook or logger |
| 259 | BronzeWriter ↔ LineageLog Recording | sequenceDiagram | BronzeWriter.write_bronze() → generate batch_id → record file_paths → write lineage_log entry → return batch_id for Silver FK |
| 260 | Delta Lake Time Travel Query Sequence | sequenceDiagram | DeltaReader.read_table(as_of_version=N) → Delta Log → resolve version N → read only relevant parquet files → return DataFrame |
| 261 | MedallionLifecycleService Clear+Rebuild Sequence | sequenceDiagram | MedallionLifecycle: validate run_type → clear_silver(table) → clear_gold(table) → log cleared → proceed with pipeline |
| 262 | Filtered ID Loading and Deduplication | sequenceDiagram | FilteredDataSource: read filter_file → parse IDs → deduplicate → log stats (loaded, duplicates) → chunk for batched fetch |
| 263 | CompositePipelineRunner Checkpoint Save/Resume | sequenceDiagram | Composite: seed completed → save checkpoint(phase=enrichment) → enricher3 fails → restart → load checkpoint → skip seed → resume enricher3 |
| 264 | GoldWriter SCD2 History Management | sequenceDiagram | New version detected → existing record: set valid_to=now → insert new record: valid_from=now, valid_to=null → Delta merge |
| 265 | Config Inheritance — _base.yaml to Entity Config | sequenceDiagram | Load _base.yaml → load entity.yaml → merge (entity overrides base) → apply dq_overrides → resolve convention paths → final PipelineConfig |
| 266 | Publication Validation Strategy 5-Level Pipeline (ADR-033) | sequenceDiagram | Record → L1:Pandera → L2:CrossField (page_start<page_end) → L3:DOI verify → L4:Year range → L5:Title similarity |
| 267 | Metrics Collection — Request to Prometheus Scrape | sequenceDiagram | Pipeline event → MetricsPort.observe() → PrometheusMetrics.observe_histogram() → /metrics endpoint → Prometheus scrape |
| 268 | Lock Contention Handling — Wait vs Fail | sequenceDiagram | Request lock → already held → check --wait-for-lock → if set: poll with timeout → if not: fail immediately with LockError |
| 269 | Composite Pipeline Cross-Validation After Merge | sequenceDiagram | MergeService.merge() → CrossValidator.validate() → check join rates → check orphans → check coverage → report quality |
| 270 | Deduplication Service in Composite Merge | sequenceDiagram | After merge → DeduplicationService.deduplicate() → identify duplicate DOIs/PMIDs → keep highest-quality source → remove duplicates |

## Lifecycle (271–310)

| # | Name | Type | Description |
|---|------|------|-------------|
| 271 | Pipeline Run Lifecycle — From Config to Completion | stateDiagram | CONFIGURED→LOCKED→PREFLIGHT→EXTRACTING→TRANSFORMING→VALIDATING→LOADING→POSTRUN→COMPLETED or FAILED |
| 272 | Batch Lifecycle States | stateDiagram | CREATED→EXTRACTING→EXTRACTED→TRANSFORMING→TRANSFORMED→VALIDATING→VALIDATED→WRITING→WRITTEN→COMMITTED |
| 273 | Lock Lifecycle States | stateDiagram | AVAILABLE→ACQUIRED(owner_id)→HEARTBEAT_RENEWED→RELEASED or EXPIRED(TTL) or FORCED_RELEASE(max_duration) |
| 274 | Checkpoint Lifecycle | stateDiagram | NONE→CREATED(first_batch)→UPDATED(each_batch)→STALE(detected)→RESUMED(--resume)→DELETED(success) |
| 275 | QuarantineEntry DQ Status Lifecycle | stateDiagram | NEW→UNDER_REVIEW→{IGNORED or REPROCESSED or EXPIRED} with transitions and triggers for each |
| 276 | Provider Health Status Transitions | stateDiagram | HEALTHY→(1-2 errors)→DEGRADED→(≥3 errors)→UNHEALTHY→(1 success)→DEGRADED→(0 errors 5min)→HEALTHY |
| 277 | Circuit Breaker Recovery Cycle Detail | stateDiagram | CLOSED(normal)→(threshold failures)→OPEN(reject all)→(timeout)→HALF_OPEN(probe 1 request)→(success)→CLOSED or (fail)→OPEN |
| 278 | Composite Pipeline Phase Lifecycle | stateDiagram | INIT→SEED_RUNNING→SEED_COMPLETE→DEPS_RUNNING→DEPS_COMPLETE→ENRICHING→ENRICHMENT_DONE→MERGING→MERGED→GOLD_WRITING→DONE |
| 279 | Enricher Lifecycle Within Composite | stateDiagram | PENDING→RUNNING→{COMPLETED or FAILED(timeout) or SKIPPED(not_required)} |
| 280 | Schema Drift Event Lifecycle | stateDiagram | DETECTED→CLASSIFIED(info/critical)→OWNER_ASSIGNED(critical)→{RESOLVED(48h) or BLOCKED(>48h→blocks release)} |
| 281 | Data Retention Lifecycle — Bronze | stateDiagram | ACTIVE(0-90 days)→ARCHIVED(after 90 days)→DELETED(after archive period) |
| 282 | Delta Lake Table Version Lifecycle | stateDiagram | V0(initial)→V1(first write)→VN(merge/append)→VACUUMED(old versions cleaned) with Time Travel window |
| 283 | Pipeline Services Async Lifecycle | stateDiagram | CREATED→ENTERED(async with __aenter__)→ACTIVE→EXITING(__aexit__)→CLOSED(aclose all) — idempotent |
| 284 | HTTP Request Lifecycle Through Adapter Stack | stateDiagram | QUEUED→RATE_LIMITED(waiting)→SENT→{SUCCESS or RETRY(backoff)→SENT or CB_OPEN(rejected) or TIMEOUT(error)} |
| 285 | Alert Lifecycle — Detection to Resolution | stateDiagram | DETECTED→SENT(webhook/logger)→ACKNOWLEDGED→{RESOLVED or ESCALATED} with cooldown between repeated alerts |
| 286 | DQ Report Lifecycle | stateDiagram | GENERATED(per batch)→AGGREGATED(per run)→WRITTEN(to file)→PUBLISHED(metrics) |
| 287 | Gold SCD2 Record Lifecycle | stateDiagram | CURRENT(valid_to=null)→SUPERSEDED(valid_to=update_time, new record created with valid_from=update_time) |
| 288 | Token Bucket Refill Lifecycle | stateDiagram | FULL(capacity tokens)→DRAINING(requests consume)→EMPTY(wait for refill)→REFILLING(rate-based)→FULL |
| 289 | Pipeline Error Recovery Lifecycle | stateDiagram | RUNNING→ERROR→CLASSIFIED→{RETRY(recoverable) or QUARANTINE(dq) or FAIL(critical)} retry→RUNNING or FAIL |
| 290 | Heartbeat Monitor Lifecycle | stateDiagram | STARTED→TICKING(every 30s)→RENEWED(lock TTL extended)→{STOPPED(normal) or FAILED(lock lost→crash)} |
| 291 | Configuration Loading Lifecycle | stateDiagram | RAW_YAML→PARSED→VALIDATED(Pydantic)→MERGED(base+entity)→RESOLVED(convention paths)→FROZEN(immutable) |
| 292 | Graceful Shutdown Lifecycle | stateDiagram | RUNNING→SIGNAL_RECEIVED(SIGTERM/SIGINT)→DRAINING(finish batch)→CHECKPOINT_SAVED→LOCK_RELEASED→EXIT(0) |
| 293 | Bronze File Lifecycle | stateDiagram | TEMP_CREATED→WRITTEN→COMPRESSED(zstd)→SYNCED(fsync)→RENAMED(atomic)→MANIFESTED→AGED→EXPIRED→DELETED |
| 294 | Composite Checkpoint Lifecycle | stateDiagram | NONE→SEED_CHECKPOINT→DEPS_CHECKPOINT→ENRICHMENT_CHECKPOINT→MERGE_CHECKPOINT→COMPLETED→DELETED |
| 295 | PipelineRun Aggregate Lifecycle (DDD) | stateDiagram | CREATED(new PipelineRun)→BATCHES_ADDED→EVENTS_RECORDED→COMPLETED or FAILED — aggregate tracks all state |
| 296 | Batch Aggregate Lifecycle (DDD) | stateDiagram | CREATED(new Batch)→RECORDS_ADDED→PROCESSED→{COMMITTED or PARTIALLY_FAILED}→FINALIZED |
| 297 | Filter ID Loading Lifecycle | stateDiagram | FILE_READ→IDS_PARSED→DEDUPLICATED→CHUNKED→FETCHING→{ALL_FETCHED or PARTIAL_FAIL} |
| 298 | Dependency Pipeline Lifecycle in Composite | stateDiagram | PENDING→KEY_EXTRACTION→KEYS_READY→RUNNING→{COMPLETED(silver written) or FAILED}→NEXT_DEPENDENCY |
| 299 | Data Contract Version Lifecycle | stateDiagram | DRAFT→PUBLISHED(JSON Schema)→ACTIVE→DEPRECATED(14 days)→REMOVED(major version bump) |
| 300 | Silver Write Mode Decision Lifecycle | stateDiagram | CONFIG_LOADED→MODE_SELECTED(MERGE/APPEND/DELETE)→VALIDATED(no OVERWRITE allowed)→EXECUTED→COMMITTED |
| 301 | Gold Write Mode Decision Lifecycle | stateDiagram | CONFIG_LOADED→MODE_SELECTED(OVERWRITE/APPEND/SCD2)→SCD2_CONFIG_LOADED(if SCD2)→EXECUTED→COMMITTED |
| 302 | Architecture Review Lifecycle (REQ-ARCH-040) | stateDiagram | DISCOVERED→FIRST_VERIFICATION(grep, wc)→CONFIRMED/REJECTED→SECOND_VERIFICATION(documentation)→REPORTED |
| 303 | ADR Lifecycle | stateDiagram | PROPOSED→DISCUSSED→{ACCEPTED or REJECTED or DEFERRED}→SUPERSEDED(by newer ADR) |
| 304 | Game Day DR Exercise Lifecycle | stateDiagram | PLANNED→SCHEDULED→EXECUTED(simulate failure)→RECOVERED(within RTO)→REVIEWED→DOCUMENTED |
| 305 | Schema Evolution Lifecycle | stateDiagram | CHANGE_PROPOSED→CLASSIFIED(minor/major)→{MINOR:add_nullable or MAJOR:deprecation_period}→DEPLOYED→OLD_REMOVED |
| 306 | Metrics Server Lifecycle | stateDiagram | NOT_STARTED→STARTING(double-check lock)→RUNNING(port bound)→SCRAPE_READY→SHUTDOWN(graceful) |
| 307 | Environment Promotion Lifecycle | stateDiagram | DEV(local fixtures)→STAGING(prod-like data)→PROD(CI/CD deploy only) with gates at each transition |
| 308 | Retry Attempt Lifecycle | stateDiagram | ATTEMPT_1→FAILED→BACKOFF(1s+jitter)→ATTEMPT_2→FAILED→BACKOFF(2s+jitter)→ATTEMPT_3→{SUCCESS or GIVE_UP} |
| 309 | Publication Composite Enrichment Lifecycle | stateDiagram | SEED_DONE→KEYS_EXTRACTED(DOIs,PMIDs)→CROSSREF_ENRICHING→PUBMED_ENRICHING→OPENALEX_ENRICHING→S2_ENRICHING→ALL_DONE→MERGING |
| 310 | Pipeline Warmup and Cooldown Lifecycle | stateDiagram | COLD_START→CONFIG_LOAD→HEALTH_CHECK→LOCK_ACQUIRE→WARM→RUNNING→COOLDOWN→METRICS_FLUSH→LOCK_RELEASE→STOPPED |

## Provider (311–360)

| # | Name | Type | Description |
|---|------|------|-------------|
| 311 | ChEMBL Adapter — 14 Entity Types Supported | flowchart | ChemblAdapter with entity_mapper routing to 14 endpoints: activity, assay, molecule, target, document, cell_line, etc. |
| 312 | ChEMBL API Pagination — Offset-Based | sequenceDiagram | fetch(offset=0, limit=1000) → response(total_count, results) → offset+=limit → repeat until offset≥total_count |
| 313 | ChEMBL Entity Mapper — entity_type to API Resource Mapping | flowchart | activity→activity, compound→molecule, publication→document, protein_class→protein_classification — full mapping table |
| 314 | ChEMBL Query Parameter Construction | flowchart | _build_params(): format=json + limit + offset + optional {field}__in=ID1,ID2 for filter_ids |
| 315 | ChEMBL Health Check — /status Endpoint Probe | sequenceDiagram | ChemblAdapter.health_check() → GET /chembl/api/data/status → parse response time → <5s:HEALTHY, >5s:DEGRADED, error:UNHEALTHY |
| 316 | ChEMBL Rate Limiting Strategy — No Explicit Limit | flowchart | ChEMBL has no explicit rate limit → TokenBucket(capacity=high) → polite delay between requests → adaptive on errors |
| 317 | ChEMBL Activity Entity — Field Map from API to Silver | flowchart | API fields: activity_id, assay_chembl_id, molecule_chembl_id, standard_value → Silver columns with types |
| 318 | ChEMBL Molecule Entity — Nested JSON Handling | flowchart | API: molecule_properties(nested), molecule_structures(nested) → flatten for Silver → exclude nested for Gold |
| 319 | ChEMBL Assay Entity — Confidence Score Processing | flowchart | API: assay_chembl_id, assay_type, confidence_score → normalize → Silver with confidence_score as int (nullable) |
| 320 | ChEMBL Target Entity — Component Relationship | flowchart | Target → has many TargetComponents → each has ProteinClass → hierarchical entity resolution |
| 321 | ChEMBL Publication Entity — Document to Publication Mapping | flowchart | API endpoint /document → domain entity ChemblPublication → extract DOI and PMID for composite enrichment |
| 322 | PubChem Adapter — Sync Library Wrapper Architecture | flowchart | PubChemAdapter(BaseSyncAdapter) → pubchempy sync call → ThreadPoolExecutor → async wrapper → yield results |
| 323 | PubChem Compound CID Resolution | flowchart | Input CIDs → PUG REST /compound/cid/{cid}/property → batch request → parse response → yield compound records |
| 324 | PubChem Rate Limiting — 5 req/sec TokenBucket | flowchart | TokenBucket(capacity=5, refill_rate=5/sec) → acquire before each request → wait if empty → respect NCBI policy |
| 325 | PubChem Health Check — Lightweight Property Query | sequenceDiagram | PubChemAdapter.health_check() → GET /rest/pug/compound/cid/2244/property/MolecularFormula/JSON → parse → status |
| 326 | UniProt Adapter — REST API with PaginatedFetcherMixin | flowchart | UniProtAdapter(BaseHttpAdapter + PaginatedFetcherMixin) → cursor-based pagination → 100 req/sec with API key |
| 327 | UniProt ID Mapping — Cross-Reference Resolution | sequenceDiagram | Submit mapping job (from=UniProtKB, to=ChEMBL) → job_id → poll /idmapping/status/{id} → download results |
| 328 | UniProt Protein Entity — Sequence and Annotation Extraction | flowchart | UniProt JSON → extract sequence, organism, organism_id, function_description → Silver protein record |
| 329 | UniProt Health Check — Search Probe | sequenceDiagram | UniProtAdapter.health_check() → GET /uniprot/search?query=test&size=1 → response time → status classification |
| 330 | PubMed Adapter — E-utilities Integration | flowchart | PubMedAdapter → esearch(term) → get PMIDs → efetch(PMIDs) → parse XML → yield publication records |
| 331 | PubMed Pagination — retstart/retmax Pattern | sequenceDiagram | esearch(retstart=0, retmax=500) → count → efetch(retstart=0) → increment retstart → repeat |
| 332 | PubMed Rate Limiting — 3 req/sec (10 with API key) | flowchart | Check NCBI_API_KEY → present: TokenBucket(10/sec) → absent: TokenBucket(3/sec) → respect E-utilities policy |
| 333 | PubMed Health Check — E-info Probe | sequenceDiagram | PubMedAdapter.health_check() → einfo(db="pubmed") → parse response → status |
| 334 | PubMed MeSH Terms Extraction Pipeline | flowchart | XML MeshHeadingList → extract DescriptorName, QualifierName → normalize → Silver mesh_terms column |
| 335 | CrossRef Adapter — Works API with Cursor Pagination | flowchart | CrossRefAdapter(BaseHttpAdapter + PaginatedFetcherMixin) → GET /works?filter=doi:{doi} → cursor-based pagination |
| 336 | CrossRef DOI Resolution Flow | sequenceDiagram | Input DOIs → CrossRefAdapter.fetch(filter_ids=DOIs) → /works?filter=doi:10.1234/... → parse → yield records |
| 337 | CrossRef Rate Limiting — Polite Pool with Email | flowchart | Include mailto: header → get polite pool access (50 req/sec) → TokenBucket(50/sec) → respect Crossref policy |
| 338 | CrossRef Health Check — Root Endpoint Probe | sequenceDiagram | CrossRefAdapter.health_check() → GET /works?rows=1 → response time → status |
| 339 | CrossRef Publication Fields Mapping | flowchart | API: DOI, title, author, container-title, issued, is-referenced-by-count → Silver column mapping |
| 340 | OpenAlex Adapter — Works API Integration | flowchart | OpenAlexAdapter(BaseHttpAdapter + PaginatedFetcherMixin) → GET /works?filter=doi:{doi} → per-page pagination |
| 341 | OpenAlex Rate Limiting — 10 req/sec Polite Pool | flowchart | Include email in config → polite pool → TokenBucket(10/sec) → OpenAlex fair usage |
| 342 | OpenAlex Health Check — Generic Probe | sequenceDiagram | OpenAlexAdapter.health_check() → GET /works?per_page=1 → response time → status |
| 343 | OpenAlex Concepts and Institutions Extraction | flowchart | API: concepts[{id, display_name, score}], authorships[{institutions}] → flatten → Silver columns |
| 344 | SemanticScholar Adapter — Paper API Integration | flowchart | SemanticScholarAdapter(BaseHttpAdapter + PaginatedFetcherMixin) → GET /paper/{id} → token-based pagination |
| 345 | SemanticScholar Rate Limiting — 100 req/5min | flowchart | TokenBucket(rate=100/300sec) → very conservative → with API key: 1 req/sec → sliding window |
| 346 | SemanticScholar Health Check — Generic Probe | sequenceDiagram | SemanticScholarAdapter.health_check() → GET /paper/search?query=test&limit=1 → response time → status |
| 347 | SemanticScholar TLDR and Embedding Fields | flowchart | API: tldr{text}, embedding{vector} → Silver: tldr_text(string), embedding(array) |
| 348 | Provider Comparison — Authentication Methods | flowchart | ChEMBL: Public → PubChem: Public → UniProt: API Key → PubMed: API Key → CrossRef: Email → OpenAlex: Email → S2: API Key |
| 349 | Provider Comparison — Rate Limit Strategies | flowchart | ChEMBL: none → PubChem: 5/s → UniProt: 100/s → PubMed: 3-10/s → CrossRef: 50/s → OpenAlex: 10/s → S2: 0.33/s |
| 350 | Provider Comparison — Pagination Methods | flowchart | ChEMBL: offset → PubChem: chunked CIDs → UniProt: cursor → PubMed: retstart → CrossRef: cursor → OpenAlex: per-page → S2: token |
| 351 | Provider Comparison — Entity Coverage Matrix | flowchart | ChEMBL: 14 entities → PubChem: 1 → UniProt: 2 (protein + idmapping) → PubMed: 1 → CrossRef: 1 → OpenAlex: 1 → S2: 1 |
| 352 | Provider Error Response Handling Comparison | flowchart | 429: all providers → retry-after → 403: auth issue → 500/502/504: server error → retry with backoff |
| 353 | Provider-Specific Transformer Class Hierarchy | classDiagram | BaseTransformer → BaseChemblTransformer → Activity/Assay/Molecule/Target; BasePublicationTransformer → PubMed/CrossRef/OpenAlex/S2 |
| 354 | ChEMBL Multi-Entity Pipeline Graph | flowchart | 14 ChEMBL pipelines with shared adapter, independent transformers and configs, common storage factory |
| 355 | Publication Provider Coverage Overlap Analysis | flowchart | DOI coverage: CrossRef (highest) → OpenAlex → ChEMBL → S2; PMID coverage: PubMed → ChEMBL → S2 |
| 356 | Provider Adapter Factory Wiring | sequenceDiagram | DataSourceFactory.create("chembl") → HttpClientFactory.create("chembl") → ChemblAdapter(http_client, logger) |
| 357 | Provider-Specific Config Loading | flowchart | configs/sources/{provider}.yaml → rate_limit, base_url, auth_type, health_check_endpoint per provider |
| 358 | Provider Response Normalization — Heterogeneous API Formats | flowchart | ChEMBL: JSON {results:[]} → PubChem: JSON {PropertyTable:{}} → UniProt: JSON-LD → PubMed: XML → all → dict records |
| 359 | Provider Silver Table Naming Convention | flowchart | silver/{provider}/{entity}/ — chembl/activity, pubchem/compound, uniprot/protein, pubmed/publication |
| 360 | Provider Gold Schema Mapping — Domain to Pandera | flowchart | Per provider: domain entity fields → Pandera DataFrameModel → Series[type] with nullable, coerce, regex constraints |

## Configuration (361–390)

| # | Name | Type | Description |
|---|------|------|-------------|
| 361 | Pipeline Config YAML Structure | flowchart | pipeline_name, provider, entity_type, version, primary_keys, silver_table, gold_table, sink{silver, gold}, dq_overrides |
| 362 | _base.yaml Inheritance Mechanism | flowchart | configs/pipelines/_base.yaml → defaults for all pipelines → entity.yaml overrides specific fields → merged config |
| 363 | Source Config YAML Structure | flowchart | configs/sources/{provider}.yaml: base_url, rate_limit, auth_type, health_check_endpoint, load_strategy |
| 364 | DQ Config YAML Structure (ADR-027) | flowchart | configs/quality/entities/{provider}/{entity}.yaml: field_validations[{field, type, min, max, nullable}], thresholds |
| 365 | Filter Config YAML Structure (ADR-028) | flowchart | configs/filters/entities/{provider}/{entity}.yaml: column_filters, row_filters, include/exclude patterns |
| 366 | Composite Pipeline Config YAML Structure | flowchart | configs/pipelines/composite/{name}.yaml: seed, dependencies[], enrichers[], merge{strategy, conflict_resolution} |
| 367 | Data Schema Config YAML Structure (ADR-034) | flowchart | configs/schemas/{provider}/{entity}.yaml: column_groups, silver{include_groups, rename_fields}, gold{include_groups, exclude_fields, rename_fields} |
| 368 | Field Groups Config YAML Structure | flowchart | configs/composite/field_groups/publication.yaml: groups with name, fields, provider_order — 106 base fields |
| 369 | RuntimeConfig Parameters Map | flowchart | RuntimeConfig: batch_size, heartbeat_interval(30s), lock_ttl(90s), max_lock_duration(4h), resume flag, run_type |
| 370 | PipelineConfig to Runtime Resolution | flowchart | YAML → PipelineConfig(frozen) → merge with CLI args → RuntimeConfig → passed to PipelineRunner |
| 371 | DQ Override Merge Strategy | flowchart | Entity DQ config (base rules) + Pipeline dq_overrides (field-specific) → merged DQConfig → applied during validation |
| 372 | Sink Configuration — Silver and Gold Write Settings | flowchart | sink.silver: primary_key, sort_by, write_mode, partition_by → sink.gold: sort_by, write_mode, scd_config |
| 373 | Convention-Based Path Resolution Algorithm | flowchart | pipeline_name → split by _ → provider + entity → derive: source_file, dq_config, filter_config, sink paths automatically |
| 374 | Environment Variable Configuration | flowchart | BIOETL_{PROVIDER}_{KEY} pattern: BIOETL_PUBCHEM_API_KEY, BIOETL_PUBMED_API_KEY, BIOETL_METRICS_PORT |
| 375 | Config Validation Pipeline | flowchart | YAML → parse → Pydantic model validation → type coercion → constraint checks → frozen dataclass → ready |
| 376 | ChEMBL Pipeline Configs — 14 Entity Configurations | flowchart | configs/pipelines/chembl/: activity.yaml, assay.yaml, molecule.yaml, target.yaml, ... — 14 files with shared base |
| 377 | Composite Config Dependencies Section | flowchart | dependencies: [{pipeline, join_keys, key_source, filter_field, required, timeout_seconds, silver_table}] — chained resolution |
| 378 | MergeConfig Parameters | flowchart | MergeConfig: strategy(left_outer/inner/union), conflict_resolution, preserve_all_sources, column_groups |
| 379 | SCD Config Parameters for Gold | flowchart | scd_config: key_columns, valid_from_column, valid_to_column, current_flag_column — for SCD Type 2 |
| 380 | Config File Discovery and Loading Order | flowchart | Working dir → configs/ → scan providers → load _base → load entities → resolve references → validate all |
| 381 | Silver Partition Configuration | flowchart | partition_by: [] (none) → ["year", "month"] → ["organism"] → Silver table directory structure per config |
| 382 | Gold Sort Configuration | flowchart | sort_by: {columns: ["activity_id"], ascending: [true]} → deterministic write order → stable Delta files |
| 383 | Provider Registration Configuration | flowchart | composition/providers/registration.py → register_all_providers() → ProviderRegistry populated with creator functions |
| 384 | Logging Configuration — structlog Setup | flowchart | structlog config: JSON renderer, ISO timestamps, log level from env, run_id context binding |
| 385 | Metrics Configuration — Prometheus Port Setup | flowchart | BIOETL_METRICS_PORT env → default 8000 → PrometheusMetrics.start_server(port) → /metrics endpoint |
| 386 | DQ Thresholds Configuration | flowchart | soft_threshold: 5% → warning; hard_threshold: 20% → batch fail; configured per entity in DQ YAML |
| 387 | Circuit Breaker Configuration | flowchart | failure_threshold: 5, recovery_timeout: 300s, half_open_max_calls: 1 — per provider in source config |
| 388 | Retry Configuration | flowchart | max_attempts: 3, multiplier: 2.0, jitter: random(0.1,0.5), deterministic: true/false — in RetryConfig |
| 389 | Lock Configuration | flowchart | heartbeat_interval: 30s, lock_ttl: 90s (3x heartbeat), max_lock_duration: 4h — in RuntimeConfig |
| 390 | Health Check Configuration | flowchart | cache_duration: 30s, timeout: 5s, probe_type: lightweight GET — per provider adapter configuration |

## DomainModel (391–420)

| # | Name | Type | Description |
|---|------|------|-------------|
| 391 | Activity Value Object — Internal Structure | classDiagram | Activity: activity_id, assay_chembl_id, molecule_chembl_id, standard_value, standard_units, pchembl_value — frozen |
| 392 | DQMetrics Value Object — Quality Metrics Bundle | classDiagram | DQMetrics: null_rates(dict), unique_counts(dict), schema_violations(int), record_count(int), error_rate(float) |
| 393 | RunContext Value Object — Pipeline Execution Context | classDiagram | RunContext: run_id(UUID), run_type(RunType), started_at(datetime), pipeline_name(str) — immutable |
| 394 | CompoundIDs Value Object — Chemical Identifiers | classDiagram | CompoundIDs: chembl_id, pubchem_cid, inchi, inchi_key, smiles, canonical_smiles — value equality |
| 395 | TaxonomyID Value Object — Organism Classification | classDiagram | TaxonomyID: tax_id(int), organism_name(str), strain(str|None) — validated, immutable |
| 396 | PipelineRun Aggregate — Complete Structure | classDiagram | PipelineRun(root): run_id, pipeline_name, run_type, status, batches:list[Batch], events:list[DomainEvent], started_at, completed_at |
| 397 | Batch Aggregate — Record Container | classDiagram | Batch: batch_id, batch_number, records:list[dict], record_count, error_count, start_time, end_time, status |
| 398 | QuarantineEntry Aggregate — Failed Record Details | classDiagram | QuarantineEntry: _pipeline_name, _error_code, _payload(truncated 64KB), _payload_hash, _batch_id, _created_at, _dq_status |
| 399 | Domain Events Class Hierarchy | classDiagram | DomainEvent → PipelineStarted, PipelineCompleted, PipelineFailed, BatchStarted, BatchCompleted, RecordQuarantined |
| 400 | ChEMBL Activity Entity — Full Field Map | classDiagram | ChemblActivity entity: 20+ fields from activity_id to pchembl_value with types and nullable flags |
| 401 | PubChem Compound Entity — CID-Based Structure | classDiagram | PubchemMolecule entity: cid, molecular_formula, molecular_weight, canonical_smiles, inchi, iupac_name |
| 402 | UniProt Protein Entity — Sequence and Annotations | classDiagram | UniprotTarget entity: accession, entry_name, protein_name, organism, organism_id, sequence, sequence_length |
| 403 | CrossRef Publication Entity — DOI Metadata | classDiagram | CrossRefPublicationEntity: doi, title, authors[], container_title, issued_date, is_referenced_by_count |
| 404 | PubMed Publication Entity — NCBI Metadata | classDiagram | PubMedPublication entity: pmid, title, abstract, authors[], journal, pub_date, mesh_terms[], keywords[] |
| 405 | Base Entity — Common Fields and Behavior | classDiagram | BaseEntity: _entity_id, _content_hash, _ingestion_ts, _run_id, _run_type — shared metadata interface |
| 406 | DataSourcePort Protocol — Complete Method Signatures | classDiagram | DataSourcePort(Protocol): fetch(entity_type, limit, query, filter_ids, filter_field)→AsyncIterator, health_check()→HealthStatus |
| 407 | StoragePort Protocol — Complete Method Signatures | classDiagram | StoragePort: write_bronze(), write_silver(), write_gold(), clear_silver(), clear_gold(), read_silver(), vacuum() |
| 408 | LockPort Protocol — Complete Method Signatures | classDiagram | LockPort: acquire(key, owner_id, ttl)→bool, release(key, owner_id)→bool, renew(key, owner_id, ttl)→bool, is_locked(key)→bool |
| 409 | CheckpointPort Protocol — Complete Method Signatures | classDiagram | CheckpointPort: save(state), load()→CheckpointState|None, delete(), exists()→bool |
| 410 | QuarantinePort Protocol — Complete Method Signatures | classDiagram | QuarantinePort: write(entry), read_sample(limit)→list, count()→int, purge(before_date)→int, replay()→int |
| 411 | MetricsPort Protocol — Counter, Histogram, Gauge | classDiagram | MetricsPort: increment_counter(name, labels), observe_histogram(name, value, labels), set_gauge(name, value, labels) |
| 412 | LoggerPort Protocol — Structured Logging Interface | classDiagram | LoggerPort: info(msg, **kw), warning(msg, **kw), error(msg, **kw), debug(msg, **kw), bind(**kw)→LoggerPort |
| 413 | TracingPort Protocol — OTel-Modeled Tracing | classDiagram | TracingPort: get_tracer(name)→Tracer; Tracer: start_as_current_span(name)→Span; Span: set_attribute(), end() |
| 414 | ValidationPort Protocol — Schema Validation Interface | classDiagram | ValidationPort: validate(df, schema)→ValidationResult with errors:list, warnings:list, passed:bool |
| 415 | Domain Services Dependency Map | flowchart | DataNormalizationService (pure), IdentityService (pure), UnitConverter (pure), ValueValidator (pure) — no I/O, no ports |
| 416 | IdentityService — Content Hash Generation Logic | flowchart | IdentityService: normalize(record) → canonical_json(sort_keys, round_floats, NaN→null) → sha256 → content_hash |
| 417 | DataNormalizationService — Field Normalization Rules | flowchart | NaN→null, Inf→null, strip strings, dates→ISO, floats→round(10), exclude META_FIELDS — per RULES.md §2.8.1 |
| 418 | UnitConverter — Standard Unit Conversion | flowchart | UnitConverter: convert_to_standard(value, from_unit, to_unit) → normalized standard_value with standard_units |
| 419 | ActivityAggregator — pChEMBL Value Processing | flowchart | Activities by target → filter valid pchembl_value → compute mean, median, min, max → aggregated activity profile |
| 420 | ErrorClassifier — HTTP Status to Error Category | flowchart | ErrorClassifier: 401→CRITICAL, 429→RECOVERABLE, 500/502/504→RECOVERABLE, invalid data→DATA_QUALITY, other→UNKNOWN |

## Composite (421–440)

| # | Name | Type | Description |
|---|------|------|-------------|
| 421 | Composite Pipeline Full Workflow — Seed to Gold | flowchart | Seed(ChEMBL docs) → Extract Keys(DOIs, PMIDs) → Dependencies → Fan-Out Enrichers → Collect → Merge → Validate → Gold Write |
| 422 | Composite Config Dataclass Structure | classDiagram | CompositeConfig: seed(SeedConfig), dependencies[DependencyConfig], enrichers[EnricherConfig], merge(MergeConfig), gold_schema |
| 423 | SeedConfig Dataclass | classDiagram | SeedConfig: pipeline_name, provider, entity_type, silver_table — defines primary data source |
| 424 | EnricherConfig Dataclass | classDiagram | EnricherConfig: pipeline_name, provider, entity_type, join_keys[], filter_field, required(bool), timeout_seconds |
| 425 | DependencyConfig Dataclass — Chained Dependencies | classDiagram | DependencyConfig: pipeline, join_keys[], key_source(str|None), filter_field, required, timeout_seconds, silver_table |
| 426 | MergeConfig Dataclass — All Parameters | classDiagram | MergeConfig: strategy, conflict_resolution, preserve_all_sources, column_groups[], field_group_registry |
| 427 | CompositeState Tracking Object | classDiagram | CompositeState: phase(enum), seed_result, dependency_results[], enrichment_results[], merge_result, errors[] |
| 428 | CompositeStrategy — Execution Order Determination | flowchart | CompositeStrategy: analyze_dependencies() → topological sort → determine execution order → parallel groups |
| 429 | CompositeLineage — Cross-Source Data Provenance | flowchart | Lineage tracking: seed_batch_id → enricher_batch_ids[] → merge_timestamp → Gold record _lineage metadata |
| 430 | Enrichment Fan-Out — asyncio.gather Parallel Execution | flowchart | EnrichmentCoordinator: create tasks per enricher → asyncio.gather(*tasks, return_exceptions=True) → collect results |
| 431 | Enricher Failure Handling — Required vs Optional | flowchart | Enricher fails → check required flag → required=true: abort composite → required=false: skip, continue with available data |
| 432 | Key Extraction — Seed Silver to Enricher Filter IDs | flowchart | KeyExtractor: read seed Silver table → select join_key columns → unique values → return list for enricher filtering |
| 433 | Chained Dependency Key Resolution | flowchart | Dep1: keys from seed → run dep1 → Dep2: key_source=dep1 → extract keys from dep1's Silver → run dep2 |
| 434 | Merge JOIN Strategy — Left Outer vs Inner vs Union | flowchart | left_outer: keep all seed records → inner: only matched → union: combine all unique records from all sources |
| 435 | Conflict Resolution Strategies Comparison | flowchart | seed_priority: prefer seed → enricher_priority: prefer enricher → coalesce: first non-null → explicit_rules: per-field config |
| 436 | Qualified Column Name Generation | flowchart | Base field "title" + provider "crossref" + entity "publication" → "crossref.publication.title" when preserve_all_sources=true |
| 437 | TRASH Group Filtering in Gold Output | flowchart | FieldGroupRegistry → identify TRASH group fields → remove from merged DataFrame before Gold write → cleaner analytics |
| 438 | Composite Pipeline Bootstrap vs Standard Bootstrap | flowchart | Standard: bootstrap_pipeline() → single runner | Composite: bootstrap_composite_runner() → CompositePipelineRunner with coordinator |
| 439 | Composite Aggregator — Multi-Source Metric Aggregation | flowchart | Per enricher: record_count, error_rate, duration → Aggregator: combine into composite-level metrics → publish |
| 440 | Cross-Validation Checks After Merge | flowchart | Check join rate (>80% expected), orphan records (<5%), duplicate DOIs (0 expected), coverage per provider → quality report |

## Observability (441–460)

| # | Name | Type | Description |
|---|------|------|-------------|
| 441 | Three Pillars of Observability in BioETL | flowchart | Logging (StructlogLogger→LoggerPort) + Metrics (PrometheusMetrics→MetricsPort) + Tracing (NoOpTracing→TracingPort) |
| 442 | Prometheus Metric Naming Convention | flowchart | prefix: bioetl_ → type: pipeline/records/errors/batch → suffix: _total/_seconds/_records → labels: pipeline, stage, run_type |
| 443 | Full Prometheus Metrics Catalog | flowchart | pipeline_duration_seconds, records_processed_total, errors_total, batch_size_records, filter_ids_loaded_total, circuit_breaker_state |
| 444 | Structured Log Schema — Required and Optional Fields | flowchart | MUST: timestamp, level, run_id, pipeline, stage → SHOULD: dataset, record_count → conditional: error_type, error_code |
| 445 | Tracing Span Hierarchy — Pipeline to HTTP Request | flowchart | PipelineRun span → Batch span → Transform span → Write span → HTTP Request span (nested spans) |
| 446 | NoOp Tracing Implementation (ADR-022) | classDiagram | NoOpTracing → NoOpTracer → NoOpSpan — zero overhead, satisfies TracingPort contract, swappable with OTel |
| 447 | OTel Integration Path — NoOp to Real Tracing | flowchart | Default: NoOpTracing → install .[tracing] → OpenTelemetryTracing → same TracingPort interface → no code changes |
| 448 | Observability Port Enforcement (ADR-019) | flowchart | Application MUST NOT import structlog → MUST use LoggerPort → Architecture test blocks direct imports |
| 449 | PipelineObserver Context Manager — Lifecycle Metrics | sequenceDiagram | with PipelineObserver(metrics, logger) → enter: log started, inc counter → body: pipeline runs → exit: log completed/failed, observe duration |
| 450 | BatchMetricsRecorder — Per-Batch Instrumentation | sequenceDiagram | BatchMetricsRecorder: record(batch_size, duration, errors) → observe_histogram(batch_size) → inc_counter(records) → inc_counter(errors) |
| 451 | BatchTracingManager — Span Management | sequenceDiagram | BatchTracingManager: start_span("batch") → set_attribute(batch_num) → execute batch → end_span(status) |
| 452 | Alert Severity Classification | flowchart | CRITICAL: system down, data loss → ERROR: pipeline fail → WARNING: DQ anomaly, degraded → INFO: schema drift (new fields) |
| 453 | DQ Anomaly Z-Score Calculation | flowchart | Current null_rate → historical mean (30 days) → standard deviation → z_score = (current - mean) / std → compare thresholds |
| 454 | Anomaly Detection Cold Start Handling | flowchart | Days 1-7: accumulate baselines, silence alerts → Days 8-30: warning-only alerts → Days 30+: full alerting with configurable thresholds |
| 455 | Metrics Export to /metrics Endpoint | sequenceDiagram | Prometheus scraper → GET /metrics → PrometheusMetrics renders all counters/histograms/gauges → text/plain response |
| 456 | Run ID Correlation Across All Observability Channels | flowchart | run_id (UUID) → bound to logger → included in metrics labels → set as trace attribute → correlates logs, metrics, traces |
| 457 | Dataset Label in Metrics and Logs | flowchart | Pipeline may write to multiple tables → dataset label (e.g., chembl/activity) → added to every metric and log entry |
| 458 | Provider Health Metric — provider_health_status Gauge | flowchart | 0=UNHEALTHY, 1=DEGRADED, 2=HEALTHY → set per provider → monitored for alerting → if stuck at 0 for >10min → P2 alert |
| 459 | Circuit Breaker Metric — State and Trip Count | flowchart | circuit_breaker_state{provider} gauge (0/1/2) + trips_total{provider} counter → alert if Open >10min |
| 460 | Graceful Degradation for Observability Failures | flowchart | Metrics server fails to start → log warning → continue pipeline → metrics data lost but pipeline runs normally |

## ErrorHandling (461–480)

| # | Name | Type | Description |
|---|------|------|-------------|
| 461 | Error Classification Decision Tree — Full Logic | flowchart | HTTP error → 401/403→CRITICAL → 429→RECOVERABLE → 500/502/504→RECOVERABLE → schema mismatch→CRITICAL → invalid data→DQ |
| 462 | Retry Strategy — Exponential Backoff with Deterministic Jitter | flowchart | Attempt N → base_delay = multiplier^N → jitter = MD5(attempt:url:seed) → total = base_delay + jitter → wait → retry |
| 463 | Circuit Breaker Integration with Retry | flowchart | Request → CB check state → CLOSED: proceed → OPEN: fail fast (no retry) → HALF_OPEN: allow probe → result updates CB |
| 464 | Batch Error Threshold Enforcement | flowchart | Count errors per batch → <5%: write with _dq_warn → 5-20%: WARNING log → >20%: FAIL batch → increment errors_total metric |
| 465 | Error Recovery Playbook — Auth Failure | flowchart | 401 detected → check BIOETL_{PROVIDER}_API_KEY → expired: rotate key → missing: configure → retry → success |
| 466 | Error Recovery Playbook — Rate Limit Exhaustion | flowchart | 429 detected → check Retry-After header → reduce requests_per_second in config → wait → retry → monitor |
| 467 | Error Recovery Playbook — Schema Mismatch in Gold | flowchart | Gold validation fails → check API changes → update Gold schema → create ADR → rebuild affected tables |
| 468 | Error Recovery Playbook — Stale Checkpoint | flowchart | Warning at startup → --resume: continue from checkpoint → no --resume: delete checkpoint + --run-type rebuild |
| 469 | Error Recovery Playbook — Lock Timeout | flowchart | Lock expired alert → check for zombie processes → kill zombie → release-lock → restart pipeline |
| 470 | Exception Propagation Through Layers | flowchart | Infrastructure error → wrapped in domain exception → Application catches → classify → retry/quarantine/fail → CLI reports |
| 471 | Data Quality Error Isolation — Per-Record vs Per-Batch | flowchart | Single invalid record → quarantine record, continue batch → >20% records invalid → fail entire batch → don't corrupt Silver |
| 472 | Network Error Retry vs Circuit Breaker Interaction | stateDiagram | NetworkError → retry_count < max → retry with backoff → retry_count >= max → record failure → CB failure_count → CB trip |
| 473 | Lock Lost Safety Guard — Abort Before Write | flowchart | About to write Silver → validate_lock() → lock valid: proceed → lock expired: ABORT immediately → no partial write → data integrity |
| 474 | Cascading Failure Prevention — Provider Isolation | flowchart | Provider A fails → CB opens for A → Provider B unaffected → Pipelines using B continue normally → no cascade |
| 475 | Error Severity to SLA Mapping | flowchart | P0: system down (15min react, 1h recover) → P1: critical pipeline (1h, 4h) → P2: secondary (8h, 24h) → P3: warning (24h, next sprint) |
| 476 | Quarantine Error Pattern Analysis | flowchart | Quarantine entries → group by error_code → SCHEMA_VIOLATION: fix transformer → INVALID_VALUE: fix DQ rules → NETWORK: transient |
| 477 | Error Handling in Composite Pipeline — Enricher Failure | flowchart | Enricher fails → required=true: abort composite → required=false: log warning → merge without that source → degraded but functional |
| 478 | Split-Brain Prevention via Fencing Token | sequenceDiagram | Worker A holds lock → A stalls → lock expires → Worker B acquires → A resumes → A tries write → fencing token mismatch → A rejected |
| 479 | Transient vs Permanent Error Classification | flowchart | Transient: 429, 502, timeout, DNS → retry → Permanent: 401, 403, 404, schema error → fail fast, no retry |
| 480 | Error Metrics Dashboard — Key Error Indicators | flowchart | errors_total by error_code → record_error_rate → entity_error_rate → circuit_breaker_state → quarantine_count_total |

## Testing (481–490)

| # | Name | Type | Description |
|---|------|------|-------------|
| 481 | Test Pyramid — Unit, Integration, E2E, Contract | flowchart | Unit tests (domain logic, fast) → Integration (VCR cassettes) → E2E (full pipeline, local FS) → Contract (monthly, live API) |
| 482 | VCR Cassette Recording and Playback Flow | sequenceDiagram | First run: record mode → real HTTP → save cassette → CI run: playback mode → cassette → no network → fast, deterministic |
| 483 | VCR Secret Sanitization — before_record Callback | flowchart | before_record: intercept request → remove Authorization header → redact X-API-Key → sanitize PII → save clean cassette |
| 484 | Architecture Test Suite Overview | flowchart | test_import_boundaries → test_no_random_in_writers → test_no_datetime_now → test_no_structlog_in_app → test_port_suffixes |
| 485 | Test Fixture Organization | flowchart | tests/fixtures/: vcr/{provider}/ → bronze_samples/ → silver_samples/ → config_fixtures/ → per-entity test data |
| 486 | Coverage Gate Enforcement — 85% Minimum | flowchart | pytest --cov=src/bioetl --cov-fail-under=85 → generate report → <85%: CI fails → ≥85%: CI passes |
| 487 | E2E Test Architecture — Local-Only Full Pipeline | flowchart | create_test_context() → run pipeline (fixture data) → assert_bronze_files_exist() → assert_silver_table_has_records() → assert Gold |
| 488 | Property-Based Testing with Hypothesis | flowchart | Hypothesis generates random Activity records → test IdentityService.hash() stability → same input always same hash |
| 489 | Snapshot Testing with Syrupy | flowchart | Transform sample data → capture output schema/format → save snapshot → next run: compare → changed: update or fail |
| 490 | Contract Test — Monthly Live API Validation | flowchart | Monthly CI job → real API calls to each provider → validate response schema → detect breaking changes → alert team |

## Security (491–495)

| # | Name | Type | Description |
|---|------|------|-------------|
| 491 | PII Data Flow Through Medallion Layers | flowchart | Bronze: PII stored as-is → Silver: PIIHasher.hash(value, salt) → sha256 → Gold: PII excluded or aggregated |
| 492 | Secret Management — Environment Variable Pattern | flowchart | BIOETL_{PROVIDER}_{KEY} → os.environ → never hardcoded → .env files never in git → CI secrets via vault |
| 493 | Security Scan Pipeline — pip-audit Integration | flowchart | CI job → pip-audit scan → CVE severity ≥ HIGH → block merge → CVE < HIGH → warning only |
| 494 | Sensitive Data Classification | flowchart | Public (Gold analytics) → Internal (Silver normalized, Bronze raw) → Restricted (PII fields, API keys) |
| 495 | VCR Cassette Secret Sanitization Pipeline | sequenceDiagram | Record HTTP interaction → before_record hook → check headers for Authorization/API-Key → replace with REDACTED → save cassette |

## Performance (496–500)

| # | Name | Type | Description |
|---|------|------|-------------|
| 496 | Adaptive Batch Size Based on Provider Health | flowchart | HEALTHY: batch_size=1000 → DEGRADED: batch_size=500 (÷2), timeout×2 → UNHEALTHY: pause → recover → ramp up |
| 497 | Memory Monitoring During Pipeline Execution | flowchart | Monitor RSS memory per batch → log memory_stats → if approaching limit: reduce batch_size → graceful degradation |
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
