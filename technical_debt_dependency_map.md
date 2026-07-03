# Technical Debt Dependency Map

**Generated:** 2026-08-18
**Project:** BioETL
**Purpose:** Map dependencies between technical debt categories and identify systemic issues

## Executive Summary

This document maps the technical debt discovered across the BioETL codebase, showing how different debt categories are interconnected. The map identifies:

- **High-Impact Debt:** Debt that blocks multiple improvements
- **Systemic Debt:** Debt that creates cascading issues
- **Independent Debt:** Debt that can be addressed in isolation

## Debt Categories Overview

| Category | Status | Impact | Owner | Priority |
|----------|--------|--------|-------|----------|
| Compatibility Layer | Clean (0 transition shims) | Medium | @bioetl-architecture | Low |
| Code Duplication | Active (23 path exemptions) | High | @bioetl-platform | High |
| Layering Violations | Active | High | @bioetl-architecture | High |
| Config/Contracts Drift | Clean (0 inconsistencies) | Low | @bioetl-config | Low |
| Test Debt | Clean (0 gaps) | Medium | @bioetl-data-platform | Low |
| Observability Debt | Active | Medium | @bioetl-observability | Medium |
| Architecture Metrics | Clean (0 exemptions) | Low | @bioetl-architecture | Low |
| Complexity Exemptions | Active (23 path + 5 function) | High | @bioetl-platform | High |

## Dependency Graph

### Tier 1: Foundation Debt (Blocks Multiple Improvements)

```
┌─────────────────────────────────────────────────────────────────┐
│                    FOUNDATION DEBT                              │
│  (Addressing these enables multiple downstream improvements)    │
└─────────────────────────────────────────────────────────────────┘

1. ADAPTER COMPLEXITY & DUPLICATION
   └─> Blocks: Layering cleanup, Test simplification, Observability
   └─> Impact: All external provider integrations (ChEMBL, OpenAlex, etc.)
   └─> Root Cause: Fallback logic embedded in adapters instead of policies
   └─> Exemptions: 7 adapters with xenon + critical_check exemptions

2. COMPOSITE ORCHESTRATION COMPLEXITY
   └─> Blocks: Testability, Debuggability, Refactoring
   └─> Impact: Join, checkpoint, runner orchestration
   └─> Root Cause: Wide branching and dependency surfaces
   └─> Exemptions: src/bioetl/application/composite/ (xenon + critical_check)

3. RUNTIME BUILDER DUPLICATION
   └─> Blocks: CLI/Runtime unification, Configuration simplification
   └─> Impact: Bootstrap wiring, service factories
   └─> Root Cause: Multi-source extraction and policy wiring branches
   └─> Exemptions: composition/runtime_builders/, composition/factories/services/
```

### Tier 2: Systemic Debt (Cascading Impact)

```
┌─────────────────────────────────────────────────────────────────┐
│                    SYSTEMIC DEBT                                │
│  (Creates cascading issues across the codebase)                 │
└─────────────────────────────────────────────────────────────────┘

1. LAYERING VIOLATIONS
   └─> Causes: Domain ↔ Infrastructure leakage
   └─> Impact: Test isolation, Refactoring safety, Dependency management
   └─> Dependencies: Adapter complexity (makes cleanup harder)
   └─> Hotspots: src/bioetl/domain/, src/bioetl/infrastructure/

2. CLI/RUNTIME DUPLICATION
   └─> Causes: Command wiring duplicated between CLI and runtime
   └─> Impact: Maintenance burden, Feature parity issues
   └─> Dependencies: Runtime builder duplication
   └─> Exemptions: src/bioetl/interfaces/cli/ (xenon + critical_check)

3. EXTRACTOR PARSING DUPLICATION
   └─> Causes: Parsing logic repeated across pipelines
   └─> Impact: Bug propagation, Maintenance overhead
   └─> Dependencies: Adapter complexity (similar patterns)
   └─> Exemptions: src/bioetl/application/pipelines/*/extractors/* (xenon)
```

### Tier 3: Independent Debt (Can Address in Isolation)

```
┌─────────────────────────────────────────────────────────────────┐
│                    INDEPENDENT DEBT                             │
│  (Can be addressed without major dependencies)                  │
└─────────────────────────────────────────────────────────────────┘

1. OBSERVABILITY GAPS
   └─> Impact: Debugging, SLO monitoring
   └─> Dependencies: None (can add tracing independently)
   └─> Hotspots: src/bioetl/infrastructure/observability/ (xenon + critical_check)
   └─> Exemptions: Label normalization and dispatch policies

2. DQ ANALYZER COMPLEXITY
   └─> Impact: Data quality rule management
   └─> Dependencies: None
   └─> Exemptions: src/bioetl/application/services/dq/ (xenon + critical_check)

3. STORAGE WRITE PATH COMPLEXITY
   └─> Impact: Silver storage performance
   └─> Dependencies: None
   └─> Exemptions: src/bioetl/infrastructure/storage/silver/ (xenon + critical_check)

4. CONTROL PLANE ORCHESTRATION
   └─> Impact: Artifact management
   └─> Dependencies: None
   └─> Exemptions: src/bioetl/infrastructure/control_plane/ (xenon + critical_check)

5. QUARANTINE NORMALIZATION
   └─> Impact: Data quarantine processing
   └─> Dependencies: None
   └─> Exemptions: src/bioetl/infrastructure/quarantine/ (xenon + critical_check)
```

## Detailed Dependency Map

### 1. Adapter Complexity → Multiple Downstream Effects

```
Adapter Fallback Logic (Foundation)
├─> Increases cyclomatic complexity
│   └─> Blocks: Test simplification (hard to mock)
│   └─> Blocks: Observability (tracing through branches)
│   └─> Blocks: Refactoring (unsafe to modify)
├─> Creates Layering Violations
│   └─> Adapters mix domain logic with infrastructure concerns
│   └─> Domain entities depend on adapter internals
├─> Causes Duplication
│   └─> Similar fallback patterns across 7 adapters
│   └─> Retry logic duplicated (fetch_filtered_with_fallback, _request_with_retry)
└─> Governance: 7 adapters with xenon + critical_check exemptions (expires 2026-12-31)

Affected Adapters:
- ChEMBL: Batch reduction + retry branches
- OpenAlex: DOI/title fallback sequencing
- Semantic Scholar: DOI/id fallback routing
- CrossRef: Batch DOI resolution
- PubMed: PMID/title fallback + retry
- UniProt: Pagination/retry parsing
- PubChem: InChIKey fallback resolution

Function Exemptions:
- fetch_filtered_with_fallback (max CC: 25)
- _request_with_retry (max CC: 20)
- fetch_batch (max CC: 15)
```

### 2. Composite Orchestration → Testability & Debuggability

```
Composite Orchestration (Foundation)
├─> Wide branching surfaces
│   └─> Blocks: Unit test coverage (too many paths)
│   └─> Blocks: Debugging (hard to trace execution)
├─> Dependency coupling
│   └─> Blocks: Refactoring (cascading changes)
│   └─> Blocks: Feature addition (high risk)
├─> Creates Test Debt
│   └─> Requires complex fixtures
│   └─> Increases flakiness risk
└─> Governance: src/bioetl/application/composite/ (xenon + critical_check)

Hotspot Budgets:
- composite_orchestration: file_size_limits=1, class_size=1, god_object=1
```

### 3. Runtime Builder Duplication → CLI/Runtime Unification

```
Runtime Builder Duplication (Foundation)
├─> Multi-source extraction branches
│   └─> Blocks: CLI/Runtime unification
│   └─> Blocks: Configuration simplification
├─> Policy wiring duplication
│   └─> Blocks: Feature parity
│   └─> Blocks: Maintenance
├─> Causes CLI Duplication
│   └─> Command wiring repeated
│   └─> Presentation branching duplicated
└─> Governance:
    - composition/runtime_builders/ (xenon + critical_check)
    - composition/factories/services/ (xenon + critical_check)
    - interfaces/cli/ (xenon + critical_check)
```

### 4. Layering Violations → Refactoring Safety

```
Layering Violations (Systemic)
├─> Domain → Infrastructure leakage
│   └─> Domain entities import infrastructure
│   └─> Blocks: Domain testing in isolation
│   └─> Blocks: Infrastructure replacement
├─> Infrastructure → Domain leakage
│   └─> Infrastructure depends on domain internals
│   └─> Blocks: Domain evolution
│   └─> Blocks: Independent deployment
├─> Circular dependencies
│   └─> Blocks: Modularization
│   └─> Blocks: Dependency injection
└─> Dependencies: Made worse by adapter complexity

Architecture Metric Exemptions:
- All registries empty (0 exemptions) - this is GOOD
- But code still has violations not yet in exemptions
```

### 5. Observability Gaps → Debugging & SLO Monitoring

```
Observability Debt (Independent)
├─> Tracing coverage gaps
│   └─> Hard to debug production issues
│   └─> Cannot enforce SLOs effectively
├─> Metric declaration mismatches
│   └─> Unused metrics (noise)
│   └─> Missing metrics (blind spots)
├─> Label normalization complexity
│   └─> High cardinality risk
│   └─> Query performance issues
└─> Governance: src/bioetl/infrastructure/observability/ (xenon + critical_check)

Related Configs:
- observability_metric_declarations.yaml
- observability_metric_governance.yaml
- observability_metric_inventory_allowlist.yaml
- observability_slo_alert_contract.yaml
```

## Governance Status

### Exemptions Summary

| Category | Count | Status | Target |
|----------|-------|--------|--------|
| Architecture Metric Exemptions | 0 | ✅ Clean | 0 |
| Duplication/Complexity Path Exemptions | 23 | ⚠️ Active | 0 |
| Duplication/Complexity Function Exemptions | 5 | ⚠️ Active | 0 |
| Compatibility Transition Shims | 0 | ✅ Clean | 0 |
| Sanctioned Public Entrypoints | 12 | ✅ Governed | Stable |
| Config Inconsistencies | 0 | ✅ Clean | 0 |
| Bronze Fixture Gaps | 0 | ✅ Clean | 0 |

### CI Enforcement

| Check | Mode | Status |
|-------|------|--------|
| Quality Integral Score (QIS) | Block | Active |
| Duplication/Complexity | Block | Active |
| C901 Baseline | Block | Active (budget=0) |
| Config Surface Ratchet | Fail-fast | Active |
| Import Linter | Block | Active |
| SonarCloud | Report | Active |
| Weekly Debt Reporting | Report | Active |

### Staged Enforcement

| Policy | Stage | Threshold | Status |
|--------|-------|-----------|--------|
| fixture_governance | soft_fail | 0.8 | Active |
| contract_identity | soft_fail | 0.7 | Active |
| checkpoint_compatibility | observe | 0.9 | Monitoring |
| effective_config_stability | observe | 0.7 | Monitoring |
| registry_consistency | observe | 0.8 | Monitoring |
| schema_compatibility | observe | 0.9 | Monitoring |

## Hotspot Analysis

### High-Impact Hotspots (Tier 1)

1. **Adapters (7 providers)**
   - Path: `src/bioetl/infrastructure/adapters/`
   - Debt: Fallback logic complexity
   - Blockers: Layering, Testing, Observability
   - Owner: @bioetl-platform

2. **Composite Orchestration**
   - Path: `src/bioetl/application/composite/`
   - Debt: Wide branching surfaces
   - Blockers: Testability, Debuggability
   - Owner: @bioetl-composite

3. **Runtime Builders**
   - Path: `src/bioetl/composition/runtime_builders/`
   - Debt: Multi-source extraction branches
   - Blockers: CLI/Runtime unification
   - Owner: @bioetl-composition

### Medium-Impact Hotspots (Tier 2)

1. **Service Factories**
   - Path: `src/bioetl/composition/factories/services/`
   - Debt: Factory branch counts
   - Owner: @bioetl-composition

2. **Pipelines/Extractors**
   - Path: `src/bioetl/application/pipelines/*/extractors/*`
   - Debt: Extraction/parsing flows
   - Owner: @bioetl-application

3. **CLI**
   - Path: `src/bioetl/interfaces/cli/`
   - Debt: Presentation branching
   - Owner: @bioetl-cli

### Low-Impact Hotspots (Tier 3)

1. **Observability Dispatch**
   - Path: `src/bioetl/infrastructure/observability/`
   - Debt: Label normalization
   - Owner: @bioetl-observability

2. **Silver Storage**
   - Path: `src/bioetl/infrastructure/storage/silver/`
   - Debt: Write path coercion
   - Owner: @bioetl-storage

3. **Control Plane**
   - Path: `src/bioetl/infrastructure/control_plane/`
   - Debt: Artifact orchestration
   - Owner: @bioetl-control-plane

4. **Quarantine**
   - Path: `src/bioetl/infrastructure/quarantine/`
   - Debt: Normalization branches
   - Owner: @bioetl-quarantine

5. **DQ Services**
   - Path: `src/bioetl/application/services/dq/`
   - Debt: Validation rule bundles
   - Owner: @bioetl-dq

## Recommendations

### Immediate Actions (Priority 1)

1. **Address Adapter Complexity First**
   - This is the foundational debt blocking multiple improvements
   - Extract fallback logic into policy helpers
   - Remove 7 adapter exemptions by 2026-12-31

2. **Simplify Composite Orchestration**
   - Split merge/checkpoint collaborators
   - Reduce branching surfaces
   - Improve testability

3. **Unify Runtime Builders**
   - Extract multi-source extraction into helpers
   - Unify CLI/Runtime wiring
   - Reduce duplication

### Short-Term Actions (Priority 2)

1. **Fix Layering Violations**
   - After adapter complexity is reduced
   - Establish clear boundaries
   - Enable safe refactoring

2. **Standardize Extractor Parsing**
   - Extract common parsing patterns
   - Reduce pipeline duplication

3. **Improve Observability**
   - Add tracing coverage
   - Normalize labels
   - Align declarations with usage

### Long-Term Actions (Priority 3)

1. **Simplify Independent Hotspots**
   - Storage, Control Plane, Quarantine, DQ
   - Can be done in parallel

2. **Maintain Governance**
   - Keep exemptions at zero
   - Monitor staged enforcement policies
   - Review quarterly

## Next Steps

1. Prioritize Tier 1 (Foundation) debt for immediate action
2. Create detailed refactoring plans for each hotspot
3. Use `generate_architecture_debt_tasks.py` to create actionable tasks
4. Track progress through weekly debt reporting
5. Update this dependency map as debt is addressed