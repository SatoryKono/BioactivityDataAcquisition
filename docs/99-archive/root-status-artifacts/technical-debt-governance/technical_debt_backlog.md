# Technical Debt Backlog

**Generated:** 2026-08-18
**Project:** BioETL
**Purpose:** Prioritized backlog for technical debt reduction

## Legend

- **Priority:** P0 (Critical) > P1 (High) > P2 (Medium) > P3 (Low)
- **Effort:** XS (<1 day), S (1-2 days), M (3-5 days), L (1-2 weeks), XL (>2 weeks)
- **Status:** 📋 Backlog, 🚧 In Progress, ✅ Done, ⏸️ Blocked
- **Owner:** Responsible team/role

---

## P0 - Critical Foundation Debt

*These tasks block multiple downstream improvements and should be addressed first.*

### [P0-001] Extract Adapter Fallback Logic into Policy Helpers

**Description:**
Currently, 7 adapters (ChEMBL, OpenAlex, Semantic Scholar, CrossRef, PubMed, UniProt, PubChem) embed fallback logic directly in adapter code, causing high cyclomatic complexity. This blocks layering cleanup, test simplification, and observability improvements.

**Impact:**
- Blocks: Layering cleanup, test simplification, observability
- Affects: All external provider integrations
- Current exemptions: 7 adapters with xenon + critical_check (expires 2026-12-31)

**Tasks:**
1. Design a unified fallback policy interface
2. Extract `fetch_filtered_with_fallback` pattern into reusable helper
3. Extract `_request_with_retry` pattern into reusable helper
4. Migrate ChEMBL adapter to use new helpers
5. Migrate OpenAlex adapter to use new helpers
6. Migrate Semantic Scholar adapter to use new helpers
7. Migrate CrossRef adapter to use new helpers
8. Migrate PubMed adapter to use new helpers
9. Migrate UniProt adapter to use new helpers
10. Migrate PubChem adapter to use new helpers
11. Update tests to mock policy helpers instead of adapters
12. Remove 7 adapter exemptions from duplication/complexity config

**Owner:** @bioetl-platform
**Effort:** L (1-2 weeks)
**Dependencies:** None
**Deadline:** 2026-12-31 (exemption expiration)
**Related Files:**
- `src/bioetl/infrastructure/adapters/chembl/`
- `src/bioetl/infrastructure/adapters/openalex/`
- `src/bioetl/infrastructure/adapters/semantic_scholar/`
- `src/bioetl/infrastructure/adapters/crossref/`
- `src/bioetl/infrastructure/adapters/pubmed/`
- `src/bioetl/infrastructure/adapters/uniprot/`
- `src/bioetl/infrastructure/adapters/pubchem/`
- `config/governance/duplication_complexity_exemptions.yaml`

**Status:** 📋 Backlog

---

### [P0-002] Simplify Composite Orchestration Branching

**Description:**
Composite orchestration (join, checkpoint, runner) has wide branching surfaces that block testability and debuggability. The wide dependency surfaces make refactoring unsafe and feature addition risky.

**Impact:**
- Blocks: Unit test coverage, debugging, refactoring, feature addition
- Current exemption: `src/bioetl/application/composite/` (xenon + critical_check)

**Tasks:**
1. Analyze branching patterns in merge/checkpoint collaborators
2. Split merge collaborator into focused sub-components
3. Split checkpoint collaborator into focused sub-components
4. Reduce dependency surfaces between collaborators
5. Add integration tests for split components
6. Update observability to trace split components
7. Remove composite orchestration exemption

**Owner:** @bioetl-composite
**Effort:** L (1-2 weeks)
**Dependencies:** None
**Deadline:** 2026-12-31
**Related Files:**
- `src/bioetl/application/composite/`
- `config/governance/duplication_complexity_exemptions.yaml`

**Status:** 📋 Backlog

---

### [P0-003] Unify Runtime Builder and CLI Wiring

**Description:**
Runtime builders and CLI have duplicated command wiring and policy extraction logic. This blocks CLI/Runtime unification and configuration simplification.

**Impact:**
- Blocks: CLI/Runtime unification, configuration simplification
- Current exemptions:
  - `src/bioetl/composition/runtime_builders/` (xenon + critical_check)
  - `src/bioetl/composition/factories/services/` (xenon + critical_check)
  - `src/bioetl/interfaces/cli/` (xenon + critical_check)

**Tasks:**
1. Extract multi-source extraction logic into shared helpers
2. Create unified command wiring abstraction
3. Migrate runtime builders to use unified wiring
4. Migrate CLI to use unified wiring
5. Ensure feature parity between CLI and runtime
6. Update tests for unified wiring
7. Remove runtime builder, service factory, and CLI exemptions

**Owner:** @bioetl-composition
**Effort:** L (1-2 weeks)
**Dependencies:** None
**Deadline:** 2026-12-31
**Related Files:**
- `src/bioetl/composition/runtime_builders/`
- `src/bioetl/composition/factories/services/`
- `src/bioetl/interfaces/cli/`
- `config/governance/duplication_complexity_exemptions.yaml`

**Status:** 📋 Backlog

---

## P1 - High Systemic Debt

*These tasks create cascading issues and should be addressed after P0.*

### [P1-001] Fix Domain ↔ Infrastructure Layering Violations

**Description:**
Domain entities import infrastructure components, and infrastructure depends on domain internals. This blocks domain testing in isolation, infrastructure replacement, and safe refactoring.

**Impact:**
- Blocks: Domain testing in isolation, infrastructure replacement, domain evolution
- Dependencies: Made worse by adapter complexity (P0-001)

**Tasks:**
1. Map all Domain → Infrastructure violations
2. Map all Infrastructure → Domain violations
3. Identify circular dependencies
4. Design clean boundary interfaces
5. Refactor domain entities to remove infrastructure imports
6. Introduce anti-corruption layers where needed
7. Update tests to respect layering
8. Add architecture tests to prevent regression

**Owner:** @bioetl-architecture
**Effort:** XL (2-3 weeks)
**Dependencies:** P0-001 (Adapter complexity cleanup)
**Deadline:** 2027-03-31
**Related Files:**
- `src/bioetl/domain/`
- `src/bioetl/infrastructure/`
- `config/governance/architecture_metric_exemptions.yaml`

**Status:** 📋 Backlog

---

### [P1-002] Standardize Extractor Parsing Logic

**Description:**
Parsing logic is duplicated across multiple pipelines' extractors, causing bug propagation and maintenance overhead.

**Impact:**
- Blocks: Bug fixes, maintenance
- Current exemption: `src/bioetl/application/pipelines/*/extractors/*` (xenon)
- Dependencies: Similar patterns to adapter complexity (P0-001)

**Tasks:**
1. Identify common parsing patterns across extractors
2. Design unified parsing helper library
3. Migrate ChEMBL extractor to use helpers
4. Migrate OpenAlex extractor to use helpers
5. Migrate other extractors to use helpers
6. Update tests for unified parsing
7. Remove extractor exemption

**Owner:** @bioetl-application
**Effort:** M (3-5 days)
**Dependencies:** P0-001 (Learn from adapter refactoring)
**Deadline:** 2027-01-31
**Related Files:**
- `src/bioetl/application/pipelines/*/extractors/`
- `config/governance/duplication_complexity_exemptions.yaml`

**Status:** 📋 Backlog

---

### [P1-003] Improve Testability of Complex Components

**Description:**
Complex components (composite orchestration, adapters, runtime builders) are hard to test due to wide branching and dependency surfaces.

**Impact:**
- Blocks: Test coverage, confidence in refactoring
- Dependencies: P0-001, P0-002, P0-003

**Tasks:**
1. Add unit tests for simplified adapters (after P0-001)
2. Add integration tests for split orchestration (after P0-002)
3. Add contract tests for unified wiring (after P0-003)
4. Improve fixture reuse across tests
5. Reduce test flakiness
6. Improve test execution time

**Owner:** @bioetl-data-platform
**Effort:** L (1-2 weeks)
**Dependencies:** P0-001, P0-002, P0-003
**Deadline:** 2027-02-28
**Related Files:**
- `tests/bioetl/infrastructure/adapters/`
- `tests/bioetl/application/composite/`
- `tests/bioetl/composition/`

**Status:** 📋 Backlog

---

## P2 - Medium Independent Debt

*These tasks can be addressed in parallel with P1.*

### [P2-001] Add Observability Tracing Coverage

**Description:**
Tracing coverage has gaps in several modules, making production debugging difficult and SLO enforcement ineffective.

**Impact:**
- Blocks: Production debugging, SLO monitoring
- Current exemption: `src/bioetl/infrastructure/observability/` (xenon + critical_check)

**Tasks:**
1. Identify modules with missing tracing
2. Add span instrumentation to key paths
3. Normalize label naming to avoid high cardinality
4. Align metric declarations with actual usage
5. Update observability configs
6. Remove observability exemption

**Owner:** @bioetl-observability
**Effort:** M (3-5 days)
**Dependencies:** None
**Deadline:** 2027-01-31
**Related Files:**
- `src/bioetl/infrastructure/observability/`
- `config/observability_metric_declarations.yaml`
- `config/observability_metric_governance.yaml`
- `config/governance/duplication_complexity_exemptions.yaml`

**Status:** 📋 Backlog

---

### [P2-002] Simplify DQ Analyzer Validation Rules

**Description:**
Data quality analyzer has complex validation rule bundles that are hard to maintain.

**Impact:**
- Blocks: DQ rule maintenance
- Current exemption: `src/bioetl/application/services/dq/` (xenon + critical_check)

**Tasks:**
1. Analyze validation rule patterns
2. Extract common rule templates
3. Simplify rule composition
4. Improve rule testability
5. Update DQ documentation
6. Remove DQ exemption

**Owner:** @bioetl-dq
**Effort:** S (1-2 days)
**Dependencies:** None
**Deadline:** 2027-01-31
**Related Files:**
- `src/bioetl/application/services/dq/`
- `config/governance/duplication_complexity_exemptions.yaml`

**Status:** 📋 Backlog

---

### [P2-003] Simplify Silver Storage Write Path

**Description:**
Silver storage write path has complex coercion logic affecting performance.

**Impact:**
- Blocks: Storage performance improvements
- Current exemption: `src/bioetl/infrastructure/storage/silver/` (xenon + critical_check)

**Tasks:**
1. Analyze write path coercion logic
2. Extract common coercion helpers
3. Simplify branching in write path
4. Add performance benchmarks
5. Remove storage exemption

**Owner:** @bioetl-storage
**Effort:** S (1-2 days)
**Dependencies:** None
**Deadline:** 2027-01-31
**Related Files:**
- `src/bioetl/infrastructure/storage/silver/`
- `config/governance/duplication_complexity_exemptions.yaml`

**Status:** 📋 Backlog

---

### [P2-004] Simplify Control Plane Artifact Orchestration

**Description:**
Control plane has complex artifact orchestration logic.

**Impact:**
- Blocks: Artifact management improvements
- Current exemption: `src/bioetl/infrastructure/control_plane/` (xenon + critical_check)

**Tasks:**
1. Analyze artifact orchestration patterns
2. Extract common orchestration helpers
3. Simplify artifact lifecycle management
4. Improve error handling
5. Remove control plane exemption

**Owner:** @bioetl-control-plane
**Effort:** S (1-2 days)
**Dependencies:** None
**Deadline:** 2027-01-31
**Related Files:**
- `src/bioetl/infrastructure/control_plane/`
- `config/governance/duplication_complexity_exemptions.yaml`

**Status:** 📋 Backlog

---

### [P2-005] Simplify Quarantine Normalization

**Description:**
Quarantine has complex normalization branches.

**Impact:**
- Blocks: Quarantine processing improvements
- Current exemption: `src/bioetl/infrastructure/quarantine/` (xenon + critical_check)

**Tasks:**
1. Analyze normalization branching patterns
2. Extract common normalization helpers
3. Simplify quarantine processing
4. Add integration tests
5. Remove quarantine exemption

**Owner:** @bioetl-quarantine
**Effort:** S (1-2 days)
**Dependencies:** None
**Deadline:** 2027-01-31
**Related Files:**
- `src/bioetl/infrastructure/quarantine/`
- `config/governance/duplication_complexity_exemptions.yaml`

**Status:** 📋 Backlog

---

## P3 - Low Priority Debt

*These tasks are nice-to-have and can be deferred.*

### [P3-001] Update Documentation for Refactored Code

**Description:**
After completing P0-P2 tasks, update all affected documentation to reflect changes.

**Impact:**
- Improves: Developer onboarding, code understanding
- Dependencies: All P0-P2 tasks

**Tasks:**
1. Update architecture docs for layering changes
2. Update adapter documentation for new patterns
3. Update composite orchestration docs
4. Update CLI documentation for unified wiring
5. Update testing guidelines
6. Update observability documentation

**Owner:** @bioetl-docs
**Effort:** M (3-5 days)
**Dependencies:** All P0-P2 tasks
**Deadline:** 2027-06-30
**Related Files:**
- `docs/02-architecture/`
- `docs/03-providers/`
- `docs/04-contracts/`

**Status:** 📋 Backlog

---

### [P3-002] Improve Developer Tooling for Debt Tracking

**Description:**
Enhance tooling to track technical debt reduction progress automatically.

**Impact:**
- Improves: Debt visibility, progress tracking
- Dependencies: None

**Tasks:**
1. Enhance `generate_architecture_debt_tasks.py` script
2. Add automated debt trend reporting
3. Integrate with weekly debt reporting
4. Add dashboard for debt metrics
5. Create debt reduction alerts

**Owner:** @bioetl-tooling
**Effort:** M (3-5 days)
**Dependencies:** None
**Deadline:** 2027-03-31
**Related Files:**
- `scripts/engineering/qa/generate_architecture_debt_tasks.py`
- `config/governance/debt_scorecard.yaml`

**Status:** 📋 Backlog

---

### [P3-003] Review and Optimize Import Structure

**Description:**
After layering cleanup (P1-001), review and optimize import structure across the codebase.

**Impact:**
- Improves: Build time, dependency clarity
- Dependencies: P1-001

**Tasks:**
1. Run import linter across codebase
2. Identify circular imports
3. Optimize import statements
4. Update import linting rules
5. Add pre-commit hooks for import hygiene

**Owner:** @bioetl-tooling
**Effort:** S (1-2 days)
**Dependencies:** P1-001
**Deadline:** 2027-04-30
**Related Files:**
- `.ruff.toml`
- `pyproject.toml`

**Status:** 📋 Backlog

---

## Summary Statistics

### By Priority

| Priority | Count | Total Effort |
|----------|-------|--------------|
| P0 (Critical) | 3 | 3-6 weeks |
| P1 (High) | 3 | 3-6 weeks |
| P2 (Medium) | 5 | 1-2 weeks |
| P3 (Low) | 3 | 1-2 weeks |
| **Total** | **14** | **8-16 weeks** |

### By Owner

| Owner | Tasks | Total Effort |
|-------|-------|--------------|
| @bioetl-platform | 1 | 1-2 weeks |
| @bioetl-composite | 1 | 1-2 weeks |
| @bioetl-composition | 1 | 1-2 weeks |
| @bioetl-architecture | 1 | 2-3 weeks |
| @bioetl-application | 1 | 3-5 days |
| @bioetl-data-platform | 1 | 1-2 weeks |
| @bioetl-observability | 1 | 3-5 days |
| @bioetl-dq | 1 | 1-2 days |
| @bioetl-storage | 1 | 1-2 days |
| @bioetl-control-plane | 1 | 1-2 days |
| @bioetl-quarantine | 1 | 1-2 days |
| @bioetl-docs | 1 | 3-5 days |
| @bioetl-tooling | 2 | 4-7 days |

### Exemption Removal Targets

| Category | Current Count | Target | Tasks |
|----------|---------------|--------|-------|
| Path Exemptions | 23 | 0 | P0-001 (7), P0-002 (1), P0-003 (3), P1-002 (1), P2-001 (1), P2-002 (1), P2-003 (1), P2-004 (1), P2-005 (1) |
| Function Exemptions | 5 | 0 | P0-001 (5) |

## Recommended Execution Order

### Phase 1 (Months 1-2): Foundation Cleanup
- P0-001: Extract Adapter Fallback Logic
- P0-002: Simplify Composite Orchestration
- P0-003: Unify Runtime Builder and CLI Wiring

### Phase 2 (Months 3-4): Systemic Fixes
- P1-001: Fix Layering Violations (depends on P0-001)
- P1-002: Standardize Extractor Parsing (depends on P0-001)
- P1-003: Improve Testability (depends on P0-001, P0-002, P0-003)

### Phase 3 (Months 5-6): Independent Improvements
- P2-001: Add Observability Tracing
- P2-002: Simplify DQ Analyzer
- P2-003: Simplify Silver Storage
- P2-004: Simplify Control Plane
- P2-005: Simplify Quarantine

### Phase 4 (Months 7-9): Documentation & Tooling
- P3-001: Update Documentation
- P3-002: Improve Developer Tooling
- P3-003: Review and Optimize Imports

## Governance Integration

- All tasks must respect `debt_scorecard.yaml` policies
- Exemptions must be removed before expiration dates
- Weekly debt reporting must track progress
- CI gates must not be weakened
- Architecture tests must be added after refactoring

## Next Steps

1. Review and approve this backlog with @bioetl-architecture
2. Assign P0 tasks to respective owners
3. Create detailed implementation plans for P0 tasks
4. Set up tracking in project management system
5. Begin Phase 1 execution
