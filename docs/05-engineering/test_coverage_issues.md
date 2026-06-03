# GitHub Issues для Test Coverage Roadmap

## Issue #1: Создать тесты для composition execution_api (0% → 90%)

**Title:** Add contract tests for composition execution_api (0% coverage → 90%)

**Priority:** P0 (Critical - public bootstrap surface)

**Labels:** `test-coverage`, `p0`, `composition-api`, `public-surface`

**Description:**
The `execution_api.py` module has 0% coverage (0/23 lines) despite being a critical public composition API. This module defines the execution interface for pipeline execution and is a key part of the public bootstrap surface.

**Context:**
- Current coverage: 0% (0/23 executable lines)
- Target coverage: 90%
- Path: `src/bioetl/composition/execution_api.py`
- Module is part of public DI/bootstrap seam
- Lazy exports and routing behavior need testing

**Steps:**
1. Analyze execution_api.py public interface and lazy export mechanisms
2. Create `tests/unit/composition/test_execution_api_contract.py`
3. Test scenarios:
   - `__all__` export validation
   - Lazy import/export behavior
   - Routing to private implementation
   - Error propagation
   - Dependency wiring behavior
4. Use mocks for downstream dependencies (pipeline runner, context)
5. Run coverage-verify lane to verify coverage >= 90%
6. Update module-coverage-inventory.json

**Acceptance Criteria:**
- [ ] Test file created with comprehensive coverage
- [ ] Coverage >= 90% for execution_api.py
- [ ] All public API paths tested
- [ ] Lazy export behavior validated
- [ ] Coverage-verify lane passes

**Risk:** Medium - requires understanding of lazy export mechanisms

---

## Issue #2: Создать тесты для composition control_plane_api (0% → 90%)

**Title:** Add contract tests for composition control_plane_api (0% coverage → 90%)

**Priority:** P0 (Critical - public bootstrap surface)

**Labels:** `test-coverage`, `p0`, `composition-api`, `public-surface`

**Description:**
The `control_plane_api.py` module has 0% coverage (0/19 lines) despite being a critical public composition API for control-plane operations. This module defines the interface for ledger, checkpoint, and manifest access.

**Context:**
- Current coverage: 0% (0/19 executable lines)
- Target coverage: 90%
- Path: `src/bioetl/composition/control_plane_api.py`
- Module exposes control-plane seam behavior
- Needs fake ledger and checkpoint store for testing

**Steps:**
1. Analyze control_plane_api.py public interface
2. Create `tests/unit/composition/test_control_plane_api_contract.py`
3. Test scenarios:
   - `__all__` export validation
   - Ledger access methods
   - Checkpoint store access
   - Manifest retrieval
   - Error handling
4. Use fake ledger and fake checkpoint store as fixtures
5. Run coverage-verify lane to verify coverage >= 90%
6. Update module-coverage-inventory.json

**Acceptance Criteria:**
- [ ] Test file created with comprehensive coverage
- [ ] Coverage >= 90% for control_plane_api.py
- [ ] All control-plane seam operations tested
- [ ] Fake fixtures implemented
- [ ] Coverage-verify lane passes

**Risk:** Medium - requires implementing fake ledger and checkpoint store

---

## Issue #3: Создать тесты для composition health_api (0% → 90%)

**Title:** Add contract tests for composition health_api (0% coverage → 90%)

**Priority:** P0 (Critical - public bootstrap surface)

**Labels:** `test-coverage`, `p0`, `composition-api`, `public-surface`

**Description:**
The `health_api.py` module has 0% coverage (0/35 lines) despite being a critical public composition API for health check operations. This module defines the interface for health monitoring and readiness probes.

**Context:**
- Current coverage: 0% (0/35 executable lines)
- Target coverage: 90%
- Path: `src/bioetl/composition/health_api.py`
- Module exposes health check endpoints
- Important for orchestration and monitoring

**Steps:**
1. Analyze health_api.py public interface
2. Create `tests/unit/composition/test_health_api_contract.py`
3. Test scenarios:
   - `__all__` export validation
   - Health check methods
   - Readiness probe behavior
   - Error handling
   - Dependency health checks
4. Use mocks for downstream health dependencies
5. Run coverage-verify lane to verify coverage >= 90%
6. Update module-coverage-inventory.json

**Acceptance Criteria:**
- [ ] Test file created with comprehensive coverage
- [ ] Coverage >= 90% for health_api.py
- [ ] All health check operations tested
- [ ] Error paths covered
- [ ] Coverage-verify lane passes

**Risk:** Low - health APIs typically straightforward

---

## Issue #4: Создать тесты для composition maintenance_api (0% → 90%)

**Title:** Add contract tests for composition maintenance_api (0% coverage → 90%)

**Priority:** P0 (Critical - public bootstrap surface)

**Labels:** `test-coverage`, `p0`, `composition-api`, `public-surface`

**Description:**
The `maintenance_api.py` module has 0% coverage (0/24 lines) despite being a critical public composition API for maintenance operations. This module defines the interface for maintenance mode and maintenance window operations.

**Context:**
- Current coverage: 0% (0/24 executable lines)
- Target coverage: 90%
- Path: `src/bioetl/composition/maintenance_api.py`
- Module exposes maintenance operations
- Important for production maintenance procedures

**Steps:**
1. Analyze maintenance_api.py public interface
2. Create `tests/unit/composition/test_maintenance_api_contract.py`
3. Test scenarios:
   - `__all__` export validation
   - Maintenance mode operations
   - Maintenance window scheduling
   - Error handling
   - State transitions
4. Use mocks for downstream maintenance dependencies
5. Run coverage-verify lane to verify coverage >= 90%
6. Update module-coverage-inventory.json

**Acceptance Criteria:**
- [ ] Test file created with comprehensive coverage
- [ ] Coverage >= 90% for maintenance_api.py
- [ ] All maintenance operations tested
- [ ] State transitions validated
- [ ] Coverage-verify lane passes

**Risk:** Low - maintenance APIs typically straightforward

---

## Issue #5: Создать тесты для composition resources_api (0% → 90%)

**Title:** Add contract tests for composition resources_api (0% coverage → 90%)

**Priority:** P0 (Critical - public bootstrap surface)

**Labels:** `test-coverage`, `p0`, `composition-api`, `public-surface`

**Description:**
The `resources_api.py` module has 0% coverage (0/16 lines) despite being a critical public composition API for resource management operations. This module defines the interface for resource allocation and cleanup.

**Context:**
- Current coverage: 0% (0/16 executable lines)
- Target coverage: 90%
- Path: `src/bioetl/composition/resources_api.py`
- Module exposes resource management operations
- Important for resource lifecycle management

**Steps:**
1. Analyze resources_api.py public interface
2. Create `tests/unit/composition/test_resources_api_contract.py`
3. Test scenarios:
   - `__all__` export validation
   - Resource allocation methods
   - Resource cleanup operations
   - Error handling
   - Resource state tracking
4. Use mocks for downstream resource dependencies
5. Run coverage-verify lane to verify coverage >= 90%
6. Update module-coverage-inventory.json

**Acceptance Criteria:**
- [ ] Test file created with comprehensive coverage
- [ ] Coverage >= 90% for resources_api.py
- [ ] All resource operations tested
- [ ] Cleanup paths validated
- [ ] Coverage-verify lane passes

**Risk:** Low - resource APIs typically straightforward

---

## Issue #6: Создать тесты для composition services_api (0% → 90%)

**Title:** Add contract tests for composition services_api (0% coverage → 90%)

**Priority:** P0 (Critical - public bootstrap surface)

**Labels:** `test-coverage`, `p0`, `composition-api`, `public-surface`

**Description:**
The `services_api.py` module has 0% coverage (0/12 lines) despite being a critical public composition API for service access operations. This module defines the interface for service factory and service retrieval.

**Context:**
- Current coverage: 0% (0/12 executable lines)
- Target coverage: 90%
- Path: `src/bioetl/composition/services_api.py`
- Module exposes service factory operations
- Critical for DI and service wiring

**Steps:**
1. Analyze services_api.py public interface
2. Create `tests/unit/composition/test_services_api_contract.py`
3. Test scenarios:
   - `__all__` export validation
   - Service factory methods
   - Service retrieval operations
   - Error handling
   - Service caching behavior
4. Use mocks for downstream service dependencies
5. Run coverage-verify lane to verify coverage >= 90%
6. Update module-coverage-inventory.json

**Acceptance Criteria:**
- [ ] Test file created with comprehensive coverage
- [ ] Coverage >= 90% for services_api.py
- [ ] All service operations tested
- [ ] Factory patterns validated
- [ ] Coverage-verify lane passes

**Risk:** Low - service factory APIs typically straightforward

---

## Issue #7: Создать тесты для composition _pipeline_execution (0% → 90%)

**Title:** Add contract tests for composition _pipeline_execution (0% coverage → 90%)

**Priority:** P0 (Critical - public bootstrap surface)

**Labels:** `test-coverage`, `p0`, `composition-api`, `public-surface`

**Description:**
The `_pipeline_execution.py` module has 0% coverage (0/84 lines) despite being a critical internal module for pipeline execution orchestration. This module contains the core pipeline execution logic and is referenced by public APIs.

**Context:**
- Current coverage: 0% (0/84 executable lines)
- Target coverage: 90%
- Path: `src/bioetl/composition/_pipeline_execution.py`
- Module contains core pipeline execution orchestration
- Large module (84 executable lines) with complex logic

**Steps:**
1. Analyze _pipeline_execution.py internal structure
2. Create `tests/unit/composition/test_pipeline_execution_contract.py`
3. Test scenarios:
   - Pipeline lifecycle orchestration
   - Stage execution logic
   - Error handling and recovery
   - State transitions
   - Event publication
4. Use mocks for all downstream dependencies
5. Consider splitting into multiple test files if module is too large
6. Run coverage-verify lane to verify coverage >= 90%
7. Update module-coverage-inventory.json

**Acceptance Criteria:**
- [ ] Test file(s) created with comprehensive coverage
- [ ] Coverage >= 90% for _pipeline_execution.py
- [ ] All orchestration paths tested
- [ ] Error recovery paths validated
- [ ] Coverage-verify lane passes

**Risk:** High - large module with complex orchestration logic

---

## Issue #8: Создать тесты для pipeline_run lifecycle transitions (31.1% → 95%)

**Title:** Add lifecycle transition tests for pipeline_run_mixins (31.1% → 95%)

**Priority:** P0 (Domain aggregates - largest gap)

**Labels:** `test-coverage`, `p0`, `domain-aggregates`, `pipeline-run`

**Description:**
The `_pipeline_run_mixins.py` module has only 31.1% coverage (19/61 lines) with a 63.9% gap to the 95% target. This module defines pipeline_run lifecycle invariants and is critical for core orchestration safety.

**Context:**
- Current coverage: 31.1% (19/61 lines)
- Target coverage: 95%
- Path: `src/bioetl/domain/aggregates/_pipeline_run_mixins.py`
- Module defines explicit lifecycle invariants
- Missing: success/failure/shutdown paths, event publication, terminal locks

**Steps:**
1. Analyze _pipeline_run_mixins.py uncovered lines
2. Create `tests/unit/domain/aggregates/test_pipeline_run_lifecycle.py`
3. Test scenarios:
   - Start → Complete transition
   - Start → Fail transition
   - Start → Shutdown transition
   - Terminal mutation lock after terminal state
   - Event publication on state changes
   - Invalid transition attempts
4. Use fake clock and fake event collector as fixtures
5. Run coverage-verify lane to verify coverage >= 95%
6. Update module-coverage-inventory.json

**Acceptance Criteria:**
- [ ] Test file created
- [ ] Coverage >= 95% for _pipeline_run_mixins.py
- [ ] All lifecycle transitions tested
- [ ] Terminal lock behavior validated
- [ ] Event publication tested
- [ ] Coverage-verify lane passes

**Risk:** Medium - requires understanding of lifecycle invariants

---

## Issue #9: Создать тесты для pipeline_run domain events (67.7% → 95%)

**Title:** Add domain event payload tests for pipeline_run (67.7% → 95%)

**Priority:** P0 (Domain aggregates)

**Labels:** `test-coverage`, `p0`, `domain-aggregates`, `pipeline-run`

**Description:**
The `pipeline_run.py` module has 67.7% coverage (21/31 lines) with a 27.3% gap to the 95% target. This module defines the PipelineRun aggregate and its domain events.

**Context:**
- Current coverage: 67.7% (21/31 lines)
- Target coverage: 95%
- Path: `src/bioetl/domain/aggregates/pipeline_run.py`
- Module defines PipelineRun aggregate and domain events
- Missing: domain event payload validation

**Steps:**
1. Analyze pipeline_run.py uncovered lines
2. Create `tests/unit/domain/aggregates/test_pipeline_run_events.py`
3. Test scenarios:
   - Domain event payload structure
   - Event field validation
   - Event serialization/deserialization
   - Event snapshot fixtures
4. Use fake publisher and event snapshot fixtures
5. Run coverage-verify lane to verify coverage >= 95%
6. Update module-coverage-inventory.json

**Acceptance Criteria:**
- [ ] Test file created
- [ ] Coverage >= 95% for pipeline_run.py
- [ ] All domain events tested
- [ ] Event payloads validated
- [ ] Coverage-verify lane passes

**Risk:** Low - event testing is typically straightforward

---

## Issue #10: Создать тесты для quarantine invariants (37.8% → 95%)

**Title:** Add quarantine invariants tests (37.8% → 95%)

**Priority:** P0 (Domain aggregates - large gap)

**Labels:** `test-coverage`, `p0`, `domain-aggregates`, `quarantine`

**Description:**
The `_quarantine_aggregate.py` module has only 37.8% coverage (14/37 lines) with a 57.2% gap to the 95% target. This module defines quarantine aggregate logic which is critical for quality control and immutability.

**Context:**
- Current coverage: 37.8% (14/37 lines)
- Target coverage: 95%
- Path: `src/bioetl/domain/aggregates/_quarantine_aggregate.py`
- Module defines quarantine aggregate for quality control
- Missing: payload immutability, status transitions, resolution invariants

**Steps:**
1. Analyze _quarantine_aggregate.py uncovered lines
2. Create `tests/unit/domain/aggregates/test_quarantine_entry_invariants.py`
3. Test scenarios:
   - Payload immutability enforcement
   - Status transition validation
   - Resolution info invariants
   - Invalid state attempts
4. Use immutable payload fixture
5. Run coverage-verify lane to verify coverage >= 95%
6. Update module-coverage-inventory.json

**Acceptance Criteria:**
- [ ] Test file created
- [ ] Coverage >= 95% for _quarantine_aggregate.py
- [ ] Immutability constraints tested
- [ ] Status transitions validated
- [ ] Resolution invariants checked
- [ ] Coverage-verify lane passes

**Risk:** Medium - requires understanding of quarantine invariants

---

## Issue #11: Создать тесты для batch lifecycle transitions (43.3% → 95%)

**Title:** Add batch lifecycle transition tests (43.3% → 95%)

**Priority:** P0 (Domain aggregates)

**Labels:** `test-coverage`, `p0`, `domain-aggregates`, `batch`

**Description:**
The `_batch_lifecycle.py` module has only 43.3% coverage (13/30 lines) with a 51.7% gap to the 95% target. This module defines batch lifecycle state transitions which are critical for batch processing semantics.

**Context:**
- Current coverage: 43.3% (13/30 lines)
- Target coverage: 95%
- Path: `src/bioetl/domain/aggregates/_batch_lifecycle.py`
- Module defines batch lifecycle state machine
- Missing: OPEN → SEALED → WRITING → COMMITTED, OPEN → SEALED → FAILED transitions, terminal guards

**Steps:**
1. Analyze _batch_lifecycle.py uncovered lines
2. Create `tests/unit/domain/aggregates/test_batch_lifecycle.py`
3. Test scenarios:
   - OPEN → SEALED transition
   - SEALED → WRITING transition
   - WRITING → COMMITTED transition
   - OPEN → SEALED → FAILED transition
   - Terminal state guards (no transitions after COMMITTED/FAILED)
   - Invalid transition attempts
4. Use deterministic clock and fake hash builder as fixtures
5. Run coverage-verify lane to verify coverage >= 95%
6. Update module-coverage-inventory.json

**Acceptance Criteria:**
- [ ] Test file created
- [ ] Coverage >= 95% for _batch_lifecycle.py
- [ ] All lifecycle transitions tested
   - Terminal guards validated
- [ ] Invalid transitions rejected
- [ ] Coverage-verify lane passes

**Risk:** Medium - requires understanding of state machine

---

## Issue #12: Создать тесты для batch determinism (61.6% → 95%)

**Title:** Add batch determinism and replay tests (61.6% → 95%)

**Priority:** P0 (Domain aggregates)

**Labels:** `test-coverage`, `p0`, `domain-aggregates`, `batch`

**Description:**
The `_batch_mixins.py` module has 61.6% coverage (61/99 lines) with a 33.4% gap to the 95% target. This module contains batch-related mixins including determinism logic.

**Context:**
- Current coverage: 61.6% (61/99 lines)
- Target coverage: 95%
- Path: `src/bioetl/domain/aggregates/_batch_mixins.py`
- Module contains batch determinism logic
- Missing: hash determinism, index sequencing, replay stability tests

**Steps:**
1. Analyze _batch_mixins.py uncovered lines
2. Create `tests/unit/domain/aggregates/test_batch_determinism.py`
3. Test scenarios:
   - Hash determinism
   - Index sequencing consistency
   - Replay stability
   - Deterministic ordering
4. Use stable payload factory as fixture
5. Run coverage-verify lane to verify coverage >= 95%
6. Update module-coverage-inventory.json

**Acceptance Criteria:**
- [ ] Test file created
- [ ] Coverage >= 95% for _batch_mixins.py
- [ ] Determinism properties validated
- [ ] Index sequencing tested
- [ ] Replay stability verified
- [ ] Coverage-verify lane passes

**Risk:** Medium - determinism testing requires careful fixture design

---

## Issue #13: Подтянуть publication_common_schema до 95% (86% → 95%)

**Title:** Increase coverage for publication_common_schema (86% → 95%)

**Priority:** P0 (Domain contracts/gold - final polish)

**Labels:** `test-coverage`, `p0`, `domain-contracts`, `gold`

**Description:**
The `_publication_common_schema.py` module has 86% coverage (43/50 lines) with a 9% gap to the 95% target. This is the only gold contract module below 95% threshold.

**Context:**
- Current coverage: 86% (43/50 lines)
- Target coverage: 95%
- Path: `src/bioetl/domain/contracts/gold/_publication_common_schema.py`
- Module defines common schema for publication contracts
- Missing: 7 lines (likely edge cases)

**Steps:**
1. Analyze _publication_common_schema.py uncovered lines
2. Extend existing `tests/unit/domain/contracts/gold/test_publication_common_schema.py`
3. Add test scenarios for uncovered edge cases
4. Use golden datasets as fixtures
5. Run coverage-verify lane to verify coverage >= 95%
6. Update module-coverage-inventory.json

**Acceptance Criteria:**
- [ ] Existing test file extended
- [ ] Coverage >= 95% for _publication_common_schema.py
- [ ] All edge cases covered
- [ ] Coverage-verify lane passes

**Risk:** Low - only 7 lines gap, existing test infrastructure

---

## Summary

**Total Issues:** 13

**Phase 1: Public APIs (7 issues)**
- Issues #1-7: Create contract tests for 7 composition API modules (0% → 90%)
- Expected effect: Coverage increase from ~12% to ~90% for public APIs

**Phase 2: Domain Aggregates Lifecycle (4 issues)**
- Issues #8-11: Create lifecycle and state transition tests
- Expected effect: Domain aggregates coverage from ~65% to ~85%

**Phase 3: Domain Aggregates Remaining (1 issue)**
- Issue #12: Batch determinism tests
- Expected effect: Domain aggregates coverage to ~90%

**Phase 4: Gold Contracts Final Polish (1 issue)**
- Issue #13: Publication common schema edge cases
- Expected effect: Gold contracts coverage from ~99% to 100%

**Execution Order:**
1. Phase 1 (Issues #1-7): Public APIs - CRITICAL (0% coverage)
2. Phase 2 (Issues #8-11): Domain lifecycle - HIGH (large gaps)
3. Phase 3 (Issue #12): Batch determinism - MEDIUM
4. Phase 4 (Issue #13): Gold polish - LOW (only 7 lines gap)

**Total Estimated Effort:** 3-4 weeks (assuming 1-2 days per issue for Phase 1, 2-3 days per issue for Phase 2, 1-2 days for Phase 3, 1 day for Phase 4)