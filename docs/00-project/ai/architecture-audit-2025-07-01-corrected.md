# Architecture Audit — Corrected Findings (2025-07-01)

## Audit Corrections

Based on actual codebase inspection on 2025-07-01:

### Original Audit Errors:
1. **compatibility_test_file_max**: Audit claimed 206, actual is **0** ✅
2. **supporting scripts**: Audit claimed 81, actual is **88**
3. **silver storage files**: Audit claimed 35+, actual is **56**

### Verified Findings:
- ✅ application/core/ — 181 files (God Package)
- ✅ domain/aggregates/ — 19 files (fragmented)
- ✅ domain/ root — 26 files (needs sub-packages)
- ✅ duplicate_test_names — 2 with 4 occurrences
- ✅ pathlib.Path in domain/control_plane/contract_registry_helpers.py

## Updated Key Problems

### CRITICAL:
**Problem 1: application/core/ — God Package (181 files)**
- Severity: CRITICAL
- Impact: Cognitive load, unclear ownership
- Evidence: Verified 181 Python files
- Action: Decompose into explicit sub-packages

### HIGH:
**Problem 2: Silver Storage Mixin Proliferation (56 files)**
- Severity: HIGH
- Impact: Hidden coupling through multiple inheritance
- Evidence: 56 files (not 35+ as originally claimed)
- Action: Replace mixins with explicit collaborator injection

**Problem 3: Aggregate Boundary Fragmentation (19 files)**
- Severity: HIGH
- Impact: Invariants scattered across files
- Evidence: 19 files in domain/aggregates/
- Action: Consolidate and document invariants

**Problem 4: Supporting Scripts Growth (88 scripts)**
- Severity: HIGH
- Impact: Maintenance burden
- Evidence: 88 supporting scripts (not 81)
- Action: Audit and reduce to <50

### MEDIUM:
**Problem 5: pathlib.Path in domain/control_plane/**
- Severity: MEDIUM
- Impact: Sanctioned exception, needs documentation
- Evidence: contract_registry_helpers.py::resolve_path
- Action: Document as sanctioned exception

**Problem 6: Duplicate Test Names (2 names, 4 occurrences)**
- Severity: MEDIUM
- Impact: Navigation difficulty
- Evidence: Verified in test-governance-current.json
- Action: Rename duplicates

**Problem 7: domain/ root contains 26 modules**
- Severity: MEDIUM
- Impact: Navigation difficulty
- Evidence: 26 files in domain/ root
- Action: Move to sub-packages

## Updated Refactoring Plan

### Phase 1: Quick Wins (This Week, 10 hours)

#### Step 1: Document Aggregate Invariants (6 hours)
- Create docs/02-architecture/domain/aggregate-invariants.md
- Add exhaustive FSM transition tests for Batch, PipelineRun, QuarantineEntry
- Expected impact: DDD Alignment 7.5 → 9.0 (+1.5)

#### Step 2: Document Path Exception (2 hours)
- Add sanctioned exception documentation to domain/README.md
- Add comment to contract_registry_helpers.py
- Update test_forbidden_imports.py with explicit allowlist
- Expected impact: DDD Alignment +0.5

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

### Current State:
- Layer Compliance: 9.0/10 ✅
- Hexagonal Architecture: 8.0/10
- DDD Alignment: 7.5/10
- Module Boundaries: 6.0/10
- Naming & Structure: 7.5/10
- Coupling & Cohesion: 6.5/10
- Technical Debt: 4.0/10
- **Overall: 7.62/10**

### Target State (After Phases 1-3):
- Layer Compliance: 9.0/10 (stable)
- Hexagonal Architecture: 8.5/10 (+0.5)
- DDD Alignment: 9.0/10 (+1.5)
- Module Boundaries: 8.0/10 (+2.0)
- Naming & Structure: 8.0/10 (+0.5)
- Coupling & Cohesion: 8.0/10 (+1.5)
- Technical Debt: 7.0/10 (+3.0)
- **Overall: 8.27/10 (+0.65)**

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
```

## Recommendations

### Immediate (This Week):
1. ✅ Step 1: Document Aggregate Invariants (6 hours)
2. ✅ Step 2: Document Path Exception (2 hours)
3. ✅ Step 3: Fix Duplicate Test Names (2 hours)

### Short-term (This Month):
4. ✅ Step 4: Reduce Supporting Scripts (40 hours)

### Long-term (Next Quarter):
5. ⏳ Step 5: Decompose application/core/ (80 hours)
6. ⏳ Step 6: Consolidate Silver Storage (60 hours)

### Requires Separate Approval:
- Step 5: application/core/ decomposition requires team alignment on sub-package boundaries
- Step 6: SilverWriter API changes require migration plan and downstream consumer coordination
- Step 4: Supporting script removal requires external caller audit and deprecation timeline
