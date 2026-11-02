# P04. Infrastructure, adapters, storage lifecycle Audit Report

## A. Audit Manifest
- **Audit ID**: pack-v2.1/P04
- **Date**: 02.11.2026
- **Pinned Source Revision**: `a5243cb4bbed67b267daecdc097b8c48501e140a`
- **Branch**: `main`
- **Worktree State**: Clean
- **Scope**: `src/bioetl/infrastructure/**`
- **Mode**: `READ_ONLY`
- **Evidence Mode**: `REPO_ONLY` / `RUNTIME_ALLOWED` (Tests/Tools)

## B. Scope/ownership and exclusions
- **In Scope**: All code under `src/bioetl/infrastructure/`, focusing on adapter implementations, storage read/write/merge lifecycle, persistence atomicity, process-crash recovery logic, and control-plane consistency.
- **Out of Scope (Exclusions)**: External provider endpoints, CI/CD pipeline code, physical infrastructure provisioning (Terraform, etc.). Semantic drift is deferred to P09. Physical schema layout is deferred to P07.
- **Missing / Not Checked**: Captured executable run artifacts for recovery, cleanup, and writer-close paths; recorded stdout/exit for `E3-CONFORMANCE-TEST`.

## C. Evidence Ledger
- `E2-PORTS`: `STATIC`, `CURRENT` - Source grep over `src/bioetl/domain/ports/` and `src/bioetl/infrastructure/adapters/`
- `E2-CONFORMANCE`: `STATIC`, `CURRENT` - Source `tests/architecture/test_adapter_port_conformance.py`
- `E3-CONFORMANCE-TEST`: `EXECUTABLE`, `NOT_CAPTURED` - Command planned (`uv run pytest tests/architecture/test_adapter_port_conformance.py`); this report does **not** include timestamp, exit code, or captured output, so the run is not attested here.
- `E2-ATOMICITY`: `STATIC`, `CURRENT` - Storage helper module `src/bioetl/infrastructure/storage/support/atomic_ops.py` and `atomic.py`
- `E2-LIFECYCLE`: `STATIC`, `CURRENT` - HTTP/sync adapter lifecycle in `src/bioetl/infrastructure/adapters/base.py` and `sync_base.py` (HTTP clients only; not storage writers)
- `E2-WRITER-LIFECYCLE`: `STATIC`, `CURRENT` - Absence of `__enter__`/`__exit__`/`close()` on `SilverWriter` / `BronzeWriter` under `src/bioetl/infrastructure/storage/`
- `E2-LEDGER-STRICT`: `STATIC`, `CURRENT` - `iter_jsonl_payloads_strict` in `src/bioetl/infrastructure/control_plane/_file_run_ledger_helpers.py`
- `E2-BRONZE-CLEANUP`: `STATIC`, `CURRENT` - Owned-artifact selection in `src/bioetl/infrastructure/storage/bronze/cleanup_support.py` / `cleanup_posix.py`
- `E2-SILVER-RETENTION`: `STATIC`, `CURRENT` - Silver vacuum / time-travel helpers in `src/bioetl/infrastructure/storage/silver/retention_delta.py` (and related archive helpers)
- `E2-POLICY-SEPARATION`: `STATIC`, `PARTIAL` - Port interfaces under `src/bioetl/domain/ports/` plus adapter placement under `src/bioetl/infrastructure/`; does **not** by itself prove all business logic lives outside infrastructure

## D. Findings Register

### Finding: P04-INFRA-001 (Informational)
- **Finding ID**: `pack-v2.1/P04-INFRA-001`
- **Root Cause ID**: `infra-port-conformance`
- **Owner Prompt**: P04
- **Concern**: Ensure that all domain ports have concrete adapter implementations matching the conformance tests.
- **Severity**: P3
- **Confidence**: high
- **Status**: PARTIAL / OBSERVED (static matrix only; executable run `NOT_CAPTURED`)
- **Expected**: The curated `PORT_ADAPTER_CASES` matrix in `tests/architecture/test_adapter_port_conformance.py` remains the explicit, tested adapter↔port contract for listed cases — **not** a claim that every domain port or discovered constructor is covered.
- **Actual**: `PORT_ADAPTER_CASES` defines the curated conformance matrix. `_DISCOVERED_BINDING_EXCLUSIONS` only documents discovered constructors intentionally **outside** that matrix (stdlib noise / composition helpers); it does **not** prove full domain-port coverage. `E3-CONFORMANCE-TEST` is planned but **not** attested in this report (`NOT_CAPTURED`), so no successful run is claimed here.
- **Evidence IDs**: E2-CONFORMANCE; E3-CONFORMANCE-TEST (`NOT_CAPTURED`)
- **Attempted Disproof**: The exclusion list is annotated as constructors intentionally outside `PORT_ADAPTER_CASES`; treating exclusions as coverage evidence would overclaim.
- **Exceptions Checked**: `_DISCOVERED_BINDING_EXCLUSIONS` in `tests/architecture/test_adapter_port_conformance.py` (scope limiters, not completeness proof)
- **Impact**: Drift risk remains for ports/adapters outside `PORT_ADAPTER_CASES`; this finding only confirms the curated matrix exists statically.
- **Root Cause**: Conformance testing is intentionally curated; discovered exclusions are noise/helpers, not a full inventory of domain ports.
- **Recommendation**: Keep the curated matrix; do not equate exclusions with full coverage. Capture an executable `E3` attestation before raising the conformance score.
- **Scope / Non-Goals**: Does not assert every domain port has a matrix row or a green CI run in this report.
- **Acceptance Criteria**: Curated `PORT_ADAPTER_CASES` remains coherent with listed adapters; executable pass recorded separately when available.
- **Verification Command**: `uv run pytest tests/architecture/test_adapter_port_conformance.py`
- **Dependencies**: None
- **Related Findings**: None

## L. Required Output Matrices

### Adapter / Port Matrix


| Adapter | Port |
|---|---|
| `FilesystemAdrCatalog` | `AdrServicePort` |
| `FileArtifactByteComparisonAdapter` | `ArtifactByteComparisonPort` |
| `BronzeWriter` | `BronzeStoragePort` |
| `CircuitBreakerGuard` | `CircuitBreakerPort` |
| `DeltaReader` | `DeltaReaderPort` |
| `CompositeReplayInputReader` | `DeltaReaderPort` |
| `RequestReader` | `DeltaReaderPort` |
| `ExportCatalogAdapter` | `ExportCatalogPort` |
| `ExportWriterAdapter` | `ExportWriterPort` |
| `SilverForeignKeyReconciliationAdapter` | `ForeignKeyReconciliationPort` |
| `GoldWriter` | `GoldStoragePort` |
| `FileLineageStore` | `LineageStorePort` |
| `MemoryLock` | `LockPort` |
| `NoOpLogger` | `LoggerPort` |
| `StructlogLogger` | `LoggerPort` |
| `UnifiedLogger` | `LoggerPort` |
| `MetadataCoordinator` | `MetadataCoordinatorPort` |
| `PrometheusMetrics` | `MetricsPort` |
| `ChEMBLProteinClassificationGraph` | `ProteinClassificationPort` |
| `PublicationControlledVocabularyLoader` | `PublicationVocabularyPort` |
| `StorageRowReconciliationAdapter` | `RowReconciliationPort` |
| `FileRunLedgerStore` | `RunLedgerPort` |
| `FileRunManifestStore` | `RunManifestPort` |
| `SilverWriter` | `SilverStoragePort` |
| `StageAccountingAccumulator` | `StageAccountingPort` |
| `FileWorkflowExecutionStateStore` | `WorkflowExecutionStatePort` |
| `FileWorkflowLedgerStore` | `WorkflowLedgerPort` |
| `FileWorkflowManifestStore` | `WorkflowManifestPort` |
| `FileAuditAdapter` | `AuditPort` |
| `LocalCheckpointAdapter` | `CheckpointPort` |
| `FileCompositeCheckpointWriter` | `CompositeCheckpointPort` |
| `CrossRefAdapter` | `DataSourcePort` |
| `PubChemAdapter` | `DataSourcePort` |
| `DebugExportAdapter` | `DebugExportPort` |
| `DQReportWriter` | `DQReportWriterPort` |
| `DQConfigLoader` | `DQConfigLoaderProtocol` |
| `FileEffectiveConfigArtifactStore` | `EffectiveConfigArtifactStorePort` |
| `HealthMetricsExpositionAdapter` | `HealthMetricsExpositionPort` |
| `IDMappingCsvReaderAdapter` | `IDMappingSourceReaderPort` |
| `NoOpMetadataWriter` | `MetadataWriterPort` |
| `MetadataWriter` | `MetadataWriterPort` |
| `NoOpMetrics` | `MetricsPort` |
| `MetricsPublisherAdapter` | `MetricsPublisherPort` |
| `MetricsServerAdapter` | `MetricsServerPort` |
| `FileRunReportStoreAdapter` | `RunReportStorePort` |

### Lifecycle Owner Matrix

| Resource / Adapter | Create Owner | Close Owner | Lifecycle Mechanism |
|---|---|---|---|
| `DataSourcePort` (PubChem, CrossRef) | Composition Root | Pipeline / async context | Provider-specific `close()` / `aclose()` or delegated HTTP client shutdown |
| `MetricsPort` | Composition Root | Observability Shutdown | `close()` (e.g. `PrometheusMetrics`) |
| `LoggerPort` | Composition Root | Graceful Shutdown | Adapter-specific shutdown (varies by logger backend) |
| `SilverWriter` / `BronzeWriter` | Composition Root | **N/A** (no close operation on these classes) | **No** `__enter__`/`__exit__` and **no** `close()`; plain port implementations without a context-manager or close API |
| `BaseHttpAdapter` | Composition Root | Pipeline / `__aexit__` | Async context via `__aenter__`/`__aexit__` closes the wrapped HTTP client; base `aclose()` is an explicit **no-op** |

### Storage Atomicity & Crash Recovery Matrix

| Storage Entity | Atomicity Mechanism | Crash Recovery / Interruption | Ordering / Serialization |
|---|---|---|---|
| Metadata sidecars | `atomic_replace` (temp file + rename) | Incomplete temp unpublished; original intact until rename | Deterministic JSON via Pydantic |
| Bronze payloads | `atomic_write_bytes` | Incomplete writes hidden until atomic rename | Binary stream / UTF-8 |
| Silver Delta Tables | Delta merge / commit | Delta Lake transaction log guarantees | Arrow Table deterministic sorting |
| Run Ledger (JSONL) | Append-only JSONL with rollback helpers on partial append | **Fail-closed**: `iter_jsonl_payloads_strict` raises `RunLedgerCorruptionError` on truncated tail / invalid lines; does **not** return a valid prefix | Strict JSONL objects + newline-terminated records |
| Run Manifest | Separate JSON document via atomic text write | Independent of ledger JSONL replay | Single JSON object (not NDJSON) |

### Retention / Cleanup Matrix

| Storage Tier / Entity | Vacuum/Archive Policy | Safety Boundary | Dry-Run Supported | Evidence |
|---|---|---|---|---|
| Bronze owned artifacts | Posix cleanup of allowlisted writer-owned artifacts (`cleanup_posix.py` + `cleanup_support.is_owned_artifact`) | Ownership allowlist / planned candidates — **not** a vacuum of in-flight atomic-write temp files | Yes (`dry_run` param) | `cleanup_posix.py`, `cleanup_support.py` |
| Silver Delta Tables | Delta vacuum / time travel (`retention_delta.py`) | Retention period (e.g., 7 days) | Yes | `retention_delta.py` |
| Orchestration Ledgers | Archive assessment (`archive_assessment.py`) | Max history threshold | Yes | `archive_assessment.py` |

### Concrete Objects Created Outside Composition Root

| Object | Created Location | Rationale / Exemption |
|---|---|---|
| `AtomicWriteGroup` | `atomic_ops.py` / `atomic.py` | Local transactional boundary |
| `AdaptiveRetryPolicy` | Resilience configurations | Structural default outside Composition Root |


## E. Quantitative Scorecard
1. **Adapter / Port Conformance**: 4 (Curated `PORT_ADAPTER_CASES` matrix + test source exist; not full domain-port coverage; executable run not captured). (Evidence: E2-CONFORMANCE; E3-CONFORMANCE-TEST `NOT_CAPTURED`)
2. **Infrastructure Policy Separation**: 3 (Port interfaces and infrastructure adapter placement observed; business-logic delegation beyond port boundaries is only partially evidenced). (Evidence: E2-PORTS, E2-POLICY-SEPARATION `PARTIAL`)
3. **HTTP/API Resilience & Closure**: 4 (Circuit breaker / retry decorators exist; `BaseHttpAdapter` closes via `__aexit__`, base `aclose()` is no-op). (Evidence: E2-LIFECYCLE)
4. **Storage Atomicity & Crash Consistency**: 4 (`atomic.py` / `atomic_ops.py` provide atomic publication; run-ledger interruption is fail-closed, not prefix-replay recovery). (Evidence: E2-ATOMICITY, E2-LEDGER-STRICT)
5. **Control-plane Consistency**: 4 (Append-only ledger JSONL + separate atomic manifest JSON; strict parse rejects truncated tails). (Evidence: E2-LEDGER-STRICT, E2-ATOMICITY)
6. **Lifecycle Management**: 3 (HTTP/sync adapters use async/sync context managers; `SilverWriter`/`BronzeWriter` expose neither CM nor `close()`). (Evidence: E2-LIFECYCLE, E2-WRITER-LIFECYCLE)
7. **Retention / Maintenance**: 3 (Bronze owned-artifact cleanup and Silver vacuum/archive helpers exist statically; end-to-end cleanup/recovery runs not evidenced here). (Evidence: E2-BRONZE-CLEANUP, E2-SILVER-RETENTION)

## F. Cross-cutting/root-cause clusters
- Storage Atomicity is highly centralized (`atomic_ops.py`).
- Adapter Conformance is guarded by architectural tests (static evidence only in this report).
- Earlier draft incorrectly treated storage writers as context-managed and ledger truncation as recoverable prefix replay.

## G. Prioritized roadmap P0->P3
- **P2**: Capture executable evidence (command + UTC timestamp + exit code + relevant stdout) for adapter conformance and for ledger corruption / bronze cleanup paths before raising scores or claiming full verification.
- **P3**: Document writer ownership at composition/pipeline call sites explicitly (since writers lack CM/`close()`).

## H. Verification Matrix
- Adapter/port matrix: curated `PORT_ADAPTER_CASES` static review — verified for listed cases only (not full domain-port census).
- `E3-CONFORMANCE-TEST` executable run: **not captured** in this report.
- Run-ledger truncated-tail behavior: static review of `iter_jsonl_payloads_strict` — verified fail-closed.
- Writer lifecycle CM/`close()` claims: static review (`E2-WRITER-LIFECYCLE`) — **disproved**; Close Owner = N/A.
- `BaseHttpAdapter` close path: static review (`E2-LIFECYCLE`) — `__aexit__` / no-op `aclose()`.
- Bronze cleanup semantics: static review (`E2-BRONZE-CLEANUP`) — owned-artifact cleanup, not write-temp vacuum.
- Silver retention helpers: static path presence (`E2-SILVER-RETENTION`) — not executable proof.
- Runtime recovery / cleanup / resource-close drills: **NOT_VERIFIABLE** here.

## I. `NOT_VERIFIABLE` and missing evidence
- `E3-CONFORMANCE-TEST` run attestation (timestamp, exit code, captured output).
- End-to-end crash-recovery drills for storage writers beyond static atomic helpers.
- Executable proof of bronze cleanup / silver vacuum / ledger archive under failure injection.
- Runtime proof that composition-root owners always close HTTP clients via `__aexit__` in every pipeline path.

## J. Self-check
- Lifecycle, ledger, cleanup, and completeness claims re-checked against pinned sources after review feedback; overstated recovery/`close()` language removed.

## K. Verdict
**Limited / partial.** Static review supports hexagonal adapter/port wiring and atomic write helpers under `src/bioetl/infrastructure/**`, with fail-closed run-ledger parsing and HTTP adapter closure via async context managers. This report does **not** attest a captured conformance-test run, nor executable recovery/cleanup/close drills; those remain `NOT_VERIFIABLE` here. Do not treat the scorecard as a completed end-to-end infrastructure audit.
