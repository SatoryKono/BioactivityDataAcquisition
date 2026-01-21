# Dead Code Cleanup Report

**Date**: 2026-01-21
**Version**: 5.9.0
**Branch**: claude/cleanup-dead-code-y77AQ
**Соответствует**: RULES.md v5.10, §14 "Рефакторинг модулей"

---

## Executive Summary

**Result: No dead code found. Codebase is clean.**

A comprehensive analysis of the BioETL codebase was performed using multiple static analysis tools and manual verification. The codebase is well-maintained with no obvious dead or unused code patterns.

---

## Baseline Metrics

| Metric | Value |
|--------|-------|
| **LOC** | ~91,032 |
| **Classes** | ~841 |
| **Functions** | ~409 |
| **Python files** | ~388 |

---

## Tools Used

| Tool | Version | Purpose |
|------|---------|---------|
| vulture | 2.14 | Dead code detection |
| autoflake | - | Unused imports detection |
| isort | 5.x | Import sorting check |
| ruff | 0.14.11 | Linting (F401, F841) |
| mypy | 1.19.1 | Type checking |

---

## Analysis Results

### 1. Vulture (Dead Code Detection)

**Findings**: 5 items at 100% confidence

All findings are **false positives**:

| File | Line | Finding | Explanation |
|------|------|---------|-------------|
| `crossref/client.py` | 184 | `if False:` condition | Intentional type workaround for AsyncIterator. `# pragma: no cover` present. |
| `filterable_mixin.py` | 84 | `if False:` condition | Intentional type workaround for AsyncIterator. `# pragma: no cover` present. |
| `openalex/client.py` | 168 | `if False:` condition | Intentional type workaround for AsyncIterator. `# pragma: no cover` present. |
| `semanticscholar/adapter.py` | 358 | `if False:` condition | Intentional type workaround for AsyncIterator. `# pragma: no cover` present. |
| `uniprot/idmapping_client.py` | 469 | `if False:` condition | Intentional type workaround for AsyncIterator. `# pragma: no cover` present. |

**Technical Note**: The `if False: yield {}` pattern is required for Python async generators that always raise exceptions. Without this, Python would not recognize the function as a generator (AsyncIterator type). This is documented in Python typing discussions and is a valid pattern.

### 2. Autoflake (Unused Imports)

**Result**: No issues detected

All 388 Python files were scanned. No unused imports found.

### 3. Ruff Linting

| Check | Result |
|-------|--------|
| F401 (unused imports) | All checks passed! |
| F841 (unused variables) | All checks passed! |
| General checks | No issues |

### 4. isort (Import Sorting)

**Result**: No issues found

### 5. mypy Type Checking

**Result**: No issues on sampled layers

### 6. Manual Verification

| Check | Result |
|-------|--------|
| Deprecated markers (TODO/FIXME remove) | None found |
| Commented-out code blocks | None found |
| Orphaned modules (no imports) | None found |
| Unused exception classes | None found |
| Backward-compat shims no longer used | None found (1 shim found, still used by tests) |
| Empty stub files | None found |
| `.pyi` stub files | None |
| `.pyc` compiled files | None |

---

## Verified False Positives (Do Not Remove)

### 1. Protocol Method Parameters

The following appear as "unused" in vulture but are **required API contract parameters**:

| File | Parameters | Reason |
|------|------------|--------|
| `domain/ports/audit.py` | `start_time`, `end_time` | Protocol signature for filtering |
| `domain/ports/data_source.py` | `exc_type`, `exc_val`, `exc_tb` | Standard `__aexit__` signature |
| `domain/ports/data_source.py` | `query`, `filters`, `fallback_mapping` | Protocol API parameters |
| `domain/ports/dq_report.py` | `source_file`, `target_table` | Protocol API parameters |
| `infrastructure/locking/memory_lock.py` | `exclusive` | API compatibility (documented as unused) |
| `composition/factories/services_factory.py` | `record` | Lambda callback type signature |

### 2. Type System Workarounds

The `if False: yield {}` pattern in async generator functions that always raise exceptions is a valid Python idiom for type checking. Files using this pattern:

- `infrastructure/adapters/crossref/client.py:184`
- `infrastructure/adapters/filterable_mixin.py:84`
- `infrastructure/adapters/openalex/client.py:168`
- `infrastructure/adapters/semanticscholar/adapter.py:358`
- `infrastructure/adapters/uniprot/idmapping_client.py:469`

### 3. Backward Compatibility Re-export

- `application/services/dq_metrics_calculator.py` - Re-exports from domain layer. **Still used** by test file `tests/unit/application/services/test_dq_metrics_calculator.py`.

---

## Recommendations

1. **No action required** - The codebase is clean.

2. **Consider for future maintenance**:
   - The backward-compat module `application/services/dq_metrics_calculator.py` can be removed after updating the test to import from `domain.services` directly (optional, low priority).

3. **Documentation is accurate** - CLAUDE.md §2.3 correctly identifies all known false positives and patterns.

---

## Validation Checklist

- [x] vulture analysis complete
- [x] autoflake check passed
- [x] isort check passed
- [x] ruff F401/F841 checks passed
- [x] mypy spot check passed
- [x] Python syntax validation passed (all files)
- [x] No deprecated markers found
- [x] No orphaned modules found
- [x] False positives documented

---

## Conclusion

The BioETL codebase (v5.9.0) is well-maintained with no dead or unused code requiring cleanup. All findings from static analysis tools are false positives related to:

1. Python type system requirements for async generators
2. Protocol/interface method signatures
3. API compatibility parameters
4. Callback type signatures

The codebase follows best practices for a hexagonal architecture project with proper separation of concerns across 5 layers (domain, application, infrastructure, composition, interfaces).

---

*Report generated: 2026-01-21*
*Analysis duration: ~30 minutes*
*Files analyzed: ~388 Python files (~91,032 LOC)*
