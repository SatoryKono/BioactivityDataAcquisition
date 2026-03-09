# Code Review Report — S6: Tests
**Date**: 2024-03-09
**Scope**: tests
**Files reviewed**: 854
**Total LOC**: 193131
**Status**: PASS
**Score**: 9.7/10.0

---

## Summary
| Category | Issues | CRIT | HIGH | MED | LOW | Score |
|----------|--------|------|------|-----|-----|-------|
| Architecture | 0 | 0 | 0 | 0 | 0 | 10.0 |
| Anti-Patterns | 1 | 0 | 0 | 1 | 0 | 9.5 |
| DI Violations | 1 | 0 | 1 | 0 | 0 | 9.0 |
| Naming | 0 | 0 | 0 | 0 | 0 | 10.0 |
| Types | 0 | 0 | 0 | 0 | 0 | 10.0 |
| Testing | 0 | 0 | 0 | 0 | 0 | 10.0 |

## High Issues
### DI-001: Hardcoded constructor instantiation
- **Rule**: DI-001
- **Severity**: HIGH
- **Description**: Found violating patterns.
- **Code**:
  ```python
  tests/unit/domain/services/test_normalization_config.py:        config = ConcentrationRangeConfig()
  tests/unit/domain/services/test_normalization_config.py:        config = ConcentrationRangeConfig(min_molar=1e-12, max_molar=1e-3)
  tests/unit/domain/services/test_normalization_config.py:        config = PChemblRangeConfig()
  tests/unit/domain/services/test_normalization_config.py:        config = NormalizationConfig()
  tests/unit/domain/services/test_normalization_config.py:        config = NormalizationConfig(
  ```

## Medium Issues
### AP-006: Print statements found
- **Rule**: AP-006
- **Severity**: MEDIUM
- **Description**: Found violating patterns.
- **Code**:
  ```python
  tests/unit/domain/hash_policy/test_hash_policy_stability.py:def _policy_fingerprint(policy: dict[str, Any]) -> str:
  tests/unit/domain/hash_policy/test_hash_policy_stability.py:            "policy_fingerprint": _policy_fingerprint(policy),
  tests/integration/pipelines/test_crossref_date_normalization.py:    async def test_online_date_used_when_no_print(
  tests/architecture/test_no_print_in_docstrings.py:"""Architecture test: no print() in docstring examples in non-domain layers.
  tests/architecture/test_no_print_in_docstrings.py:MUST use LoggerPort in docstring examples instead of print().
  ```

## Scoring Calculation
| Category | Weight | Raw Score | Deductions | Weighted |
|----------|--------|-----------|------------|----------|
| Architecture | 30% | 10 | -0 | 3.0 |
| Anti-Patterns | 25% | 10 | -0.5 | 2.4 |
| DI Violations | 20% | 10 | -1.0 | 1.8 |
| Naming | 10% | 10 | -0 | 1.0 |
| Types | 10% | 10 | -0 | 1.0 |
| Testing | 5% | 10 | -0 | 0.5 |
| **FINAL** | **100%** | | | **9.7** |
