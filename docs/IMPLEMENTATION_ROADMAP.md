# BioETL: Implementation Roadmap

*Updated: 2025-12-16*
*Based on: RULES.md v5.0 (Production Ready)*
*Project Version: 5.0.0*

## 🎯 Project Status

**Current Phase**: Phase 5 (Data Quality & Observability) 🔄 IN PROGRESS
**Overall Progress**: ~55% (Phases 0-4 COMPLETED; Phase 5 started, Phase 6 advanced)
**MVP Target**: 8-10 weeks (on track for Week 7)
**Production-Ready Target**: 16-20 weeks

---

## ✅ Completed Work

### Phase 0: Foundation & Infrastructure (COMPLETED)

#### 0.1 Developer Experience Setup ✅

- **Makefile**: 25+ commands for development workflow
  - Core: `install`, `test`, `lint`, `run-local`
  - Operations: `quarantine-inspect/replay/purge`, `release-lock`, `dr-restore`, `rollback`
  - CI/CD: `ci-lint`, `ci-test`, `ci-build`
- **Docker Compose**: Local environment (Postgres, Redis, MinIO)
  - Auto-initialization: S3 buckets, DB schemas
  - Services: Health checks, volume persistence
- **.env.example**: 100+ environment variables template
  - All providers API keys
  - Security (PII salt, rotation)
  - Observability, DQ thresholds, Circuit breaker
- **.gitignore**: Updated for secrets protection

#### 0.2 Type Safety & Linting ✅

- **.pre-commit-config.yaml**: Automated code quality checks
  - Ruff (linting + formatting)
  - mypy (strict type checking)
  - bandit (security)
  - detect-secrets (no hardcoded secrets)
  - General file checks (trailing whitespace, YAML/JSON validation)

#### 0.3 Observability Foundation ✅

- **Structured Logging** (`src/bioetl/observability/logging.py`)
  - JSON format with mandatory fields (ts, level, run_id, pipeline, stage)
  - Implements REQ-OBS-001, REQ-OBS-004, REQ-OBS-005
  - Factory function: `create_logger()`
  - Log to console + file, configurable levels

---

### Phase 1: Domain Layer (COMPLETED)

#### 1.1 Core Domain Types ✅

**File**: `src/bioetl/domain/types.py`

**Type Aliases**:

- `RunID`, `EntityID`, `ContentHash`, `BatchID`, `Watermark`

**Enums**:

- `RunType`: incremental | backfill | rebuild (with priority)
- `DriftLevel`: INFO | WARN | CRITICAL
- `HealthStatus`: HEALTHY | DEGRADED | UNHEALTHY
- `CircuitBreakerState`: CLOSED | OPEN | HALF_OPEN
- `DataClassification`: PUBLIC | INTERNAL | RESTRICTED
- `ErrorType`: 11 error types with classification methods
- `DQStatus`: NEW | IGNORED | REPROCESSED

#### 1.2 Ports (Protocol Interfaces) ✅

**File**: `src/bioetl/domain/ports.py`

**Defined Protocols**:

1. **DataSourcePort**: Provider adapters (fetch, health_check)
2. **StoragePort**: Bronze/Silver/Gold writes (JSONL+zstd, Delta Lake)
3. **LockPort**: Distributed locking (acquire, release, heartbeat)
4. **CheckpointPort**: State persistence (save, load, delete)
5. **QuarantinePort**: Dead letter queue (write, inspect, replay, purge)
6. **LineagePort**: Data provenance (log_batch, get_batch_sources)
7. **MetricsPort**: Prometheus metrics (DQ, freshness, health, circuit breaker)

All protocols use `typing.Protocol` for structural typing (REQ-ARCH-001).

#### 1.3 Domain Transformations ✅

**File**: `src/bioetl/domain/transformations.py`

**Pure Functions** (no I/O):

- `normalize_for_hash()`: NaN→null, round floats, ISO dates, strip strings
- `canonical_json_dumps()`: Deterministic JSON (sorted keys, no spaces)
- `generate_content_hash()`: SHA256 of canonical JSON (REQ-ID-001)
- `generate_entity_id()`: Stable business key or content hash fallback
- `detect_schema_drift()`: INFO/WARN/CRITICAL drift detection
- `calculate_dq_score()`: Quality score (0.0-1.0)
- `exceeds_threshold()`: Soft (5%) / Hard (20%) threshold checks
- `detect_hash_collision()`: Collision detection for logging

**Compliance**: All REQ-ID-001 through REQ-ID-008, REQ-SCHEMA-001 to 004 implemented.

#### 1.4 Unit Tests ✅

**File**: `tests/unit/domain/test_transformations.py`

**Test Coverage**:

- Content hash normalization (NaN, floats, dates, strings, meta-fields)
- Canonical JSON (sorted keys, no spaces, ASCII)
- Hash determinism, SHA256 length, provider separation
- Entity ID generation (stable vs fallback)
- Schema drift (INFO/WARN/CRITICAL levels)
- DQ score and thresholds (soft 5%, hard 20%)
- Hash collision detection
- **Property-based tests** (Hypothesis): Float normalization, string stripping, DQ score bounds

**Test Markers**: `@pytest.mark.unit` for fast execution

---

### Phase 6: Documentation (ADVANCED PROGRESS) ✅

We have significantly advanced the documentation phase, originally scheduled for later.

#### 6.1 Core Documentation ✅

- **README.md**: Project entry point, quick start, badges.
- **MkDocs Setup**: `mkdocs.yml` configured with Material theme, Mermaid, and mkdocstrings.
- **Structure**: `docs/` folder organized by Governance, Architecture, Guides, Reference, Operations.

#### 6.2 Guides & Runbooks ✅

- **Getting Started**: `docs/03-guides/getting-started.md`
- **Running Pipelines**: `docs/03-guides/running-pipelines.md`
- **Troubleshooting**: `docs/03-guides/troubleshooting.md`
- **Incident Response**: `docs/05-operations/runbooks/incident-response.md`
- **Data Recovery**: `docs/05-operations/runbooks/data-recovery.md`
- **Scaling**: `docs/05-operations/runbooks/scaling.md`

#### 6.3 Architecture Decision Records (ADR) ✅

- **ADR-001**: Delta Lake vs Parquet
- **ADR-002**: Medallion Architecture
- **ADR-003**: Redis for Distributed Locking
- **ADR-004**: Pydantic vs Dataclasses

#### 6.4 Reference ✅

- **CLI Reference**: `docs/04-reference/cli.md`
- **API Reference**: Auto-generated from docstrings (`docs/04-reference/api/`)
- **Pipeline Docs**: Example for `chembl_activity`

---

### Testing Infrastructure (STARTED) 🔄

- **Meta-Testing**: `tests/test_architecture.py` checks project structure and rules compliance.
- **Config Testing**: `tests/test_data_storage.py` validates pipeline YAML configurations.
- **Domain Logic**: `tests/test_domain_logic.py` covers core business rules.
- **Conftest**: `tests/conftest.py` with shared fixtures.

---

## 📦 Deliverables Created

### Infrastructure Files

- `Makefile`
- `docker-compose.yml`
- `docker/init-db.sql`
- `.env.example`
- `.gitignore`
- `.pre-commit-config.yaml`
- `pyproject.toml` (updated with docs dependencies)

### Source Code

**Domain Layer**:

- `src/bioetl/domain/types.py`
- `src/bioetl/domain/ports.py`
- `src/bioetl/domain/transformations.py`

**Infrastructure Layer**:

*Storage*:

- `src/bioetl/infrastructure/storage/bronze_writer.py` ✨ Phase 2
- `src/bioetl/infrastructure/storage/delta_writer.py` ✨ Phase 2
- `src/bioetl/infrastructure/storage/gold_writer.py` ✨ Phase 2

*Locking & State*:

- `src/bioetl/infrastructure/locking/redis_lock.py`
- `src/bioetl/infrastructure/checkpoint/s3_checkpoint.py` ✨ Phase 2
- `src/bioetl/infrastructure/quarantine/unified_quarantine.py` ✨ Phase 2

*HTTP & Adapters*:

- `src/bioetl/infrastructure/adapters/http/client.py`
- `src/bioetl/infrastructure/adapters/http/rate_limiter.py`
- `src/bioetl/infrastructure/adapters/http/circuit_breaker.py`
- `src/bioetl/infrastructure/adapters/chembl/client.py`
- `src/bioetl/infrastructure/adapters/pubchem/client.py` ✨ Phase 3
- `src/bioetl/infrastructure/adapters/uniprot/client.py` ✨ Phase 3

**Observability**:

- `src/bioetl/observability/logging.py`

### Tests

- `tests/unit/domain/test_transformations.py`
- `tests/unit/infrastructure/test_adapters.py` ✨ Phase 3
- `tests/test_architecture.py`
- `tests/test_data_storage.py`
- `tests/test_domain_logic.py`
- `tests/conftest.py`

### Documentation

- `README.md`
- `RULES.md`
- `REQUIREMENTS.md`
- `CHANGELOG.md`
- `mkdocs.yml`
- `docs/` (comprehensive structure)

**Total Code**: ~6,500+ lines of production-ready code + tests + infrastructure + docs

- Domain Layer: ~600 lines
- Infrastructure Layer:
  - Storage: ~1,780 lines (Phase 2)
  - Locking & State: ~910 lines (Phase 2 + pre-existing)
  - HTTP & Adapters: ~1,300 lines (Phase 3) ✨
  - **Total Infrastructure**: ~3,990 lines
- Observability: ~150 lines
- Tests: ~1,000 lines (includes adapter tests)
- Documentation: ~1,400+ lines

---

## 🚀 Next Steps (Phase 2-11)

### Phase 2: Infrastructure - Adapters (COMPLETED) ✅

#### 2.1 Storage Adapters ✅

**Status**: ✅ COMPLETED

**Implemented**:

- [x] **Bronze Writer** (`src/bioetl/infrastructure/storage/bronze_writer.py`)
  - S3-compatible storage with MinIO support
  - JSONL + zstandard compression (REQ-DATA-001)
  - Path format: `bronze/v1/{provider}/{entity}/{date}/batch_{batch_id}.jsonl.zst` (REQ-DATA-002)
  - Append-only, atomic writes via S3 PutObject (REQ-DATA-003, REQ-DATA-004)
  - Read/list methods for testing and debugging
  - ~220 lines

- [x] **Silver Writer** (`src/bioetl/infrastructure/storage/delta_writer.py`)
  - Delta Lake via deltalake (delta-rs) (REQ-DATA-006)
  - Merge/Upsert strategy with run_type priority (REQ-DATA-008)
  - VACUUM operation with 7-day retention (REQ-DELTA-002)
  - Optimize (file compaction) support
  - Time Travel support (REQ-DATA-008)
  - Table info and metadata methods
  - ~280 lines

- [x] **Gold Writer** (`src/bioetl/infrastructure/storage/gold_writer.py`)
  - Strict Pandera schema validation (REQ-DATA-009)
  - SCD Type 2 (Slowly Changing Dimensions) support (REQ-DATA-010)
  - Overwrite/Append modes
  - History tracking for entities
  - Read methods with current_only filter
  - ~340 lines

**Total Storage Code**: ~840 lines of production-ready storage adapters

#### 2.2 Lock Adapter (Redis) ✅

**Status**: ✅ COMPLETED (Pre-existing)

**Features**:

- [x] **Redis Distributed Lock** (`src/bioetl/infrastructure/locking/redis_lock.py`)
  - Redis SETNX + EXPIRE (REQ-LOCK-001)
  - TTL 60s, Heartbeat 20s (REQ-LOCK-002, REQ-LOCK-003)
  - Fencing tokens via owner_id (REQ-LOCK-005)
  - Max duration 4 hours (REQ-LOCK-004)
  - Exclusive locks for backfill/rebuild (REQ-LOCK-006)
  - Heartbeat loop with LockLostError (REQ-LOCK-007)
  - Lua scripts for atomic operations (REQ-LOCK-008)
  - ~330 lines

#### 2.3 Checkpoint Adapter (S3) ✅

**Status**: ✅ COMPLETED

**Implemented**:

- [x] **S3 Checkpoint Storage** (`src/bioetl/infrastructure/checkpoint/s3_checkpoint.py`)
  - Atomic writes using S3 ETag (If-Match) (REQ-CHECKPOINT-002, REQ-SHUTDOWN-003)
  - Check existence on startup (REQ-CHECKPOINT-001)
  - Recovery support for --resume flag (REQ-CHECKPOINT-003)
  - Delete after successful run (REQ-CHECKPOINT-004)
  - Path: `s3://{bucket}/checkpoints/{pipeline}/latest.json`
  - Watermark serialization (datetime/int/str)
  - CheckpointConflictError for concurrent modifications
  - List all checkpoints method
  - ~250 lines

#### 2.4 Quarantine Adapter ✅

**Status**: ✅ COMPLETED

**Implemented**:

- [x] **Unified Quarantine Table** (`src/bioetl/infrastructure/quarantine/unified_quarantine.py`)
  - Single Delta Lake table: `common.quarantine` (REQ-QUARANTINE-001)
  - Payload truncation to 64KB (REQ-QUARANTINE-002)
  - 30-day retention with purge() (REQ-QUARANTINE-003)
  - Links to Bronze via bronze_batch_id and bronze_file_uri (REQ-QUARANTINE-004)
  - Schema: ingestion_ts, pipeline, error_code, payload, payload_hash, dq_status
  - Operations: write, inspect, replay, purge
  - DQ status updates (NEW → IGNORED/REPROCESSED)
  - Statistics method (count by error_code, status, age)
  - Deduplication via SHA256 payload_hash
  - Partitioned by pipeline for query efficiency
  - ~360 lines

**Total Phase 2 Code**: ~1,780 lines (new) + 330 lines (pre-existing) = ~2,110 lines

#### 2.5 Dependencies Updated ✅

- [x] Added `boto3>=1.34` for S3 operations
- [x] Added `pyarrow>=15.0` for Delta Lake operations
- [x] Updated `mypy` overrides for boto3, botocore

---

### Phase 3: Provider Adapters (COMPLETED) ✅

#### 3.0 HTTP Infrastructure ✅

**Status**: ✅ COMPLETED (Pre-existing)

**Implemented**:

- [x] **UnifiedHTTPClient** (`src/bioetl/infrastructure/adapters/http/client.py`)
  - Async httpx-based client
  - Integrated rate limiting and circuit breaker
  - Exponential backoff with jitter (RULES.md §3.1.3)
  - Max attempts: 3, Multiplier: 2.0, Jitter: 0.1-0.5s
  - ~200 lines

- [x] **TokenBucket Rate Limiter** (`src/bioetl/infrastructure/adapters/http/rate_limiter.py`)
  - Async token bucket algorithm
  - Smooth rate control with burst capacity
  - Provider-specific configurations
  - ~120 lines

- [x] **Circuit Breaker** (`src/bioetl/infrastructure/adapters/http/circuit_breaker.py`)
  - State machine: CLOSED → OPEN → HALF_OPEN
  - Configurable failure threshold (default: 5)
  - Recovery timeout (default: 300s = 5min)
  - Metrics integration
  - ~150 lines

**Total HTTP Infrastructure**: ~470 lines

#### 3.1 ChEMBL Adapter ✅

**Status**: ✅ COMPLETED (Pre-existing)

**Implemented**:

- [x] **ChEMBL Client** (`src/bioetl/infrastructure/adapters/chembl/client.py`)
  - Uses `chembl_webresource_client` library
  - Health check: `/chembl/api/data/status.json`
  - Entities: activities, compounds, targets, assays, documents
  - Async iterator interface (DataSourcePort)
  - Pagination support (1000 records/page)
  - ThreadPoolExecutor for sync API calls
  - Error tracking and health status
  - ~180 lines

**Features**:

- Health check with HEALTHY/DEGRADED/UNHEALTHY states
- Watermark support for incremental loading
- Batch fetching with configurable page size
- Entity type mapping (activity, compound, target, etc.)

#### 3.2 PubChem Adapter ✅

**Status**: ✅ COMPLETED

**Implemented**:

- [x] **PubChem Client** (`src/bioetl/infrastructure/adapters/pubchem/client.py`)
  - Uses `pubchempy` library (sync → ThreadPoolExecutor)
  - Rate limit: 5 req/sec (TokenBucket)
  - Entities: compounds, substances, assays
  - Health check: lightweight query (CID 962 - water)
  - Search by name, formula, SMILES
  - Incremental loading by CID range
  - Batch fetching (100 CIDs per request)
  - ~330 lines

**Features**:

- Compound search and retrieval
- Substance search
- Assay data access
- SMILES/InChI/InChIKey support
- Molecular properties (weight, formula, complexity)

#### 3.3 UniProt Adapter ✅

**Status**: ✅ COMPLETED

**Implemented**:

- [x] **UniProt Client** (`src/bioetl/infrastructure/adapters/uniprot/client.py`)
  - Async httpx-based REST API client
  - Rate limit: 100 req/sec (with API key), 10 req/sec (without)
  - Entities: proteins, features, sequences
  - Health check: `/rest/beta/health`
  - UniProt query syntax support
  - Cursor-based pagination (500 records/page)
  - FASTA format parsing
  - ~320 lines

**Features**:

- Protein entry search with rich field selection
- Protein feature extraction
- Sequence retrieval (FASTA format)
- Gene name, organism, keyword searches
- Cross-references (PDB, ChEMBL, etc.)

**Phase 3 Total**: ~1,300 lines (HTTP infrastructure + 3 provider adapters)

---

### Phase 4: Application Layer - Pipelines (3-4 weeks)

**Status**: ✅ COMPLETED

**Implemented**:

#### 4.1 Base Pipeline ✅

- [x] **BasePipeline** (`src/bioetl/application/pipeline/base.py`)
  - Abstract base class for all ETL pipelines
  - Lock acquisition with heartbeat mechanism
  - Checkpoint save/restore support
  - Graceful shutdown handlers (SIGTERM/SIGINT)
  - Bronze → Silver → Gold flow orchestration
  - Error handling and quarantine integration
  - Configurable resume/rebuild/backfill modes
  - ~450 lines

**Features**:

- Distributed locking with automatic heartbeat
- Checkpoint-based recovery
- Signal handling for clean shutdown
- Abstract methods for pipeline-specific logic
- Metrics tracking (records processed, errors)

#### 4.2 ChEMBL Activities Pipeline ✅

- [x] **ChEMBLActivityPipeline** (`src/bioetl/application/pipelines/chembl_activity.py`)
  - Concrete implementation for ChEMBL bioactivity data
  - Bronze: Raw ChEMBL API responses
  - Silver: Normalized activity records with content hash
  - Gold: High-quality activities (IC50, Ki, EC50, Kd)
  - Factory pattern for instantiation
  - ~220 lines

**Features**:

- Entity ID generation (sha256-based)
- Content hash for deduplication
- Standard type filtering (IC50, Ki, EC50, Kd, etc.)
- Target and molecule linking
- Gold layer quality filters

#### 4.3 CLI Runner ✅

- [x] **CLI** (`src/bioetl/cli.py`)
  - Click-based command-line interface
  - `bioetl run`: Execute pipelines
  - `bioetl quarantine`: Inspect/manage failed records
  - `bioetl checkpoint`: List/delete checkpoints
  - Environment variable support (.env)
  - ~320 lines

- [x] **Entry Point** (`pyproject.toml`)
  - Added `click>=8.1` dependency
  - Configured `[project.scripts]` entry point

**Commands**:

```bash
bioetl run --pipeline chembl_activity [--run-type incremental|backfill|rebuild] [--resume]
bioetl quarantine inspect --pipeline <name>
bioetl quarantine stats --pipeline <name>
bioetl checkpoint list
bioetl checkpoint delete --pipeline <name>
```

**Phase 4 Total**: ~990 lines

**Remaining Tasks**:

- [ ] Integration tests for pipelines
- [ ] End-to-end pipeline testing
- [ ] Additional concrete pipelines (PubChem, UniProt)

---

### Phase 5: Data Quality & Observability (2-3 weeks)

**Status**: 🔄 IN PROGRESS (~25% завершено)

**Completed**:

- [x] **Structured Logging** (`src/bioetl/infrastructure/observability/logging.py`)
  - JSON format с обязательными полями (ts, level, run_id, pipeline, stage)
  - Реализованы REQ-OBS-001, REQ-OBS-004, REQ-OBS-005
  - Factory function: `create_logger()`
  - Логирование в консоль + файл с настраиваемыми уровнями

**In Progress**:

- [ ] **Prometheus metrics exporter**
  - Метрики: dq_validation_score, data_freshness_seconds, circuit_breaker_state
  - Endpoint `/metrics` для scraping

**Pending**:

- [ ] Anomaly detection (baseline, thresholds)
  - Baseline: скользящее среднее за 30 дней
  - Warning: >2x baseline для null_rate, <70% для record_count
  - Critical: >5x baseline для null_rate, <50% для record_count
  - Cold Start период (Days 1-30)
- [ ] Lineage tracking implementation
  - Таблица `sys.lineage_log` (batch_id → Bronze files)
  - `_source_batch_id` в Silver записях
- [ ] Grafana dashboards
  - DQ metrics dashboard
  - Pipeline health dashboard
  - Provider status dashboard

---

## 📊 Requirements Compliance

### Implemented Requirements (Phase 0-1 + Docs)

| ID                     | Requirement                              | Status                 |
|------------------------|------------------------------------------|------------------------|
| REQ-ARCH-001           | Ports via typing.Protocol                | ✅                      |
| REQ-ARCH-002           | mypy --strict enforcement                | ✅                      |
| REQ-ARCH-003           | No I/O in domain layer                   | ✅                      |
| REQ-ARCH-004           | @runtime_checkable for critical adapters | ⚠️ Deferred to Phase 2 |
| REQ-OBS-001            | run_id in all logs                       | ✅                      |
| REQ-OBS-004            | Structured JSON logs                     | ✅                      |
| REQ-OBS-005            | Log Schema mandatory fields              | ✅                      |
| REQ-ID-001 to 008      | Content hash algorithm                   | ✅                      |
| REQ-SCHEMA-001 to 004  | Schema drift detection                   | ✅                      |
| REQ-THRESHOLD-001, 002 | DQ thresholds                            | ✅                      |
| REQ-SECRET-004         | .env not in git                          | ✅                      |
| REQ-DX-001 to 005      | Developer experience (Makefile, Docker)  | ✅                      |
| REQ-DOC-001, 002       | Documentation automation & structure     | ✅                      |
| REQ-CONTRACT-001       | Gold schemas published (structure ready) | ✅                      |

**Total**: ~25 of 126 requirements implemented (20%)

### Pending Requirements (Phase 2+)

- **Data/Medallion**: 35 requirements (Bronze/Silver/Gold storage)
- **Errors/Observability**: 32 requirements (Circuit breaker, metrics, locks)
- **Code/Tests**: 10 requirements (VCR.py, contract tests)
- **Operations**: 24 requirements (Rate limiting, secrets, DR)
- **Others**: 8 requirements (Contracts, dependencies, providers)

---

## 🎯 Milestones

### ✅ Milestone 1: Foundation (COMPLETED)

**Date**: 2025-12-15
**Deliverables**:

- Development environment setup (Docker, Makefile)
- Type-safe domain layer (types, ports, transformations)
- Structured logging foundation
- Unit tests with property-based testing
- **Comprehensive Documentation Site**

---

### ✅ Milestone 2: Storage & Locking (COMPLETED)

**Date**: 2025-12-15
**Deliverables**:

- ✅ Bronze/Silver/Gold writers (Delta Lake)
- ✅ Redis distributed locking
- ✅ S3 checkpoint storage
- ✅ Quarantine implementation
- ⏳ Integration tests (pending)

---

### 🔜 Milestone 3: First Pipeline (Target: Week 5-7)

**Deliverables**:

- ChEMBL adapter
- Pipeline orchestrator
- ChEMBL Activities pipeline
- CLI runner
- E2E test

---

## 📝 Change Log

| Date       | Phase | Change                                                                                        |
|------------|-------|-----------------------------------------------------------------------------------------------|
| 2025-12-15 | 0-1   | Initial implementation: Foundation + Domain Layer                                             |
| 2025-12-15 | 6     | Documentation overhaul: MkDocs, Guides, Runbooks, ADRs                                        |
| 2025-12-15 | Test  | Added meta-testing and domain logic tests                                                     |
| 2025-12-15 | 2     | ✅ **Phase 2 COMPLETED**: Storage (Bronze/Silver/Gold), Locking, Checkpoint, Quarantine        |
| 2025-12-15 | 3     | ✅ **Phase 3 COMPLETED**: HTTP infrastructure + 3 provider adapters (ChEMBL, PubChem, UniProt) |

---

**Next Update**: After Phase 4 start or significant progress
