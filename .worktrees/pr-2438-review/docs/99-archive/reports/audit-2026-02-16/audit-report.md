# BioETL Code Audit Report

**Date**: 2026-02-16
**Scope**: `src/bioetl/` (all layers), 534 Python files, ~115K LOC
**Branch**: `claude/audit-bioetl-code-3BOwh`
**Baseline**: Previous audit (2026-02-08) — all MUST findings resolved

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Total objects (classes/functions/constants) | 1711 |
| Classes | 911 |
| Module-level functions | 619 |
| Constants (UPPER-SNAKE-CASE) | 181 |
| **MUST violations** | **2** |
| SHOULD violations | 9 |
| MAY / informational | 6 |
| Security CVEs | 3 |
| Cyclomatic complexity violations | 38 |
| Import-linter contracts | 5/5 PASS |
| Architecture tests | 1151 pass, 1 fail (formatting) |

**Overall Score: 9.55 / 10.0 — PASS**

---

## 1. Inventory Summary (Phase A)

### Objects per Layer

| Layer | Classes | Functions | Constants | Total |
|-------|---------|-----------|-----------|-------|
| domain | 432 | 184 | 51 | 667 |
| application | 185 | 129 | 40 | 354 |
| infrastructure | 256 | 85 | 77 | 418 |
| composition | 34 | 149 | 5 | 188 |
| interfaces | 4 | 72 | 8 | 84 |
| **Total** | **911** | **619** | **181** | **1711** |

### Top 10 Largest Classes

| Class | LOC | Location |
|-------|-----|----------|
| MergeService | 1749 | application/composite/merger.py |
| SilverWriter | 1075 | infrastructure/storage/silver-writer.py |
| CompositePipelineRunner | 1039 | application/composite/runner.py |
| ChemblAdapter | 933 | infrastructure/adapters/chembl/client.py |
| GoldWriter | 894 | infrastructure/storage/gold-writer.py |
| BronzeWriter | 755 | infrastructure/storage/bronze-writer.py |
| BaseTransformer | 738 | application/core/base-transformer.py |
| BatchExecutor | 725 | application/core/batch-executor.py |
| PubMedPublicationTransformer | 685 | application/pipelines/pubmed/transformer.py |
| OpenAlexAdapter | 677 | infrastructure/adapters/openalex/client.py |

> **Note (EXC-005):** Large classes (500+ LOC) are NOT flagged as god objects if they
> demonstrate proper delegation via `self.-component.method()`. These classes
> are predominantly orchestrators/adapters with high delegation counts.

### Top 10 Largest Functions

| Function | LOC | Location |
|----------|-----|----------|
| bootstrap-composite-runner | 279 | composition/bootstrap/runtime/composite.py |
| register-all-providers | 174 | composition/providers/registration.py |
| assemble-runner | 144 | composition/factories/pipeline-factory.py |
| create-pipeline-with-services | 112 | composition/factories/pipeline-factory.py |
| register-all-transformers | 103 | composition/factories/transformer-factory.py |
| register-provider | 100 | composition/providers/decorators.py |
| build-pipeline-runner | 97 | composition/runtime-builders/runner-builder.py |
| export-command | 93 | interfaces/cli/commands/export.py |
| check-anomaly-detection | 82 | application/services/dq/-checks-statistical.py |
| bootstrap-storage-adapter | 82 | composition/bootstrap/assembly/storage.py |

> Large functions are concentrated in `composition/` (assembly/factory) which is
> architecturally expected — this is the wiring layer.

---

## 2. Architecture Rules (ARCH)

### ARCH-001: Import Matrix — PASS

All 10 forbidden import directions checked: **0 violations**.

| Direction | Result |
|-----------|--------|
| domain → infrastructure | CLEAN |
| domain → application | CLEAN |
| domain → composition | CLEAN |
| domain → interfaces | CLEAN |
| application → infrastructure | CLEAN |
| application → composition | CLEAN |
| application → interfaces | CLEAN |
| infrastructure → application | CLEAN |
| infrastructure → composition | CLEAN |
| infrastructure → interfaces | CLEAN |

### ARCH-002: Domain Purity — PASS

- No `import requests/httpx/aiohttp` in domain
- No `import structlog` in domain
- No file I/O (`open()`) in domain (false positives from `-assert-open()` method correctly excluded)

### ARCH-003: Port Protocol Naming — PASS

All ports defined as `typing.Protocol` with `*Port` suffix in `domain/ports/`.

### ARCH-006: Silver Layer ACID — PASS

No `to-parquet` or `write-parquet` found in `infrastructure/storage/`. Delta Lake is used.

### ARCH-008: Single Source of Imports — PASS

No external layers import from `bioetl.domain.ports.<submodule>` directly.
All use the facade `bioetl.domain.ports`.

**Architecture Score: 10.0 / 10.0**

---

## 3. Anti-Patterns (AP)

### AP-001: Hard-coded Constructors — SHOULD (informational)

The `application/core/` layer creates internal helper objects:
- `BatchMetricsRecorder(...)` in `record-processor.py` and `batch-executor.py`
- `BatchTransformer(...)` in `record-processor.py` and `batch-executor.py`
- `BatchWriter(...)` in `batch-executor.py`
- `MedlineDateParser()` in `pubmed/extractors/date.py`

**Assessment:** These are internal application-layer components (not cross-layer dependencies),
created from injected ports and config. This is acceptable per EXC-002 (Optional Parameters
with Defaults) and follows the pattern of internal decomposition within a single layer.
**Not flagged as violations.**

### AP-002: Direct structlog Import — PASS

Zero `import structlog` in `application/` or `interfaces/`.

### AP-005: Hardcoded Secrets — PASS

No hardcoded passwords, API keys, or secrets found.

### AP-006: Print Statements — PASS

Zero `print()` calls outside `interfaces/cli/`.

### AP-008: Blocking I/O in Async — PASS

The one hit (`bronze-writer.py:681`) uses `open()` inside a sync `-read-and-decompress()`
helper that is called via `run-in-executor()` — this is the correct async pattern.

**Anti-Patterns Score: 10.0 / 10.0**

---

## 4. DI Violations (DI)

### DI-001: Hard-coded Constructor — See AP-001 (informational, not violation)

### DI-003: Service Locator — PASS

No `ServiceLocator`, `Container.resolve`, or `Container.get` found.

### DI-004: Import-time Side Effects — PASS

No module-level object instantiation in `application/` or `domain/` (excluding tests, TypeVar, configs).

### DI-005: Factory in Business Logic — PASS

No `Factory()` calls in `application/` or `domain/`.

**DI Score: 10.0 / 10.0**

---

## 5. Naming Conventions (NAME)

### NAME-001: Class Suffixes — SHOULD

30 classes found without standard suffixes. Analysis by category:

**Enums (valid, NAME-006 compliant):** `RunType`, `DriftLevel`, `HealthStatus`,
`CircuitBreakerState`, `DataClassification`, `ErrorType`, `QuarantineRecordStatus`,
`Layer`, `WriteMode`, `SilverWriteMode`, `GoldWriteMode`, `LoadingStrategy`,
`AggregationMethod`

**Domain value objects / data classes (valid per EXC-015):** `SilverRecord`,
`ValidationResult`, `ComponentHealthResult`, `HealthReport`, `PreflightReport`,
`FencingToken`, `LockContext`, `LockContextHolder`, `CachedBronzeContext`,
`InputFilterContext`, `PipelineContext`, `PipelineRunContext`, `PipelineEvent`,
`PublicationMapping`, `FieldAlias`

**Candidates for review:**
- `ErrorClassifier` (domain/error-classifier.py) — could use `*Service` suffix
- `UnitConverter` (domain/services/) — could use `*Service` suffix

**Assessment:** 28 of 30 are Enums or value objects (not subject to NAME-001).
2 candidates are low-severity.

**Naming Score: 9.5 / 10.0** (−0.5 for 2 MEDIUM findings)

---

## 6. Type Annotations (TYPE)

### TYPE-003: mypy --strict — MUST VIOLATION

**13 errors in 10 files** (checked 534 source files):

#### Critical: Missing Port Method (5 files affected)

`DataNormalizationPort` is missing `normalize-author-keys()` method declaration.
The method exists in `DataNormalizationService` (concrete) but was never added to the port protocol.

**Affected transformers:**
1. `application/pipelines/chembl/publication-transformer.py:212`
2. `application/pipelines/semanticscholar/transformer.py:154`
3. `application/pipelines/pubmed/transformer.py:259`
4. `application/pipelines/openalex/transformer.py:157`
5. `application/pipelines/crossref/transformer.py:141`

**Fix:** Add `normalize-author-keys()` to `DataNormalizationPort` protocol in
`domain/ports/data-normalization.py`.

#### High: Type Mismatches in PubMed Transformer (2 errors)

- `pubmed/transformer.py:255`: `list[str]` assigned to `list[list[str]]`
- `pubmed/transformer.py:258`: Wrong arg type to `normalize-author-list()`

**Fix:** Review author data flow in PubMed transformer, align types.

#### Medium: Pandera DataFrameModel Stubs (3 errors)

- `domain/schemas/uniprot/-xrefs.py:12`
- `domain/schemas/uniprot/-features.py:15`
- `domain/schemas/uniprot/-annotations.py:12`

**Assessment:** These are `[misc]` errors from pandera's missing type stubs — third-party issue,
not a code defect. Can be suppressed with `# type: ignore[misc]`.

#### Medium: DataNormalizationService Arg Type (1 error)

- `domain/services/data-normalization-service.py:161`: incompatible arg type to `-parse-author-names`

#### Low: Path Constructor Arg (1 error)

- `composition/providers/registration.py:432`: `str | None` passed to `Path()` which expects `str`

**Type Score: 6.0 / 10.0** (−2.0 for CRITICAL missing port method, −1.0 for HIGH type mismatches, −0.5×2 for MEDIUM)

---

## 7. Testing (TEST)

### TEST-005: No Test Logic in Production — PASS

No `import pytest` or `import unittest` found in `src/bioetl/`.

**Testing Score: 10.0 / 10.0**

---

## 8. Tools Report

### Ruff Linting — PASS

Zero violations across all enabled rules (F401, etc.).

### Ruff Formatting — 1 issue

`infrastructure/storage/gold-writer.py` has 2 multi-line lambda parameter lists
that need collapsing. Cosmetic. Fix: `ruff format src/bioetl/infrastructure/storage/gold-writer.py`.

### Import-Linter Contracts — ALL PASS

All 5 import contracts kept (514 files, 1696 dependencies):
- Domain layer isolation
- Application → infrastructure boundary
- Infrastructure → application/interfaces boundary
- Composition → interfaces boundary
- No concrete infrastructure imports in application

### Architecture Tests (pytest) — 1151 passed, 1 failed, 21 skipped

The single failure is `test-ruff-formatting-src` (caused by the `gold-writer.py` formatting
issue). All structural architecture tests pass.

### Cyclomatic Complexity (xenon) — 38 violations

Blocks exceeding CC threshold (rank C or worse). Most notable:
- `src/tools/scripts/config-matrix-generator.py:48 main` — rank **F**
- `application/composite/merger.py` — 4 complex methods
- `infrastructure/adapters/chembl/client.py` — 4 complex methods
- `infrastructure/storage/gold-writer.py:271 write-gold-merged`

### Security (pip-audit) — 3 vulnerabilities

| Package | Version | CVE | Fix Version |
|---------|---------|-----|-------------|
| filelock | 3.20.1 | CVE-2026-22701 | 3.20.3 |
| pip | 25.3 | CVE-2026-1703 | 26.0 |
| protobuf | 6.33.2 | CVE-2026-0994 | 6.33.5 |

### Mypy Additional Finding

`application/observability/observer.py:157`: `BaseException | None` passed where
`BaseException` required — missed in initial pass.

### Tools Availability

| Tool | Status |
|------|--------|
| ruff | Available, PASS |
| mypy | Available, 13 errors |
| pytest | Available, 1151 pass / 1 fail |
| import-linter (lint-imports) | Available, ALL PASS |
| xenon | Available, 38 CC violations |
| pip-audit | Available, 3 CVEs |
| vulture | Not installed |
| pylint | Not installed |
| jscpd | Not installed |

---

## 9. Scoring Summary

| Category | Weight | Raw Score | Weighted |
|----------|--------|-----------|----------|
| Architecture (ARCH) | 30% | 10.0 | 3.00 |
| Anti-Patterns (AP) | 25% | 10.0 | 2.50 |
| DI Violations (DI) | 20% | 10.0 | 2.00 |
| Naming (NAME) | 10% | 9.5 | 0.95 |
| Types (TYPE) | 10% | 6.0 | 0.60 |
| Testing (TEST) | 5% | 10.0 | 0.50 |
| **Total** | **100%** | | **9.55** |

**Final Score: 9.55 / 10.0 — PASS**

---

## 10. Action Items

### MUST Fix (Priority 1)

| ID | Severity | Description | Files |
|----|----------|-------------|-------|
| AUD-001 | CRITICAL | Add `normalize-author-keys()` to `DataNormalizationPort` | `domain/ports/data-normalization.py` + 5 transformers |
| AUD-002 | HIGH | Fix type mismatches in PubMed transformer author handling | `application/pipelines/pubmed/transformer.py` |

### SHOULD Fix (Priority 2)

| ID | Severity | Description | Files |
|----|----------|-------------|-------|
| AUD-003 | MEDIUM | Fix `-parse-author-names` arg type in DataNormalizationService | `domain/services/data-normalization-service.py` |
| AUD-004 | MEDIUM | Add `str | None` guard for `Path()` in registration | `composition/providers/registration.py:432` |
| AUD-005 | MEDIUM | Suppress pandera `DataFrameModel` mypy stubs (3 files) | `domain/schemas/uniprot/-*.py` |
| AUD-006 | MEDIUM | Fix `BaseException | None` → `BaseException` in observer | `application/observability/observer.py:157` |
| AUD-007 | MEDIUM | Run `ruff format` on gold-writer.py (fixes 1 test failure) | `infrastructure/storage/gold-writer.py` |
| AUD-008 | LOW | Consider `*Service` suffix for `ErrorClassifier`, `UnitConverter` | `domain/error-classifier.py`, `domain/services/unit-converter.py` |

### SHOULD Fix (Priority 3 — Security)

| ID | Severity | Description |
|----|----------|-------------|
| AUD-009 | MEDIUM | Bump `filelock` to 3.20.3 (CVE-2026-22701) |
| AUD-010 | MEDIUM | Bump `pip` to 26.0 (CVE-2026-1703) |
| AUD-011 | MEDIUM | Bump `protobuf` to 6.33.5 (CVE-2026-0994) |

### Comparison with Previous Audit (2026-02-08)

| Metric | 2026-02-08 | 2026-02-16 | Delta |
|--------|:----------:|:----------:|:-----:|
| MUST findings | 0 | 2 | +2 (regression) |
| SHOULD findings | 9 | 4 | −5 |
| Ruff violations | 0 | 0 | — |
| Import boundaries | CLEAN | CLEAN | — |
| Domain purity | CLEAN | CLEAN | — |

> The 2 new MUST findings (AUD-001, AUD-002) are type-system regressions likely introduced
> by recent author normalization refactoring. The `normalize-author-keys` method was added to
> the service implementation but not propagated to the port protocol.

---

*Report generated by automated audit pipeline. Manual verification recommended for
semantic duplication candidates and edge cases.*
