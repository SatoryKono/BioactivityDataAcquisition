# BioETL: Implementation Roadmap

*Updated: 2025-12-15*
*Based on: RULES.md v5.0 (Production Ready)*

## 🎯 Project Status

**Current Phase**: Phase 2 (Infrastructure Adapters) 🔄
**Overall Progress**: ~25% (Phase 0, 1, and part of 6 COMPLETED)
**MVP Target**: 8-10 weeks
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
- `src/bioetl/domain/types.py`
- `src/bioetl/domain/ports.py`
- `src/bioetl/domain/transformations.py`
- `src/bioetl/observability/logging.py`

### Tests
- `tests/unit/domain/test_transformations.py`
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

**Total Code**: ~3,000+ lines of production-ready code + tests + infrastructure + docs

---

## 🚀 Next Steps (Phase 2-11)

### Phase 2: Infrastructure - Adapters (3-4 weeks)

#### 2.1 Storage Adapters (Priority: HIGH)
**Status**: 🔴 Not Started

**Tasks**:
- [ ] Bronze Writer (S3-compatible, JSONL+zstd)
  - Path: `src/bioetl/infrastructure/storage/bronze_writer.py`
  - Requirements: REQ-DATA-001 to 005
  - Append-only, atomic writes, lifecycle policy stub

- [ ] Silver Writer (Delta Lake via delta-rs)
  - Path: `src/bioetl/infrastructure/storage/delta_writer.py`
  - Requirements: REQ-DATA-006 to 008, REQ-DELTA-001 to 003
  - Merge/Upsert, VACUUM scheduler, forensic retention

- [ ] Gold Writer (Strict validation)
  - Path: `src/bioetl/infrastructure/storage/gold_writer.py`
  - Requirements: REQ-DATA-009 to 010
  - SCD Type 2 or date partitioning

**Testing**:
- Integration tests with MinIO (Docker)
- VACUUM scheduling (cron job simulation)

#### 2.2 Lock Adapter (Redis) (Priority: HIGH)
**Status**: 🔴 Not Started

**Tasks**:
- [ ] Redis Lock Implementation
  - Path: `src/bioetl/infrastructure/locking/redis_lock.py`
  - Requirements: REQ-LOCK-001 to 008
  - SETNX + EXPIRE, TTL 60s, Heartbeat 20s, Fencing tokens
  - Safety guard before commit

**Testing**:
- Integration test with Redis (Docker)
- Concurrency tests (multiple workers)
- Heartbeat failure scenarios

#### 2.3 Checkpoint Adapter (S3) (Priority: MEDIUM)
**Status**: 🔴 Not Started

**Tasks**:
- [ ] S3 Checkpoint Storage
  - Path: `src/bioetl/infrastructure/checkpoint/s3_checkpoint.py`
  - Requirements: REQ-CHECKPOINT-001 to 004, REQ-SHUTDOWN-003
  - Atomic writes (If-Match/ETag), recovery, cleanup

#### 2.4 Quarantine Adapter (Priority: MEDIUM)
**Status**: 🔴 Not Started

**Tasks**:
- [ ] Unified Quarantine Table
  - Path: `src/bioetl/infrastructure/quarantine/unified_quarantine.py`
  - Requirements: REQ-QUARANTINE-001 to 004
  - Schema: Delta Lake, 64KB payload limit, 30d retention
  - Operations: write, inspect, replay, purge

---

### Phase 3: Provider Adapters (4-5 weeks, parallel)

#### 3.1 ChEMBL Adapter (Priority 1)
**Status**: 🔴 Not Started

**Tasks**:
- [ ] ChEMBL client implementation
  - Path: `src/bioetl/infrastructure/adapters/chembl/`
  - Library: `chembl_webresource_client`
  - Health check: `/chembl/api/data/status.json`
  - Entities: activities, compounds, targets, assays
  - Rate limiter: backoff on 502/504
  - Circuit breaker (5 errors, 5min open)

**Testing**:
- VCR.py cassettes for API responses
- Contract tests (monthly)

#### 3.2 PubChem Adapter (Priority 2)
**Status**: 🔴 Not Started

**Tasks**:
- [ ] PubChem client implementation
  - Library: `pubchempy` (legacy sync → run_in_executor)
  - Rate limit: 5 req/sec (TokenBucket)
  - Health: lightweight query

#### 3.3 UniProt Adapter (Priority 3)
**Status**: 🔴 Not Started

**Tasks**:
- [ ] UniProt client implementation
  - Library: `unipressed`
  - Rate limit: 100 req/sec (with API key)
  - Health: `/rest/beta/health`

---

### Phase 4: Application Layer - Pipelines (3-4 weeks)

**Status**: 🔴 Not Started

**Tasks**:
- [ ] Pipeline Orchestrator (DAG execution)
- [ ] Graceful shutdown handler (SIGTERM/SIGINT)
- [ ] Lock + Heartbeat manager
- [ ] Checkpoint save/restore
- [ ] Generic ETL Pipeline base class
- [ ] First concrete pipeline: ChEMBL Activities
- [ ] CLI runner (`bioetl run --pipeline ...`)

---

### Phase 5: Data Quality & Observability (2-3 weeks)

**Status**: 🔴 Not Started

**Tasks**:
- [ ] Prometheus metrics exporter
- [ ] Anomaly detection (baseline, thresholds)
- [ ] Lineage tracking implementation
- [ ] Grafana dashboards

---

## 📊 Requirements Compliance

### Implemented Requirements (Phase 0-1 + Docs)

| ID | Requirement | Status |
|----|-------------|--------|
| REQ-ARCH-001 | Ports via typing.Protocol | ✅ |
| REQ-ARCH-002 | mypy --strict enforcement | ✅ |
| REQ-ARCH-003 | No I/O in domain layer | ✅ |
| REQ-ARCH-004 | @runtime_checkable for critical adapters | ⚠️ Deferred to Phase 2 |
| REQ-OBS-001 | run_id in all logs | ✅ |
| REQ-OBS-004 | Structured JSON logs | ✅ |
| REQ-OBS-005 | Log Schema mandatory fields | ✅ |
| REQ-ID-001 to 008 | Content hash algorithm | ✅ |
| REQ-SCHEMA-001 to 004 | Schema drift detection | ✅ |
| REQ-THRESHOLD-001, 002 | DQ thresholds | ✅ |
| REQ-SECRET-004 | .env not in git | ✅ |
| REQ-DX-001 to 005 | Developer experience (Makefile, Docker) | ✅ |
| REQ-DOC-001, 002 | Documentation automation & structure | ✅ |
| REQ-CONTRACT-001 | Gold schemas published (structure ready) | ✅ |

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

### 🔄 Milestone 2: Storage & Locking (In Progress)
**Target**: Week 3-4
**Deliverables**:
- Bronze/Silver/Gold writers (Delta Lake)
- Redis distributed locking
- S3 checkpoint storage
- Quarantine implementation
- Integration tests

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

| Date | Phase | Change |
|------|-------|--------|
| 2025-12-15 | 0-1 | Initial implementation: Foundation + Domain Layer |
| 2025-12-15 | 6 | Documentation overhaul: MkDocs, Guides, Runbooks, ADRs |
| 2025-12-15 | Test | Added meta-testing and domain logic tests |

---

**Next Update**: After Phase 2 completion (Storage & Locking)
