# Code Review Report — S5: Cross-cutting
**Date**: 2026-03-13
**Files reviewed**: 998
**Total LOC**: 124913
**Status**: WARN
**Score**: 6.9/10.0
---
## Summary

| Category | Issues | CRIT | HIGH | MED | LOW | Score |
|----------|--------|------|------|-----|-----|-------|
| Architecture | 0 | 0 | 0 | 0 | 0 | 10.0 |
| Anti-Patterns | 0 | 0 | 0 | 0 | 0 | 10.0 |
| DI Violations | 15 | 0 | 15 | 0 | 0 | 0.0 |
| Naming | 2 | 0 | 0 | 2 | 0 | 9.0 |
| Types | 43 | 0 | 0 | 0 | 43 | 0.0 |
| Testing | 0 | 0 | 0 | 0 | 0 | 10.0 |
| **TOTAL** | **60** | **0** | **15** | **2** | **43** | **6.9** |

## High Issues

### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `src/bioetl/infrastructure/adapters/base.py:161`
- **Description**: Direct instantiation of AdapterMetrics in class attribute
- **Code**:
  ```python
  self._adapter_metrics = AdapterMetrics(metrics_port, self.provider_name)
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `src/bioetl/infrastructure/adapters/base.py:162`
- **Description**: Direct instantiation of APIRequestCollector in class attribute
- **Code**:
  ```python
  self._request_collector = APIRequestCollector()
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `src/bioetl/infrastructure/export/dq_report_writer.py:59`
- **Description**: Direct instantiation of DQReportSerializer in class attribute
- **Code**:
  ```python
  self._serializer = DQReportSerializer()
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
- **File**: `src/bioetl/infrastructure/observability/tracing.py:90`
- **Description**: Direct instantiation of TracerProvider in class attribute
- **Code**:
  ```python
  self._provider = TracerProvider()
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
- **File**: `src/bioetl/infrastructure/adapters/chembl/client.py:97`
- **Description**: Direct instantiation of ErrorService in class attribute
- **Code**:
  ```python
  self._error_handler = ErrorService(self._logger, metrics=metrics_port)
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
- **File**: `src/bioetl/domain/aggregates/_quarantine_entry_transitions_mixin.py:56`
- **Description**: Direct instantiation of ResolutionInfo in class attribute
- **Code**:
  ```python
  self._resolution_info = ResolutionInfo(
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `src/bioetl/domain/aggregates/_quarantine_entry_transitions_mixin.py:95`
- **Description**: Direct instantiation of ResolutionInfo in class attribute
- **Code**:
  ```python
  self._resolution_info = ResolutionInfo(
  ```
### DI-001: Hard-coded Constructor Dependency
- **Rule**: DI-001 (Hard-coded Constructor Dependency)
- **Severity**: HIGH
- **File**: `src/bioetl/domain/aggregates/_quarantine_entry_transitions_mixin.py:129`
- **Description**: Direct instantiation of ResolutionInfo in class attribute
- **Code**:
  ```python
  self._resolution_info = ResolutionInfo(
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
- **File**: `src/bioetl/infrastructure/adapters/semanticscholar/adapter.py:191`
- **Description**: Direct instantiation of ComposableFallbackDecorator in class attribute
- **Code**:
  ```python
  self._fallback_decorator = ComposableFallbackDecorator(
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
## Medium Issues

### NAME-001: Invalid Class Suffix
- **Rule**: NAME-001 (Invalid Class Suffix)
- **Severity**: MEDIUM
- **File**: `src/bioetl/application/pipelines/uniprot/extractors/extractor_helpers.py:16`
- **Description**: Class 'ExtractorHelper' uses an invalid suffix (Manager/Utils/Helper)
- **Code**:
  ```python
  class ExtractorHelper:
  ```
### NAME-001: Invalid Class Suffix
- **Rule**: NAME-001 (Invalid Class Suffix)
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/storage/retention_manager.py:34`
- **Description**: Class 'RetentionManager' uses an invalid suffix (Manager/Utils/Helper)
- **Code**:
  ```python
  class RetentionManager:
  ```
## Low Issues

### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/domain/transformations/hashing.py:27`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def _normalize_value(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/domain/ports/observability/logging.py:35`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def warning(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/domain/ports/observability/logging.py:75`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def exception(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/domain/entities/bioactivity/_converters.py:36`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def _require_field(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/infrastructure/observability/logging_config.py:109`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def secret_filter_processor(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/domain/services/text_normalization.py:85`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def normalize_to_string(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/domain/value_objects/base.py:93`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def __setattr__(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/infrastructure/config/_yaml_settings_source.py:35`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def prepare_field_value(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/infrastructure/adapters/http/client_retry_mixin.py:24`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def _can_retry(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/infrastructure/adapters/http/client_retry_mixin.py:44`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def _record_request_metrics(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/application/pipelines/common/base_publication_transformer.py:195`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def _log_fallback_if_needed(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/application/pipelines/common/base_publication_transformer.py:213`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def _compute_identifiers(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/application/pipelines/semanticscholar/transformer.py:129`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def _resolve_publication_type(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/application/pipelines/semanticscholar/transformer.py:158`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def _extract_author_metadata(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/application/pipelines/semanticscholar/transformer.py:299`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def entity_to_silver_record(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/infrastructure/storage/gold_writer.py:294`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def _set_write_span_attributes(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/infrastructure/observability/logging.py:124`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def warning(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/infrastructure/observability/logging.py:164`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def exception(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/domain/ports/observability/tracing.py:12`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def get_tracer(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/application/pipelines/chembl/assay_parameters_transformer.py:98`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def _normalize_type(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/application/core/publication_term_extraction_mixin.py:57`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def _extract_terms_from_publication(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/application/core/publication_term_extraction_mixin.py:125`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def _create_term_record(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/application/core/publication_term_extraction_mixin.py:159`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def _compute_entity_id(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/infrastructure/observability/unified_logger.py:178`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def warning(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/infrastructure/observability/unified_logger.py:235`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def exception(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/domain/ports/data_source.py:219`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def create(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/application/services/data_quality_service.py:268`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def _process_single_anomaly(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/application/pipelines/chembl/publication_transformer.py:302`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def entity_to_silver_record(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/infrastructure/storage/base_delta_writer.py:39`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def _serialize_value(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/application/core/_data_source_mixins.py:26`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def get_source_metadata(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/application/pipelines/crossref/transformer.py:226`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def entity_to_silver_record(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/application/core/batch_writer_columns_mixin.py:24`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def _get_schema_columns(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/application/core/base_transformer/base.py:144`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def _start_transform_span(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/application/core/base_transformer/base.py:182`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def _handle_transformation_error(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/application/core/base_transformer/base.py:200`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def _handle_validation_error(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/application/core/base_transformer/base.py:217`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def _record_metrics_and_close_span(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/domain/value_objects/molecular_descriptors.py:91`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def _validate(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/domain/value_objects/molecular_descriptors.py:165`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def _validate(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/application/core/publication_term_filtering_mixin.py:17`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def _ensure_filterable(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/application/core/subcellular_fraction_data_source.py:109`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def _normalize_fraction(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/domain/services/dq_serializer.py:47`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def _serialize_dataclass(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/domain/services/dq_serializer.py:71`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def _serialize_value(
  ```
### TYPE-002: Unjustified Any Usage
- **Rule**: TYPE-002 (Unjustified Any Usage)
- **Severity**: LOW
- **File**: `src/bioetl/application/pipelines/pubmed/transformer.py:269`
- **Description**: Usage of Any without comment justification
- **Code**:
  ```python
  def entity_to_silver_record(
  ```
## Positive Observations
- AST parsing and file processing completed successfully.

## Scoring Calculation
| Category | Weight | Raw Score | Deductions | Weighted |
|----------|--------|-----------|------------|----------|
| Architecture | 30% | 10.0 | -0.00 | 3.00 |
| Anti-Patterns | 25% | 10.0 | -0.00 | 2.50 |
| DI Violations | 20% | 10.0 | -15.00 | 0.00 |
| Naming | 10% | 10.0 | -1.00 | 0.90 |
| Types | 10% | 10.0 | -10.75 | 0.00 |
| Testing | 5% | 10.0 | -0.00 | 0.50 |
| **FINAL** | **100%** | | | **6.9** |
