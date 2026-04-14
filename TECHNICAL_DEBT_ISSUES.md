# Technical Debt Issues - Auto-Generated from Neo4j Analysis

## Issue 1: Remove Legacy Column Ordering System
**Priority**: High 🔴
**Labels**: `technical-debt`, `refactoring`, `cleanup`
**Component**: `src/bioetl/application/composite/`

### Description
Remove the deprecated column ordering system that has been marked as legacy. This includes:
- `src/bioetl/application/composite/column_orderer.py` (12 methods, 1 class)
- `src/bioetl/application/composite/column_priority_orderer.py` (multiple functions)
- `src/bioetl.application/composite/column_service.py` (service layer)

### Rationale
- All components marked with `compat`, `deprecated`, `legacy` markers
- High removable scores (14-15) with high removal confidence
- No detected runtime usage
- Replaced by modern field ordering systems

### Impact Analysis Required
```bash
python -m scripts.ops query-neo4j-memory neighbors-module src.bioetl.application.composite.column_orderer
```

### Acceptance Criteria
- [ ] Remove all legacy column ordering files
- [ ] Update any remaining references to use modern field ordering
- [ ] Remove related tests and documentation
- [ ] Verify no runtime impact through CI tests

---

## Issue 2: Eliminate Deprecated Checkpoint State Management
**Priority**: High 🔴
**Labels**: `technical-debt`, `refactoring`, `checkpoint`
**Component**: `src/bioetl/application/composite/checkpoint/`

### Description
Remove the deprecated checkpoint state management system in favor of the modern checkpoint implementation:
- `src.bioetl.application.composite/checkpoint/state.py` (entire module)
- `src.bioetl.application.composite/checkpoint.state.CompositeCheckpointState` class
- All related state parsing and serialization functions

### Rationale
- Marked with `compat` deprecation markers
- High removable scores (14-15) with high removal confidence
- Replaced by modern checkpoint system introduced in v2.1
- No detected runtime usage in current pipelines

### Impact Analysis Required
```bash
python -m scripts.ops query-neo4j-memory neighbors-class src.bioetl.application.composite.checkpoint.state.CompositeCheckpointState
```

### Acceptance Criteria
- [ ] Remove deprecated checkpoint state module
- [ ] Ensure modern checkpoint system handles all use cases
- [ ] Update pipeline configurations to use new checkpoint system
- [ ] Verify checkpoint/restore functionality in CI

---

## Issue 3: Simplify Coalesce Policy System
**Priority**: High 🔴
**Labels**: `technical-debt`, `refactoring`, `simplification`
**Component**: `src/bioetl/application/composite/`

### Description
Simplify or remove the complex coalesce policy system that has been marked as legacy:
- `src.bioetl.application.composite/coalesce_policy.py` (entire module)
- `CoalescePolicyService` class with 15 methods
- All related coalesce functions and helpers

### Rationale
- Marked with `compat` deprecation markers
- High removable scores (15) with high removal confidence
- Complex system with 35 branches across the module
- Modern field merging handles most use cases more efficiently

### Impact Analysis Required
```bash
python -m scripts.ops query-neo4j-memory neighbors-service src.bioetl.application.composite.coalesce_policy.CoalescePolicyService
```

### Acceptance Criteria
- [ ] Remove or simplify coalesce policy system
- [ ] Migrate any critical functionality to modern field merging
- [ ] Update pipeline configurations
- [ ] Verify field merging behavior in integration tests

---

## Issue 4: Refactor Complex PubChem Fetch Strategies
**Priority**: Medium 🟡
**Labels**: `technical-debt`, `performance`, `refactoring`
**Component**: `src/bioetl/infrastructure/adapters/pubchem/`

### Description
Refactor the overengineered PubChem fetch strategies to reduce complexity:
- `PubChemFetchStrategies` class (23 branches, 4 nesting levels)
- Multiple fetch methods (`fetch_by_cids`, `fetch_by_inchikey`, `fetch_by_smiles`)
- High complexity scores (8) with removable complexity markers

### Rationale
- Overengineered with compat/wrapper/helper patterns
- High branch counts (6-7 branches per method)
- High nesting levels (4 levels)
- Can be simplified using modern fetch patterns

### Impact Analysis Required
```bash
python -m scripts.ops query-neo4j-memory neighbors-class src.bioetl.infrastructure.adapters.pubchem.fetch_strategies.PubChemFetchStrategies
```

### Acceptance Criteria
- [ ] Reduce method complexity in fetch strategies
- [ ] Consolidate common fetch logic
- [ ] Maintain backward compatibility for PubChem API
- [ ] Verify fetch performance and reliability

---

## Issue 5: Simplify ChEMBL Paging Mixin
**Priority**: Medium 🟡
**Labels**: `technical-debt`, `performance`, `refactoring`
**Component**: `src/bioetl/infrastructure/adapters/chembl/`

### Description
Refactor the complex ChEMBL fetch paging mixin:
- `ChemblFetchPagingMixin._page_iterator` method
- High complexity score (9) with removable complexity (13)
- Helper/mixin patterns with stateful markers

### Rationale
- Overengineered paging logic
- High branch count (7 branches)
- High nesting level (4 levels)
- Can be simplified using modern pagination patterns

### Impact Analysis Required
```bash
python -m scripts.ops query-neo4j-memory neighbors-method src.bioetl.infrastructure.adapters.chembl.fetch_paging_mixin.ChemblFetchPagingMixin._page_iterator
```

### Acceptance Criteria
- [ ] Simplify paging logic while maintaining functionality
- [ ] Reduce branch complexity
- [ ] Ensure ChEMBL API compatibility
- [ ] Verify pagination behavior in tests

---

## Issue 6: Consolidate Runner Stage Mixins
**Priority**: Medium 🟡
**Labels**: `technical-debt`, `refactoring`, `architecture`
**Component**: `src/bioetl/application/composite/runner_pkg/`

### Description
Consolidate and simplify the complex runner stage mixin system:
- `CompositeRunnerStageMixin` (stateful, checkpoint, fsm markers)
- `CompositeRunnerStageEnrichmentMixin` (policy, helper patterns)
- Multiple related mixins with high complexity

### Rationale
- Overengineered with multiple mixin patterns
- High removable complexity scores
- Can be consolidated into simpler runner architecture

### Impact Analysis Required
```bash
python -m scripts.ops query-neo4j-memory neighbors-class src.bioetl.application.composite.runner_pkg.runner_stage_mixin.CompositeRunnerStageMixin
```

### Acceptance Criteria
- [ ] Consolidate runner mixins into cleaner architecture
- [ ] Reduce stateful complexity
- [ ] Maintain pipeline runner functionality
- [ ] Verify all pipeline types work correctly

---

## Issue 7: Remove Deprecated Merge Input Mixin
**Priority**: Medium 🟡
**Labels**: `technical-debt`, `refactoring`, `cleanup`
**Component**: `src/bioetl/application/composite/`

### Description
Remove the deprecated merge input mixin system:
- `_MergeInputLoaderMixin` class
- Related merge input functions
- Marked as legacy with high removable scores

### Rationale
- Marked with `compat`, `legacy` deprecation markers
- High removable score (15)
- Replaced by modern merge input handling

### Impact Analysis Required
```bash
python -m scripts.ops query-neo4j-memory neighbors-class src.bioetl.application.composite.merger_input_mixin._MergeInputLoaderMixin
```

### Acceptance Criteria
- [ ] Remove deprecated merge input mixin
- [ ] Ensure modern merge system handles all use cases
- [ ] Update composite pipeline configurations
- [ ] Verify merge behavior in integration tests

---

## Issue 8: Simplify HTTP Client Retry Logic
**Priority**: Low 🟢
**Labels**: `technical-debt`, `refactoring`, `performance`
**Component**: `src/bioetl/infrastructure/adapters/http/`

### Description
Simplify the complex HTTP client retry mixin:
- `HTTPClientRetryMixin` class
- High complexity with wrapper/compat patterns
- 14 branches, 3 nesting levels

### Rationale
- Overengineered retry logic
- Can be simplified using modern retry patterns
- Maintains HTTP adapter reliability

### Impact Analysis Required
```bash
python -m scripts.ops query-neo4j-memory neighbors-class src.bioetl.infrastructure.adapters.http.client_retry_mixin.HTTPClientRetryMixin
```

### Acceptance Criteria
- [ ] Simplify retry logic while maintaining reliability
- [ ] Reduce branch complexity
- [ ] Ensure all HTTP adapters continue to work
- [ ] Verify retry behavior in tests

---

## Meta Issue: Technical Debt Tracking Dashboard
**Priority**: High 🔴
**Labels**: `technical-debt`, `meta`, `tracking`
**Component**: `project-management`

### Description
Create a dashboard or tracking system for monitoring technical debt resolution progress across all the issues created from this analysis.

### Rationale
- Track progress on 8+ technical debt issues
- Monitor complexity metrics over time
- Ensure systematic reduction of technical debt

### Acceptance Criteria
- [ ] Create GitHub project board for technical debt tracking
- [ ] Set up metrics dashboard showing complexity trends
- [ ] Establish quarterly review process
- [ ] Define success criteria for technical debt reduction

---

## Implementation Notes

### Prioritization Guidelines
1. **High Priority**: Issues affecting maintainability, with clear removal paths
2. **Medium Priority**: Complexity reduction with architectural impact
3. **Low Priority**: Performance optimizations and minor simplifications

### Recommended Workflow
1. Create GitHub issues from this template
2. Run impact analysis for each high/medium priority issue
3. Prioritize based on business impact and maintenance burden
4. Implement changes with comprehensive test coverage
5. Monitor complexity metrics after each refactoring

### Verification Commands
```bash
# Check current complexity metrics
python -m scripts.ops query-neo4j-memory overengineered-candidates all

# Verify removal candidates
python -m scripts.ops query-neo4j-memory removable-complexity all

# Generate comprehensive report
python -m scripts.ops sync-neo4j-memory --report /tmp/technical-debt-report.json
```