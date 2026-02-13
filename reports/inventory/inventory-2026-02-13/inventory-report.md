# Code Inventory Report — BioETL

Date: 2026-02-13
Scope: src/bioetl/ (all layers)

## Executive Summary

| Метрика                      | Значение                         |
| ---------------------------- | -------------------------------- |
| Всего классов                | 878                              |
| Всего функций (module-level) | 564                              |
| Всего констант               | 132                              |
| Мёртвых объектов (DEAD)      | 9                                |
| Дублей (confirmed)           | 0 (manual verification required) |
| Дублей (suspected)           | 264 structural signature groups  |

Полный реестр: `reports/inventory/inventory-2026-02-13/object-registry.csv`.

## 1. Реестр Объектов

### 1.1 Domain Layer

| Classes | Functions | Constants | Type aliases | Total objects |
| ------: | --------: | --------: | -----------: | ------------: |
|     410 |       154 |        30 |            1 |           595 |

### 1.2 Application Layer

| Classes | Functions | Constants | Type aliases | Total objects |
| ------: | --------: | --------: | -----------: | ------------: |
|     181 |       127 |        15 |            1 |           324 |

### 1.3 Infrastructure Layer

| Classes | Functions | Constants | Type aliases | Total objects |
| ------: | --------: | --------: | -----------: | ------------: |
|     250 |        70 |        73 |            0 |           393 |

### 1.4 Composition Layer

| Classes | Functions | Constants | Type aliases | Total objects |
| ------: | --------: | --------: | -----------: | ------------: |
|      33 |       141 |         4 |            1 |           179 |

### 1.5 Interfaces Layer

| Classes | Functions | Constants | Type aliases | Total objects |
| ------: | --------: | --------: | -----------: | ------------: |
|       4 |        72 |        10 |            0 |            86 |

### 1.6 Проверка `__all__` экспортов

| #   | Module                                                             | Missing exports in namespace                                                                                                                                                                                                                                                                                             |
| --- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | `bioetl.infrastructure.serialization.encoders`                     | `ORJSON_AVAILABLE`                                                                                                                                                                                                                                                                                                       |
| 2   | `bioetl.composition.factories.pipeline_factories`                  | `PIPELINE_CONFIGS`                                                                                                                                                                                                                                                                                                       |
| 3   | `bioetl.interfaces.cli.exit_codes`                                 | `EXCEPTION_EXIT_CODES`                                                                                                                                                                                                                                                                                                   |
| 4   | `bioetl.application.pipelines.chembl.assay_parameters_transformer` | `KNOWN_PARAM_TYPES`                                                                                                                                                                                                                                                                                                      |
| 5   | `bioetl.application.core.field_specs`                              | `FLOAT`, `INT`, `PMID`, `STR`                                                                                                                                                                                                                                                                                            |
| 6   | `bioetl.domain.composite.field_groups`                             | `DEFAULT_PROVIDER_ORDER`                                                                                                                                                                                                                                                                                                 |
| 7   | `bioetl.domain.schemas.column_order`                               | `ALL_SYSTEM_FIELDS`, `DQ_FIELDS_SUFFIX`, `SYSTEM_FIELDS_PREFIX`                                                                                                                                                                                                                                                          |
| 8   | `bioetl.domain.schemas.constants`                                  | `ACTIVITY_STANDARD_TYPES`, `ASSAY_CATEGORIES`, `ASSAY_PARAMETER_STANDARD_TYPES`, `ASSAY_TEST_TYPES`, `ASSAY_TYPES`, `DATA_VALIDITY_COMMENTS`, `MAX_PHASE_VALUES`, `MOLECULE_TYPES`, `PUBLICATION_TYPES`, `RELATIONSHIP_TYPES`, `STANDARD_RELATIONS`, `STRUCTURE_TYPES`, `TARGET_COMPONENT_RELATIONSHIPS`, `TARGET_TYPES` |
| 9   | `bioetl.domain.value_objects.column_order`                         | `DEFAULT_COLUMN_ORDER`, `PUBLICATION_FIELD_GROUPS`                                                                                                                                                                                                                                                                       |
| 10  | `bioetl.domain.value_objects.publication_field_groups`             | `DEFAULT_FIELD_GROUP_CONFIG`, `FIELD_TO_GROUP_MAPPING`                                                                                                                                                                                                                                                                   |
| 11  | `bioetl.domain.value_objects.column_qualifier`                     | `JOIN_KEY_COLUMNS`                                                                                                                                                                                                                                                                                                       |

## 2. Dead Code

### 2.1 DEAD объекты (0 ссылок)

| #   | Object                                 | Type     | Layer          | File:Line                                                      |
| --- | -------------------------------------- | -------- | -------------- | -------------------------------------------------------------- |
| 1   | CIRCUIT_BREAKER_HELPERS                | constant | infrastructure | src/bioetl/infrastructure/adapters/http/circuit_breaker.py:235 |
| 2   | METRICS_COLLECTOR                      | constant | infrastructure | src/bioetl/infrastructure/observability/metrics.py:221         |
| 3   | LOGGING_API                            | constant | infrastructure | src/bioetl/infrastructure/observability/logging.py:52          |
| 4   | BOOTSTRAP_LOGGER_EXPORTS               | constant | composition    | src/bioetl/composition/bootstrap_logger.py:140                 |
| 5   | EXIT_CODE_HELPERS                      | constant | interfaces     | src/bioetl/interfaces/cli/exit_codes.py:120                    |
| 6   | RUN_HEALTH_SERVER                      | constant | interfaces     | src/bioetl/interfaces/http/health_server.py:305                |
| 7   | PARSER_HELPERS                         | constant | application    | src/bioetl/application/pipelines/pubmed/xml_parser.py:79       |
| 8   | compute_subcellular_fraction_entity_id | function | application    | src/bioetl/application/core/entity_id.py:36                    |
| 9   | VALIDATION_API                         | constant | domain         | src/bioetl/domain/validation.py:412                            |

### 2.2 TEST_ONLY объекты

| #   | Object                        | Type     | Layer          | File:Line                                              |
| --- | ----------------------------- | -------- | -------------- | ------------------------------------------------------ |
| 1   | PIPELINE_HEALTH_CHECK_PASSED  | constant | infrastructure | src/bioetl/infrastructure/observability/metrics.py:148 |
| 2   | INFRASTRUCTURE_VALIDATED      | constant | infrastructure | src/bioetl/infrastructure/observability/metrics.py:154 |
| 3   | HEALTH_CHECK_DURATION_SECONDS | constant | infrastructure | src/bioetl/infrastructure/observability/metrics.py:160 |
| 4   | TransformerPort               | class    | application    | src/bioetl/application/core/protocols.py:49            |

### 2.3 SELF_ONLY объекты

| #   | Object                          | Type     | Layer          | File:Line                                                     |
| --- | ------------------------------- | -------- | -------------- | ------------------------------------------------------------- |
| 1   | \_load_base_config              | function | infrastructure | src/bioetl/infrastructure/config_loader.py:54                 |
| 2   | \_apply_file_reference_defaults | function | infrastructure | src/bioetl/infrastructure/config_loader.py:70                 |
| 3   | \_load_column_groups_config     | function | infrastructure | src/bioetl/infrastructure/config_loader.py:90                 |
| 4   | \_load_data_schema_config       | function | infrastructure | src/bioetl/infrastructure/config_loader.py:112                |
| 5   | \_apply_layer_defaults          | function | infrastructure | src/bioetl/infrastructure/config_loader.py:151                |
| 6   | \_apply_convention_defaults     | function | infrastructure | src/bioetl/infrastructure/config_loader.py:179                |
| 7   | \_load_filter_config            | function | infrastructure | src/bioetl/infrastructure/config_loader.py:230                |
| 8   | \_merge_filter_config           | function | infrastructure | src/bioetl/infrastructure/config_loader.py:250                |
| 9   | \_load_column_groups_section    | function | infrastructure | src/bioetl/infrastructure/config_loader.py:309                |
| 10  | \_load_source_section           | function | infrastructure | src/bioetl/infrastructure/config_loader.py:338                |
| 11  | \_check_psutil_available        | function | infrastructure | src/bioetl/infrastructure/system/memory_monitor.py:39         |
| 12  | BasePanderaValidator            | class    | infrastructure | src/bioetl/infrastructure/validation/pandera_validator.py:20  |
| 13  | NoOpValidator                   | class    | infrastructure | src/bioetl/infrastructure/validation/pandera_validator.py:192 |
| 14  | \_get_git_commit_cached         | function | infrastructure | src/bioetl/infrastructure/storage/metadata_builder.py:39      |
| 15  | \_get_string_fields             | function | infrastructure | src/bioetl/infrastructure/storage/base_delta_writer.py:63     |
| 16  | METADATA_FILENAME               | constant | infrastructure | src/bioetl/infrastructure/storage/metadata_writer.py:31       |
| 17  | \_get_metadata_filename         | function | infrastructure | src/bioetl/infrastructure/storage/metadata_writer.py:34       |
| 18  | AtomicWriteError                | class    | infrastructure | src/bioetl/infrastructure/storage/\_atomic.py:26              |
| 19  | atomic_write                    | function | infrastructure | src/bioetl/infrastructure/storage/\_atomic.py:36              |
| 20  | ErrorCategory                   | class    | infrastructure | src/bioetl/infrastructure/adapters/error_handling.py:41       |
| 21  | AdapterErrorContext             | class    | infrastructure | src/bioetl/infrastructure/adapters/error_handling.py:80       |
| 22  | HealthCheckContext              | class    | infrastructure | src/bioetl/infrastructure/adapters/health_check_mixin.py:36   |
| 23  | HealthCheckMixin                | class    | infrastructure | src/bioetl/infrastructure/adapters/health_check_mixin.py:58   |
| 24  | HasFetchFiltered                | class    | infrastructure | src/bioetl/infrastructure/adapters/filterable_mixin.py:23     |
| 25  | DelegatingFallbackMixin         | class    | infrastructure | src/bioetl/infrastructure/adapters/filterable_mixin.py:86     |
| 26  | UniProtEcNumber                 | class    | infrastructure | src/bioetl/infrastructure/adapters/uniprot/models.py:20       |
| 27  | UniProtKeyword                  | class    | infrastructure | src/bioetl/infrastructure/adapters/uniprot/models.py:28       |
| 28  | UniProtOrganism                 | class    | infrastructure | src/bioetl/infrastructure/adapters/uniprot/models.py:38       |
| 29  | UniProtName                     | class    | infrastructure | src/bioetl/infrastructure/adapters/uniprot/models.py:53       |
| 30  | UniProtFullName                 | class    | infrastructure | src/bioetl/infrastructure/adapters/uniprot/models.py:61       |

### 2.4 Orphan-модули (файлы без imports)

| #   | File | Recommendation |
| --- | ---- | -------------- |

### 2.5 Неиспользуемые импорты

`pyflakes` не установлен в окружении; требуется отдельный запуск в CI/dev-контейнере.

## 3. Duplicate Logic

### 3.1 Confirmed Duplicates

Не подтверждались автоматически (требуется ручная верификация по правилам исключений).

### 3.2 Suspected Duplicates (structural signatures)

| #   | Signature                                                                                            | Occurrences |
| --- | ---------------------------------------------------------------------------------------------------- | ----------- |
| 1   | `aclose(self)`                                                                                       | 35          |
| 2   | `to_domain(self)`                                                                                    | 27          |
| 3   | `fetch(self, entity_type, limit, query, filter_ids, filter_field)`                                   | 16          |
| 4   | `_validate_invariants(self)`                                                                         | 16          |
| 5   | `_validate(self, value)`                                                                             | 16          |
| 6   | `_extract_business_data(self, record, primary_id)`                                                   | 15          |
| 7   | `from_raw(cls, raw)`                                                                                 | 15          |
| 8   | `_transform_impl(self, context, record, index)`                                                      | 14          |
| 9   | `health_check(self)`                                                                                 | 12          |
| 10  | `_validate(self)`                                                                                    | 12          |
| 11  | `fetch_filtered(self, entity_type, filter_ids, filter_field, limit)`                                 | 11          |
| 12  | `from_string(cls, value)`                                                                            | 11          |
| 13  | `fetch_filtered_with_fallback(self, entity_type, filter_ids, filter_field, fallback_mapping, limit)` | 10          |
| 14  | `get_source_metadata(self, api_version)`                                                             | 10          |
| 15  | `_get_health_endpoint(self)`                                                                         | 9           |
| 16  | `_probe_health(self)`                                                                                | 9           |
| 17  | `fetch_multi_filtered(self, entity_type, filters, limit)`                                            | 9           |
| 18  | `provider_name(self)`                                                                                | 9           |
| 19  | `request_count(self)`                                                                                | 8           |
| 20  | `close(self)`                                                                                        | 7           |
| 21  | `clear_request_collector(self)`                                                                      | 7           |
| 22  | `to_dict(self)`                                                                                      | 7           |
| 23  | `_fallback_health_status(self)`                                                                      | 6           |
| 24  | `reset(self)`                                                                                        | 6           |
| 25  | `get_format_enum(self)`                                                                              | 6           |
| 26  | `get_checks_enums(self)`                                                                             | 6           |
| 27  | `list_pipelines(self)`                                                                               | 6           |
| 28  | `entity_to_silver_record(entity)`                                                                    | 6           |
| 29  | `extract(self, element)`                                                                             | 6           |
| 30  | `normalize(self, raw_value)`                                                                         | 6           |
| 31  | `is_success(self)`                                                                                   | 6           |
| 32  | `_search_by_title(self, title)`                                                                      | 5           |
| 33  | `status(self)`                                                                                       | 5           |
| 34  | `is_running(self)`                                                                                   | 5           |
| 35  | `bind(self)`                                                                                         | 5           |
| 36  | `run_id(self)`                                                                                       | 5           |
| 37  | `_extract_business_data(self, record)`                                                               | 5           |
| 38  | `_get_primary_id_field(self)`                                                                        | 5           |
| 39  | `_get_entity_class(self)`                                                                            | 5           |
| 40  | `is_under_pressure(self)`                                                                            | 4           |

### 3.3 Cross-layer Duplicates (by object name)

| #   | Object Name            | Layers                                           |
| --- | ---------------------- | ------------------------------------------------ |
| 1   | `_get_bioetl_version`  | composition, infrastructure                      |
| 2   | `T`                    | application, composition, domain, infrastructure |
| 3   | `_serialize_value`     | domain, infrastructure                           |
| 4   | `ValidationResult`     | domain, infrastructure                           |
| 5   | `P`                    | domain, infrastructure                           |
| 6   | `BaseClientConfig`     | domain, infrastructure                           |
| 7   | `DQReportConfig`       | domain, infrastructure                           |
| 8   | `DQConfig`             | domain, infrastructure                           |
| 9   | `CircuitBreakerConfig` | domain, infrastructure                           |
| 10  | `InputFilterConfig`    | domain, infrastructure                           |
| 11  | `RateLimitConfig`      | composition, domain                              |
| 12  | `normalize_string`     | application, domain                              |
| 13  | `parse_date_field`     | application, domain                              |
| 14  | `validate_smiles`      | application, domain                              |

## 4. Dependency Map

### 4.1 Модули с наибольшим fan-out

| #   | Module                                                | Dependencies Count |
| --- | ----------------------------------------------------- | ------------------ |
| 1   | `bioetl.composition.factories.pipeline_factories`     | 49                 |
| 2   | `bioetl.domain.__init__`                              | 25                 |
| 3   | `bioetl.domain.ports.__init__`                        | 24                 |
| 4   | `bioetl.composition.bootstrap.runtime.composite`      | 22                 |
| 5   | `bioetl.composition.factories.services_factory`       | 22                 |
| 6   | `bioetl.composition.factories.pipeline_factory`       | 21                 |
| 7   | `bioetl.application.core.__init__`                    | 21                 |
| 8   | `bioetl.infrastructure.adapters.chembl.client`        | 20                 |
| 9   | `bioetl.composition.providers.registration`           | 18                 |
| 10  | `bioetl.domain.value_objects.__init__`                | 18                 |
| 11  | `bioetl.infrastructure.adapters.pubmed.pubmed_client` | 17                 |
| 12  | `bioetl.application.pipelines.chembl.__init__`        | 17                 |
| 13  | `bioetl.composition.bootstrap.assembly.storage`       | 16                 |
| 14  | `bioetl.domain.entities.__init__`                     | 16                 |
| 15  | `bioetl.application.services.__init__`                | 15                 |
| 16  | `bioetl.infrastructure.storage.bronze_writer`         | 14                 |
| 17  | `bioetl.infrastructure.config._base`                  | 14                 |
| 18  | `bioetl.interfaces.cli.main`                          | 14                 |
| 19  | `bioetl.application.core.batch_executor`              | 14                 |
| 20  | `bioetl.infrastructure.storage.silver_writer`         | 13                 |

### 4.2 Модули с наибольшим fan-in

| #   | Module                       | Dependents Count |
| --- | ---------------------------- | ---------------- |
| 1   | `__future__`                 | 477              |
| 2   | `typing`                     | 314              |
| 3   | `dataclasses`                | 125              |
| 4   | `bioetl.domain.types`        | 74               |
| 5   | `datetime`                   | 65               |
| 6   | `bioetl.domain.ports`        | 46               |
| 7   | `asyncio`                    | 43               |
| 8   | `collections.abc`            | 41               |
| 9   | `pathlib`                    | 34               |
| 10  | `pandera.typing`             | 30               |
| 11  | `pandera.pandas`             | 30               |
| 12  | `enum`                       | 29               |
| 13  | `time`                       | 27               |
| 14  | `bioetl.domain.exceptions`   | 26               |
| 15  | `pydantic`                   | 23               |
| 16  | `re`                         | 18               |
| 17  | `contextlib`                 | 17               |
| 18  | `click`                      | 17               |
| 19  | `bioetl.domain.medallion`    | 16               |
| 20  | `bioetl.domain.schemas.base` | 16               |

### 4.3 Циклические зависимости внутри слоя

Требуется отдельный графовый анализ (например, `pydeps`/`grimp`). В этом отчёте не вычислялось автоматически.

## 5. Рекомендации

### 5.1 Немедленные действия (Quick Wins)

| #   | Action                                                       | Impact                  | Effort |
| --- | ------------------------------------------------------------ | ----------------------- | ------ |
| 1   | Верифицировать TOP-30 DEAD объектов и удалить подтверждённые | Снижение сложности кода | M      |
| 2   | Прогнать `pyflakes` и устранить неиспользуемые импорты       | Чистота модулей         | S      |
| 3   | Провести ручной ревью TOP-40 structural duplicates           | Снижение DRY-нарушений  | M      |

### 5.3 По слоям — сводка

| Layer          | Dead Objects | Duplicates (suspected groups involved) | Health |
| -------------- | -----------: | -------------------------------------: | ------ |
| domain         |            1 |                                    178 | ✅     |
| application    |            2 |                                     81 | ✅     |
| infrastructure |            3 |                                    135 | ✅     |
| composition    |            1 |                                     30 | ✅     |
| interfaces     |            2 |                                      3 | ✅     |
