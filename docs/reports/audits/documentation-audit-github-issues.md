# 📋 GitHub Issues for Documentation Audit Remediation

## 🎯 Issue Creation Guide

This document contains pre-formatted GitHub issues for all P0-P2 documentation problems identified in the BioETL documentation audit. Each issue includes:
- Clear title with priority and category
- Detailed description with evidence
- Impact assessment
- Proposed solution
- Acceptance criteria

## 🔴 P0 Issues (Critical - Must Fix Immediately)

### Issue #1: Control-Plane Documentation Drift - Missing legacy_observe Policy

**Title**: `[P0][Docs][Drift] Control-Plane Documentation Drift: Missing legacy_observe Policy in Published Contracts`

**Body**:
```markdown
## Problem

The published control-plane documentation (run-manifest-ledger.md, cli.md, run-manifest-inspection.md) only lists `observe`, `soft_fail`, and `hard_fail` as valid values for `checkpoint_compatibility_policy`, but the runtime code in `src/bioetl/infrastructure/config/_base.py` also supports `legacy_observe`.

## Impact

**Critical Impact**: This drift directly affects determinism, idempotency, and replay semantics. The documentation describes an incomplete runtime contract, which breaks the fail-closed principle for audit-safe operations.

## Evidence

- **Code**: `src/bioetl/infrastructure/config/_base.py` - supports `legacy_observe`
- **Docs**: `docs/04-reference/contracts/run-manifest-ledger.md` - missing `legacy_observe`
- **CLI**: `docs/04-reference/cli.md` - missing `legacy_observe`
- **Runbook**: `docs/05-operations/runbooks/run-manifest-inspection.md` - missing `legacy_observe`

## Solution

1. Update `docs/04-reference/contracts/run-manifest-ledger.md` to include `legacy_observe`
2. Update `docs/04-reference/cli.md` to include `legacy_observe`
3. Update `docs/05-operations/runbooks/run-manifest-inspection.md` to include `legacy_observe`
4. Add documentation for:
   - Area of application for `legacy_observe`
   - Difference from `observe`
   - Connection with compatibility transitions
   - Operator interpretation guidelines

## Acceptance Criteria

- [ ] All control-plane documentation includes `legacy_observe` policy
- [ ] Documentation explains when to use `legacy_observe` vs `observe`
- [ ] Added test/assertion for doc parity with code
- [ ] No breaking changes to existing functionality

## Priority

**P0 - Critical**: This affects core replay/resume semantics and must be fixed immediately.
```

**Labels**: `documentation`, `critical`, `control-plane`, `replay-semantics`, `P0`

---

## 🟠 P1 Issues (High Priority - Must Fix)

### Issue #2: Missing DQ Contract Surface in Contracts Registry

**Title**: `[P1][Docs][Completeness] Missing DQ Contract Surface in Published Contracts Registry`

**Body**:
```markdown
## Problem

The Contracts Registry (`docs/04-reference/contracts/README.md`) and Reference Index publish Gold contracts and control-plane contracts, but DQ contracts are not exposed as a registry-grade contract surface. DQ knowledge is fragmented across ADR-045, guide, and component doc, with the component doc being partially outdated.

## Impact

**High Impact**: Reduces auditability of DQ posture and prevents engineers from having a single entrypoint for DQ contracts. This violates the principle that all contract families in scope should have published contract surfaces.

## Evidence

- **Registry**: `docs/04-reference/contracts/README.md` - no DQ contract entry
- **Index**: `docs/04-reference/index.md` - no DQ contract entry
- **ADR-045**: Exists but not linked as contract surface
- **Component Doc**: `docs/04-reference/components/dq-contract-system.md` - partially outdated

## Solution

1. Create `docs/04-reference/contracts/dq-contracts.md` as canonical DQ contract surface
2. Add DQ contract entry to `docs/04-reference/contracts/README.md`
3. Add DQ contract entry to `docs/04-reference/index.md`
4. Update ADR-045 and DQ guide to reference the new contract surface
5. Make ADR-045 and guides supporting surfaces, not surrogate contracts

## Acceptance Criteria

- [ ] DQ contract surface created and published
- [ ] Contracts Registry updated with DQ entry
- [ ] Reference Index updated with DQ entry
- [ ] ADR-045 updated to reference new contract surface
- [ ] All cross-references validated

## Priority

**P1 - High**: Required for DQ audit readiness and contract consistency.
```

**Labels**: `documentation`, `high-priority`, `DQ`, `contracts`, `P1`

---

### Issue #3: Stale DQ Component Documentation with Unverified API References

**Title**: `[P1][Docs][Maintainability] Stale DQ Component Documentation with Unverified Service Seams`

**Body**:
```markdown
## Problem

`docs/04-reference/components/dq-contract-system.md` contains code examples and service seams (DQPolicyResolver, EffectiveConfigService, PhasedMigrationSupportService, create_composite_validation_service, CompositeValidationConfig) that are not confirmed by repository search. The document creates false expectations about API and architecture.

## Impact

**High Impact**: Engineers may rely on non-existent APIs, leading to implementation errors and wasted development time. False documentation is worse than no documentation.

## Evidence

- **Document**: `docs/04-reference/components/dq-contract-system.md`
- **Search Results**: Repository search returns only the document itself, not code implementations
- **Unverified Services**: DQPolicyResolver, EffectiveConfigService, PhasedMigrationSupportService, etc.

## Solution

**Option A (Recommended)**: Rewrite the document to reflect current state
1. Remove unverified service seams and pseudo-API examples
2. Document only confirmed current-state implementation
3. Add clear disclaimers about what is implemented vs planned

**Option B**: Deprecate the document
1. Replace with short stub linking to ADR-045, DQ guide, and new DQ contract
2. Add deprecation notice
3. Remove from navigation

## Acceptance Criteria

- [ ] Document either rewritten to current state or deprecated
- [ ] No unverified API references remain
- [ ] Clear distinction between implemented and planned features
- [ ] Cross-references to ADR-045 and DQ guide added

## Priority

**P1 - High**: False API documentation creates significant engineering risk.
```

**Labels**: `documentation`, `high-priority`, `DQ`, `API`, `stale`, `P1`

---

### Issue #4: Naming Drift - document vs publication Terminology

**Title**: `[P1][Docs][Terminology] Naming Drift: document vs publication Terminology Conflict`

**Body**:
```markdown
## Problem

API reference (`docs/04-reference/api/application.md`) uses legacy entity names like "Document", "Document Similarity", "Document Term", while the configuration guide (`docs/03-guides/pipeline-configuration.md`) fixes "publication*" as canonical naming. This creates terminology conflicts and violates naming policy.

## Impact

**High Impact**: Terminology conflicts make documentation harder to search, create cross-reference issues, and confuse new developers during onboarding.

## Evidence

- **API Docs**: `docs/04-reference/api/application.md` - uses "Document" terminology
- **Config Guide**: `docs/03-guides/pipeline-configuration.md` - uses "publication" terminology
- **Glossary**: Should be consistent with configuration guide

## Solution

1. Update `docs/04-reference/api/application.md` to use "publication" terminology
2. Update related API pages for consistency
3. Ensure all cross-references use canonical naming
4. Add glossary consistency check to CI/CD

## Acceptance Criteria

- [ ] All API documentation uses "publication" terminology
- [ ] No "Document" references remain in API docs
- [ ] Cross-references validated
- [ ] Glossary consistency enforced

## Priority

**P1 - High**: Terminology consistency is critical for documentation quality.
```

**Labels**: `documentation`, `high-priority`, `terminology`, `naming`, `P1`

---

### Issue #5: Fragmented Pipeline Reference Surface

**Title**: `[P1][Docs][Navigation] Fragmented Pipeline Reference Surface - Mixed Active/Historical Content`

**Body**:
```markdown
## Problem

`docs/04-reference/pipelines/README.md` mixes "deep current specs", "historical deep specs", and "compact compatibility stubs" on the same navigation surface. Readers cannot instantly determine which pages represent current norms vs historical context.

## Impact

**High Impact**: Degrades documentation usability and makes it difficult for engineers to find authoritative current information quickly.

## Evidence

- **Pipeline Index**: `docs/04-reference/pipelines/README.md` - admits mixing current/historical content
- **User Experience**: No clear visual distinction between active and historical pages

## Solution

1. Separate navigation into three distinct sections:
   - **Current Canonical Artifacts** (top section)
   - **Historical Deep Specs** (collapsible section)
   - **Compatibility Stubs** (bottom section)
2. Add clear visual indicators for each category
3. Ensure active index leads to current canonical artifact first
4. Move historical context to secondary navigation

## Acceptance Criteria

- [ ] Pipeline navigation clearly separated by category
- [ ] Current canonical artifacts prominently featured
- [ ] Historical content moved to secondary navigation
- [ ] Visual indicators added for each category

## Priority

**P1 - High**: Navigation fragmentation significantly impacts documentation usability.
```

**Labels**: `documentation`, `high-priority`, `navigation`, `UX`, `P1`

---

## 🟡 P2 Issues (Medium Priority - Should Fix)

### Issue #6: ADR-042 Incomplete References

**Title**: `[P2][Docs][Maintainability] ADR-042 Incomplete References - Broken Verification Chain`

**Body**:
```markdown
## Problem

ADR-042 (`docs/02-architecture/decisions/ADR-042-testing-strategy-matrix.md`) contained a placeholder reference token in the References section, breaking the navigability and verification chain for this important testing strategy document.

## Impact

**Medium Impact**: Broken references reduce traceability and make it difficult to verify ADR implementation. Testing strategy is high-visibility for users.

## Evidence

- **ADR-042**: Contains placeholder reference token in References section
- **User Impact**: Cannot trace ADR to implementation/test/workflow

## Solution

1. Replace the placeholder reference token with actual links to:
   - Implementation code
   - Test files
   - CI/CD workflows
   - Related documentation
2. Add direct links where ADR claims current adoption
3. Validate all references

## Acceptance Criteria

- [ ] All placeholders replaced with valid links
- [ ] References section complete and validated
- [ ] Verification chain restored
- [ ] Cross-references to tests/workflows added

## Priority

**P2 - Medium**: Important for traceability but not blocking core functionality.
```

**Labels**: `documentation`, `medium-priority`, `ADR`, `testing`, `P2`

---

### Issue #7: API Reference Partially Navigational

**Title**: `[P2][Docs][Structure] API Reference Partially Navigational - Not Strict Contract Surface`

**Body**:
```markdown
## Problem

The API reference section (`docs/04-reference/api/`) is intentionally minimized and serves as a nav/facade description rather than a strict published contract surface. This reduces its suitability for package-level audit and precise onboarding.

## Impact

**Medium Impact**: Experienced maintainers can work with this, but audit/readiness and onboarding suffer from lack of strict package seams documentation.

## Evidence

- **API Index**: `docs/04-reference/api/index.md` - admits being navigational
- **Layer Pages**: Some API pages are placeholders rather than complete contract surfaces

## Solution

1. Formalize sanctioned public seam concept for package-level surfaces
2. Create strict package-root pages for:
   - Domain layer
   - Application layer
   - Composition layer
   - Interfaces layer
3. Each package-root page should include:
   - Package-root exports
   - Non-root sanctioned imports
   - Unstable/internal modules
   - Owner path information

## Acceptance Criteria

- [ ] Package-root API pages created for all layers
- [ ] Sanctioned public seams clearly documented
- [ ] Unstable/internal modules marked appropriately
- [ ] Owner information added

## Priority

**P2 - Medium**: Improves onboarding and audit without requiring architectural changes.
```

**Labels**: `documentation`, `medium-priority`, `API`, `structure`, `P2`

---

## 📋 Remediation Plan Issues

### Issue #8: Control-Plane Documentation Sync

**Title**: `[Plan][Docs] Control-Plane Documentation Sync - Phase 1 Implementation`

**Body**:
```markdown
## Objective

Synchronize control-plane documentation with runtime code to eliminate P0 drift.

## Tasks

1. **Update run-manifest-ledger.md**:
   - Add `legacy_observe` to checkpoint_compatibility_policy values
   - Document when to use `legacy_observe` vs `observe`
   - Explain compatibility transitions
   - Add operator interpretation guidelines

2. **Update cli.md**:
   - Add `legacy_observe` to CLI reference
   - Ensure consistency with contract documentation
   - Add usage examples

3. **Update run-manifest-inspection.md**:
   - Add `legacy_observe` to runbook
   - Document operational implications
   - Add troubleshooting guidance

4. **Update diagnostics/observability docs**:
   - Ensure consistency with control-plane changes
   - Add monitoring guidance for `legacy_observe`

5. **Add doc parity test**:
   - Create test to verify doc-code parity
   - Integrate with CI/CD
   - Prevent future drift

## Success Criteria

- [ ] All control-plane docs synchronized with code
- [ ] Doc parity test implemented and passing
- [ ] No breaking changes introduced
- [ ] P0 issue resolved

## Timeline

**Estimated**: 1 week
**Priority**: Critical (blocks other documentation work)
```

**Labels**: `documentation`, `plan`, `control-plane`, `sync`, `P0-fix`

---

### Issue #9: DQ Contract Publication

**Title**: `[Plan][Docs] DQ Contract Publication - Phase 2 Implementation`

**Body**:
```markdown
## Objective

Publish DQ contracts as registry-grade contract surface to resolve P1 completeness issue.

## Tasks

1. **Create DQ contract surface**:
   - Create `docs/04-reference/contracts/dq-contracts.md`
   - Document all DQ contract families
   - Include schema definitions and validation rules
   - Add usage examples

2. **Update Contracts Registry**:
   - Add DQ entry to `docs/04-reference/contracts/README.md`
   - Ensure consistent format with other contracts
   - Add cross-references

3. **Update Reference Index**:
   - Add DQ contract entry to `docs/04-reference/index.md`
   - Ensure proper categorization
   - Add navigation links

4. **Update Supporting Documents**:
   - Modify ADR-045 to reference new contract surface
   - Update DQ guide to use new contract as primary source
   - Ensure component doc references new contract

5. **Add validation**:
   - Create test for DQ contract completeness
   - Integrate with CI/CD

## Success Criteria

- [ ] DQ contract surface created and published
- [ ] Contracts Registry updated
- [ ] Reference Index updated
- [ ] All supporting documents updated
- [ ] P1 issue resolved

## Timeline

**Estimated**: 2 weeks
**Priority**: High (required for DQ audit readiness)
```

**Labels**: `documentation`, `plan`, `DQ`, `contracts`, `P1-fix`

---

### Issue #10: DQ Component Documentation Cleanup

**Title**: `[Plan][Docs] DQ Component Documentation Cleanup - Phase 3 Implementation`

**Body**:
```markdown
## Objective

Clean up stale DQ component documentation to resolve P1 maintainability issue.

## Tasks

1. **Assess current state**:
   - Verify which services/APIs are actually implemented
   - Identify unverified references
   - Consult with DQ team on current architecture

2. **Option A - Rewrite (Recommended)**:
   - Remove unverified service seams
   - Document only confirmed current-state implementation
   - Add clear disclaimers about implemented vs planned features
   - Structure as current-state reference

3. **Option B - Deprecate**:
   - Replace with short stub
   - Link to ADR-045, DQ guide, and new DQ contract
   - Add deprecation notice
   - Remove from primary navigation

4. **Update cross-references**:
   - Ensure all links point to accurate documentation
   - Remove references to deprecated content
   - Add redirects if needed

5. **Add validation**:
   - Create test to verify no unverified API references
   - Integrate with CI/CD

## Success Criteria

- [ ] Document either rewritten or deprecated
- [ ] No unverified API references remain
- [ ] Clear distinction between implemented and planned
- [ ] Cross-references validated
- [ ] P1 issue resolved

## Timeline

**Estimated**: 1 week
**Priority**: High (prevents engineering confusion)
```

**Labels**: `documentation`, `plan`, `DQ`, `cleanup`, `P1-fix`

---

### Issue #11: Terminology and Navigation Cleanup

**Title**: `[Plan][Docs] Terminology and Navigation Cleanup - Phase 4 Implementation`

**Body**:
```markdown
## Objective

Fix terminology drift and improve navigation to resolve P1 usability issues.

## Tasks

1. **Terminology cleanup**:
   - Update `docs/04-reference/api/application.md` to use "publication" terminology
   - Update all related API pages
   - Ensure consistency with configuration guide
   - Add glossary consistency check to CI/CD

2. **Pipeline navigation restructuring**:
   - Separate current canonical artifacts (top section)
   - Move historical deep specs to collapsible section
   - Move compatibility stubs to bottom section
   - Add clear visual indicators for each category

3. **ADR-042 reference fix**:
   - Replace placeholder reference token with actual links
   - Add links to implementation, tests, and workflows
   - Validate all references

4. **Add navigation tests**:
   - Create tests for navigation consistency
   - Verify no broken links in navigation
   - Integrate with CI/CD

## Success Criteria

- [ ] All terminology consistent
- [ ] Pipeline navigation clearly organized
- [ ] ADR-042 references complete
- [ ] Navigation tests implemented
- [ ] P1 issues resolved

## Timeline

**Estimated**: 1 week
**Priority**: High (improves documentation usability)
```

**Labels**: `documentation`, `plan`, `terminology`, `navigation`, `P1-fix`

---

### Issue #12: API Surface Hardening

**Title**: `[Plan][Docs] API Surface Hardening - Phase 5 Implementation`

**Body**:
```markdown
## Objective

Formalize sanctioned public seams for package-level surfaces to improve maintainability.

## Tasks

1. **Define package-root API structure**:
   - Create template for package-root API pages
   - Define what constitutes sanctioned public seam
   - Establish documentation standards

2. **Create package-root pages**:
   - Domain layer: `docs/04-reference/api/domain.md`
   - Application layer: `docs/04-reference/api/application.md` (enhanced)
   - Composition layer: `docs/04-reference/api/composition.md`
   - Interfaces layer: `docs/04-reference/api/interfaces.md`

3. **Document each package-root**:
   - Package-root exports
   - Non-root sanctioned imports
   - Unstable/internal modules
   - Owner path information

4. **Add validation gates**:
   - Create doc parity tests for API surfaces
   - Integrate with CI/CD
   - Prevent future drift

5. **Update navigation**:
   - Ensure API index leads to package-root pages
   - Add clear hierarchy
   - Improve cross-references

## Success Criteria

- [ ] Package-root API pages created for all layers
- [ ] Sanctioned public seams clearly documented
- [ ] Validation gates implemented
- [ ] Navigation improved
- [ ] P2 issues resolved

## Timeline

**Estimated**: 2 weeks
**Priority**: Medium (improves long-term maintainability)
```

**Labels**: `documentation`, `plan`, `API`, `structure`, `P2-fix`

---

## 🎯 Implementation Roadmap

### Phase 1: Critical Fixes (Week 1-2)
- **Issue #1**: Control-Plane Documentation Drift (P0)
- **Issue #8**: Control-Plane Documentation Sync
- **Goal**: Resolve all P0 issues, restore contract accuracy

### Phase 2: High-Priority Fixes (Week 3-4)
- **Issue #2**: Missing DQ Contract Surface (P1)
- **Issue #9**: DQ Contract Publication
- **Issue #3**: Stale DQ Component Documentation (P1)
- **Issue #10**: DQ Component Documentation Cleanup
- **Goal**: Resolve all P1 issues, improve DQ documentation

### Phase 3: Navigation and Terminology (Week 5)
- **Issue #4**: Naming Drift (P1)
- **Issue #5**: Fragmented Pipeline Navigation (P1)
- **Issue #11**: Terminology and Navigation Cleanup
- **Goal**: Resolve remaining P1 issues, improve usability

### Phase 4: Quality Improvements (Week 6-7)
- **Issue #6**: ADR-042 Incomplete References (P2)
- **Issue #7**: API Reference Partially Navigational (P2)
- **Issue #12**: API Surface Hardening
- **Goal**: Resolve all P2 issues, improve documentation quality

## 📊 Expected Outcomes

### After Phase 1:
- ✅ All P0 issues resolved
- ✅ Control-plane documentation accurate
- ✅ Replay/resume semantics documented correctly
- ✅ Doc parity tests implemented

### After Phase 2:
- ✅ All P1 issues resolved
- ✅ DQ contracts published as first-class surface
- ✅ DQ documentation accurate and complete
- ✅ No false API expectations

### After Phase 3:
- ✅ Consistent terminology across all documentation
- ✅ Clear navigation structure
- ✅ Improved user experience
- ✅ Better onboarding materials

### After Phase 4:
- ✅ All P2 issues resolved
- ✅ Strict API contract surfaces
- ✅ Improved maintainability
- ✅ Better audit readiness

## 🎯 Success Metrics

### Documentation Quality:
- **Before**: 7.2/10 (from audit)
- **After Phase 1**: 8.0/10
- **After Phase 2**: 8.5/10
- **After Phase 3**: 8.8/10
- **After Phase 4**: 9.2/10

### Issue Resolution:
- **P0 Issues**: 1 → 0 (100% resolved)
- **P1 Issues**: 4 → 0 (100% resolved)
- **P2 Issues**: 2 → 0 (100% resolved)

### Coverage:
- **Contract Completeness**: 67% → 100%
- **Terminology Consistency**: 85% → 100%
- **Navigation Clarity**: 70% → 95%
- **API Surface Quality**: 60% → 90%

This comprehensive issue set addresses all problems identified in the documentation audit with clear priorities, solutions, and success criteria.
