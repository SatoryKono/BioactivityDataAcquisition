# Test Baseline: TEST-BASELINE-001

**Date**: 2026-03-04 (session start)
**Phase**: baseline
**RF scope**: All (pre-refactoring snapshot after import bug fixes)
**Runner**: `make test-fast` (unit + architecture, HYPOTHESIS_PROFILE=fast, -n auto)

---

## Summary

| Category | Total | Pass | Fail | Skip | Error |
|----------|:-----:|:----:|:----:|:----:|:-----:|
| unit | 10,958 (est) | 10,915 | 84 | — | 43 |
| architecture | 1,567 | 1,506 | 35 | 26 | 0 |
| **TOTAL (test-fast)** | **12,532** | **12,395** | **116** | **21** | **43** |

> Note: `make test-fast` final line: `116 failed, 12395 passed, 21 skipped, 43 errors in 122.63s`
> Architecture run (serial): `35 failed, 1506 passed, 26 skipped in 86.63s`
> Unit run (serial): `84 failed, 10915 passed, 43 errors in 215.70s`

---

## Coverage

| Scope | Stmts | Miss | Branch | BPart | Coverage |
|-------|:-----:|:----:|:------:|:-----:|:--------:|
| overall (`src/bioetl`) | 38,176 | 3,574 | 8,470 | 914 | **88.27%** |
| domain (`src/bioetl/domain`) | 11,358 | 520 | 1,576 | 134 | **94.68%** |

**Status vs thresholds:**
- Overall 88.27% >= 85% threshold: PASS
- Domain 94.68% >= 90% threshold: PASS

---

## Failure Groups

### GROUP-1: `PipelineYamlConfig` not fully defined (Pydantic forward-ref) — 60+ failures

**Root Cause**: `PipelineYamlConfig` uses a forward reference to `JsonDict` that is not resolved at class definition time. Pydantic v2 requires `model_rebuild()` to be called after all referenced types are defined.

**Error**:
```
pydantic.errors.PydanticUserError: `PipelineYamlConfig` is not fully defined;
you should define `JsonDict`, then call `PipelineYamlConfig.model_rebuild()`.
```

**Source**: `src/bioetl/infrastructure/config_loader.py:342` → `PipelineYamlConfig.model_validate(config)`

**Affected tests (representative)**:
- `tests/unit/infrastructure/test_config.py` (15 tests)
- `tests/unit/infrastructure/test_config_dynamic.py` (10 tests)
- `tests/unit/infrastructure/test_config_settings.py` (4 tests)
- `tests/unit/infrastructure/config/test_pipeline_config_loader.py` (1 test)
- `tests/unit/infrastructure/config/test_pipeline_config_loader_extended.py` (7 tests)
- `tests/unit/infrastructure/config/test_pipeline_config_legacy_normalization.py` (1 test)
- `tests/unit/infrastructure/schemas/test_pipeline_sort_policy_schema.py` (2 tests)
- `tests/unit/composition/providers/test_extraction_params_registration.py` (2 tests)
- `tests/unit/cli/test_registry_consistency.py` (1 test)
- `tests/unit/application/core/test_record_processor.py` (2 tests — via `get_pipeline_config`)
- `tests/architecture/test_config_golden_master.py` (4 tests)
- `tests/architecture/test_config_strict_keys.py` (17 tests — all providers)
- `tests/architecture/test_deterministic_sort_policy_coverage.py` (1 test)

**FAIL IDs**: FAIL-001 through FAIL-060 (approximate, all same root cause)

---

### GROUP-2: `domain/aggregates/events.py` dataclass field ordering — 11 failures (ERRORS)

**Root Cause**: A dataclass in `src/bioetl/domain/aggregates/events.py` at line 63 has a non-default argument following a default argument (`'run_id'` follows a field with a default). Python dataclass inheritance ordering violation.

**Error**:
```
TypeError: non-default argument 'run_id' follows default argument
```

**Source**: `src/bioetl/domain/aggregates/events.py:63`

**Affected tests**:
- `tests/unit/domain/aggregates/test_batch.py` (2 FAILs + 14 ERRORs in fixture setup)
- `tests/unit/domain/aggregates/test_pipeline_run.py` (8 FAILs)
- `tests/unit/domain/aggregates/test_quarantine_entry.py` (4 FAILs)

**FAIL IDs**: FAIL-061 through FAIL-074

---

### GROUP-3: `SemanticScholar` fallback — `JsonDict` NameError — 7 failures

**Root Cause**: `JsonDict` is not defined at runtime in `src/bioetl/infrastructure/adapters/semanticscholar/fallback.py:171`. It was in `TYPE_CHECKING` block but used as a `cast()` type argument at runtime.

**Error**:
```
NameError: name 'JsonDict' is not defined
src/bioetl/infrastructure/adapters/semanticscholar/fallback.py:171:
    return cast(JsonDict, record)
```

**Affected tests**:
- `tests/unit/infrastructure/adapters/semanticscholar/test_fallback.py` (5 FAILs)
- `tests/unit/infrastructure/adapters/semanticscholar/test_adapter.py` (2 FAILs)

**FAIL IDs**: FAIL-075 through FAIL-081

---

### GROUP-4: Logic/assertion failures — 3 failures

**Root Cause**: Test assertions fail due to logic mismatches in production code.

#### FAIL-082: `test_log_retry_uses_reason_when_no_status_code`
- **Test**: `tests/unit/infrastructure/adapters/test_client_retry_mixin.py::test_log_retry_uses_reason_when_no_status_code`
- **Error**: `AssertionError: assert 'connection refused' in 'unknown'`
- **Analysis**: Retry logging uses 'unknown' as the reason string instead of propagating the exception message.

#### FAIL-083: `test_process_missing_dois_yields_records_for_unresolved_ids`
- **Test**: `tests/unit/infrastructure/adapters/test_fallback_policy.py::test_process_missing_dois_yields_records_for_unresolved_ids`
- **Error**: `AssertionError: assert 2 == 1` — 2 records yielded when 1 expected.
- **Analysis**: Fallback policy yields records for all unresolved IDs, not just the expected subset.

#### FAIL-084: `test_write_silver_applies_renames_from_layer_config`
- **Test**: `tests/unit/application/core/test_batch_writer_io_mixin.py::TestBatchWriterIOMixinSilver::test_write_silver_applies_renames_from_layer_config`
- **Error**: `TypeError: RecordProcessorConfig.__init__() got an unexpected keyword argument 'data_schema'`
- **Analysis**: Test uses outdated API — `RecordProcessorConfig` no longer accepts `data_schema` kwarg.

---

### GROUP-5: Composite runner FSM — `InvalidStateError` — 5 failures

**Root Cause**: The composite runner raises `InvalidStateError` when a required enricher fails, but tests assert this exception is NOT raised (or expect a different flow). The error propagates too early.

**Error**:
```
bioetl.domain.exceptions.internal.InvalidStateError: Required enricher 'crossref' failed: Connection timeout
src/bioetl/application/composite/runner_support_mixin.py:263
```

**Affected tests**:
- `tests/unit/application/composite/test_runner_enrichment_fsm.py` (3 FAILs)
- `tests/unit/application/composite/test_runner_fsm_logging.py` (1 FAIL)
- `tests/unit/application/composite/test_runner_required_flag.py` (1 FAIL)

**FAIL IDs**: FAIL-085 through FAIL-089

---

### GROUP-6: Architecture — code formatting (ruff) — 3 failures

**Root Cause**: 21 source files + test files have ruff formatting violations. Not architectural regressions — formatting drift from recent code changes.

**Affected files (src)**:
```
src/bioetl/application/composite/runner_support_mixin.py
src/bioetl/application/core/dict_transformers.py
src/bioetl/application/core/field_specs.py
src/bioetl/application/core/record_processor.py
src/bioetl/application/pipelines/pubmed/extractors/base.py
src/bioetl/application/pipelines/uniprot/extractors/taxonomy.py
src/bioetl/application/services/data_quality_service.py
src/bioetl/application/services/health_service.py
src/bioetl/composition/factories/services_factory.py
src/bioetl/composition/factories/storage_adapter_write_mixin.py
src/bioetl/domain/composite/cross_validation.py
src/bioetl/domain/normalization.py
src/bioetl/domain/ports/data_normalization.py
src/bioetl/domain/ports/metadata_coordinator.py
src/bioetl/domain/serialization.py
src/bioetl/domain/services/dq_serializer.py
src/bioetl/domain/transformations.py
src/bioetl/domain/value_objects/dq_result.py
src/bioetl/domain/value_objects/molecular_descriptors.py
src/bioetl/infrastructure/serialization/encoders.py
src/bioetl/infrastructure/storage/metadata_builder.py
```

**FAIL IDs**: FAIL-090, FAIL-091, FAIL-092

---

### GROUP-7: Architecture — file size / LOC limits exceeded — 2 failures

**Root Cause**: Files exceed their per-layer LOC limits defined in the burn-down registry.

**domain layer violations**:
```
bioetl/domain/transformations.py: 387 LOC (limit: 386)
bioetl/domain/types.py: 502 LOC (limit: 497)
bioetl/domain/composite/config_models.py: 312 LOC (limit: 305)
bioetl/domain/services/organism_classification_service.py: 365 LOC (limit: 362)
```

**application layer violations** (additional, from serial run):
- (details from `test_application_files_under_limit`)

**FAIL IDs**: FAIL-093, FAIL-094

---

### GROUP-8: Architecture — docs drift / ADR issues — 4 failures

#### FAIL-095: Dependency-map docs drift
- **Test**: `tests/architecture/test_architecture_dependency_docs_drift.py::test_dependency_map_drift_check_passes_current_repo`
- **Error**: `docs/02-architecture/generated/module-dependency-map.md` and `.json` are stale.
- **Fix**: Run `python scripts/generate_architecture_dependency_map.py --update`

#### FAIL-096: ADR index missing ADR-041
- **Test**: `tests/architecture/test_documentation_sync.py::test_adr_index_links_match_decision_files`
- **Error**: `ADR-041-naming-policy-skills-agents.md` exists on disk but is missing from README index.

#### FAIL-097: ADR-041 has invalid status 'Proposed'
- **Test**: `tests/architecture/test_documentation_sync.py::test_adr_status_is_from_allowed_set`
- **Error**: Status 'Proposed' is not in allowed set `['accepted', 'added', 'deprecated', 'superseded']`.

#### FAIL-098: Stale file_size_limits exemption
- **Test**: `tests/architecture/test_quality_burndown_priorities.py::test_file_size_limit_registry_has_no_stale_entries`
- **Error**: `src/bioetl/infrastructure/quality/debt_scorecard.py: 310 <= default layer limit 650` (exemption no longer needed).

---

## Failure Summary by Root Cause

| # | Root Cause | Failures | Priority |
|---|-----------|:--------:|:--------:|
| 1 | `PipelineYamlConfig` Pydantic forward-ref (`JsonDict` not defined) | ~60 | CRITICAL |
| 2 | `events.py` dataclass field ordering (`run_id` after default) | ~14 | CRITICAL |
| 3 | SemanticScholar `fallback.py` `JsonDict` NameError at runtime | 7 | HIGH |
| 4 | Composite runner FSM raises wrong exception / at wrong point | 5 | HIGH |
| 5 | Logic assertions failures (3 independent bugs) | 3 | MEDIUM |
| 6 | Ruff formatting violations (21 src files) | 3 arch | LOW |
| 7 | LOC limits exceeded in domain/application | 2 arch | LOW |
| 8 | Docs drift: dependency-map stale, ADR-041 not in index, invalid status | 4 arch | LOW |

---

## Errors (43 total — all in test fixture setup)

All 43 errors are `ERROR at setup of` caused by fixture failures. They fall into two groups:

1. **events.py TypeError** (14 errors): `tests/unit/domain/aggregates/test_batch.py` and related — fixture calls `Batch.create()` which triggers `events.py` import at runtime.
2. **PipelineYamlConfig error** (~29 errors): test fixtures call `load_pipeline_config()` or `get_pipeline_config()` which hit the Pydantic forward-ref error.

---

## What Passes

- **12,395 tests pass** (98.0% of collected)
- All core domain logic tests
- All infrastructure adapter tests except SemanticScholar fallback
- All integration-style unit tests that don't hit `PipelineYamlConfig`
- All architecture layer boundary tests
- All import order tests (except ruff formatting)

---

## Actions Required (for py-debug-bot)

| Priority | Action | Scope |
|----------|--------|-------|
| CRITICAL | Fix `PipelineYamlConfig` Pydantic forward-ref — add `model_rebuild()` or move `JsonDict` definition | `src/bioetl/infrastructure/config_loader.py` (or `pipeline_yaml_config.py`) |
| CRITICAL | Fix `events.py` dataclass field ordering — non-default `run_id` after default field | `src/bioetl/domain/aggregates/events.py:63` |
| HIGH | Fix SemanticScholar `fallback.py` — `JsonDict` not available at runtime for `cast()` | `src/bioetl/infrastructure/adapters/semanticscholar/fallback.py:171` |
| HIGH | Investigate composite runner FSM — required enricher failure propagation | `src/bioetl/application/composite/runner_support_mixin.py:263` |
| MEDIUM | Fix 3 logic assertion failures (retry reason, fallback policy count, RecordProcessorConfig API) | `test_client_retry_mixin.py`, `test_fallback_policy.py`, `test_batch_writer_io_mixin.py` |
| LOW | Run `ruff format src/ tests/` to fix 21 formatting violations | CI hygiene |
| LOW | Update LOC limits in burn-down registry OR reduce file sizes | Architecture tests |
| LOW | Update dependency-map docs, ADR-041 index entry, fix ADR-041 status | Documentation sync |

---

## Re-test Section

*(To be appended after fixes are applied by py-debug-bot)*
