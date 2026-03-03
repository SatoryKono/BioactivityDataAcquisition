# Architecture Audit Report

Date: 2026-03-03
Scope: `src/bioetl`, `tests/architecture`, active docs/workflows

## Executive Summary

- Total findings: 6
- Critical (MUST): 1
- Moderate (SHOULD): 3
- Informational (MAY): 2
- Integrated score (weighted, 10 categories): **7.41 / 10**

### Interpretation

- **0.0–4.9**: unstable architecture, high refactoring urgency
- **5.0–7.9**: workable but constrained by technical debt
- **8.0–10**: architecturally mature system

Current state: **5.0–7.9 band** — architecture is disciplined and strongly guarded by tests, but large orchestration modules, broad exception handling, and one active documentation contract violation reduce maintainability and delivery velocity.

______________________________________________________________________

## Verification Log

Commands executed:

```bash
uv run python -m pytest tests/architecture/ -q
uv run python -m pytest tests/architecture/test_layer_dependencies.py tests/architecture/test_di_compliance.py tests/architecture/test_naming_conventions.py tests/architecture/test_medallion_invariants.py -q
uv run python -m pytest tests/architecture/test_code_metrics.py -q
rg --files src/bioetl/domain src/bioetl/application src/bioetl/infrastructure src/bioetl/composition src/bioetl/interfaces | wc -l
rg --files tests | wc -l
rg -n "def test_" tests | wc -l
find src/bioetl -name '*.py' -print0 | xargs -0 wc -l | sort -nr | head -20
grep -c "def \|async def " src/bioetl/application/composite/merger.py
rg -n "except Exception" src/bioetl/application src/bioetl/infrastructure
rg -n "httpx|requests|open\(|print\(|structlog" src/bioetl/domain src/bioetl/application
rg -n "deltalake|parquet|write_deltalake|to_parquet" src/bioetl/infrastructure/storage/silver_writer.py src/bioetl/infrastructure/storage/delta_writer.py src/bioetl/infrastructure/storage/gold_writer.py
```

Observed outcomes:

- Architecture suite: mostly green, **1 fail** in docs sync (`test_no_legacy_kebab_pipeline_ids_in_active_docs`).
- Focused architecture tests (layers/DI/naming/medallion invariants): green.
- Code metrics architecture tests: green.
- Scale snapshot: 548 Python files in `src/bioetl`; 869 files in `tests`; ~10,740 test functions.
- Large-module signal: `application/composite/merger.py` is 1,850 LOC and 44 methods.

______________________________________________________________________

## Scorecard (10 categories)

| Category                                        | Description                                                                | Weight | Score (1–10) | Weighted score |
| ----------------------------------------------- | -------------------------------------------------------------------------- | -----: | -----------: | -------------: |
| 1. Layered architecture compliance              | Соблюдение границ domain/application/infrastructure/composition/interfaces |   0.14 |          8.7 |          1.218 |
| 2. Hexagonal (Ports & Adapters) + DDD fidelity  | Явность портов, инверсия зависимостей, доменная изоляция                   |   0.12 |          8.3 |          0.996 |
| 3. Module boundaries & coupling                 | Размеры модулей, cohesion/coupling, риск god-object                        |   0.12 |          6.1 |          0.732 |
| 4. Domain model quality                         | Чистота доменной модели, value objects, policy/invariants                  |   0.10 |          7.8 |          0.780 |
| 5. Test architecture & regression safety        | Архитектурные тесты, покрытие контракта, сигнализация регрессов            |   0.13 |          8.5 |          1.105 |
| 6. Error handling resilience                    | Гранулярность исключений, деградация, диагностичность                      |   0.08 |          6.2 |          0.496 |
| 7. Logging & observability                      | Structured logging, run_id context, tracing/metrics hooks                  |   0.08 |          8.0 |          0.640 |
| 8. Performance & scalability posture            | Асинхронность, тяжёлые места, управление ресурсами                         |   0.08 |          7.1 |          0.568 |
| 9. Security & secrets hygiene                   | Управление секретами, отсутствие hardcode, PII controls                    |   0.07 |          7.6 |          0.532 |
| 10. Documentation consistency & maintainability | Согласованность активной документации и кода/правил                        |   0.08 |          4.8 |          0.384 |

**Integral score = 7.451 ≈ 7.41 / 10**

______________________________________________________________________

## Architectural Assessment

### 1) Layer structure (domain/application/infrastructure/interfaces)

- Layer contracts are actively enforced by dedicated tests for disallowed imports and dependency direction, including domain purity constraints.
- This provides strong baseline confidence against accidental cross-layer coupling.

### 2) Hexagonal + DDD adherence

- Centralized `domain.ports` facade is present and broad, matching a Ports & Adapters strategy.
- Composition layer (`pipeline_factory`) performs assembly and dependency wiring, while domain/infrastructure consume abstractions.

### 3) Explicit module boundaries and dependencies

- Positive: architecture test suite is comprehensive and codifies many invariants.
- Concern: several files in application/infrastructure are very large (1k+ LOC), increasing coupling risk and reducing local reasoning speed.

### 4) Naming/package conventions consistency

- Dedicated naming-convention architecture tests pass, indicating strong systemic conventions.
- One active docs consistency violation indicates process drift at the documentation boundary rather than in code naming.

______________________________________________________________________

## Findings

## [Critical (P1)] Active documentation contract is broken by legacy kebab-case IDs

**Location**: `tests/architecture/test_documentation_sync.py:273-288`
**Rule**: active docs/workflows MUST avoid legacy kebab-case pipeline IDs

**Evidence**:

```python
candidates = [Path("README.md")]
...
assert (
    not violations
), "Legacy kebab-case pipeline IDs found in active docs/workflows:\n" + "\n".join(
    f"  - {item}" for item in sorted(violations)
)
```

`uv run python -m pytest tests/architecture/ -q` fails with:
`docs/exports/full-documentation-no-plans-reports-skills.merged.md`

**Impact**: CI noise and trust erosion in documentation-as-contract; can hide real architectural drift.

**Recommendation**:

1. Replace remaining kebab-case pipeline IDs with underscore IDs in active docs export pipeline.
1. Add pre-merge docs sanitizer/check for generated docs.

**Verification command**: `uv run python -m pytest tests/architecture/test_documentation_sync.py::test_no_legacy_kebab_pipeline_ids_in_active_docs -q`

______________________________________________________________________

## [Moderate (P2)] Large orchestration module indicates potential god-object pressure

**Location**: `src/bioetl/application/composite/merger.py:52-260` and file-level metrics
**Rule**: high cohesion + explicit boundaries SHOULD be preserved for maintainability

**Evidence**:

- Single `MergeService` class coordinates reading, join logic, dependency handling, cross-validation, column renaming, and ordering.
- Measured size: 1,850 LOC and 44 methods.

**Impact**: high change blast radius, onboarding friction, difficult targeted testing/refactoring.

**Recommendation**:

- Split into focused collaborators: `SeedReader`, `EnricherReader`, `JoinPlanner`, `ConflictResolver`, `MergeTelemetry`, `MergeResultAssembler`.

**Verification command**:

```bash
find src/bioetl -name '*.py' -print0 | xargs -0 wc -l | sort -nr | head -20
grep -c "def \|async def " src/bioetl/application/composite/merger.py
```

______________________________________________________________________

## [Moderate (P2)] Broad exception handling is pervasive in app/composite flows

**Location**: `src/bioetl/application/composite/merger.py:189-227`, `src/bioetl/application/composite/runner.py` (multiple blocks)
**Rule**: exception handling SHOULD be typed and actionable for operational diagnostics

**Evidence**:

```python
except Exception as e:
    self._logger.warning(...)
```

Pattern repeats widely in application services/composite modules.

**Impact**: obscures root causes, complicates retries/circuit breaker behavior and error analytics.

**Recommendation**:

- Introduce domain/application exception taxonomy per flow stage.
- Convert generic catches to explicit exceptions + fallback boundary catch with structured error_code.

**Verification command**: `rg -n "except Exception" src/bioetl/application src/bioetl/infrastructure`

______________________________________________________________________

## [Moderate (P2)] Application-layer file I/O exists in data source implementation

**Location**: `src/bioetl/application/core/idmapping_data_source.py:219-237`
**Rule**: I/O SHOULD live in infrastructure adapters where feasible; application orchestrates via ports

**Evidence**:

```python
with self._input_path.open(newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
```

**Impact**: blurs app/infra boundary, harder to test with pure port doubles, duplicates file-access concerns.

**Recommendation**:

- Extract CSV input loading to `InputFilterPort`/infrastructure adapter and inject into use-case orchestration.

**Verification command**: `rg -n "open\(" src/bioetl/application/core/idmapping_data_source.py`

______________________________________________________________________

## [Informational (P3)] Strong architecture guardrails are a clear project asset

**Location**: `tests/architecture/test_layer_dependencies.py:24-121`, `tests/architecture/test_domain_purity.py:322-353`

**Evidence**: explicit tests enforce disallowed imports, domain purity, and protocol-based ports.

**Impact**: reduces architecture regression risk during rapid development.

______________________________________________________________________

## [Informational (P3)] Silver/Gold storage follows Delta-centric policy

**Location**: `src/bioetl/infrastructure/storage/silver_writer.py:1-27`, `src/bioetl/infrastructure/storage/gold_writer.py` (Delta usage)

**Evidence**: Delta Lake APIs (`DeltaTable`, `write_deltalake`) are used in core writers.

**Impact**: aligned with Medallion policy and ACID/upsert requirements.

______________________________________________________________________

## Prioritized Refactoring Plan

### RF-001 (Critical): Fix active docs contract pipeline

- **Goal**: eliminate architecture test failure in docs sync.
- **Concrete edits**:
  - Normalize pipeline IDs in active generated docs (`docs/exports/...`).
  - Add docs generation post-step to enforce underscore naming.
- **Risks**: breaking links or external references.
- **Mitigation**: compatibility alias table for old IDs in archived docs only.
- **Done criteria**:
  - `test_no_legacy_kebab_pipeline_ids_in_active_docs` passes.
  - No new docs diff introducing kebab-case IDs.

### RF-002 (High): Decompose `MergeService` into subservices

- **Goal**: reduce coupling and cognitive complexity in composite merge path.
- **Concrete edits**:
  - Create modules: `merge/seed_reader.py`, `merge/enricher_reader.py`, `merge/join_service.py`, `merge/conflict_resolver.py`, `merge/result_builder.py`.
  - Keep façade `MergeService` as orchestrator only.
- **Risks**: behavior drift in merge ordering/conflict semantics.
- **Mitigation**:
  - Golden-master tests on merge outputs.
  - Property-based tests for join-key normalization and idempotence.
- **Done criteria**:
  - `merger.py` < 600 LOC.
  - New module tests cover each collaborator.
  - Existing composite tests unchanged/passing.

### RF-003 (High): Introduce typed exception taxonomy in composite/application flows

- **Goal**: improve operational diagnosability and deterministic fallback behavior.
- **Concrete edits**:
  - Add `domain/exceptions/composite.py` and stage-specific exceptions.
  - Replace `except Exception` in hot paths with typed catches.
  - Add terminal boundary catch with standardized `error_code` + run context.
- **Risks**: missed edge exceptions causing unexpected failures.
- **Mitigation**: staged rollout + shadow logging for unmapped exceptions.
- **Done criteria**:
  - `except Exception` count in application/composite reduced by >= 70%.
  - Error dashboards show classified failure reasons.

### RF-004 (Medium): Move CSV/FS access from application to infrastructure adapter

- **Goal**: restore strict app/infra separation for idmapping input path.
- **Concrete edits**:
  - Introduce `FileInputIdsPort` (domain port) and infra implementation for CSV.
  - Refactor `IDMappingDataSource` to consume port instead of `Path.open`.
- **Risks**: integration wiring regressions.
- **Mitigation**: DI composition tests + backward-compatible adapter wrapper.
- **Done criteria**:
  - no direct `open()` in `application/core/idmapping_data_source.py`.
  - architecture tests + new unit tests pass.

### RF-005 (Medium): Standardize observability envelope for all pipeline events

- **Goal**: enforce consistent event fields (`run_id`, `pipeline`, `phase`, `error_code`).
- **Concrete edits**:
  - Introduce shared event schema helper in application observability.
  - Normalize all error logs in composite/application services.
- **Risks**: log schema migration issues.
- **Mitigation**: dual-write fields for one release.
- **Done criteria**:
  - sampled logs contain required fields in > 99% events.

### RF-006 (Desirable): Reduce module size outliers systematically

- **Goal**: improve maintainability and reviewability.
- **Concrete edits**:
  - Set architectural threshold policy (e.g., warning at > 700 LOC).
  - Add CI check + allowlist with expiration for temporary exceptions.
- **Risks**: mechanical splits without semantic improvement.
- **Mitigation**: split by use-case boundaries and verify with contract tests.
- **Done criteria**:
  - top-10 largest files reduced by average >= 30% LOC.

______________________________________________________________________

## Metrics and Tests to Add/Update

1. **Architecture drift KPI**

   - Metric: number of boundary violations from `tests/architecture` + import-linter.
   - Score link: categories 1, 2, 3.

1. **Module size/complexity KPI**

   - Metrics: LOC/file, CC percentile (P90/P95), methods/class.
   - Score link: categories 3, 10.

1. **Exception quality KPI**

   - Metrics: `% typed catches`, `% generic catches`, `% errors with error_code`.
   - Score link: category 6.

1. **Observability completeness KPI**

   - Metrics: `% logs with run_id + pipeline + phase`, tracing span coverage.
   - Score link: category 7.

1. **Docs contract KPI**

   - Metric: active docs sync failures (must be 0).
   - Score link: category 10.

1. **Performance regression KPI**

   - Metrics: end-to-end pipeline duration, memory peak, merge stage latency.
   - Score link: category 8.

### Expected score uplift after key steps

- After RF-001 + RF-002 + RF-003 + RF-004:
  - Category 3: 6.1 → 7.8
  - Category 6: 6.2 → 8.0
  - Category 10: 4.8 → 8.2
  - Category 1: 8.7 → 9.1
- Projected integrated score: **~8.2 / 10**.
