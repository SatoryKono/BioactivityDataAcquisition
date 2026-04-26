# Script Analysis and Cleanup Prompt

**Purpose**: Comprehensive guide for analyzing scripts to identify obsolete, duplicate, and suboptimal scripts with systematic cleanup planning.

**Last Updated**: 2024-04-14
**Status**: Active
**Owner**: @bioetl-architecture

---

## Enhanced Script Analysis Prompt

### Analysis Objectives

**Primary Goals:**
- Identify obsolete scripts safe for removal
- Find duplicate scripts suitable for consolidation
- Detect suboptimal scripts needing refactoring
- Uncover governance violations
- Provide actionable cleanup recommendations

**Scope:**
- All scripts in `scripts/` directory
- Scripts in `src/tools/` directory
- Script references in workflows, agents, and documentation

---

## 1. Obsolete Scripts (Deprecation Candidates)

### Identification Criteria

**Technical Indicators:**
- ✅ No references in `.github/workflows/*` files
- ✅ No usage in `.codex/skills/*` or agent documentation
- ✅ Marked as "legacy" or "orphan" in `scripts_inventory_manifest.json`
- ✅ Contains deprecated technology (e.g., `gemini run`, old API versions)
- ✅ Located in `archive/`, `tmp/`, or `legacy/` directories
- ✅ No git commits in past 12 months

**Governance Indicators:**
- ✅ No owner specified in lifecycle registry
- ✅ No documentation in README files
- ✅ No tests covering the script
- ✅ Violates current architecture rules

### Analysis Questions

**Usage Evidence:**
```bash
# Check workflow references
grep -r "script_name" .github/workflows/

# Check agent/skill usage
grep -r "script_name" .codex/ docs/00-project/ai/agents/

# Check test coverage
grep -r "script_name" tests/
```

**Safety Assessment:**
- What's the last known usage in git history?
- Are there hidden dependencies in configs or documentation?
- What's the rollback plan if removal causes issues?
- Can removal be automated or requires manual verification?

### Removal Checklist

- [ ] Verify no CI/CD references
- [ ] Check no agent/skill dependencies
- [ ] Confirm no test dependencies
- [ ] Update lifecycle registry
- [ ] Remove from inventory manifest
- [ ] Document removal rationale

---

## 2. Duplicate Scripts (Consolidation Candidates)

### Identification Criteria

**Code-Level Duplication:**
- ✅ Same functionality with different extensions (`.sh` vs `.py`)
- ✅ Wrapper scripts that only delegate (`exec "$SCRIPT_DIR/..."`)
- ✅ Cross-platform duplicates (Windows `.ps1` vs Unix `.sh`)
- ✅ >80% code similarity (AST analysis)
- ✅ Multiple scripts with identical help text

**Functional Duplication:**
- ✅ Different scripts solving same problem
- ✅ Overlapping command-line interfaces
- ✅ Redundant error handling patterns
- ✅ Duplicate configuration logic

### Consolidation Strategy

**Decision Matrix:**

| Factor | Weight | Canonical Choice Criteria |
|--------|--------|--------------------------|
| **Usage Frequency** | 40% | Most frequently called in workflows |
| **Documentation** | 25% | Best documented version |
| **Code Quality** | 20% | Best error handling, logging |
| **Platform Support** | 15% | Cross-platform compatibility |

**Migration Path:**
1. Identify canonical version
2. Update all callers (workflows, docs, agents)
3. Add deprecation warnings to old versions
4. Monitor usage during transition period
5. Remove deprecated versions

### Common Duplication Patterns

**Test Runners:**
```bash
# Before: Multiple runners
scripts/engineering/dev/run_pytest.sh
scripts/engineering/dev/run_pytest.ps1
scripts/engineering/ci/run_pytest_resilient.py

# After: Single canonical
scripts/engineering/ci/run_pytest_resilient.py
```

**Cross-Platform Wrappers:**
```bash
# Before: Platform-specific duplicates
scripts/ai/mcp/mcp_wrapper.ps1
scripts/ai/mcp/mcp_wrapper.sh

# After: Single cross-platform or documented choice
scripts/ai/mcp/mcp_wrapper.sh  # Canonical
```

---

## 3. Suboptimal Scripts (Refactoring Candidates)

### Identification Criteria

**Code Quality Issues:**
- ✅ >8 command-line parameters (complex interface)
- ✅ No error handling (`set -e` missing, no try/catch)
- ✅ No logging or minimal logging
- ✅ Hardcoded paths/values instead of config
- ✅ No type hints (Python) or shellcheck errors
- ✅ Missing documentation (no `--help`, no README)

**Architecture Issues:**
- ✅ Script does multiple unrelated things
- ✅ Violates separation of concerns
- ✅ Mixes I/O with business logic
- ✅ Poor error messages (generic "failed")
- ✅ No exit codes or inconsistent codes
- ✅ No input validation

### Refactoring Priorities

**Critical (Do Now):**
- Add proper error handling and logging
- Extract configuration to separate files
- Add input validation
- Implement consistent exit codes

**High (Next Sprint):**
- Add type hints and docstrings
- Split complex scripts into modules
- Implement proper argument parsing
- Add comprehensive tests

**Medium (Backlog):**
- Improve performance bottlenecks
- Add metrics/telemetry
- Enhance documentation
- Add examples to README

---

## 4. Governance Violations (Policy Candidates)

### Identification Criteria

**Location Violations:**
- ✅ Scripts not in canonical roots (`scripts/engineering/repo/catalog.yaml`)
- ✅ Scripts in wrong directory for their purpose
- ✅ Scripts violating layer boundaries

**Documentation Violations:**
- ✅ No README entry for script group
- ✅ Missing from inventory manifest
- ✅ No owner in lifecycle registry
- ✅ Undocumented parameters or behavior

**Quality Violations:**
- ✅ No tests for critical scripts
- ✅ Bypassing established patterns
- ✅ Inconsistent naming conventions
- ✅ Missing license headers

### Policy Actions

**Immediate Fixes:**
```bash
# Move to canonical location
mv scripts/misc/important.sh scripts/engineering/qa/important.sh

# Add to catalog
vim scripts/engineering/repo/catalog.yaml

# Update lifecycle registry
vim configs/quality/scripts_lifecycle_registry.json
```

**Preventive Measures:**
- Add governance checks to CI
- Create script location linter
- Document canonical patterns
- Add script creation template

---

## Analysis Methodology

### Step 1: Data Collection

**Inventory Analysis:**
```bash
# Get comprehensive script inventory
python3 -m scripts.engineering.repo sync-inventory --write

# Export JSON for analysis
python3 -m scripts.engineering.repo check-inventory --json > inventory.json
```

**Reference Analysis:**
```bash
# Check workflow references
grep -r "scripts/" .github/workflows/ | sort | uniq -c

# Check agent usage
grep -r "scripts/" .codex/ docs/00-project/ai/agents/

# Check test references
grep -r "scripts/" tests/ | grep -v ".pyc"
```

**Quality Analysis:**
```bash
# Shell script quality
shellcheck scripts/**/*.sh

# Python script quality
pylint scripts/**/*.py

# Code duplication detection
# (Would use specialized tool in real analysis)
```

### Step 2: Categorization Matrix

```markdown
| Script | Type | Last Used | References | Status | Decision | Action | Owner |
|--------|------|-----------|------------|--------|----------|--------|-------|
| `scripts/old.sh` | test | 2023-05-15 | None | legacy | remove | safe | @platform |
| `scripts/dup.py` | util | 2024-01-10 | agents/bot.md:15 | active | consolidate | needs migration | @architecture |
```

### Step 3: Impact Analysis

**Risk Assessment Framework:**

| Risk Level | Criteria | Example |
|------------|----------|---------|
| **Low** | No references, archived, documented replacement | Legacy migration scripts |
| **Medium** | Some references, needs migration, has replacement | Deprecated test runners |
| **High** | Active usage, no clear replacement, complex dependencies | Core CI scripts |

**Validation Strategy:**
```bash
# Test CI still works
act -j tests

# Verify agent functionality
# (Would test agent workflows)

# Check inventory validation
python3 -m scripts.engineering.repo check-inventory --check
```

### Step 4: Prioritized Action Plan

```markdown
## Phase 1: Safe Removals (Week 1)
- [ ] Remove 10 legacy scripts (no references, archived)
- [ ] Update lifecycle registry entries
- [ ] Verify CI still passes
- [ ] Document removals in changelog

## Phase 2: Consolidations (Week 2)
- [ ] Merge test runners (keep resilient version)
- [ ] Unify cross-platform wrappers
- [ ] Update all workflow callers
- [ ] Add deprecation warnings

## Phase 3: Refactoring (Week 3-4)
- [ ] Add error handling to top 5 critical scripts
- [ ] Extract configurations
- [ ] Improve documentation
- [ ] Add missing tests

## Phase 4: Governance (Ongoing)
- [ ] Add script location checks to CI
- [ ] Create script quality gates
- [ ] Document canonical patterns
- [ ] Train team on governance rules
```

---

## Expected Output Format

### Executive Summary
```
✅ **Analysis Complete**: [Date]
📊 **Total Scripts Analyzed**: 316
🗑️ **Obsolete Candidates**: 15 (4.7%)
🔄 **Duplicate Groups**: 8 groups (24 scripts)
⚠️ **Suboptimal Scripts**: 42 (13.3%)
📉 **Governance Violations**: 12
🎯 **Estimated Cleanup Potential**: 39 scripts (12.3%)
```

### Detailed Findings

#### 1. Obsolete Scripts (High Confidence for Removal)

| Script | Last Commit | References | Removal Risk | Savings | Notes |
|--------|-------------|------------|--------------|---------|-------|
| `scripts/ops/archive/old_migration.py` | 2023-05-15 | None | Low | 1 script | Historical only |
| `scripts/ai/legacy_bot.sh` | 2023-08-20 | None | Low | 1 script | Replaced by skills |
| `scripts/tmp/setup_temp.sh` | 2023-11-01 | None | Low | 1 script | Temporary setup |

**Total Obsolete**: 15 scripts = **4.7%** of inventory

#### 2. Duplicate Scripts (Consolidation Opportunities)

| Group ID | Scripts | Canonical Candidate | Savings | Complexity |
|----------|---------|---------------------|---------|------------|
| TR-001 | `run_pytest.sh`, `run_pytest.ps1`, `run_pytest_resilient.py` | `run_pytest_resilient.py` | 2 scripts | Medium |
| MCP-001 | `mcp_wrapper.ps1`, `mcp_wrapper.sh` | `mcp_wrapper.sh` | 1 script | Low |
| QA-001 | `check_arch.py`, `validate_arch.py` | `validate_arch.py` | 1 script | High |

**Total Duplicate Groups**: 8 = **24 scripts** = **7.6%** of inventory
**Consolidation Potential**: 16 scripts = **5.1%** savings

#### 3. Suboptimal Scripts (Refactoring Needed)

| Script | Issue Type | Severity | Effort | Impact |
|--------|------------|----------|--------|--------|
| `critical_process.sh` | No error handling | High | Medium | High |
| `complex_etl.py` | 12 parameters | High | High | Medium |
| `config_loader.sh` | Hardcoded paths | Medium | Low | High |

**Top 10 Refactoring Candidates**: 10 scripts = **3.2%**
**Medium Priority**: 20 scripts = **6.3%**
**Low Priority**: 12 scripts = **3.8%**

#### 4. Governance Violations

| Script | Violation Type | Fix Required | Owner |
|--------|----------------|--------------|-------|
| `scripts/misc/important.sh` | Wrong location | Move to scripts/engineering/qa/ | @architecture |
| `scripts/undocumented.py` | No README | Add documentation | @docs |
| `scripts/untested.sh` | No tests | Add test coverage | @qa |

**Critical Violations**: 4
**Major Violations**: 6
**Minor Violations**: 2

---

## Recommendations

### Immediate Actions (Next 2 Weeks)

1. **Remove Obsolete Scripts**
   - Remove 15 legacy scripts (4.7% reduction)
   - Update lifecycle registry
   - Expected savings: 15 scripts

2. **Consolidate Test Runners**
   - Standardize on `run_pytest_resilient.py`
   - Remove duplicate wrappers
   - Expected savings: 2 scripts

### Short-Term (Next Month)

3. **Cross-Platform Consolidation**
   - Review PS1/SH pairs
   - Standardize on SH versions
   - Expected savings: 8 scripts

4. **Critical Refactoring**
   - Add error handling to top 5 scripts
   - Extract hardcoded configurations
   - Expected improvement: 5 scripts

### Long-Term (Next Quarter)

5. **Governance Enforcement**
   - Add CI checks for script locations
   - Create quality gates
   - Document patterns

6. **Comprehensive Refactoring**
   - Address mediumpriority issues
   - Improve documentation
   - Add test coverage

---

## Implementation Roadmap

### Phase 1: Safe Cleanup (Week 1-2)
**Objective**: Remove low-risk obsolete scripts
**Actions**:
- Remove 15 legacy scripts
- Update lifecycle registry
- Verify CI/CD pipelines
- Document changes
**Success Criteria**:
- CI still passes
- No breaking changes
- 4.7% inventory reduction

### Phase 2: Consolidation (Week 3-4)
**Objective**: Merge duplicate functionality
**Actions**:
- Consolidate test runners
- Unify cross-platform wrappers
- Update all callers
- Add deprecation warnings
**Success Criteria**:
- All workflows updated
- 5.1% inventory reduction
- No duplicate functionality

### Phase 3: Quality Improvement (Week 5-8)
**Objective**: Refactor suboptimal scripts
**Actions**:
- Add error handling
- Extract configurations
- Improve documentation
- Add tests
**Success Criteria**:
- Top 10 scripts refactored
- Code quality metrics improved
- Better maintainability

### Phase 4: Governance (Ongoing)
**Objective**: Prevent regression
**Actions**:
- Add CI checks
- Document patterns
- Team training
- Regular audits
**Success Criteria**:
- No new violations
- Governance automated
- Team compliance

---

## Tools and Commands

### Inventory Analysis
```bash
# Sync inventory
python3 -m scripts.engineering.repo sync-inventory --write

# Check inventory status
python3 -m scripts.engineering.repo check-inventory --check

# Export JSON for analysis
python3 -m scripts.engineering.repo check-inventory --json > analysis.json
```

### Reference Analysis
```bash
# Find script references in workflows
grep -r "scripts/" .github/workflows/ | sort | uniq -c > workflow_refs.txt

# Find script references in agents
grep -r "scripts/" .codex/ docs/00-project/ai/agents/ > agent_refs.txt

# Find script references in tests
grep -r "scripts/" tests/ | grep -v ".pyc" > test_refs.txt
```

### Quality Analysis
```bash
# Check shell scripts
shellcheck scripts/**/*.sh | tee shellcheck_results.txt

# Check Python scripts
pylint scripts/**/*.py | tee pylint_results.txt

# Count script types
find scripts/ -name "*.sh" | wc -l
find scripts/ -name "*.py" | wc -l
find scripts/ -name "*.ps1" | wc -l
```

---

## Success Metrics

### Quantitative Goals
- **Inventory Reduction**: 12-15% (38-47 scripts)
- **Legacy Reduction**: 50%+ reduction
- **Duplicate Elimination**: 80%+ consolidation
- **Code Quality**: 20% improvement in linting scores

### Qualitative Goals
- **Maintainability**: Easier to understand and modify
- **Discoverability**: Clearer script purposes and locations
- **Reliability**: Better error handling and logging
- **Governance**: Automated compliance checking

---

## Appendix: Common Patterns

### Healthy Script Characteristics
```markdown
✅ Clear single responsibility
✅ Proper error handling and logging
✅ Good documentation (help text, README)
✅ Type hints (Python) or shellcheck clean (Bash)
✅ Proper exit codes
✅ Input validation
✅ Configuration externalized
✅ Tests available
✅ Canonical location
✅ Active usage evidence
```

### Problematic Script Characteristics
```markdown
❌ Multiple responsibilities
❌ No error handling
❌ Undocumented parameters
❌ Hardcoded values
❌ No tests
❌ Duplicate functionality
❌ Wrong location
❌ No recent usage
❌ Poor naming
❌ Complex interfaces
```

---

**Document Status**: Active
**Review Cycle**: Quarterly
**Next Review**: 2024-07-14
**Change Log**:
- 2024-04-14: Initial version based on cleanup analysis
- 2024-04-14: Added governance violation section
- 2024-04-14: Enhanced methodology with specific commands
