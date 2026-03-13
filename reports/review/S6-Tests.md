# Consolidated Review — S6: Tests
**Date**: 2026-03-13
**Sub-reviews**: 6 agents
**Status**: WARN
**Consolidated Score**: 9.2/10.0

## Sub-review Summary
| Sub-sector | Files | Score | Status | CRIT | HIGH |
|------------|-------|-------|--------|------|------|
| S6.1 — architecture | 116 | 9.9 | PASS | 0 | 0 |
| S6.2 — domain | 164 | 10.0 | PASS | 0 | 0 |
| S6.3 — application | 157 | 7.7 | WARN | 0 | 33 |
| S6.4 — infrastructure | 179 | 8.6 | PASS | 0 | 7 |
| S6.5 — composition_interfaces_etc | 96 | 9.8 | PASS | 0 | 0 |
| S6.6 — integration_e2e_etc | 120 | 9.9 | PASS | 0 | 0 |

## Aggregated Issues
### High

### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/core/test_publication_term_data_source.py:26`
- **Description**: Direct instantiation of AsyncMock in class attribute
- **Code**:
  ```python
  self.__aenter__ = AsyncMock(return_value=self)
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/core/test_publication_term_data_source.py:27`
- **Description**: Direct instantiation of AsyncMock in class attribute
- **Code**:
  ```python
  self.__aexit__ = AsyncMock(return_value=None)
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/core/test_publication_term_data_source.py:28`
- **Description**: Direct instantiation of AsyncMock in class attribute
- **Code**:
  ```python
  self.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/core/test_publication_term_data_source.py:29`
- **Description**: Direct instantiation of AsyncMock in class attribute
- **Code**:
  ```python
  self.aclose = AsyncMock()
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/core/test_publication_term_data_source.py:541`
- **Description**: Direct instantiation of AsyncMock in class attribute
- **Code**:
  ```python
  self.__aenter__ = AsyncMock(return_value=self)
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/core/test_publication_term_data_source.py:542`
- **Description**: Direct instantiation of AsyncMock in class attribute
- **Code**:
  ```python
  self.__aexit__ = AsyncMock(return_value=None)
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/core/test_publication_term_data_source.py:543`
- **Description**: Direct instantiation of AsyncMock in class attribute
- **Code**:
  ```python
  self.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/core/test_publication_term_data_source.py:544`
- **Description**: Direct instantiation of AsyncMock in class attribute
- **Code**:
  ```python
  self.aclose = AsyncMock()
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/core/test_batch_executor_dq_mixin.py:48`
- **Description**: Direct instantiation of SimpleNamespace in class attribute
- **Code**:
  ```python
  self._services = SimpleNamespace(dq_report_service=object())
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/core/test_batch_executor_dq_mixin.py:49`
- **Description**: Direct instantiation of SimpleNamespace in class attribute
- **Code**:
  ```python
  self._context = SimpleNamespace(run_id="run-1")
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/core/test_batch_executor_dq_mixin.py:50`
- **Description**: Direct instantiation of SimpleNamespace in class attribute
- **Code**:
  ```python
  self._config = SimpleNamespace(
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/core/test_filtered_data_source.py:24`
- **Description**: Direct instantiation of AsyncMock in class attribute
- **Code**:
  ```python
  self.__aenter__ = AsyncMock(return_value=self)
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/core/test_filtered_data_source.py:25`
- **Description**: Direct instantiation of AsyncMock in class attribute
- **Code**:
  ```python
  self.__aexit__ = AsyncMock(return_value=None)
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/core/test_filtered_data_source.py:26`
- **Description**: Direct instantiation of AsyncMock in class attribute
- **Code**:
  ```python
  self.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/core/test_filtered_data_source.py:27`
- **Description**: Direct instantiation of AsyncMock in class attribute
- **Code**:
  ```python
  self.aclose = AsyncMock()
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/core/test_filtered_data_source.py:43`
- **Description**: Direct instantiation of AsyncMock in class attribute
- **Code**:
  ```python
  self.__aenter__ = AsyncMock(return_value=self)
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/core/test_filtered_data_source.py:44`
- **Description**: Direct instantiation of AsyncMock in class attribute
- **Code**:
  ```python
  self.__aexit__ = AsyncMock(return_value=None)
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/core/test_filtered_data_source.py:45`
- **Description**: Direct instantiation of AsyncMock in class attribute
- **Code**:
  ```python
  self.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/core/test_filtered_data_source.py:46`
- **Description**: Direct instantiation of AsyncMock in class attribute
- **Code**:
  ```python
  self.aclose = AsyncMock()
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/composite/test_runner_checkpoint_resume.py:103`
- **Description**: Direct instantiation of MagicMock in class attribute
- **Code**:
  ```python
  self._executor = MagicMock()
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/composite/test_runner_required_flag.py:113`
- **Description**: Direct instantiation of MagicMock in class attribute
- **Code**:
  ```python
  self._executor = MagicMock()
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/composite/test_column_orderer_renames.py:13`
- **Description**: Direct instantiation of NoOpLogger in class attribute
- **Code**:
  ```python
  self.logger = NoOpLogger()
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/core/test_subcellular_fraction_data_source.py:23`
- **Description**: Direct instantiation of AsyncMock in class attribute
- **Code**:
  ```python
  self.__aenter__ = AsyncMock(return_value=self)
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/core/test_subcellular_fraction_data_source.py:24`
- **Description**: Direct instantiation of AsyncMock in class attribute
- **Code**:
  ```python
  self.__aexit__ = AsyncMock(return_value=None)
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/core/test_subcellular_fraction_data_source.py:25`
- **Description**: Direct instantiation of AsyncMock in class attribute
- **Code**:
  ```python
  self.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/core/test_subcellular_fraction_data_source.py:26`
- **Description**: Direct instantiation of AsyncMock in class attribute
- **Code**:
  ```python
  self.aclose = AsyncMock()
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/core/test_subcellular_fraction_data_source.py:40`
- **Description**: Direct instantiation of AsyncMock in class attribute
- **Code**:
  ```python
  self.__aenter__ = AsyncMock(return_value=self)
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/core/test_subcellular_fraction_data_source.py:41`
- **Description**: Direct instantiation of AsyncMock in class attribute
- **Code**:
  ```python
  self.__aexit__ = AsyncMock(return_value=None)
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/core/test_subcellular_fraction_data_source.py:42`
- **Description**: Direct instantiation of AsyncMock in class attribute
- **Code**:
  ```python
  self.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/core/test_subcellular_fraction_data_source.py:43`
- **Description**: Direct instantiation of AsyncMock in class attribute
- **Code**:
  ```python
  self.aclose = AsyncMock()
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/composite/test_runner_observability_mixin.py:22`
- **Description**: Direct instantiation of SimpleNamespace in class attribute
- **Code**:
  ```python
  self._config = SimpleNamespace(
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/composite/test_runner_observability_mixin.py:33`
- **Description**: Direct instantiation of MagicMock in class attribute
- **Code**:
  ```python
  self._logger = MagicMock()
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/application/composite/test_runner.py:86`
- **Description**: Direct instantiation of MagicMock in class attribute
- **Code**:
  ```python
  self._executor = MagicMock()
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/infrastructure/adapters/test_client_retry_mixin.py:41`
- **Description**: Direct instantiation of MagicMock in class attribute
- **Code**:
  ```python
  self._metrics = MagicMock()
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/infrastructure/adapters/test_client_retry_mixin.py:42`
- **Description**: Direct instantiation of AsyncMock in class attribute
- **Code**:
  ```python
  self.rate_limiter = AsyncMock()
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/infrastructure/adapters/test_client_retry_mixin.py:43`
- **Description**: Direct instantiation of AsyncMock in class attribute
- **Code**:
  ```python
  self.circuit_breaker = AsyncMock()
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/infrastructure/adapters/semanticscholar/test_batch_request_mixin.py:34`
- **Description**: Direct instantiation of MagicMock in class attribute
- **Code**:
  ```python
  self._logger = MagicMock()
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/infrastructure/adapters/semanticscholar/test_batch_request_mixin.py:37`
- **Description**: Direct instantiation of MagicMock in class attribute
- **Code**:
  ```python
  self._http_client = MagicMock()
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/infrastructure/adapters/semanticscholar/test_batch_request_mixin.py:39`
- **Description**: Direct instantiation of MagicMock in class attribute
- **Code**:
  ```python
  self._request_collector = MagicMock()
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `tests/unit/infrastructure/adapters/openalex/test_client_helpers_adapter_mixin.py:21`
- **Description**: Direct instantiation of APIRequestCollector in class attribute
- **Code**:
  ```python
  self._request_collector = APIRequestCollector()
  ```
## Cross-subzone Observations
- Verified zero overlap between subzones.
- Corrected score distributions applied.

## Top Recommendations
1. Review reported violations.
