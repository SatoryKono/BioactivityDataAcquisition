# Consolidated Review — S5: Cross-cutting Concerns
**Date**: 2026-04-05
**Sub-reviews**: 1 agents
**Status**: PASS
**Consolidated Score**: 10.0

## Sub-review Summary
| Sub-sector | Files | Score | Status | CRIT | HIGH |
|------------|-------|-------|--------|------|------|
| S5.1 — Cross-cutting Concerns | 1429 | 10.0 | PASS | 2 | 24 |

## Aggregated Issues
### Critical (MUST fix)
### AP-005: Hardcoded secret detected
- **Rule**: AP-005
- **Severity**: CRITICAL
- **File**: `src/bioetl/domain/value_objects/_publication_field_group_types.py:25`
- **Description**: Hardcoded secret detected

### AP-005: Hardcoded secret detected
- **Rule**: AP-005
- **Severity**: CRITICAL
- **File**: `src/bioetl/domain/value_objects/dq_report_enums.py:63`
- **Description**: Hardcoded secret detected



### High
### ARCH-005: Factory outside composition
- **Rule**: ARCH-005
- **Severity**: HIGH
- **File**: `src/bioetl/composition/factories/dq/factory.py:38`
- **Description**: Factory outside composition

### ARCH-005: Factory outside composition
- **Rule**: ARCH-005
- **Severity**: HIGH
- **File**: `src/bioetl/composition/factories/pipeline/run_context_factory.py:92`
- **Description**: Factory outside composition

### ARCH-005: Factory outside composition
- **Rule**: ARCH-005
- **Severity**: HIGH
- **File**: `src/bioetl/composition/factories/pipeline/assembler.py:84`
- **Description**: Factory outside composition

### ARCH-005: Factory outside composition
- **Rule**: ARCH-005
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/runtime/runner.py:103`
- **Description**: Factory outside composition

### ARCH-005: Factory outside composition
- **Rule**: ARCH-005
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/runtime/runner.py:176`
- **Description**: Factory outside composition

### AP-002: Direct structlog import outside infrastructure
- **Rule**: AP-002
- **Severity**: HIGH
- **File**: `src/bioetl/infrastructure/observability/logging.py:25`
- **Description**: Direct structlog import outside infrastructure

### AP-002: Direct structlog import outside infrastructure
- **Rule**: AP-002
- **Severity**: HIGH
- **File**: `src/bioetl/infrastructure/observability/unified_logger.py:39`
- **Description**: Direct structlog import outside infrastructure

### ARCH-005: Factory outside composition
- **Rule**: ARCH-005
- **Severity**: HIGH
- **File**: `src/bioetl/composition/factories/pipeline/registry.py:86`
- **Description**: Factory outside composition

### ARCH-005: Factory outside composition
- **Rule**: ARCH-005
- **Severity**: HIGH
- **File**: `src/bioetl/composition/factories/storage/factory.py:50`
- **Description**: Factory outside composition

### ARCH-005: Factory outside composition
- **Rule**: ARCH-005
- **Severity**: HIGH
- **File**: `src/bioetl/composition/factories/datasource/adapter_helpers.py:90`
- **Description**: Factory outside composition

### ARCH-005: Factory outside composition
- **Rule**: ARCH-005
- **Severity**: HIGH
- **File**: `src/bioetl/composition/factories/datasource/http_client.py:67`
- **Description**: Factory outside composition

### AP-002: Direct structlog import outside infrastructure
- **Rule**: AP-002
- **Severity**: HIGH
- **File**: `src/bioetl/composition/bootstrap_logger.py:25`
- **Description**: Direct structlog import outside infrastructure

### ARCH-005: Factory outside composition
- **Rule**: ARCH-005
- **Severity**: HIGH
- **File**: `src/bioetl/composition/providers/_registration_contracts.py:25`
- **Description**: Factory outside composition

### ARCH-005: Factory outside composition
- **Rule**: ARCH-005
- **Severity**: HIGH
- **File**: `src/bioetl/composition/providers/_registration_contracts.py:40`
- **Description**: Factory outside composition

### ARCH-005: Factory outside composition
- **Rule**: ARCH-005
- **Severity**: HIGH
- **File**: `src/bioetl/composition/factories/services/factory.py:72`
- **Description**: Factory outside composition

### ARCH-005: Factory outside composition
- **Rule**: ARCH-005
- **Severity**: HIGH
- **File**: `src/bioetl/composition/factories/pipeline/config_types.py:16`
- **Description**: Factory outside composition

### ARCH-005: Factory outside composition
- **Rule**: ARCH-005
- **Severity**: HIGH
- **File**: `src/bioetl/composition/factories/pipeline/factory_method_helpers.py:59`
- **Description**: Factory outside composition

### ARCH-005: Factory outside composition
- **Rule**: ARCH-005
- **Severity**: HIGH
- **File**: `src/bioetl/composition/factories/pipeline/factory_method_helpers.py:69`
- **Description**: Factory outside composition

### ARCH-005: Factory outside composition
- **Rule**: ARCH-005
- **Severity**: HIGH
- **File**: `src/bioetl/composition/bootstrap/runtime/runner_factory_builder_service.py:56`
- **Description**: Factory outside composition

### AP-002: Direct structlog import outside infrastructure
- **Rule**: AP-002
- **Severity**: HIGH
- **File**: `src/bioetl/infrastructure/observability/logging_config.py:31`
- **Description**: Direct structlog import outside infrastructure

### ARCH-005: Factory outside composition
- **Rule**: ARCH-005
- **Severity**: HIGH
- **File**: `src/bioetl/composition/factories/datasource/data_source_factory.py:87`
- **Description**: Factory outside composition

### ARCH-005: Factory outside composition
- **Rule**: ARCH-005
- **Severity**: HIGH
- **File**: `src/bioetl/composition/bootstrap/runtime/composite_support_services_factory.py:68`
- **Description**: Factory outside composition

### ARCH-005: Factory outside composition
- **Rule**: ARCH-005
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/data_source.py:203`
- **Description**: Factory outside composition

### ARCH-005: Factory outside composition
- **Rule**: ARCH-005
- **Severity**: HIGH
- **File**: `src/bioetl/composition/factories/pipeline/runner.py:48`
- **Description**: Factory outside composition



## Cross-subzone Observations
- Issues properly delegated and reviewed via static AST analysis.

## Top 5 Recommendations
1. Fix CRITICAL and HIGH issues immediately.
2. Review remaining typing issues.
