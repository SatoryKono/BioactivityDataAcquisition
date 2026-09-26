# Documentation Audit Issues - 2026-04-23

## P0 Issues (Critical - Contract & Runtime Semantics Drift)

### Issue #1: Sync DQ Contracts Documentation with Active Config DSL
**Priority**: P0
**Component**: docs/04-reference/contracts/dq-contracts.md
**Problem**: 
- Documentation describes outdated `quality.content`/`quality.consistency` structure
- Active entity configs use `entity_field_validations`, `entity_cross_field_validations`, `entity_conditional_validations`, `key_nullability`
- DQ audit, config review, and contract-driven validation rely on incorrect model

**Impact**: 
- DQ governance based on wrong documentation
- Contract validation failures due to DSL mismatch
- Audit and replay processes use incorrect reference

**Solution**:
1. Update dq-contracts.md to reflect current quality.* DSL structure
2. Add cross-references to actual config sections
3. Create architecture tests for DQ parity
4. Link to DQ validation tooling

**Acceptance Criteria**:
- dq-contracts.md accurately describes active config DSL
- All quality validation sections documented
- Architecture tests pass for DQ parity
- Cross-links to configs and validation code established

---

### Issue #2: Sync Control-Plane Documentation Pack with Runtime Settings
**Priority**: P0  
**Component**: docs/04-reference/contracts/run-manifest-ledger.md, docs/05-operations/runbooks/run-manifest-inspection.md, docs/04-reference/cli.md
**Problem**:
- Control-plane docs don't reflect `legacy_observe` in checkpoint_compatibility_policy
- Runtime model supports it but documentation doesn't
- Affects resume/replay semantics interpretation

**Impact**:
- Incorrect operator interpretation of resume/replay semantics
- Potential replay failures due to undocumented compatibility modes
- Audit trails may be misinterpreted

**Solution**:
1. Update run-manifest-ledger.md with full checkpoint_compatibility_policy enum
2. Explicitly document legacy_observe mode
3. Update CLI reference with missing flags
4. Update runbook with correct semantics
5. Atomic documentation pack update (contract + CLI + runbook)

**Acceptance Criteria**:
- All checkpoint_compatibility_policy values documented
- CLI reference includes all relevant flags
- Runbook reflects actual runtime behavior
- Cross-references between contract, CLI, and runbook consistent

---

### Issue #3: Refresh ADR-026 Composite Pipeline Pattern
**Priority**: P0
**Component**: docs/02-architecture/decisions/ADR-026-composite-pipeline-pattern.md
**Problem**:
- ADR states CrossRef is required enricher for composite_publication
- Active config (configs/composites/publication.yaml) has required: false
- Contains outdated implementation details
- No longer reflects operational contract

**Impact**:
- Composite execution docs unreliable for current behavior
- Architectural decision record contradicts actual config
- Engineering changes based on wrong assumptions

**Solution**:
1. Either refresh ADR-026 to current composite semantics
2. Or mark operational sections as superseded
3. Explicitly document decision boundary changes
4. Update cross-references to current configs

**Acceptance Criteria**:
- ADR-026 accurately reflects current composite execution
- Or clearly marked as superseded with pointers to current docs
- Config references updated
- No contradictions between ADR and active configs

---

## P1 Issues (High - Engineering Efficiency)

### Issue #4: Add CLI Documentation Parity Checks
**Priority**: P1
**Component**: docs/04-reference/cli.md
**Problem**:
- Published CLI reference covers 12 top-level groups
- Actual CLI registers 16 groups
- Missing: debug, diagnostics, lineage, dq
- run command missing --tracing switch
- Manual updates lead to persistent drift

**Impact**:
- Poor onboarding experience
- Operators missing critical CLI features
- Self-service triage hindered
- Documentation not trusted as reference

**Solution**:
1. Generate CLI reference from actual command registry
2. Or add architecture/QA check comparing published vs actual
3. Compare _LAZY_COMMAND_SPECS with docs table
4. Add validation for run command options
5. Automate or verify CLI documentation

**Acceptance Criteria**:
- CLI docs cover all registered top-level commands
- All options for run/run-composite documented
- Parity check script exists and passes
- Documentation generation/verification automated

---

### Issue #5: Repair Project Navigator Source-Code Map and ADR Status
**Priority**: P1
**Component**: docs/00-project/00-map.md
**Problem**:
- Source-code map outdated (wrong package topology)
- Document internally contradictory on ADR set status
- Claims ADR-001..043 but references ADR-044/045
- Main entrypoint no longer trusted

**Impact**:
- Main navigator entrypoint unreliable
- Developers waste time on wrong paths
- Architecture references may point to wrong locations
- Undermines confidence in entire documentation system

**Solution**:
1. Update source-code map to current package layout
2. Fix Document Status block inconsistencies
3. Add explicit cross-links: ADR ↔ implementation ↔ config ↔ runbook/CLI
4. Verify all control-plane, DQ, composite execution references
5. Machine-reliable consistency for critical paths

**Acceptance Criteria**:
- Source-code map matches current package structure
- ADR status table accurate and consistent
- All critical cross-links verified
- Navigator trusted as primary entrypoint

---

### Issue #6: Define Canonical Navigation Rule for Pipeline Documentation
**Priority**: P1
**Component**: docs/04-reference/pipelines/README.md, pipeline pages, provider pages, configs
**Problem**:
- Three-layer pipeline surface: pipeline page + provider page + unified config
- Hybrid model creates ambiguity
- Some pages are historical stubs (e.g., openalex/01-publication-spec.md)
- Canonical entrypoint depends on pipeline family

**Impact**:
- Knowledge fragmentation
- Developers unsure which is source of truth
- Inconsistent documentation quality
- Maintenance overhead

**Solution**:
1. Define single canonical rule:
   - Either: provider page + config = source of truth, pipeline page = thin router
   - Or: pipeline page = primary surface, provider page reduced
2. Formalize policy in documentation governance
3. Apply consistently across all pipelines
4. Update navigation accordingly

**Acceptance Criteria**:
- Single canonical navigation rule defined and documented
- All pipeline documentation follows same pattern
- No ambiguity about source of truth
- Navigation consistent and predictable

---

### Issue #7: Fix Naming Drift in Pipeline/Config Documentation
**Priority**: P1
**Component**: docs/04-reference/pipelines/README.md, composite configs
**Problem**:
- Documentation states composite.merge.column-groups
- Active config uses column_groups
- Leads to configuration errors
- Breaks config reading/modification

**Impact**:
- Configuration errors during setup
- Maintenance difficulties
- Documentation not matching actual usage
- Time wasted on troubleshooting

**Solution**:
1. Audit all pipeline/config documentation for naming inconsistencies
2. Fix column-groups → column_groups
3. Add naming consistency checks
4. Update templates and examples

**Acceptance Criteria**:
- All naming consistent between docs and configs
- No naming drift in critical config keys
- Examples match actual usage
- Naming consistency verified

---

## P2 Issues (Medium - Technical Debt)

### Issue #8: Remove Historical Schema Pages from Active Navigation
**Priority**: P2
**Component**: docs/04-reference/schemas/domain/chembl/activity-schema.md and similar
**Problem**:
- Historical deep schema pages in active reference surface
- Navigator still references them as schema documents
- Creates ambiguity between active and historical
- Main entrypoint includes outdated materials

**Impact**:
- Confusion between current and historical reference
- Developers may use wrong schema information
- Maintenance burden
- Documentation quality degraded

**Solution**:
1. Move historical schema pages out of active navigator routes
2. Add strict nav-banners to historical pages
3. Exclude from main navigator routing
4. Or remove entirely if no longer needed

**Acceptance Criteria**:
- No historical schema pages in active navigation
- Clear distinction between current and historical
- Navigator routes only to active reference
- Historical materials properly labeled

---

## Implementation Roadmap

### Immediate Phase (P0 Issues)
1. **Sync DQ contracts with active config DSL** - Fix contract documentation
2. **Sync control-plane pack** - Update checkpoint compatibility documentation
3. **Refresh ADR-026** - Align composite pipeline documentation with reality

### Near-Term Phase (P1 Issues)  
4. **Add CLI parity checks** - Automate CLI documentation verification
5. **Repair project navigator** - Fix main entrypoint reliability
6. **Define canonical navigation rule** - Standardize pipeline documentation
7. **Fix naming drift** - Eliminate config key inconsistencies

### Next Phase (P2 Issues)
8. **Remove historical schema pages** - Clean up reference surface

### Stabilization Phase
- Add CI/QA checks for documentation parity
- Prevent regression of drift issues
- Automate verification where possible

### Maintenance Phase
- Add invariant-led appendices for critical components
- Improve operational documentation cross-references
- Enhance audit and replay documentation

## Risk Assessment

- **P0 Issues**: Low risk (mostly docs-only), high impact if not fixed
- **P1 Issues**: Low risk, medium impact on engineering efficiency
- **P2 Issues**: Medium risk (nav changes), low immediate impact
- **Automation**: Medium risk (new scripts/tests), high long-term benefit

## Success Metrics

- ✅ All P0 issues resolved (contract accuracy)
- ✅ Navigation consistency restored
- ✅ CLI documentation complete and verified
- ✅ No naming drift between docs and configs
- ✅ Historical materials properly separated
- ✅ Automation prevents regression

## Implementation Plans

Detailed implementation plans for each issue are available in:
- **`docs/reports/audit-issues/implementation-plans.md`** - Comprehensive step-by-step plans with timelines, resources, and success criteria

### Plan Highlights

**Issue #1 (DQ Contracts Sync)**: 5-7 days, 3 phases (Research → Documentation → Validation)
**Issue #2 (Control-Plane Update)**: 3-5 days, atomic documentation pack update
**Issue #3 (ADR-026 Refresh)**: 2-3 days, architecture team review required
**Issue #4 (CLI Parity)**: 3-5 days, includes automation script development
**Issue #5 (Navigator Repair)**: 3-4 days, source-code map and ADR status fixes
**Issue #6 (Navigation Rules)**: 2-3 days, policy definition and standardization
**Issue #7 (Naming Drift)**: 1-2 days, comprehensive audit and automation
**Issue #8 (Historical Cleanup)**: 2-3 days, content migration and verification

## Related Materials

- Full audit report: `docs/reports/2026-04-23-documentation-audit.md`
- Implementation plans: `docs/reports/audit-issues/implementation-plans.md`
- Current documentation: `docs/00-project/00-map.md`
- Architecture decisions: `docs/02-architecture/decisions/`
- Contract documentation: `docs/04-reference/contracts/`