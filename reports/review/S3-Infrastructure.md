# Consolidated Review — S3: Infrastructure
**Date**: 2026-03-13
**Sub-reviews**: 5 agents
**Status**: PASS
**Consolidated Score**: 9.6/10.0

## Sub-review Summary
| Sub-sector | Files | Score | Status | CRIT | HIGH |
|------------|-------|-------|--------|------|------|
| S3.1 — adapters1 | 38 | 9.6 | PASS | 0 | 2 |
| S3.2 — adapters2 | 57 | 9.4 | PASS | 0 | 3 |
| S3.3 — adapters3 | 27 | 9.8 | PASS | 0 | 1 |
| S3.4 — storage_config_schemas | 76 | 9.7 | PASS | 0 | 1 |
| S3.5 — observability_other | 28 | 9.5 | PASS | 0 | 2 |

## Aggregated Issues
### High

### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `src/bioetl/infrastructure/adapters/chembl/client.py:97`
- **Description**: Direct instantiation of ErrorService in class attribute
- **Code**:
  ```python
  self._error_handler = ErrorService(self._logger, metrics=metrics_port)
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `src/bioetl/infrastructure/adapters/pubmed/pubmed_client.py:173`
- **Description**: Direct instantiation of ComposableFallbackDecorator in class attribute
- **Code**:
  ```python
  self._fallback_decorator = ComposableFallbackDecorator(
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `src/bioetl/infrastructure/adapters/pubchem/fetch_strategies.py:154`
- **Description**: Direct instantiation of PubChemResponseMapper in class attribute
- **Code**:
  ```python
  self._response_mapper = PubChemResponseMapper(mapper)
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `src/bioetl/infrastructure/adapters/pubchem/fetch_strategies.py:155`
- **Description**: Direct instantiation of PubChemFetchFlowService in class attribute
- **Code**:
  ```python
  self._fetch_flow = PubChemFetchFlowService(
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `src/bioetl/infrastructure/adapters/semanticscholar/adapter.py:191`
- **Description**: Direct instantiation of ComposableFallbackDecorator in class attribute
- **Code**:
  ```python
  self._fallback_decorator = ComposableFallbackDecorator(
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `src/bioetl/infrastructure/adapters/common/fallback_policy_mixin.py:117`
- **Description**: Direct instantiation of ComposableFallbackDecorator in class attribute
- **Code**:
  ```python
  self._fallback_decorator = ComposableFallbackDecorator(
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `src/bioetl/infrastructure/storage/base_delta_writer.py:184`
- **Description**: Direct instantiation of RetentionManager in class attribute
- **Code**:
  ```python
  self._retention_manager = RetentionManager(base_path)
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `src/bioetl/infrastructure/observability/anomaly/monitor.py:64`
- **Description**: Direct instantiation of AnomalyDetector in class attribute
- **Code**:
  ```python
  self.detector = AnomalyDetector(
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `src/bioetl/infrastructure/observability/tracing.py:90`
- **Description**: Direct instantiation of TracerProvider in class attribute
- **Code**:
  ```python
  self._provider = TracerProvider()
  ```
## Cross-subzone Observations
- Verified zero overlap between subzones.
- Corrected score distributions applied.

## Top Recommendations
1. Review reported violations.
