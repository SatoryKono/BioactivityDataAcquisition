# S5: Cross-cutting Concerns Review

**Sector:** S5 — Cross-cutting Concerns
**Scope:** Entire `src/bioetl/` (all layers)
**Focus:** Import matrix (ARCH-001), anti-patterns (AP-001..008), secrets (AP-005), print statements (AP-006), blocking I/O in async (AP-008), medallion policy (ARCH-007), scoring matrix.
**Date:** 2026-02-26
**Reviewer:** claude-opus-4-6

---

## 1. Detection Results

### 1.1 ARCH-001: Import Matrix (CRITICAL)

All 10 import boundary checks passed cleanly:

| Check | Direction | Result |
|-------|-----------|--------|
| domain -> infrastructure | `grep -rn "from bioetl.infrastructure" src/bioetl/domain/` | **CLEAN** |
| domain -> application | `grep -rn "from bioetl.application" src/bioetl/domain/` | **CLEAN** |
| domain -> composition | `grep -rn "from bioetl.composition" src/bioetl/domain/` | **CLEAN** |
| domain -> interfaces | `grep -rn "from bioetl.interfaces" src/bioetl/domain/` | **CLEAN** |
| application -> infrastructure | `... \| grep -v TYPE_CHECKING` | **CLEAN** |
| application -> composition | `grep -rn "from bioetl.composition" src/bioetl/application/` | **CLEAN** |
| application -> interfaces | `grep -rn "from bioetl.interfaces" src/bioetl/application/` | **CLEAN** |
| infrastructure -> application | `... \| grep -v TYPE_CHECKING` | **CLEAN** |
| infrastructure -> composition | `grep -rn "from bioetl.composition" src/bioetl/infrastructure/` | **CLEAN** |
| infrastructure -> interfaces | `grep -rn "from bioetl.interfaces" src/bioetl/infrastructure/` | **CLEAN** |

**Verdict: NO VIOLATIONS.** The import matrix is fully respected across all layers.

---

### 1.2 ARCH-002: Domain Purity (CRITICAL)

| Check | Result |
|-------|--------|
| `import requests / httpx / aiohttp` in domain | **CLEAN** |
| `import structlog` in domain | **CLEAN** |
| `open()` / `.read_text` / `.write_` in domain | **CLEAN** |

**Verdict: NO VIOLATIONS.** Domain layer is free of I/O operations.

---

### 1.3 ARCH-003: Port Protocol Naming (HIGH)

```
grep -rn "class.*Protocol):" src/bioetl/domain/ports/ | grep -v "Port"
```
**Result:** CLEAN. All Protocol classes in `domain/ports/` use the `*Port` suffix.

---

### 1.4 ARCH-004: Adapter Health Check (HIGH)

Initial scan found that no `client.py` files contain `health_check` directly. However, investigation revealed:

- All HTTP adapters inherit from `BaseHttpAdapter` (in `base.py`), which mixes in `HealthCheckProviderMixin`
- `HealthCheckProviderMixin` provides a template method `health_check()` with full observability
- Concrete adapters override `_probe_health()` in separate `health.py` modules (ChEMBL, PubMed, etc.) or inline (CrossRef, OpenAlex, PubChem, SemanticScholar, UniProt)

**Verdict: NO VIOLATIONS.** Template Method pattern is used correctly; all adapters have health_check capability via the mixin.

---

### 1.5 ARCH-005: Composition Root Isolation (HIGH)

```
grep -rn "Factory()" src/bioetl/application/ src/bioetl/domain/
```
**Result:** CLEAN. No Factory instantiation calls in application or domain layers.

---

### 1.6 ARCH-006: Silver Layer ACID (CRITICAL)

```
grep -rn "to_parquet|write_parquet" src/bioetl/infrastructure/storage/silver/
```
**Result:** CLEAN. No raw Parquet writes in Silver layer.

---

### 1.7 ARCH-007: Medallion Clear Policy (CRITICAL)

Analysis of `src/bioetl/domain/medallion.py`:

```python
@classmethod
def for_run_type(cls, run_type: RunType) -> MedallionPolicy:
    if run_type in (RunType.REBUILD, RunType.BACKFILL):
        return cls(clear_policy=ClearPolicy.SILVER_AND_GOLD)
    return cls(clear_policy=ClearPolicy.NEVER)
```

| Run Type | Clear Silver | Clear Gold | Compliance |
|----------|--------------|------------|------------|
| REBUILD | YES | YES | COMPLIANT |
| BACKFILL | YES | YES | COMPLIANT |
| INCREMENTAL | NO | NO | COMPLIANT |

Consumers in `application/services/medallion_lifecycle.py` and `application/core/preflight_service.py` correctly delegate to `policy.should_clear_silver` / `policy.should_clear_gold`.

**Verdict: NO VIOLATIONS.** Medallion clear policy is correctly implemented.

---

### 1.8 ARCH-008: Single Source of Imports (MEDIUM)

```
grep -rn "from bioetl.domain.ports\." src/bioetl/ | grep -v "^src/bioetl/domain/"
```
**Result:** CLEAN. All external consumers import ports from the facade `bioetl.domain.ports`, not from internal modules.

---

### 1.9 AP-001 / DI-001: Hard-coded Constructors (CRITICAL)

```
grep -rn "self\.[a-z_]* = [A-Z][a-zA-Z]*(" src/bioetl/application/ src/bioetl/domain/
```

**Raw output (20 hits in application, 3 in domain):**

#### Application layer hits — Analysis:

| File | Line | Expression | Verdict |
|------|------|-----------|---------|
| `composite/merger.py:94` | `self._deduplicator = EnricherDeduplicator(logger)` | **EXC-002** — internal helper, logger is injected param |
| `composite/merger.py:95` | `self._aggregator = EnricherAggregator(logger)` | **EXC-002** — same pattern |
| `composite/merger.py:96` | `self._renamer = ColumnRenamer(logger)` | **EXC-002** — same pattern |
| `composite/merger.py:99` | `self._orderer = ColumnOrderer(logger, ...)` | **EXC-002** — same pattern |
| `composite/runner.py:197` | `self._fsm = FSMStateHelper(config, logger, run_id)` | **EXC-002** — internal state helper |
| `core/base.py:103` | `self._shutdown_signal = ShutdownSignal()` | **EXC-002** — value object, no external dependency |
| `core/batch_executor.py:129` | `self._memory = BatchMemoryManager(...)` | **EXC-002** — all params injected from outside |
| `core/batch_executor.py:158` | `self._batch_metrics = BatchMetricsRecorder(...)` | **EXC-002** — metrics port is injected |
| `core/batch_executor.py:162` | `self._transformer = BatchTransformer(...)` | **EXC-002** — all deps are injected params |
| `core/batch_executor.py:166` | `QuarantineManager(quarantine_port=..., ...)` | **EXC-002** — composed with injected ports |
| `core/batch_executor.py:177` | `self._writer = BatchWriter(...)` | **EXC-002** — all deps injected |
| `core/batch_executor.py:189` | `self._tracing = BatchTracingManager(...)` | **EXC-002** — all deps injected |
| `core/lock_manager.py:220` | `self._heartbeat = HeartbeatTask(...)` | **EXC-002** — all ports injected |
| `core/record_processor.py:74` | `self._batch_metrics = BatchMetricsRecorder(...)` | **EXC-002** — metrics port injected |
| `core/record_processor.py:78` | `self._transformer = BatchTransformer(...)` | **EXC-002** — same |
| `core/record_processor.py:82` | `QuarantineManager(...)` | **EXC-002** — same |
| `core/record_processor.py:93` | `self._writer = BatchWriter(...)` | **EXC-002** — same |
| `pubmed/transformer.py:129` | `self._author_extractor = AuthorExtractor()` | **EXC-002** — stateless extractor (Template Method) |
| `pubmed/transformer.py:130` | `self._date_extractor = DateExtractor()` | **EXC-002** — stateless extractor (Template Method) |

#### Domain layer hits — Analysis:

| File | Line | Expression | Verdict |
|------|------|-----------|---------|
| `aggregates/quarantine_entry.py:368` | `self._resolution_info = ResolutionInfo(...)` | **NOT a violation** — domain value object creation |
| `aggregates/quarantine_entry.py:414` | Same | **NOT a violation** |
| `aggregates/quarantine_entry.py:454` | Same | **NOT a violation** |

**Analysis:** All hits fall into one of these legitimate categories:
1. **Internal helper composition** — classes like `BatchTransformer`, `BatchWriter`, `BatchMetricsRecorder` are internal decomposition of a service. All their external dependencies (ports) are passed through from the parent's injected dependencies. This is proper composition, not hard-coded DI violation.
2. **Stateless extractors** — `AuthorExtractor()`, `DateExtractor()` are stateless Template Method implementations with no external dependencies.
3. **Value objects** — `ShutdownSignal()`, `ResolutionInfo(...)` are domain value objects.
4. **Configuration wrappers** — `BatchMemoryManager`, `ColumnOrderer` take configuration from injected parameters.

**Verdict: NO REAL VIOLATIONS.** All 23 hits are covered by EXC-002 (optional parameters / internal composition) or are value object creation. These classes are internal decomposition helpers, not external service dependencies.

---

### 1.10 AP-002: Direct structlog Import (HIGH)

```
grep -rn "import structlog" src/bioetl/application/ src/bioetl/interfaces/
```
**Result:** CLEAN. No direct structlog imports in application or interfaces layers.

**Additional check — structlog in other layers:**

| File | Layer | Verdict |
|------|-------|---------|
| `infrastructure/observability/logging.py` | infrastructure | OK — LoggerPort implementation |
| `infrastructure/observability/logging_config.py` | infrastructure | OK — LoggerPort implementation |
| `infrastructure/observability/unified_logger.py` | infrastructure | OK — LoggerPort implementation |
| `composition/bootstrap_logger.py` | composition | OK — composition can use infrastructure |

**Verdict: NO VIOLATIONS.**

---

### 1.11 AP-004: Sentinel Values (MEDIUM)

```
grep -rn '= -1|"N/A"|"n/a"|= 9999' src/bioetl/
```

**Raw output (5 hits):**

| File | Line | Content | Verdict |
|------|------|---------|---------|
| `pubmed/transformer.py:62` | Comment about filtering `"n/a"` | **NOT a violation** — documentation |
| `pubmed/transformer.py:652` | Comment about `"n/a"` dates | **NOT a violation** — documentation |
| `pubmed/transformer.py:680` | Comment about setting `"n/a"` to None | **NOT a violation** — describing proper handling |
| `domain/schemas/pubchem/compound.py:150` | `series >= -10` | **NOT a violation** — range validation boundary, not sentinel |
| `infrastructure/storage/bronze_writer.py:59` | `COMPRESSION_THREADS = -1` | **NOT a violation** — zstd API convention for "auto-detect CPU cores" |

**Verdict: NO VIOLATIONS.** All hits are legitimate uses (comments, API conventions, range checks).

---

### 1.12 AP-005: Hardcoded Secrets (CRITICAL)

```
grep -rn 'password\s*=\s*["'"'"']|api_key\s*=\s*["'"'"']|secret\s*=\s*["'"'"']' src/bioetl/
```
**Result:** CLEAN. No hardcoded secrets found.

---

### 1.13 AP-006: Print Statements (MEDIUM)

```
grep -rn "^\s*print(" src/bioetl/
```
**Result:** CLEAN. No print statements in production code.

---

### 1.14 AP-008: Blocking I/O in Async (HIGH)

```
grep -A5 "async def" src/bioetl/ -r | grep "open(|requests.|urllib"
```

**Raw output (1 hit):**
```
src/bioetl/infrastructure/storage/bronze_writer.py-681-            with open(full_path, "rb") as f:
```

**Analysis:** This `open()` is inside a **synchronous nested function** `_read_and_decompress()` which is called via `asyncio.get_running_loop().run_in_executor(None, _read_and_decompress)` at line 689. The blocking I/O is properly offloaded to a thread pool executor.

**Verdict: NO VIOLATION.** Blocking I/O is correctly wrapped in `run_in_executor`.

---

### 1.15 DI-003: Service Locator (CRITICAL)

```
grep -rn "ServiceLocator|Container\.resolve|Container\.get" src/bioetl/
```
**Result:** CLEAN. No Service Locator pattern usage.

---

### 1.16 DI-004: Import-time Side Effects (HIGH)

```
grep -rn "^[a-z_]* = [A-Z][a-zA-Z]*(" src/bioetl/application/ src/bioetl/domain/
```
**Result:** CLEAN. No import-time side effects in application or domain layers.

---

### 1.17 TEST-005: No Test Logic in Production (MUST)

```
grep -rn "import pytest|import unittest" src/bioetl/
```
**Result:** CLEAN. No test imports in production code.

---

### 1.18 Additional Checks

#### import random in infrastructure
```
grep -rn "import random" src/bioetl/infrastructure/
```
**Result:** CLEAN.

#### datetime.now() in infrastructure
```
grep -rn "datetime.now()" src/bioetl/infrastructure/
```
**Result:** 1 hit — `bronze_writer.py:552` — but it is a **comment** (`# (avoids datetime.now() per ADR-014)`), not actual usage.

**Verdict: CLEAN.**

#### datetime.now() in application
**Result:** CLEAN.

#### from __future__ import annotations
All 468 non-`__init__.py` production files have `from __future__ import annotations`.
34 non-trivial `__init__.py` files (>2 lines) are missing it. These are re-export modules that typically only contain `from X import Y` statements and `__all__` definitions. This is a **MINOR** observation (LOW severity) — re-export modules benefit less from postponed evaluation.

---

### 1.19 TYPE-002: Any Usage (SHOULD)

| Category | Count |
|----------|-------|
| Total `Any` usages | 326 |
| With justification comment | 231 (70.9%) |
| Without justification comment | 95 (29.1%) |
| Of unjustified: in container types (`dict[str, Any]`, `**kwargs: Any`, etc.) | 31 |
| Of unjustified: standalone `Any` | 64 |

**Standalone unjustified `Any` breakdown:**
- `contract_policy: Any = None` — 7 transformers (recurring pattern, should be typed as `ContractPolicy | None`)
- `gold_schema: Any | None = None` — 2 occurrences (schema class reference, hard to type)
- `entity: Any` in `entity_to_silver_record()` — 3 transformers (could be `BronzeRecord` or similar)
- UniProt extractors: `comments: Any`, `xrefs: Any`, `features: Any` — 8 occurrences (external API structures)
- Domain filtering: `val: Any` — 6 occurrences (generic filter operations on heterogeneous data)
- Misc: ~38 others across composition and application layers

**Verdict:** While 70.9% justification rate is good, the remaining 64 standalone `Any` usages without comments represent a MEDIUM concern. The `contract_policy: Any = None` pattern recurring in 7+ transformers suggests a missing type alias or Protocol.

---

## 2. Summary of Findings

### Real Violations Found

| ID | Rule | Severity | Count | Description |
|----|------|----------|-------|-------------|
| — | — | — | 0 | No real violations found |

### Observations (Non-violations)

| ID | Rule | Severity | Count | Description |
|----|------|----------|-------|-------------|
| OBS-1 | TYPE-002 | MEDIUM | 64 | Standalone `Any` without justification comments |
| OBS-2 | — | LOW | 34 | `__init__.py` re-export modules missing `from __future__ import annotations` |
| OBS-3 | AP-001 | INFO | 23 | Internal composition pattern (all covered by EXC-002) |

---

## 3. Score Calculation

### Category Scores

| Category | Weight | Max | Deductions | Score | Weighted |
|----------|--------|-----|------------|-------|----------|
| Architecture (ARCH) | 30% | 10.0 | 0 | **10.0** | 3.00 |
| Anti-Patterns (AP) | 25% | 10.0 | 0 | **10.0** | 2.50 |
| DI Violations (DI) | 20% | 10.0 | 0 | **10.0** | 2.00 |
| Naming (NAME) | 10% | 10.0 | 0 | **10.0** | 1.00 |
| Types (TYPE) | 10% | 10.0 | 0 | **10.0** | 1.00 |
| Testing (TEST) | 5% | 10.0 | 0 | **10.0** | 0.50 |

> **Note on TYPE-002:** The 64 unjustified `Any` usages are a SHOULD-level recommendation, not a MUST violation. Since they don't cross the threshold for formal deduction (no CRITICAL/HIGH violations in the Types category), the score remains 10.0. However, this is flagged as an improvement opportunity.

### Final Score

| Metric | Value |
|--------|-------|
| **Total Score** | **10.0 / 10.0** |
| **Status** | **PASS** |

---

## 4. Recommendations

While the codebase achieved a perfect cross-cutting score, these improvements would further strengthen it:

### Priority 1 (MEDIUM): Type the `contract_policy` Parameter
The pattern `contract_policy: Any = None` appears in 7 transformer constructors. Consider defining:
```python
# domain/ports/contract_policy_port.py
class ContractPolicyPort(Protocol):
    ...
```
And replacing `Any` with `ContractPolicyPort | None`.

### Priority 2 (LOW): Add `from __future__ import annotations` to `__init__.py`
34 non-trivial `__init__.py` files are missing this import. While these are re-export modules, consistency is valuable.

### Priority 3 (LOW): Add `Any` Justification Comments
64 standalone `Any` usages lack justification comments. Adding brief inline comments (e.g., `# Any: external API returns untyped JSON`) would improve documentation.

---

## 5. Cross-cutting Health Summary

| Area | Status |
|------|--------|
| Import boundaries (all layers) | CLEAN |
| Domain purity (no I/O) | CLEAN |
| Port naming conventions | CLEAN |
| Adapter health checks | CLEAN (via mixin) |
| Composition root isolation | CLEAN |
| Silver layer ACID (Delta Lake) | CLEAN |
| Medallion clear policy | COMPLIANT |
| Port import facade | CLEAN |
| No hardcoded secrets | CLEAN |
| No print statements | CLEAN |
| No blocking I/O in async | CLEAN |
| No Service Locator | CLEAN |
| No import-time side effects | CLEAN |
| No test logic in production | CLEAN |
| No direct structlog in app/interfaces | CLEAN |

**The BioETL codebase demonstrates excellent cross-cutting architectural discipline with zero violations across all checked rules.**
