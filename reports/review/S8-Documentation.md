# Code Review Report — S8: Documentation
**Date**: 2026-03-04
**Scope**: docs
**Files reviewed**: 855
**Total LOC**: 189836
**Status**: FAIL
**Score**: 0.0/10.0

---
## Summary
| Category | Issues | CRIT | HIGH | MED | LOW | Score |
|----------|--------|------|------|-----|-----|-------|
| Architecture | 0 | 0 | 0 | 0 | 0 | 10.0 |
| Anti-Patterns | 5 | 0 | 0 | 5 | 0 | 7.5 |
| DI Violations | 0 | 0 | 0 | 0 | 0 | 10.0 |
| Naming | 0 | 0 | 0 | 0 | 0 | 10.0 |
| Types | 5 | 0 | 5 | 0 | 0 | 5.0 |
| Testing | 0 | 0 | 0 | 0 | 0 | 10.0 |
| **TOTAL** | **10** | **0** | **5** | **5** | **0** | **0.0** |

## High Issues
### TYPE-001: Public Function Annotations
- **Rule**: TYPE-001 (Public Function Annotations)
- **Severity**: HIGH
- **File**: `docs/03-guides/registry-pattern.md:136`
- **Description**: Public function missing return type annotation
- **Code**:
  ```python
  def reset_registries():
  ```
- **Fix**:
  ```python
  def reset_registries() -> Any: # TODO: fix type
  ```
- **Verification**: `mypy docs/03-guides/registry-pattern.md`

### TYPE-001: Public Function Annotations
- **Rule**: TYPE-001 (Public Function Annotations)
- **Severity**: HIGH
- **File**: `docs/03-guides/development/config-schema-guidelines.md:282`
- **Description**: Public function missing return type annotation
- **Code**:
  ```python
  def test-to_domain-conversion():
  ```
- **Fix**:
  ```python
  def test-to_domain-conversion() -> Any: # TODO: fix type
  ```
- **Verification**: `mypy docs/03-guides/development/config-schema-guidelines.md`

### TYPE-001: Public Function Annotations
- **Rule**: TYPE-001 (Public Function Annotations)
- **Severity**: HIGH
- **File**: `docs/03-guides/development/config-schema-guidelines.md:294`
- **Description**: Public function missing return type annotation
- **Code**:
  ```python
  def test_threshold_validation():
  ```
- **Fix**:
  ```python
  def test_threshold_validation() -> Any: # TODO: fix type
  ```
- **Verification**: `mypy docs/03-guides/development/config-schema-guidelines.md`

### TYPE-001: Public Function Annotations
- **Rule**: TYPE-001 (Public Function Annotations)
- **Severity**: HIGH
- **File**: `docs/exports/full-documentation-no-plans-reports-skills.merged.md:5493`
- **Description**: Public function missing return type annotation
- **Code**:
  ```python
  def test-<provider>-<entity>-config-valid():
  ```
- **Fix**:
  ```python
  def test-<provider>-<entity>-config-valid() -> Any: # TODO: fix type
  ```
- **Verification**: `mypy docs/exports/full-documentation-no-plans-reports-skills.merged.md`

### TYPE-001: Public Function Annotations
- **Rule**: TYPE-001 (Public Function Annotations)
- **Severity**: HIGH
- **File**: `docs/exports/full-documentation-no-plans-reports-skills.merged.md:5503`
- **Description**: Public function missing return type annotation
- **Code**:
  ```python
  def test-<provider>-<entity>-has-sort-by():
  ```
- **Fix**:
  ```python
  def test-<provider>-<entity>-has-sort-by() -> Any: # TODO: fix type
  ```
- **Verification**: `mypy docs/exports/full-documentation-no-plans-reports-skills.merged.md`

### TYPE-001: Public Function Annotations
- **Rule**: TYPE-001 (Public Function Annotations)
- **Severity**: HIGH
- **File**: `docs/exports/full-documentation-no-plans-reports-skills.merged.md:11566`
- **Description**: Public function missing return type annotation
- **Code**:
  ```python
  def test_clear_exports(...):
  ```
- **Fix**:
  ```python
  def test_clear_exports(...) -> Any: # TODO: fix type
  ```
- **Verification**: `mypy docs/exports/full-documentation-no-plans-reports-skills.merged.md`

### TYPE-001: Public Function Annotations
- **Rule**: TYPE-001 (Public Function Annotations)
- **Severity**: HIGH
- **File**: `docs/exports/full-documentation-no-plans-reports-skills.merged.md:12739`
- **Description**: Public function missing return type annotation
- **Code**:
  ```python
  def test-strict-validation-fails-without-schema():
  ```
- **Fix**:
  ```python
  def test-strict-validation-fails-without-schema() -> Any: # TODO: fix type
  ```
- **Verification**: `mypy docs/exports/full-documentation-no-plans-reports-skills.merged.md`

### TYPE-001: Public Function Annotations
- **Rule**: TYPE-001 (Public Function Annotations)
- **Severity**: HIGH
- **File**: `docs/exports/full-documentation-no-plans-reports-skills.merged.md:12757`
- **Description**: Public function missing return type annotation
- **Code**:
  ```python
  def test-non-strict-validation-warns-without-schema(caplog):
  ```
- **Fix**:
  ```python
  def test-non-strict-validation-warns-without-schema(caplog) -> Any: # TODO: fix type
  ```
- **Verification**: `mypy docs/exports/full-documentation-no-plans-reports-skills.merged.md`

### TYPE-001: Public Function Annotations
- **Rule**: TYPE-001 (Public Function Annotations)
- **Severity**: HIGH
- **File**: `docs/exports/full-documentation-no-plans-reports-skills.merged.md:12992`
- **Description**: Public function missing return type annotation
- **Code**:
  ```python
  def test-no-structlog-import-in-application-interfaces(...):
  ```
- **Fix**:
  ```python
  def test-no-structlog-import-in-application-interfaces(...) -> Any: # TODO: fix type
  ```
- **Verification**: `mypy docs/exports/full-documentation-no-plans-reports-skills.merged.md`

### TYPE-001: Public Function Annotations
- **Rule**: TYPE-001 (Public Function Annotations)
- **Severity**: HIGH
- **File**: `docs/exports/full-documentation-no-plans-reports-skills.merged.md:15973`
- **Description**: Public function missing return type annotation
- **Code**:
  ```python
  def test-composite-domain-has-no-infrastructure-imports():
  ```
- **Fix**:
  ```python
  def test-composite-domain-has-no-infrastructure-imports() -> Any: # TODO: fix type
  ```
- **Verification**: `mypy docs/exports/full-documentation-no-plans-reports-skills.merged.md`

## Medium Issues
### AP-006: Print Statement
- **Rule**: AP-006 (Print Statement)
- **Severity**: MEDIUM
- **File**: `docs/03-guides/publication-validation-guide.md:668`
- **Description**: Print statement used instead of structlog
- **Code**:
  ```python
  print(df["doi"].value_counts())
  ```
- **Fix**:
  ```python
  logger.info(df["doi"].value_counts())
  ```
- **Verification**: `grep 'print(' docs/03-guides/publication-validation-guide.md`

### AP-006: Print Statement
- **Rule**: AP-006 (Print Statement)
- **Severity**: MEDIUM
- **File**: `docs/03-guides/dq-configuration.md:352`
- **Description**: Print statement used instead of structlog
- **Code**:
  ```python
  print(f"Soft threshold: {dq_config.soft_fail_threshold}")
  ```
- **Fix**:
  ```python
  logger.info(f"Soft threshold: {dq_config.soft_fail_threshold}")
  ```
- **Verification**: `grep 'print(' docs/03-guides/dq-configuration.md`

### AP-006: Print Statement
- **Rule**: AP-006 (Print Statement)
- **Severity**: MEDIUM
- **File**: `docs/03-guides/dq-configuration.md:353`
- **Description**: Print statement used instead of structlog
- **Code**:
  ```python
  print(f"Hard threshold: {dq_config.hard_fail_threshold}")
  ```
- **Fix**:
  ```python
  logger.info(f"Hard threshold: {dq_config.hard_fail_threshold}")
  ```
- **Verification**: `grep 'print(' docs/03-guides/dq-configuration.md`

### AP-006: Print Statement
- **Rule**: AP-006 (Print Statement)
- **Severity**: MEDIUM
- **File**: `docs/03-guides/dq-configuration.md:354`
- **Description**: Print statement used instead of structlog
- **Code**:
  ```python
  print(f"Field validations: {len(dq_config.field_validations)}")
  ```
- **Fix**:
  ```python
  logger.info(f"Field validations: {len(dq_config.field_validations)}")
  ```
- **Verification**: `grep 'print(' docs/03-guides/dq-configuration.md`

### AP-006: Print Statement
- **Rule**: AP-006 (Print Statement)
- **Severity**: MEDIUM
- **File**: `docs/03-guides/add-pipeline-existing-source.md:112`
- **Description**: Print statement used instead of structlog
- **Code**:
  ```python
  python -c "from bioetl.infrastructure.config_loader import load_pipeline_config; load_pipeline_config('chembl_mechanism'); print('ok')"
  ```
- **Fix**:
  ```python
  python -c "from bioetl.infrastructure.config_loader import load_pipeline_config; load_pipeline_config('chembl_mechanism'); logger.info('ok')"
  ```
- **Verification**: `grep 'print(' docs/03-guides/add-pipeline-existing-source.md`

### AP-006: Print Statement
- **Rule**: AP-006 (Print Statement)
- **Severity**: MEDIUM
- **File**: `docs/03-guides/add-new-source.md:167`
- **Description**: Print statement used instead of structlog
- **Code**:
  ```python
  python -c "from bioetl.infrastructure.config_loader import load_pipeline_config, load_source_config; load_source_config('myprovider'); load_pipeline_config('myprovider_publication'); print('ok')"
  ```
- **Fix**:
  ```python
  python -c "from bioetl.infrastructure.config_loader import load_pipeline_config, load_source_config; load_source_config('myprovider'); load_pipeline_config('myprovider_publication'); logger.info('ok')"
  ```
- **Verification**: `grep 'print(' docs/03-guides/add-new-source.md`

### AP-006: Print Statement
- **Rule**: AP-006 (Print Statement)
- **Severity**: MEDIUM
- **File**: `docs/03-guides/local-storage-layout.md:200`
- **Description**: Print statement used instead of structlog
- **Code**:
  ```python
  print(settings.data-dir)  # Path("data")
  ```
- **Fix**:
  ```python
  logger.info(settings.data-dir)  # Path("data")
  ```
- **Verification**: `grep 'print(' docs/03-guides/local-storage-layout.md`

### AP-006: Print Statement
- **Rule**: AP-006 (Print Statement)
- **Severity**: MEDIUM
- **File**: `docs/03-guides/coverage-configuration.md:185`
- **Description**: Print statement used instead of structlog
- **Code**:
  ```python
  print(x)
  ```
- **Fix**:
  ```python
  logger.info(x)
  ```
- **Verification**: `grep 'print(' docs/03-guides/coverage-configuration.md`

### AP-006: Print Statement
- **Rule**: AP-006 (Print Statement)
- **Severity**: MEDIUM
- **File**: `docs/03-guides/registry-pattern.md:125`
- **Description**: Print statement used instead of structlog
- **Code**:
  ```python
  print(f"Provider not found: {e}")
  ```
- **Fix**:
  ```python
  logger.info(f"Provider not found: {e}")
  ```
- **Verification**: `grep 'print(' docs/03-guides/registry-pattern.md`

### AP-006: Print Statement
- **Rule**: AP-006 (Print Statement)
- **Severity**: MEDIUM
- **File**: `docs/exports/full-documentation-no-plans-reports-skills.merged.md:3778`
- **Description**: Print statement used instead of structlog
- **Code**:
  ```python
  1. I/O в `domain` (`httpx/requests/open()/print()` и т.п.).
  ```
- **Fix**:
  ```python
  1. I/O в `domain` (`httpx/requests/open()/logger.info()` и т.п.).
  ```
- **Verification**: `grep 'print(' docs/exports/full-documentation-no-plans-reports-skills.merged.md`

## Positive Observations
- Hexagonal architecture directory structure is strictly maintained.
