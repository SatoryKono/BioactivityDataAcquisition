# GitHub Issues Creation Guide

## Overview
Based on the architecture audit (2025-01-30), three issues have been prepared for creation. Since GitHub CLI is not available in this environment, you can create these issues manually or use another method.

## Prepared Issues

### 1. Aggregate Invariants Documentation
**File:** `.github/issues/ARCHITECTURE_AUDIT_2025-01-30_aggregate_invariants.md`
- **Priority:** P1 (High)
- **Type:** Documentation
- **Estimate:** 4 hours
- **Impact:** DDD Alignment +1.0

### 2. Scripts Governance Audit and Cleanup
**File:** `.github/issues/ARCHITECTURE_AUDIT_2025-01-30_scripts_governance.md`
- **Priority:** P1 (High)
- **Type:** Technical Debt
- **Estimate:** 40 hours (6 weeks)
- **Impact:** Technical Debt +1.5

### 3. Exhaustive Batch FSM Tests
**File:** `.github/issues/ARCHITECTURE_AUDIT_2025-01-30_batch_fsm_tests.md`
- **Priority:** P2 (Medium)
- **Type:** Testing
- **Estimate:** 8 hours
- **Impact:** DDD Alignment +1.0, Test Strategy +0.5

## Creation Methods

### Method 1: GitHub Web Interface
1. Go to https://github.com/[org]/[repo]/issues/new
2. Copy content from each markdown file
3. Fill in title, labels, assignees
4. Submit

### Method 2: GitHub CLI (if available)
```bash
# Install GitHub CLI first
# Then for each issue:
gh issue create --title "Document Aggregate Invariants" \
  --body-file .github/issues/ARCHITECTURE_AUDIT_2025-01-30_aggregate_invariants.md \
  --label documentation,architecture,ddd,technical-debt \
  --assignee @username
```

### Method 3: GitHub API
Use GitHub REST API to create issues programmatically.

## Recommended Order
1. **Issue 1:** Aggregate Invariants Documentation (P1, 4 hours) - Quick win, high impact
2. **Issue 2:** Scripts Governance Audit (P1, 40 hours) - Long-term, but start with audit phase
3. **Issue 3:** Batch FSM Tests (P2, 8 hours) - Can be done in parallel with Issue 2

## Labels to Use
- `architecture` - All issues
- `technical-debt` - Scripts governance
- `documentation` - Aggregate invariants, Dashboard docs
- `testing` - Batch FSM tests
- `ddd` - Aggregate invariants, Batch FSM
- `quality` - All issues
- `governance` - Scripts governance

## Expected Outcome
After creating and addressing these issues:
- Architecture quality score: 8.53 → 9.35 (+0.82)
- DDD Alignment: 7.0 → 8.0 (+1.0)
- Technical Debt: 8.0 → 9.5 (+1.5)
- Test Strategy: 9.0 → 9.5 (+0.5)
