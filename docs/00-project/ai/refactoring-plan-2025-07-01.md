# Refactoring Plan — Updated (2025-07-01)

## Audit Corrections

Based on actual codebase inspection on 2025-07-01:

### Original Audit Errors:
1. ❌ **compatibility_test_file_max**: Audit claimed 206, actual is **0** ✅
2. ❌ **supporting scripts**: Audit claimed 81, actual is **88**
3. ❌ **silver storage files**: Audit claimed 35+, actual is **56**

### Verified Findings:
- ✅ application/core/ — 181 files (God Package)
- ✅ domain/aggregates/ — 19 files (fragmented)
- ✅ domain/ root — 26 files (needs sub-packages)
- ✅ duplicate_test_names — 2 with 4 occurrences
- ✅ pathlib.Path in domain/control_plane/contract_registry_helpers.py
- ✅ aggregate-invariants.md exists and is well-documented

## Completed Quick Wins (2025-07-01)

### ✅ Step 2: Document Path Exception (COMPLETED)
- Added sanctioned exception documentation to domain/README.md
- Added comment to contract_registry_helpers.py
- Status: DONE
- Impact: DDD Alignment +0.5

## Updated Refactoring Plan

### Phase 1: Remaining Quick Wins (This Week, 8 hours)

#### Step 1: Add Exhaustive FSM Transition Tests (6 hours)
- Create tests/architecture/domain/test_aggregate_fsm_transitions.py
- Add exhaustive FSM transition tests for Batch, PipelineRun, QuarantineEntry
- Cover all valid and invalid transitions
- Expected impact: DDD Alignment 7.5 → 9.0 (+1.5)

#### Step 3: Fix Duplicate Test Names (2 hours)
- Rename 2 duplicate test names
- Update references
- Expected impact: Naming & Structure +0.5

### Phase 2: Debt Reduction (This Month, 40 hours)

#### Step 4: Reduce Supporting Scripts (40 hours)
- Audit all 88 supporting scripts
- Migrate callers to canonical paths
- Remove obsolete wrappers with phased deprecation
- Target: 88 → <50 scripts
- Expected impact: Technical Debt 4.0 → 7.0 (+3.0)

### Phase 3: Structural Improvements (Next Quarter, 140 hours)

#### Step 5: Decompose application/core/ (80 hours)
- Create explicit sub-packages: batch/, record/, runner/, pipeline/
- Move 181 files into organized structure
- Target: ≤10 files in core/ root
- Expected impact: Module Boundaries 6.0 → 8.0 (+2.0)

#### Step 6: Consolidate Silver Storage (60 hours)
- Replace mixin-based composition with explicit DI
- Target: 56 → ≤15 files
- Expected impact: Coupling & Cohesion 6.5 → 8.0 (+1.5)

## Updated Metrics

### Current State (2025-07-01):
- Layer Compliance: 9.0/10 ✅
- Hexagonal Architecture: 8.0/10
- DDD Alignment: 8.0/10 (+0.5 from Path documentation)
- Module Boundaries: 6.0/10
- Naming & Structure: 7.5/10
- Coupling & Cohesion: 6.5/10
- Technical Debt: 4.0/10
- **Overall: 7.77/10**

### Target State (After Phases 1-3):
- Layer Compliance: 9.0/10 (stable)
- Hexagonal Architecture: 8.5/10 (+0.5)
- DDD Alignment: 9.5/10 (+1.5)
- Module Boundaries: 8.0/10 (+2.0)
- Naming & Structure: 8.0/10 (+0.5)
- Coupling & Cohesion: 8.0/10 (+1.5)
- Technical Debt: 7.0/10 (+3.0)
- **Overall: 8.42/10 (+0.65)**

## Quality Gates

```bash
# Gate 1: Layer compliance
python -m scripts.engineering.qa check-import-graph --strict

# Gate 2: Module boundaries
python -c "import os; count = sum(1 for f in os.scandir('src/bioetl/application/core') if f.is_file() and f.name.endswith('.py')); assert count <= 10, f'core/ root has {count} files'"

# Gate 3: Compatibility debt
python scripts/engineering/repo/check_scripts_inventory.py --check-lifecycle
# assert supporting_count <= 50

# Gate 4: Test governance
python -m pytest tests/architecture/test_test_governance_audit.py -x

# Gate 5: Architecture tests
python -m pytest tests/architecture/ -x --timeout=300

# Gate 6: Aggregate FSM tests (NEW)
python -m pytest tests/architecture/domain/test_aggregate_fsm_transitions.py -x
```

## Recommendations

### Immediate (This Week):
1. ✅ Step 2: Document Path Exception (COMPLETED)
2. ⏳ Step 1: Add Exhaustive FSM Transition Tests (6 hours)
3. ⏳ Step 3: Fix Duplicate Test Names (2 hours)

### Short-term (This Month):
4. ⏳ Step 4: Reduce Supporting Scripts (40 hours)

### Long-term (Next Quarter):
5. ⏳ Step 5: Decompose application/core/ (80 hours)
6. ⏳ Step 6: Consolidate Silver Storage (60 hours)

### Requires Separate Approval:
- Step 5: application/core/ decomposition requires team alignment on sub-package boundaries
- Step 6: SilverWriter API changes require migration plan and downstream consumer coordination
- Step 4: Supporting script removal requires external caller audit and deprecation timeline

## Evidence

- Architecture audit: docs/00-project/ai/architecture-audit-2025-07-01-corrected.md
- Aggregate invariants: docs/02-architecture/domain/aggregate-invariants.md
- Scripts inventory: configs/quality/scripts_inventory_manifest.json
- Test governance: configs/quality/test_governance_audit.yaml
- Path exception documentation: src/bioetl/domain/README.md#sanctioned-exceptions
