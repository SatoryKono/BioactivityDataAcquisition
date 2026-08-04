> Mirror status: This file is a published/internal mirror under `docs/00-project/ai/**`. It is not a canonical runtime surface.
> Canonical runtime source: `.codex/skills/py-reproducibility-audit/SKILL.md`
> Governance: AI_RUNTIME_MIRROR_OWNERSHIP.md
> Edit the runtime source first, then refresh this mirror.
______________________________________________________________________

---
name: "py-reproducibility-audit"
description: "Use when auditing code changes for reproducibility and replay capability. Ensures that changes maintain deterministic behavior, proper test coverage, and can be reliably replayed across environments."
context: "fork"
agent: "general-purpose"
---

# Python Reproducibility Audit

## Source Of Truth

- Normative index: `../../../../NORMATIVE_SOURCES.md`
- Root runtime contract: `../../../../../../AGENTS.md`
- Project rules: `../../../../RULES.md`
- Requirements: `../../../../../01-requirements/REQUIREMENTS.md`
- Accepted ADRs in `../../../../../02-architecture/decisions/`
- Memory policy: `../../../agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../agents/policy/POST_CHANGE_VALIDATION.md`

- Reproducibility contract: [references/reproducibility-audit.md](references/reproducibility-audit.md)
This skill audits code changes for reproducibility and replay capability.

## Prerequisites

- Code changes proposed or committed
- Test coverage available
- Environment configuration documented

## Workflow

Use TodoWrite to track these mandatory steps:

<required>
1. Analyze code changes for determinism violations
2. Review test coverage for new code paths
3. Check for non-deterministic I/O operations
4. Validate schema and contract compliance
5. Review logging and observability
6. Check environment dependencies
7. Generate reproducibility audit report
</required>

### Step 1: Analyze Code Changes for Determinism

Review code changes for determinism violations:

**Common violations:**

| Violation Type | Pattern | Risk Level |
| -------------- | ------- | ---------- |
| Unsorted DataFrame operations | `df.head()`, `df.tail()` without `sort_values()` | High |
| Non-UTC timestamps | `datetime.now()`, `datetime.utcnow()` | High |
| Random operations without seed | `random.random()`, `np.random.rand()` | High |
| Unstable iteration | `dict.keys()`, `set` iteration | Medium |
| File system ordering | `os.listdir()`, `glob.glob()` without sorting | Medium |

**Check for:**

```python
# BAD: Non-deterministic
result = df.head(10)
timestamp = datetime.now()
items = list(my_dict.keys())

# GOOD: Deterministic
result = df.sort_values("id").head(10)
timestamp = datetime.now(timezone.utc)
items = sorted(my_dict.keys())
```

### Step 2: Review Test Coverage

Ensure new code paths have test coverage:

**Coverage requirements:**

- New functions: ≥80% line coverage
- New classes: ≥75% line coverage
- Critical paths: 100% coverage
- Error handling: All branches covered

**Check for:**

- Unit tests for new functions
- Integration tests for new workflows
- Edge case tests for boundary conditions
- Error handling tests for exceptions

### Step 3: Check Non-Deterministic I/O

Review I/O operations for determinism:

**I/O patterns to check:**

```python
# BAD: Non-deterministic file ordering
files = os.listdir("data/")

# GOOD: Deterministic file ordering
files = sorted(os.listdir("data/"))

# BAD: Non-atomic writes
with open("output.json", "w") as f:
    json.dump(data, f)

# GOOD: Atomic writes via write_dataset_atomic
write_dataset_atomic(data, "output.json")
```

**Check for:**

- File operations without sorting
- Non-atomic writes
- Network calls without retry logic
- Database operations without transactions

### Step 4: Validate Schema and Contract Compliance

Ensure schema validation is in place:

**Schema checks:**

- Pandera schemas defined for all data structures
- Schema validation before writes
- Proper error handling for validation failures
- Schema evolution documented

**Contract checks:**

- API contracts defined and tested
- Breaking changes documented
- Version bumps if needed
- Migration plans provided

### Step 5: Review Logging and Observability

Ensure proper structured logging:

**Logging checks:**

- Only `UnifiedLogger` used (no `print()`)
- Structured logging with context
- Proper log levels (DEBUG, INFO, WARNING, ERROR)
- No secrets in logs

**Observability checks:**

- Metrics defined for key operations
- Tracing for critical paths
- Error tracking configured
- No PII in telemetry

### Step 6: Check Environment Dependencies

Review environment configuration:

**Dependency checks:**

- All dependencies version-pinned
- No floating ranges (e.g., `>=`, `latest`)
- Dependency security scan passed
- No deprecated packages

**Configuration checks:**

- `.env` files not committed
- Configuration via environment variables
- Secrets management documented
- Local-only runtime by default

### Step 7: Generate Reproducibility Audit Report

Produce audit report:

```markdown
## Reproducibility Audit Report

**Changes Audited:** [file list]
**Audit Date:** [timestamp]
**Auditor:** [agent/skill]

### Determinism Analysis

| Check | Status | Notes |
| ----- | ------ | ----- |
| DataFrame operations | ✓ PASS | All operations use stable sorting |
| Timestamp handling | ✓ PASS | All timestamps in UTC |
| Random operations | ✓ PASS | Seeded where used |
| Iteration stability | ✓ PASS | All iterations sorted |

### Test Coverage

| Component | Coverage | Status |
| --------- | -------- | ------ |
| New functions | 85% | ✓ PASS |
| New classes | 78% | ✓ PASS |
| Critical paths | 100% | ✓ PASS |
| Error handling | 92% | ✓ PASS |

### I/O Operations

| Operation | Deterministic | Atomic | Status |
| --------- | ------------- | ------ | ------ |
| File reads | ✓ | N/A | ✓ PASS |
| File writes | ✓ | ✓ | ✓ PASS |
| Network calls | ✓ | N/A | ✓ PASS |

### Schema Validation

| Schema | Validated | Status |
| ------ | --------- | ------ |
| Input schema | ✓ | ✓ PASS |
| Output schema | ✓ | ✓ PASS |
| Internal schema | ✓ | ✓ PASS |

### Logging & Observability

| Check | Status | Notes |
| ----- | ------ | ----- |
| UnifiedLogger only | ✓ PASS | No print() found |
| Structured logging | ✓ PASS | Context bound |
| No secrets in logs | ✓ PASS | Scan passed |
| Metrics defined | ✓ PASS | Key operations covered |

### Environment Dependencies

| Check | Status | Notes |
| ----- | ------ | ----- |
| Version-pinned | ✓ PASS | All dependencies pinned |
| Security scan | ✓ PASS | No vulnerabilities |
| No deprecated packages | ✓ PASS | All current |

### Overall Assessment

**Reproducibility Score:** [X]/10
**Replay Capability:** [YES/NO]
**Recommendation:** [APPROVE/REQUEST CHANGES]

### Required Changes (if any)

- [List any required changes to meet reproducibility standards]
```

## User Interaction

Use the **AskUserQuestion tool** when:

### Determinism violation found

```
Question: "Non-deterministic pattern found: [pattern]. How to resolve?"
Options:
- "Fix with stable sorting"
- "Add deterministic seed"
- "Accept with justification"
- "Help me understand the risk"
```

### Test coverage insufficient

```
Question: "Test coverage for [component] is [X]%, below threshold of 80%. How to proceed?"
Options:
- "Add unit tests for missing paths"
- "Add integration tests"
- "Accept with risk documentation"
- "Help me identify test gaps"
```

### Breaking change detected

```
Question: "Breaking change detected in [component]. Schema/contract changed without version bump."
Options:
- "Add version bump and migration plan"
- "Revert breaking change"
- "Document as non-breaking with justification"
- "Help me assess impact"
```

### Environment dependency issue

```
Question: "Dependency [package] uses floating range [version]. This may cause reproducibility issues."
Options:
- "Pin to specific version"
- "Accept with justification"
- "Find alternative package"
- "Help me understand the risk"
```

## Output

After reproducibility audit:

```markdown
## Audit Complete

**Reproducibility Score:** [X]/10
**Replay Capability:** [YES/NO]
**Recommendation:** [APPROVE/REQUEST CHANGES]

### Summary
- Determinism violations: [N]
- Test coverage gaps: [N]
- I/O issues: [N]
- Schema violations: [N]
- Logging issues: [N]
- Dependency issues: [N]

### Required Actions
- [List any required actions]
- [List any recommended actions]
```

## References

- [references/reproducibility-audit.md](references/reproducibility-audit.md) - reproducibility standards
- [references/github-issue-design.md](references/github-issue-design.md) - issue template for reproducibility issues
