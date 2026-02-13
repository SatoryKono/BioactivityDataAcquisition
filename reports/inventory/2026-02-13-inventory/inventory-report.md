# Code Inventory Report — BioETL

Date: 2026-02-13
Scope: src/bioetl/ (all layers)

## Executive Summary

| Метрика                      | Значение |
| ---------------------------- | -------- |
| Всего классов                | 878      |
| Всего функций (module-level) | 564      |
| Всего констант               | 192      |
| Мёртвых объектов (DEAD)      | 264      |
| Дублей (confirmed)           | 0        |
| Дублей (suspected)           | 21       |

## 1. Реестр Объектов

### 1.1 Domain Layer

| Classes | Functions | Constants | Type aliases |
| ------- | --------: | --------: | -----------: |
| 410     |       154 |        73 |            4 |

### 1.2 Application Layer

| Classes | Functions | Constants | Type aliases |
| ------- | --------: | --------: | -----------: |
| 181     |       127 |        20 |            4 |

### 1.3 Infrastructure Layer

| Classes | Functions | Constants | Type aliases |
| ------- | --------: | --------: | -----------: |
| 250     |        70 |        83 |            6 |

### 1.4 Composition Layer

| Classes | Functions | Constants | Type aliases |
| ------- | --------: | --------: | -----------: |
| 33      |       141 |         5 |            2 |

### 1.5 Interfaces Layer

| Classes | Functions | Constants | Type aliases |
| ------- | --------: | --------: | -----------: |
| 4       |        72 |        11 |            0 |

## 2. Dead Code

### 2.1 DEAD объекты (0 ссылок)

| #   | Object                                 | Type       | Layer       | File:Line                                                               | Last Modified |
| --- | -------------------------------------- | ---------- | ----------- | ----------------------------------------------------------------------- | ------------- |
| 1   | \_collect_pattern_columns              | function   | application | src/bioetl/application/composite/column_orderer.py:34                   | 2026-02-12    |
| 2   | SchemaFields                           | type_alias | application | src/bioetl/application/composite/preflight_validator.py:98              | 2026-02-11    |
| 3   | V                                      | constant   | application | src/bioetl/application/core/base_transformer.py:43                      | 2026-02-12    |
| 4   | V                                      | type_alias | application | src/bioetl/application/core/base_transformer.py:43                      | 2026-02-12    |
| 5   | ValueObjectWithFromRaw                 | class      | application | src/bioetl/application/core/base_transformer.py:47                      | 2026-02-12    |
| 6   | \_extract_nested_values                | function   | application | src/bioetl/application/core/dict_transformers.py:139                    | 2026-02-11    |
| 7   | compute_subcellular_fraction_entity_id | function   | application | src/bioetl/application/core/entity_id.py:36                             | 2026-02-12    |
| 8   | ExecutorMetricsProtocol                | class      | application | src/bioetl/application/core/postrun_service.py:44                       | 2026-02-11    |
| 9   | \_span_context                         | function   | application | src/bioetl/application/observability/span_helpers.py:27                 | 2026-02-12    |
| 10  | \_extract_variant                      | function   | application | src/bioetl/application/pipelines/chembl/assay_transformer.py:51         | 2026-02-12    |
| 11  | \_normalize_orcid                      | function   | application | src/bioetl/application/pipelines/crossref/author_extractors.py:17       | 2026-02-12    |
| 12  | \_extract_author_sequence              | function   | application | src/bioetl/application/pipelines/crossref/author_extractors.py:40       | 2026-02-12    |
| 13  | \_extract_author_affiliations_list     | function   | application | src/bioetl/application/pipelines/crossref/author_extractors.py:49       | 2026-02-12    |
| 14  | \_build_author_detail                  | function   | application | src/bioetl/application/pipelines/crossref/author_extractors.py:64       | 2026-02-12    |
| 15  | \_clean_string                         | function   | application | src/bioetl/application/pipelines/crossref/reference_extractors.py:17    | 2026-02-11    |
| 16  | \_parse_year                           | function   | application | src/bioetl/application/pipelines/crossref/reference_extractors.py:27    | 2026-02-11    |
| 17  | \_extract_id_from_url                  | function   | application | src/bioetl/application/pipelines/openalex/extractors.py:43              | 2026-02-12    |
| 18  | \_get_nested_display_name              | function   | application | src/bioetl/application/pipelines/openalex/extractors.py:57              | 2026-02-12    |
| 19  | \_parse_topic_dict                     | function   | application | src/bioetl/application/pipelines/openalex/extractors.py:71              | 2026-02-12    |
| 20  | \_extract_orcid_from_url               | function   | application | src/bioetl/application/pipelines/openalex/extractors.py:132             | 2026-02-12    |
| 21  | \_parse_grant_dict                     | function   | application | src/bioetl/application/pipelines/openalex/extractors.py:347             | 2026-02-12    |
| 22  | EMAIL_PATTERN                          | constant   | application | src/bioetl/application/pipelines/pubmed/extractors/author.py:25         | 2026-02-11    |
| 23  | RawClassification                      | class      | application | src/bioetl/application/pipelines/pubmed/extractors/classification.py:14 | 2026-02-11    |
| 24  | NormalizedClassification               | class      | application | src/bioetl/application/pipelines/pubmed/extractors/classification.py:22 | 2026-02-11    |
| 25  | RawDate                                | class      | application | src/bioetl/application/pipelines/pubmed/extractors/date.py:25           | 2026-02-11    |
| 26  | MedlineDateParser                      | class      | application | src/bioetl/application/pipelines/pubmed/extractors/date.py:40           | 2026-02-11    |
| 27  | ArticleIdentifiers                     | class      | application | src/bioetl/application/pipelines/pubmed/extractors/identifier.py:15     | 2026-02-12    |
| 28  | PARSER_HELPERS                         | constant   | application | src/bioetl/application/pipelines/pubmed/xml_parser.py:79                | 2026-02-12    |
| 29  | OA_STATUS_SET                          | constant   | application | src/bioetl/application/pipelines/semanticscholar/extractors.py:163      | 2026-02-12    |
| 30  | \_extract_reaction_data                | function   | application | src/bioetl/application/pipelines/uniprot/extractors/comments.py:23      | 2026-02-11    |
| 31  | \_extract_location_value               | function   | application | src/bioetl/application/pipelines/uniprot/extractors/comments.py:40      | 2026-02-11    |
| 32  | \_build_isoform_data                   | function   | application | src/bioetl/application/pipelines/uniprot/extractors/comments.py:57      | 2026-02-11    |
| 33  | \_extract_cofactor_entry               | function   | application | src/bioetl/application/pipelines/uniprot/extractors/comments.py:95      | 2026-02-11    |
| 34  | \_extract_km_entry                     | function   | application | src/bioetl/application/pipelines/uniprot/extractors/comments.py:124     | 2026-02-11    |
| 35  | \_extract_vmax_entry                   | function   | application | src/bioetl/application/pipelines/uniprot/extractors/comments.py:136     | 2026-02-11    |
| 36  | \_extract_list_entries                 | function   | application | src/bioetl/application/pipelines/uniprot/extractors/comments.py:148     | 2026-02-11    |
| 37  | \_extract_kinetic_parameters           | function   | application | src/bioetl/application/pipelines/uniprot/extractors/comments.py:159     | 2026-02-11    |
| 38  | \_extract_absorption_data              | function   | application | src/bioetl/application/pipelines/uniprot/extractors/comments.py:182     | 2026-02-11    |
| 39  | \_extract_biophys_from_comment         | function   | application | src/bioetl/application/pipelines/uniprot/extractors/comments.py:193     | 2026-02-11    |
| 40  | \_extract_feature_location             | function   | application | src/bioetl/application/pipelines/uniprot/extractors/features.py:10      | 2026-02-11    |
| 41  | \_build_feature_dict                   | function   | application | src/bioetl/application/pipelines/uniprot/extractors/features.py:27      | 2026-02-11    |
| 42  | \_build_keyword_dict                   | function   | application | src/bioetl/application/pipelines/uniprot/extractors/features.py:51      | 2026-02-11    |
| 43  | PipelineSettingsProtocol               | class      | application | src/bioetl/application/services/config_service.py:22                    | 2026-02-12    |
| 44  | SettingsProtocol                       | class      | application | src/bioetl/application/services/config_service.py:30                    | 2026-02-12    |
| 45  | PipelineYamlConfigProtocol             | class      | application | src/bioetl/application/services/config_service.py:72                    | 2026-02-12    |
| 46  | PipelineRegistryProtocol               | class      | application | src/bioetl/application/services/config_service.py:86                    | 2026-02-12    |
| 47  | SettingsLoaderProtocol                 | class      | application | src/bioetl/application/services/config_service.py:94                    | 2026-02-12    |
| 48  | PipelineConfigLoaderProtocol           | class      | application | src/bioetl/application/services/config_service.py:102                   | 2026-02-12    |
| 49  | DomainConfigMapperProtocol             | class      | application | src/bioetl/application/services/config_service.py:110                   | 2026-02-12    |
| 50  | RegistryAccessorProtocol               | class      | application | src/bioetl/application/services/config_service.py:118                   | 2026-02-12    |

_Полный список DEAD объектов: 264 (см. data.json)._

### 2.2 TEST_ONLY объекты (ссылки только в тестах)

| #   | Object                     | Type     | Layer       | File:Line                                                                  | Test File |
| --- | -------------------------- | -------- | ----------- | -------------------------------------------------------------------------- | --------- |
| 1   | PubMedPublicationPipeline  | class    | application | src/bioetl/application/pipelines/pubmed/__init__.py:17                     | tests/\*  |
| 2   | get_int                    | function | application | src/bioetl/application/pipelines/pubmed/xml_parser.py:41                   | tests/\*  |
| 3   | NormalizedDate             | class    | application | src/bioetl/application/pipelines/pubmed/extractors/date.py:33              | tests/\*  |
| 4   | KNOWN_PARAM_TYPES          | constant | application | src/bioetl/application/pipelines/chembl/assay_parameters_transformer.py:28 | tests/\*  |
| 5   | UniProtProteinPipeline     | class    | application | src/bioetl/application/pipelines/uniprot/__init__.py:21                    | tests/\*  |
| 6   | \_is_comment_of_type       | function | application | src/bioetl/application/pipelines/uniprot/extractors/comments.py:10         | tests/\*  |
| 7   | \_extract_texts_from_dict  | function | application | src/bioetl/application/pipelines/uniprot/extractors/comments.py:76         | tests/\*  |
| 8   | \_path_to_table_name       | function | application | src/bioetl/application/composite/merger.py:34                              | tests/\*  |
| 9   | ValidationIssue            | class    | application | src/bioetl/application/composite/preflight_validator.py:38                 | tests/\*  |
| 10  | \_HealthAggregator         | class    | application | src/bioetl/application/core/preflight_service.py:45                        | tests/\*  |
| 11  | \_MedallionConfigValidator | class    | application | src/bioetl/application/core/preflight_service.py:279                       | tests/\*  |
| 12  | INT                        | constant | application | src/bioetl/application/core/field_specs.py:33                              | tests/\*  |
| 13  | FLOAT                      | constant | application | src/bioetl/application/core/field_specs.py:34                              | tests/\*  |
| 14  | STR                        | constant | application | src/bioetl/application/core/field_specs.py:35                              | tests/\*  |
| 15  | map_field                  | function | application | src/bioetl/application/core/field_specs.py:123                             | tests/\*  |
| 16  | map_fields                 | function | application | src/bioetl/application/core/field_specs.py:152                             | tests/\*  |
| 17  | map_field_group            | function | application | src/bioetl/application/core/field_specs.py:186                             | tests/\*  |
| 18  | pmid_fields                | function | application | src/bioetl/application/core/field_specs.py:291                             | tests/\*  |
| 19  | TransformerPort            | class    | application | src/bioetl/application/core/protocols.py:49                                | tests/\*  |
| 20  | \_write_xlsx_file          | function | application | src/bioetl/application/services/export_service.py:181                      | tests/\*  |

### 2.3 SELF_ONLY объекты (используются только в своём модуле)

| #   | Object                             | Type     | Layer       | File:Line                                                           | Recommendation             |
| --- | ---------------------------------- | -------- | ----------- | ------------------------------------------------------------------- | -------------------------- |
| 1   | GenericPipeline                    | class    | application | src/bioetl/application/pipelines/generic.py:33                      | Рассмотреть inline/private |
| 2   | extract_institution_ror_ids        | function | application | src/bioetl/application/pipelines/openalex/extractors.py:272         | Рассмотреть inline/private |
| 3   | StructuredAffiliation              | class    | application | src/bioetl/application/pipelines/pubmed/extractors/author.py:28     | Рассмотреть inline/private |
| 4   | RawAuthor                          | class    | application | src/bioetl/application/pipelines/pubmed/extractors/author.py:51     | Рассмотреть inline/private |
| 5   | AllArticleIds                      | class    | application | src/bioetl/application/pipelines/pubmed/extractors/identifier.py:27 | Рассмотреть inline/private |
| 6   | ELocationIds                       | class    | application | src/bioetl/application/pipelines/pubmed/extractors/identifier.py:52 | Рассмотреть inline/private |
| 7   | GeneExtractor                      | class    | application | src/bioetl/application/pipelines/uniprot/extractors/genes.py:10     | Рассмотреть inline/private |
| 8   | calculate_had_warnings             | function | application | src/bioetl/application/composite/runner_helpers.py:88               | Рассмотреть inline/private |
| 9   | get_mergeable_enrichers            | function | application | src/bioetl/application/composite/runner_helpers.py:193              | Рассмотреть inline/private |
| 10  | get_mergeable_dependencies         | function | application | src/bioetl/application/composite/runner_helpers.py:241              | Рассмотреть inline/private |
| 11  | BatchTracingManager                | class    | application | src/bioetl/application/core/batch_tracing.py:27                     | Рассмотреть inline/private |
| 12  | create_shutdown_service            | function | application | src/bioetl/application/core/shutdown.py:123                         | Рассмотреть inline/private |
| 13  | extract_list_field                 | function | application | src/bioetl/application/core/dict_transformers.py:91                 | Рассмотреть inline/private |
| 14  | aggregate_nested_lists             | function | application | src/bioetl/application/core/dict_transformers.py:150                | Рассмотреть inline/private |
| 15  | safe_extract                       | function | application | src/bioetl/application/core/dict_transformers.py:282                | Рассмотреть inline/private |
| 16  | compute_publication_term_entity_id | function | application | src/bioetl/application/core/entity_id.py:13                         | Рассмотреть inline/private |
| 17  | build_summary                      | function | application | src/bioetl/application/services/dq/dq_report_builders.py:72         | Рассмотреть inline/private |
| 18  | echo_table_list                    | function | interfaces  | src/bioetl/interfaces/cli/formatters.py:163                         | Рассмотреть inline/private |
| 19  | echo_export_preview                | function | interfaces  | src/bioetl/interfaces/cli/formatters.py:182                         | Рассмотреть inline/private |
| 20  | echo_export_result                 | function | interfaces  | src/bioetl/interfaces/cli/formatters.py:225                         | Рассмотреть inline/private |

### 2.4 Orphan-модули (файлы без imports)

| #   | File                                                            | LOC | Objects Defined | Recommendation                             |
| --- | --------------------------------------------------------------- | --- | --------------- | ------------------------------------------ |
| 1   | src/bioetl/__main__.py                                          | 8   | 0               | Проверить entry-point/facade необходимость |
| 2   | src/bioetl/application/core/subcellular_fraction_data_source.py | 297 | 1               | Проверить entry-point/facade необходимость |
| 3   | src/bioetl/interfaces/observability.py                          | 19  | 0               | Проверить entry-point/facade необходимость |
| 4   | src/bioetl/interfaces/cli/__main__.py                           | 9   | 0               | Проверить entry-point/facade необходимость |
| 5   | src/bioetl/infrastructure/storage/delta_writer.py               | 8   | 0               | Проверить entry-point/facade необходимость |
| 6   | src/bioetl/composition/types.py                                 | 52  | 0               | Проверить entry-point/facade необходимость |
| 7   | src/bioetl/composition/factories/storage_factory.py             | 341 | 2               | Проверить entry-point/facade необходимость |
| 8   | src/bioetl/composition/factories/storage_adapter.py             | 652 | 1               | Проверить entry-point/facade необходимость |

### 2.5 Неиспользуемые импорты

| #   | File:Line | Import | Recommendation |
| --- | --------- | ------ | -------------- |

## 3. Duplicate Logic

### 3.1 Confirmed Duplicates (идентичная логика)

| #   | Object A | Object B | Similarity                           | Type | Recommendation                                                         |
| --- | -------- | -------- | ------------------------------------ | ---- | ---------------------------------------------------------------------- |
| 1   | n/a      | n/a      | Требуется ручная AST/PDG верификация | -    | В рамках аудита подтверждённых copy-paste не фиксировано автоматически |

### 3.2 Suspected Duplicates (похожая логика, требует ручной верификации)

| #   | Object A                                                                    | Object B                                                     | Similarity Basis                                                | Risk   |
| --- | --------------------------------------------------------------------------- | ------------------------------------------------------------ | --------------------------------------------------------------- | ------ |
| 1   | src/bioetl/application/pipelines/semanticscholar/\_author_extractors.py:13  | src/bioetl/application/pipelines/openalex/extractors.py:119  | Одинаковое имя `extract_authors` в разных модулях               | MEDIUM |
| 2   | src/bioetl/application/pipelines/semanticscholar/\_author_extractors.py:102 | src/bioetl/application/pipelines/openalex/extractors.py:177  | Одинаковое имя `extract_author_orcids` в разных модулях         | MEDIUM |
| 3   | src/bioetl/application/pipelines/semanticscholar/\_author_extractors.py:176 | src/bioetl/application/pipelines/openalex/extractors.py:206  | Одинаковое имя `extract_affiliations` в разных модулях          | MEDIUM |
| 4   | src/bioetl/application/pipelines/semanticscholar/extractors.py:106          | src/bioetl/application/pipelines/openalex/extractors.py:386  | Одинаковое имя `extract_journal_info` в разных модулях          | MEDIUM |
| 5   | src/bioetl/application/pipelines/semanticscholar/extractors.py:308          | src/bioetl/application/pipelines/openalex/extractors.py:39   | Одинаковое имя `extract_author_ormolecule_ids` в разных модулях | MEDIUM |
| 6   | src/bioetl/infrastructure/adapters/openalex/fallback.py:21                  | src/bioetl/infrastructure/adapters/pubmed/fallback.py:21     | Одинаковое имя `TitleFallbackHandler` в разных модулях          | MEDIUM |
| 7   | src/bioetl/application/pipelines/semanticscholar/\_author_extractors.py:44  | src/bioetl/application/pipelines/openalex/extractors.py:156  | Одинаковое имя `extract_author_ids` в разных модулях            | MEDIUM |
| 8   | src/bioetl/application/pipelines/semanticscholar/extractors.py:32           | src/bioetl/application/pipelines/openalex/extractors.py:435  | Одинаковое имя `extract_external_ids` в разных модулях          | MEDIUM |
| 9   | src/bioetl/application/pipelines/semanticscholar/extractors.py:195          | src/bioetl/application/pipelines/openalex/extractors.py:424  | Одинаковое имя `extract_open_access_info` в разных модулях      | MEDIUM |
| 10  | src/bioetl/application/core/dict_transformers.py:198                        | src/bioetl/domain/normalization.py:16                        | Одинаковое имя `normalize_string` в разных модулях              | MEDIUM |
| 11  | src/bioetl/application/core/dict_transformers.py:223                        | src/bioetl/domain/normalization.py:79                        | Одинаковое имя `parse_date_field` в разных модулях              | MEDIUM |
| 12  | src/bioetl/application/core/dict_transformers.py:252                        | src/bioetl/domain/validation.py:34                           | Одинаковое имя `validate_smiles` в разных модулях               | MEDIUM |
| 13  | src/bioetl/application/core/cleanup_service.py:47                           | src/bioetl/application/services/bronze_cleanup_service.py:21 | Одинаковое имя `CleanupResult` в разных модулях                 | MEDIUM |
| 14  | src/bioetl/domain/resilience.py:124                                         | src/bioetl/infrastructure/schemas/pipeline_config.py:281     | Одинаковое имя `CircuitBreakerConfig` в разных модулях          | MEDIUM |
| 15  | src/bioetl/domain/types.py:265                                              | src/bioetl/infrastructure/adapters/validation.py:27          | Одинаковое имя `ValidationResult` в разных модулях              | MEDIUM |
| 16  | src/bioetl/domain/composite/lineage.py:34                                   | src/bioetl/domain/models/metadata.py:461                     | Одинаковое имя `LineageMetadata` в разных модулях               | MEDIUM |
| 17  | src/bioetl/domain/configs/base.py:20                                        | src/bioetl/composition/bootstrap_contexts.py:107             | Одинаковое имя `RateLimitConfig` в разных модулях               | MEDIUM |
| 18  | src/bioetl/domain/configs/base.py:55                                        | src/bioetl/infrastructure/schemas/base_schemas.py:151        | Одинаковое имя `BaseClientConfig` в разных модулях              | MEDIUM |
| 19  | src/bioetl/domain/config/dq.py:20                                           | src/bioetl/infrastructure/schemas/pipeline_config.py:119     | Одинаковое имя `DQReportConfig` в разных модулях                | MEDIUM |
| 20  | src/bioetl/domain/config/dq.py:39                                           | src/bioetl/infrastructure/schemas/pipeline_config.py:135     | Одинаковое имя `DQConfig` в разных модулях                      | MEDIUM |
| 21  | src/bioetl/domain/filtering/input_config.py:25                              | src/bioetl/infrastructure/schemas/pipeline_config.py:316     | Одинаковое имя `InputFilterConfig` в разных модулях             | MEDIUM |

### 3.3 Cross-layer Duplicates

| #   | Domain Object              | Other Layer Object            | Nature                               | Recommendation                                    |
| --- | -------------------------- | ----------------------------- | ------------------------------------ | ------------------------------------------------- |
| 1   | `*Schema` (domain)         | `infrastructure/validation/*` | Потенциальное дублирование валидации | Выделить единый контракт в domain + thin adapters |
| 2   | `*Config` (domain/configs) | `infrastructure/config/*`     | Потенциальный рассинхрон конфигов    | Проверить границу ответственности и маппинг DTO   |

### 3.4 Cross-provider Duplicates (Transformer/Client/Schema)

| #   | Provider A          | Provider B                           | Shared Logic                             | LOC Savings          |
| --- | ------------------- | ------------------------------------ | ---------------------------------------- | -------------------- |
| 1   | chembl transformers | pubchem/openalex/pubmed transformers | повторяющиеся `normalize/transform` хуки | 100-250 LOC (оценка) |

## 4. Dependency Map

### 4.1 Объекты с наибольшим fan-out (зависят от многих)

| #   | Object                                             | Layer          | Dependencies Count | Risk              |
| --- | -------------------------------------------------- | -------------- | ------------------ | ----------------- |
| 1   | `bioetl.composition.factories.pipeline_factories`  | composition    | 48                 | Высокая связность |
| 2   | `bioetl.composition.factories.pipeline_factory`    | composition    | 34                 | Высокая связность |
| 3   | `bioetl.composition.factories.services_factory`    | composition    | 31                 | Высокая связность |
| 4   | `bioetl.domain.__init__`                           | domain         | 28                 | Высокая связность |
| 5   | `bioetl.domain.ports.__init__`                     | domain         | 24                 | Высокая связность |
| 6   | `bioetl.composition.factories.transformer_factory` | composition    | 24                 | Высокая связность |
| 7   | `bioetl.composition.bootstrap.runtime.composite`   | composition    | 23                 | Высокая связность |
| 8   | `bioetl.application.composite.runner`              | application    | 22                 | Высокая связность |
| 9   | `bioetl.infrastructure.storage.silver_writer`      | infrastructure | 21                 | Высокая связность |
| 10  | `bioetl.application.core.__init__`                 | application    | 20                 | Высокая связность |

### 4.2 Объекты с наибольшим fan-in (от них зависят многие)

| #   | Object                          | Layer          | Dependents Count | Criticality |
| --- | ------------------------------- | -------------- | ---------------- | ----------- |
| 1   | `bioetl.domain.ports`           | domain         | 181              | High        |
| 2   | `bioetl.domain.types`           | domain         | 131              | High        |
| 3   | `bioetl.domain.config`          | domain         | 37               | High        |
| 4   | `bioetl.domain.context`         | domain         | 36               | High        |
| 5   | `bioetl.domain.models.metadata` | domain         | 34               | High        |
| 6   | `bioetl.domain.filtering`       | domain         | 32               | High        |
| 7   | `bioetl.domain.exceptions`      | domain         | 30               | High        |
| 8   | `bioetl.infrastructure.config`  | infrastructure | 27               | High        |
| 9   | `bioetl.domain.medallion`       | domain         | 21               | High        |
| 10  | `bioetl.domain.entities`        | domain         | 18               | High        |

### 4.3 Циклические зависимости внутри слоя

| #   | Cycle                                                     | Layer | Files Involved                   |
| --- | --------------------------------------------------------- | ----- | -------------------------------- |
| 1   | Требуется отдельный graph-анализ (networkx/import-linter) | all   | Не вычислялось в текущем проходе |

## 5. Рекомендации

### 5.1 Немедленные действия (Quick Wins)

| #   | Action                            | Objects            | Impact                     | Effort |
| --- | --------------------------------- | ------------------ | -------------------------- | ------ |
| 1   | Удалить/пересмотреть DEAD объекты | 264 объектов       | Снижение техдолга          | M      |
| 2   | Почистить неиспользуемые импорты  | 0 записей pyflakes | Повышение читаемости/линта | S      |
| 3   | Проверить orphan-модули           | 8 файлов           | Упрощение структуры        | M      |

### 5.2 Рефакторинги (требуют планирования)

| #   | RF-ID      | Description                                                    | Objects                                    | Impact | Risk   |
| --- | ---------- | -------------------------------------------------------------- | ------------------------------------------ | ------ | ------ |
| 1   | RF-INV-001 | Унификация transformer normalization hooks                     | application/pipelines/\*                   | HIGH   | MEDIUM |
| 2   | RF-INV-002 | Централизация validation contracts между domain/infrastructure | domain/schemas + infrastructure/validation | HIGH   | MEDIUM |
| 3   | RF-INV-003 | Ревизия фасадных re-export (`__all__`)                         | package `__init__` modules                 | MEDIUM | LOW    |

### 5.3 По слоям — сводка

| Layer          | Dead Objects | Duplicates | Health |
| -------------- | ------------ | ---------- | ------ |
| domain         | 70           | 14         | ⚠️     |
| application    | 64           | 12         | ⚠️     |
| infrastructure | 92           | 9          | ⚠️     |
| composition    | 26           | 2          | ✅     |
| interfaces     | 12           | 1          | ✅     |
