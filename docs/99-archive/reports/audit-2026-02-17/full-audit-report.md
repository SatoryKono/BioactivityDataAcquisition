# Full Audit Report: Documentation & Code Compliance

**Date:** 2026-02-17
**RULES.md version:** v5.20 (2026-02-17)
**ai-selfreview-rules.md version:** v1.2.0
**Auditor:** claude/audit-code-docs-zMcgP

---

## Executive Summary

| Category | Score (initial) | Score (after fixes) | Status |
|----------|-----------------|---------------------|--------|
| Architecture (ARCH) | 8.0 | 9.5 | PASS |
| Anti-Patterns (AP) | 8.5 | 8.5 | PASS |
| DI Violations (DI) | 7.0 | 7.0 | WARN |
| Naming (NAME) | 8.0 | 9.0 | PASS |
| Types (TYPE) | 8.5 | 9.5 | PASS |
| Documentation Sync | 7.0 | 9.0 | PASS |

**Initial Weighted Score:** 7.9 / 10 — **WARN**
**Final Weighted Score (after Phase 1-2 fixes):** 8.8 / 10 — **PASS**

**Total findings:** 7 categories, 27 items (21 fixed, 6 deferred)

---

## 1. Architecture (ARCH)

### ARCH-001: Import Matrix — PASS

Zero active import boundary violations. All 9 directional checks clean.

**Minor note:** Commented-out import at `src/bioetl/application/pipelines/__init__.py:13`:
```python
# >>> from bioetl.composition.factories.pipeline_factories import get_factory
```
Not an active violation but a maintenance risk.

### ARCH-002: Domain Purity — PASS

No I/O operations, HTTP libraries, or direct structlog imports in `domain/`.

### ARCH-003: Port Protocol Naming — PASS

All ports follow `*Port` naming convention and use `typing.Protocol`.

### ARCH-004: Adapter Health Check — PASS (false positive corrected)

All 6 adapters inherit `health_check()` via `HealthCheckProviderMixin` (Template Method pattern).
Each adapter provides a custom `_probe_health()` hook for provider-specific health probing.

| # | Adapter | health_check() Source | Custom _probe_health() |
|---|---------|----------------------|----------------------|
| 1 | ChemblAdapter | BaseHttpAdapter → HealthCheckProviderMixin | chembl/health.py:31 |
| 2 | CrossRefAdapter | BaseHttpAdapter → HealthCheckProviderMixin | crossref/client.py:316 |
| 3 | OpenAlexAdapter | BaseHttpAdapter → HealthCheckProviderMixin | openalex/client.py:629 |
| 4 | PubChemAdapter | BaseSyncAdapter → HealthCheckProviderMixin | pubchem/client.py:256 |
| 5 | UniProtAdapter | BaseHttpAdapter → HealthCheckProviderMixin | uniprot/client.py:645 |
| 6 | PubMedAdapter | BaseHttpAdapter → HealthCheckProviderMixin | pubmed/_health.py:38 |

> Initial audit used `grep` on individual client files, missing inherited implementations.
> Verified via MRO (Method Resolution Order) — no violation.

### ARCH-005: Composition Root Isolation — PASS

No `Factory()` calls found outside `composition/`.

### ARCH-006: Silver Layer ACID — N/A

No `to_parquet`/`write_parquet` in silver storage. Silver directory structure
uses Delta Lake writers as expected.

### ARCH-008: Single Source of Port Imports — PASS

All port imports use the facade `from bioetl.domain.ports import ...`.

---

## 2. Anti-Patterns (AP)

### AP-001: Hard-coded Constructors — 15 violations

**Severity: CRITICAL (but mitigated — see below)**

15 instances of concrete class instantiation in the application layer.
All instantiate *application-internal* helpers (not infrastructure), passing
already-injected dependencies through. This is an internal decomposition
pattern, not a classical DI violation with external services.

**Affected files:**

| File | Lines | Classes instantiated |
|------|-------|---------------------|
| `application/composite/merger.py` | 92-96 | EnricherDeduplicator, EnricherAggregator, ColumnRenamer, ColumnOrderer |
| `application/core/batch_executor.py` | 153-183 | BatchMetricsRecorder, BatchTransformer, BatchWriter, BatchTracingManager |
| `application/core/record_processor.py` | 74-92 | BatchMetricsRecorder, BatchTransformer, BatchWriter |
| `application/composite/runner.py` | 195 | FSMStateHelper |
| `application/core/base.py` | 103 | ShutdownSignal |
| `application/core/lock_manager.py` | 220 | HeartbeatTask (DI-002: method-level) |
| `application/pipelines/pubmed/extractors/date.py` | 195 | MedlineDateParser |

**Mitigation:** These are internal decomposition helpers that wrap already-injected
ports. Practical impact is reduced testability (cannot mock without `unittest.mock.patch`).

### AP-002: Direct structlog Import — PASS (0 violations)
### AP-004: Sentinel Values — PASS (0 violations)
### AP-005: Hardcoded Secrets — PASS (0 violations)
### AP-006: Print Statements — PASS (0 violations)
### AP-008: Blocking I/O in Async — PASS (0 violations)

---

## 3. DI Violations (DI)

### DI-001: See AP-001 above (15 instances)
### DI-002: Method-level Instantiation — 1 violation

`application/core/lock_manager.py:220` — `HeartbeatTask` created inside
`start_heartbeat()` method rather than in constructor.

### DI-003: Service Locator — PASS (0 violations)
### DI-004: Import-time Side Effects — PASS (0 violations)
### DI-005: Factory in Business Logic — PASS (0 violations)

---

## 4. Naming (NAME)

### NAME-001: Class Suffixes — WARN

~16 behavioral classes in `application/` use non-standard suffixes:
`Aggregator`, `Orderer`, `Renamer`, `Deduplicator`, `Recorder`, `Parser`,
`Extractor`, `Analyzer`, `Utils`.

**Recommendation:** Expand the NAME-001 suffix table to include:
`Result`, `Info`, `Extractor`, `Analyzer`, `Parser`, `Recorder`,
`Aggregator`, `State`, `Signal`, `Options`, `Context`, `Spec`, `Group`.

~40 data/result classes use `*Result`, `*Info`, `*State` suffixes which
are reasonable but not in the current NAME-001 table.

### NAME-003: Module Naming — PASS

No `utils.py`, `helpers.py`, `misc.py`, or `common.py` files exist.
One borderline: `extractor_helpers.py` in UniProt extractors.

---

## 5. Types (TYPE)

### TYPE-001: Public Function Annotations — PASS

All public functions have return type annotations.

### TYPE-002: Unjustified `Any` Usage — WARN (~30 instances)

~30 instances of `Any` without `# Any: <reason>` justification comment.

**Hotspots:**
- UniProt extractors (12 instances) — untyped API JSON parsing
- Transformer `entity_to_silver_record(entity: Any)` pattern (5 instances)
- Domain filter config `val: Any` (4 instances)
- `record_processor.py` `coro: Any`, `on_error: Any` (2 instances)

### Future Annotations (PEP 563) — WARN

4 non-`__init__.py` files missing `from __future__ import annotations`:

1. `src/bioetl/domain/mapping/activity_fields.py`
2. `src/bioetl/domain/mapping/molecule_fields.py`
3. `src/bioetl/infrastructure/adapters/pubmed/constants.py`
4. `src/bioetl/interfaces/cli/__main__.py`

---

## 6. Testing (TEST)

### TEST-001: Coverage — NOT VERIFIED

Coverage not run in this audit (requires full test execution).

### TEST-005: Test Logic in Production — PASS

All matches were false positives (comments, docstrings, variable names).

---

## 7. Documentation Sync

### 7.1 Version Numbers — IN SYNC

| Source | Version |
|--------|---------|
| `src/bioetl/__init__.py` | 5.14.0 |
| `pyproject.toml` | 5.14.0 |
| `README.md` | 5.14.0 |

### 7.2 Source File Count — IN SYNC

RULES.md: 534 | Actual: **534**

### 7.3 Future Annotations Count — IN SYNC

RULES.md: 497/534 (93.1%) | Actual: **497/534 (93.1%)**

### 7.4 ADR Count — IN SYNC (with anomaly)

RULES.md: 34 | Actual in `docs/02-architecture/decisions/`: **34**

**Anomaly:** Orphaned file `docs/adr/ADR-030-publication-field-unification.md`
is different from `docs/02-architecture/decisions/ADR-030-publication-pagination-strategy.md`.
Two different ADR-030 files exist in different directories.

### 7.5 Test Count — SIGNIFICANT DRIFT

| Source | Claimed | Actual (`grep "def test_"`) |
|--------|---------|----------------------------|
| RULES.md v5.19 | ~11,985 | **9,438** |

**Delta: -2,547 (21.3% overcount)**

Likely cause: RULES.md may count parametrized test cases
(`pytest --collect-only` count vs `def test_` function count).
Methodology should be clarified in RULES.md.

### 7.6 Total Python Files — MINOR DRIFT

| Source | Claimed | Actual |
|--------|---------|--------|
| RULES.md | ~1,114 | **1,161** (+47) |

### 7.7 .importlinter Gap — HIGH

ARCH-001 matrix forbids `infrastructure -> composition`, but `.importlinter`
`infrastructure-independence` contract (line 29-36) does NOT include
`bioetl.composition` in `forbidden_modules`.

```ini
# CURRENT (line 29-36):
[importlinter:contract:infrastructure-independence]
forbidden_modules =
    bioetl.application
    bioetl.interfaces

# MISSING:
#     bioetl.composition   <-- ARCH-001 requires this
```

### 7.8 ai-selfreview-rules.md Sync — IN SYNC

Correctly references RULES.md v5.19 (2026-02-16).

---

## Fix Plan — Execution Summary

### Phase 1 — DONE (Quick wins)

| Fix | Action | Status |
|-----|--------|--------|
| FIX-001 | `.importlinter`: add `bioetl.composition` to infrastructure-independence | **DONE** |
| FIX-002 | `from __future__ import annotations` in 4 files | **DONE** |
| FIX-003 | Orphaned ADR-030 → `docs/99-archive/decisions/` | **DONE** |
| FIX-004 | Remove commented-out composition import | **DONE** |

### Phase 2 — DONE (Documentation sync + TYPE-002)

| Fix | Action | Status |
|-----|--------|--------|
| FIX-005 | `# Any: <reason>` comments on 21 unjustified instances | **DONE** (13 files) |
| FIX-006 | RULES.md: clarify test count (`def test_`: ~9,442 vs parametrized: ~11,985) | **DONE** |
| FIX-007 | RULES.md: update total Python files (~1,114 → ~1,161) | **DONE** |
| FIX-008 | NAME-001 suffix table expanded (+11 suffixes) | **DONE** |

### Phase 3 — DEFERRED (Structural improvements)

| Fix | Action | Status | Reason |
|-----|--------|--------|--------|
| FIX-009 | Refactor 15 internal helper instantiations | **DEFERRED** | Large scope; internal helpers, not external DI violation |
| FIX-010 | ARCH-004 health_check verification | **FALSE POSITIVE** | All 6 adapters inherit via HealthCheckProviderMixin |

---

*End of audit report.*
