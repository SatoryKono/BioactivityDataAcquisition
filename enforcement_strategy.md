# Enforcement Strategy for Technical Debt Prevention

**Status:** Draft
**Author:** BioETL Architecture Team
**Date:** 2026-08-18
**Linked Issue:** TBD

## Executive Summary

This document defines the enforcement strategy to prevent new technical debt accumulation in the BioETL project. It builds on existing CI/CD governance mechanisms and extends them to cover all identified debt categories from the technical debt audit.

## Current Enforcement Landscape

### Active CI/CD Gates

| Workflow | Purpose | Trigger | Enforcement Level |
|----------|---------|---------|-------------------|
| `import-linter.yml` | Ruff linting, C901 complexity, architectural contracts | Push/PR | **Hard Block** |
| `architecture.yml` | Architecture metrics baseline, cyclomatic complexity | Push/PR (fast), Daily (heavy) | **Hard Block** |
| `duplication-complexity.yml` | Duplication (jscpd), complexity (radon, xenon) | Push/PR | **Hard Block** |
| `schema-governance.yml` | Schema artifacts, contracts export, parity checks | Push/PR (schema paths) | **Hard Block** |
| `contract-governance-fast-check.yml` | Contract identity, registry consistency, ownership matrix | Push/PR (contract paths) | **Hard Block** |
| `quality-debt-weekly.yml` | Weekly debt report, config gap analysis | Weekly schedule | **Observation** |

### Configuration-Based Governance

| Config File | Purpose | Status |
|-------------|---------|--------|
| `debt_scorecard.yaml` | Debt budgets, ratchet policies, burn-down priorities | **Active** |
| `architecture_metric_exemptions.yaml` | Metric exemptions (currently zero) | **Active** |
| `staged_enforcement_policy_registry.yaml` | Staged enforcement thresholds | **Active** |
| `.importlinter` | Architectural layer contracts | **Active** |

## Identified Enforcement Gaps

### 1. Observability Debt Enforcement
**Status:** ❌ No automated enforcement
**Risk:** Missing metrics, incomplete tracing, SLO violations accumulate silently

**Required Actions:**
- [ ] Add metric coverage gates to CI
- [ ] Enforce mandatory tracing coverage (`mandatory_tracing_coverage.yaml`)
- [ ] Validate observability metric inventory (`observability_metric_governance.yaml`)
- [ ] Add SLO alert contract validation

### 2. Test Debt Enforcement
**Status:** ⚠️ Partial enforcement (fixture governance staged)
**Risk:** Golden test drift, VCR gaps, flaky tests

**Required Actions:**
- [ ] Promote fixture governance from `soft_fail` to `hard_fail`
- [ ] Add VCR metadata validation to PR checks
- [ ] Enforce golden test freshness
- [ ] Add flaky test detection and blocking

### 3. Compatibility Layer Enforcement
**Status:** ⚠️ Partial enforcement (tracked in scorecard)
**Risk:** New compatibility shims accumulate, deprecated code persists

**Required Actions:**
- [ ] Block new compatibility shims without explicit ADR
- [ ] Enforce sunset dates for transition debt
- [ ] Validate facade inventory consistency
- [ ] Add public entrypoint governance checks

### 4. Code Duplication Enforcement
**Status:** ✅ Enforced (hotspot-level zero-duplication budget)
**Risk:** New duplication in non-hotspot areas

**Required Actions:**
- [ ] Expand duplication checks to adapter/pipeline/bootstrap families
- [ ] Add function-level duplication detection
- [ ] Enforce hotspot family budgets from `debt_scorecard.yaml`

### 5. Layering Violations Enforcement
**Status:** ✅ Enforced (import-linter contracts)
**Risk:** None (existing enforcement is robust)

### 6. Config/Contracts Drift Enforcement
**Status:** ✅ Enforced (contract governance, schema governance)
**Risk:** None (existing enforcement is robust)

## Proposed Enforcement Strategy

### Phase 1: Immediate Hard Gates (Week 1-2)

#### 1.1 Observability Coverage Gate
**Workflow:** New `observability-governance.yml`
**Trigger:** Push/PR on observability changes
**Checks:**
- Metric inventory completeness
- Mandatory tracing coverage
- SLO alert contract validity
**Enforcement:** **Hard Block**

#### 1.2 VCR Metadata Gate
**Workflow:** Extend `schema-governance.yml` or create new `vcr-governance.yml`
**Trigger:** Push/PR on VPR cassettes
**Checks:**
- VCR filename policy
- Metadata completeness
- Secret safety checks
**Enforcement:** **Hard Block**

#### 1.3 Golden Test Freshness Gate
**Workflow:** Extend existing test workflows
**Trigger:** Push/PR on golden test data
**Checks:**
- Golden test age (warn > 30 days, block > 60 days)
- Snapshot consistency
**Enforcement:** **Hard Block** (after grace period)

### Phase 2: Staged Enforcement (Month 1)

#### 2.1 Fixture Governance Promotion
**Current:** `soft_fail` (0.8 threshold)
**Target:** `hard_fail` (0.9 threshold)
**Timeline:** 2-week transition with warning phase
**Governance:** Update `staged_enforcement_policy_registry.yaml`

#### 2.2 Compatibility Shim Blocking
**Workflow:** Extend `contract-governance-fast-check.yml`
**Checks:**
- Block new compatibility shims without ADR reference
- Validate sunset dates for existing shims
- Check facade inventory consistency
**Enforcement:** **Hard Block**

#### 2.3 Flaky Test Detection
**Workflow:** Extend test workflows with pytest-rerunfailures
**Checks:**
- Detect flaky tests in CI
- Block PRs that introduce flaky tests
- Track flaky test history
**Enforcement:** **Hard Block**

### Phase 3: Comprehensive Governance (Month 2-3)

#### 3.1 Debt Scorecard Integration
**Workflow:** New `debt-scorecard-gate.yml`
**Trigger:** Weekly + on debt scorecard changes
**Checks:**
- Validate debt scorecard consistency
- Check ratchet policy compliance
- Verify burn-down progress
- Enforce zero-growth for coarse budgets
**Enforcement:** **Observation** with alerts → **Hard Block** after baseline

#### 3.2 Hotspot Duplication Enforcement
**Workflow:** Extend `duplication-complexity.yml`
**Checks:**
- Enforce hotspot-level zero-duplication budget
- Track family-level non-growth budgets
- Validate against `debt_scorecard.yaml` baselines
**Enforcement:** **Hard Block**

#### 3.3 Config Surface Ratchet
**Workflow:** Extend `contract-governance-fast-check.yml`
**Checks:**
- Validate config surface metrics against `debt_scorecard.yaml`
- Block growth of inconsistent parameters
- Enforce parameter taxonomy compliance
**Enforcement:** **Hard Block** (already in place, enhance telemetry)

## Enforcement Policy Matrix

| Debt Category | Current Enforcement | Target Enforcement | Timeline |
|---------------|---------------------|-------------------|----------|
| Code Quality (Ruff) | ✅ Hard Block | ✅ Hard Block | Complete |
| Type Checking (Mypy) | ✅ Hard Block | ✅ Hard Block | Complete |
| Architecture Contracts | ✅ Hard Block | ✅ Hard Block | Complete |
| Cyclomatic Complexity | ✅ Hard Block | ✅ Hard Block | Complete |
| Code Duplication | ✅ Hard Block (hotspots) | ✅ Hard Block (expanded) | Phase 3 |
| Observability Coverage | ❌ None | ✅ Hard Block | Phase 1 |
| Tracing Coverage | ⚠️ Partial | ✅ Hard Block | Phase 1 |
| Fixture Governance | ⚠️ Soft Fail | ✅ Hard Fail | Phase 2 |
| VCR Metadata | ⚠️ Partial | ✅ Hard Block | Phase 1 |
| Golden Test Freshness | ❌ None | ✅ Hard Block | Phase 1 |
| Flaky Tests | ❌ None | ✅ Hard Block | Phase 2 |
| Compatibility Shims | ⚠️ Tracked | ✅ Hard Block | Phase 2 |
| Config Surface Drift | ✅ Hard Block | ✅ Hard Block | Complete |
| Contract Drift | ✅ Hard Block | ✅ Hard Block | Complete |

## Ratchet Policies

### Zero-Growth Policies (Hard Ratchets)
The following metrics MUST NOT increase without explicit scorecard update:
- `ruff_error_count` (current: 0)
- `mypy_error_count` (current: 0)
- `architecture_skip_count` (current: 0)
- `inconsistent_parameter_count` (current: 0)
- `hotspot_duplication_cluster_count` (target: 0)

### Downward-Only Ratchets
The following metrics MUST decrease over time:
- `transition_compat_count` (target: 0 by 2026-09-30)
- `sunset_compat_count` (target: 0 by 2026-09-30)
- `sanctioned_partial_parameter_count` (target: 0)
- `active_fixture_gap_count` (target: 0)

### Non-Growth Budgets
The following metrics may increase only with explicit budget update:
- `config_count` (entity + composite)
- `unique_parameter_count`
- `public_entrypoint_count` (reviewed additions only)

## Governance Workflow

### Adding New Exemptions
1. Create issue in GitHub with classification (`technical_debt` or `intentional_exception`)
2. Link to RF (Request for Change) document
3. Specify expiration date and removal step
4. Assign owner from approved team (@bioetl-architecture, @bioetl-platform, @bioetl-data-model)
5. Update `debt_scorecard.yaml` with required fields
6. PR must pass architecture review

### Removing Exemptions
1. Technical work to address debt
2. Update `debt_scorecard.yaml` to remove entry
3. PR must pass all quality gates
4. Update architecture metrics baseline if needed

### Scorecard Reviews
- **Cadence:** Quarterly
- **Owner:** @bioetl-architecture
- **Deliverables:**
  - Burn-down progress report
  - Exemption review (remove expired, extend with justification)
  - Budget adjustment proposals
  - Architecture metrics baseline update

## Implementation Priority

### High Priority (Phase 1)
1. Observability coverage gate
2. VCR metadata gate
3. Golden test freshness gate

### Medium Priority (Phase 2)
1. Fixture governance promotion
2. Compatibility shim blocking
3. Flaky test detection

### Low Priority (Phase 3)
1. Debt scorecard integration
2. Hotspot duplication enforcement
3. Config surface ratchet enhancement

## Success Metrics

### Short-term (1 month)
- ✅ All Phase 1 gates implemented and blocking
- ✅ Zero new observability debt
- ✅ Zero new VCR gaps
- ✅ Golden test freshness enforced

### Medium-term (3 months)
- ✅ All Phase 2 gates implemented
- ✅ Fixture governance at `hard_fail`
- ✅ Zero new compatibility shims
- ✅ Flaky test rate < 1%

### Long-term (6 months)
- ✅ All Phase 3 gates implemented
- ✅ Debt scorecard fully automated
- ✅ Hotspot duplication at zero
- ✅ Config surface stable

## Risk Mitigation

### Risk: Overly Aggressive Blocking
**Mitigation:** Staged enforcement with observation phase, warning thresholds, and grace periods

### Risk: False Positives
**Mitigation:** Allowlist mechanisms, exemption workflow, manual override for emergencies

### Risk: CI Performance Degradation
**Mitigation:** Fast/slow lane separation, incremental checks, caching strategies

### Risk: Team Resistance
**Mitigation:** Clear documentation, training, automated tooling to fix violations, gradual rollout

## References

- `configs/quality/debt_scorecard.yaml` - Debt budgets and ratchet policies
- `configs/quality/staged_enforcement_policy_registry.yaml` - Staged enforcement thresholds
- `.importlinter` - Architectural layer contracts
- `technical_debt_report.md` - Technical debt audit findings
- `technical_debt_backlog.md` - Prioritized debt backlog
- `technical_debt_roadmap.mmd` - Debt reduction roadmap

## Appendix: Enforcement Check Commands

### Observability Coverage
```bash
uv run python -m scripts.engineering.qa report-observability-metric-inventory --check
uv run python -m scripts.engineering.qa check-mandatory-tracing-coverage --check
```

### VCR Metadata
```bash
uv run python -m scripts.engineering.qa.vcr check-root-vcr-cassettes --check
uv run python -m scripts.engineering.qa.vcr check-vcr-filename-policy --check
```

### Fixture Governance
```bash
uv run python -m scripts.engineering.qa report-test-governance-audit --check
```

### Golden Test Freshness
```bash
uv run pytest --golden-test --max-age-days 60
```

### Compatibility Shims
```bash
uv run python -m scripts.engineering.qa report-compatibility-importer-census --check
uv run python -m scripts.engineering.qa check-quality-exemptions --check
```

### Debt Scorecard
```bash
uv run python -m scripts.engineering.qa report-debt-governance-gates --check
```