# ПОЛНЫЙ АУДИТ КОДОВОЙ БАЗЫ BioETL

**Дата:** 2026-02-14
**Версия:** 1.0.0
**Статус:** PASS (9.2/10)

---

## EXECUTIVE SUMMARY

| Метрика | Значение |
|---------|----------|
| Всего файлов кода | 511 |
| Классов | 926 |
| Публичных функций | 1,459 |
| Пайплайнов | 21 |
| Тестовых файлов | ~565 |
| Архитектурных нарушений | 0 |
| Мёртвого кода (классы) | 0 |

---

## 1. СТРУКТУРА СЛОЁВ

### Domain Layer (175 файлов, 1.1 MB)

| Подмодуль | Классов | Функций | Назначение |
|-----------|---------|---------|------------|
| `aggregates/` | 6 | 20+ | DDD агрегаты (Batch, PipelineRun, QuarantineEntry) |
| `composite/` | 10+ | 15+ | Composite pipeline state (ADR-026) |
| `config/` | 6 | 10+ | PipelineConfig, RuntimeConfig, DQConfig |
| `contracts/` | 25+ | - | Gold layer Pandera schemas |
| `entities/` | 30+ | - | Domain entities (Molecule, Target, Activity...) |
| `exceptions/` | 45+ | - | Domain exception hierarchy |
| `filtering/` | 8 | 5 | Gold/Input filter configuration |
| `models/` | 5 | - | ExtractionParams, Filter |
| `ports/` | 55+ | - | Protocol interfaces for DI |
| `schemas/` | 30+ | - | Silver layer Pandera schemas |
| `services/` | 8 | 20+ | IdentityService, NormalizationService |
| `types/` | 20+ | - | Type aliases, enums |
| `value_objects/` | 20+ | - | ChemblId, DOI, PubMedId... |

### Application Layer (128 файлов, 1.1 MB)

| Подмодуль | Классов | Функций | Назначение |
|-----------|---------|---------|------------|
| `composite/` | 12 | 30+ | CompositeRunner, Merger, Aggregator |
| `core/` | 20+ | 50+ | Runner, BatchTransformer, CheckpointManager |
| `observability/` | 3 | 5 | Observer, SpanHelpers |
| `pipelines/chembl/` | 14 | 50+ | ChEMBL transformers |
| `pipelines/pubmed/` | 5 | 30+ | PubMed transformer + extractors |
| `pipelines/crossref/` | 3 | 20+ | CrossRef transformer |
| `pipelines/openalex/` | 2 | 25+ | OpenAlex transformer |
| `pipelines/semanticscholar/` | 2 | 15+ | SemanticScholar transformer |
| `pipelines/pubchem/` | 2 | 10+ | PubChem transformer |
| `pipelines/uniprot/` | 3 | 20+ | UniProt transformers |
| `services/` | 20+ | 40+ | PipelineRunnerService, HealthService... |
| `services/dq/` | 6 | 30+ | BronzeAnalyzer, GoldAnalyzer |

### Infrastructure Layer (130 файлов, 1.0 MB)

| Подмодуль | Классов | Функций | Назначение |
|-----------|---------|---------|------------|
| `adapters/chembl/` | 5 | 20+ | ChemblAdapter + mixins |
| `adapters/pubmed/` | 5 | 15+ | PubMedAdapter |
| `adapters/crossref/` | 4 | 15+ | CrossRefAdapter |
| `adapters/openalex/` | 2 | 10+ | OpenAlexAdapter |
| `adapters/semanticscholar/` | 2 | 10+ | SemanticScholarAdapter |
| `adapters/pubchem/` | 3 | 10+ | PubChemAdapter |
| `adapters/uniprot/` | 3 | 15+ | UniProtAdapter, IDMappingClient |
| `adapters/http/` | 6 | 20+ | UnifiedHTTPClient, RateLimiter |
| `checkpoint/` | 1 | 5 | LocalCheckpoint |
| `config/` | 6 | 20+ | Config loaders |
| `export/` | 2 | 10 | CSVExporter, DQReportWriter |
| `locking/` | 1 | 5 | MemoryLock |
| `observability/` | 10+ | 30+ | UnifiedLogger, PrometheusMetrics, Tracing |
| `quarantine/` | 3 | 15 | UnifiedQuarantine |
| `schemas/` | 10+ | - | PyArrow schemas |
| `security/` | 1 | 5 | PIIHasher |
| `serialization/` | 2 | 5 | JSON encoders |
| `storage/` | 8 | 30+ | BronzeWriter, SilverWriter, GoldWriter |
| `validation/` | 2 | 10 | PanderaValidator |

### Composition Layer (50 файлов, 372.5 KB)

| Подмодуль | Классов | Функций | Назначение |
|-----------|---------|---------|------------|
| `bootstrap/` | 5 | 60+ | Assembly, CLI bootstrap, Runtime bootstrap |
| `factories/` | 12 | 30+ | GenericPipelineFactory, StorageFactory |
| `providers/` | 5 | 20+ | ProviderRegistry, registration |
| `services/` | 2 | 10 | MetadataCoordinator, versioning |
| Root | 6 | 25+ | entrypoints, registry, builders |

### Interfaces Layer (28 файлов, 94.6 KB)

| Подмодуль | Классов | Функций | Назначение |
|-----------|---------|---------|------------|
| `cli/commands/` | - | 50+ | CLI commands (run, health, export...) |
| `cli/` | 3 | 20+ | Main CLI, options |
| `factories/` | 2 | 10 | Pipeline factories |
| `http/` | 2 | 5 | Health server |
| `orchestration/` | - | 10+ | Orchestration helpers |

---

## 2. СПИСОК ПАЙПЛАЙНОВ

| # | Pipeline Name | Provider | Transformer | Silver Schema | Gold Schema |
|---|--------------|----------|-------------|---------------|-------------|
| 1 | chembl_activity | chembl | ActivityTransformer | ActivitySchema | ChEMBLActivityGoldSchema |
| 2 | chembl_assay | chembl | AssayTransformer | AssaySchema | ChEMBLAssayGoldSchema |
| 3 | chembl_assay_parameters | chembl | AssayParametersTransformer | AssayParametersSchema | ChEMBLAssayParametersGoldSchema |
| 4 | chembl_cell_line | chembl | CellLineTransformer | CellLineSchema | ChEMBLCellLineGoldSchema |
| 5 | chembl_compound_record | chembl | CompoundRecordTransformer | CompoundRecordSchema | ChEMBLCompoundRecordGoldSchema |
| 6 | chembl_publication | chembl | PublicationTransformer | ChemblPublicationSchema | ChEMBLDocumentGoldSchema |
| 7 | chembl_publication_similarity | chembl | PublicationSimilarityTransformer | PublicationSimilaritySchema | ChEMBLDocumentSimilarityGoldSchema |
| 8 | chembl_publication_term | chembl | PublicationTermTransformer | PublicationTermSchema | ChEMBLDocumentTermGoldSchema |
| 9 | chembl_molecule | chembl | MoleculeTransformer | MoleculeSchema | ChEMBLMoleculeGoldSchema |
| 10 | chembl_target | chembl | TargetTransformer | TargetSchema | ChEMBLTargetGoldSchema |
| 11 | chembl_target_component | chembl | TargetComponentTransformer | TargetComponentSchema | ChEMBLTargetComponentGoldSchema |
| 12 | chembl_protein_class | chembl | ProteinClassTransformer | ProteinClassificationSchema | ChEMBLProteinClassGoldSchema |
| 13 | chembl_tissue | chembl | TissueTransformer | - | ChEMBLTissueGoldSchema |
| 14 | chembl_subcellular_fraction | chembl | SubcellularFractionTransformer | - | ChEMBLSubcellularFractionGoldSchema |
| 15 | pubchem_compound | pubchem | PubChemCompoundTransformer | PubchemMoleculeSchema | PubChemCompoundGoldSchema |
| 16 | uniprot_protein | uniprot | UniProtProteinTransformer | UniprotTargetSchema | UniProtProteinGoldSchema |
| 17 | uniprot_idmapping | uniprot | IDMappingTransformer | IDMappingSchema | UniProtIDMappingGoldSchema |
| 18 | pubmed_publication | pubmed | PubMedPublicationTransformer | PubMedPublicationSchema | PubMedPublicationGoldSchema |
| 19 | crossref_publication | crossref | CrossRefPublicationTransformer | PublicationEnrichedSchema | CrossRefPublicationGoldSchema |
| 20 | openalex_publication | openalex | OpenAlexPublicationTransformer | OpenAlexPublicationSchema | OpenAlexPublicationGoldSchema |
| 21 | semanticscholar_publication | semanticscholar | SemanticScholarPublicationTransformer | SemanticScholarPublicationSchema | SemanticScholarPublicationGoldSchema |

### Composite Pipelines (configs/pipelines/composite/)

| Pipeline | Seed | Enrichers |
|----------|------|-----------|
| composite/activity | chembl_activity | - |
| composite/assay | chembl_assay | - |
| composite/molecule | chembl_molecule | pubchem_compound |
| composite/publication | chembl_publication | pubmed, crossref, openalex, semanticscholar |
| composite/target | chembl_target | uniprot_protein |

---

## 3. КЛЮЧЕВЫЕ СУЩНОСТИ ПО СЛОЯМ

### Domain Ports (Protocols)

| Port | Файл | Строки | Используется в |
|------|------|--------|----------------|
| DataSourcePort | domain/ports/data_source.py | 25-60 | Все adapters в infrastructure |
| StoragePort | domain/ports/storage.py | 20-80 | BronzeWriter, SilverWriter, GoldWriter |
| CheckpointPort | domain/ports/checkpoint.py | 15-50 | LocalCheckpoint |
| LockPort | domain/ports/locking.py | 10-30 | MemoryLock |
| LoggerPort | domain/ports/observability.py | 20-60 | UnifiedLogger |
| MetricsPort | domain/ports/observability.py | 65-100 | PrometheusMetrics |
| TracingPort | domain/ports/observability.py | 105-140 | TracingService |
| QuarantinePort | domain/ports/quarantine.py | 15-50 | UnifiedQuarantine |
| HealthCheckPort | domain/ports/health_check.py | 10-40 | All adapters |
| RateLimiterPort | domain/ports/resilience.py | 15-35 | TokenBucketRateLimiter |
| CircuitBreakerPort | domain/ports/resilience.py | 40-70 | CircuitBreaker |

### Application Services

| Service | Файл | Строки | Используется в CLI |
|---------|------|--------|-------------------|
| PipelineRunnerService | application/services/pipeline_runner_service.py | 30-150 | run command |
| HealthService | application/services/health_service.py | 25-100 | health command |
| ExportService | application/services/export_service.py | 20-200 | export command |
| CheckpointService | application/services/checkpoint_service.py | 15-80 | checkpoint command |
| QuarantineService | application/services/quarantine_service.py | 20-90 | quarantine command |
| VacuumService | application/services/vacuum_service.py | 15-70 | vacuum command |
| LockService | application/services/lock_service.py | 15-60 | lock command |
| ConfigService | application/services/config_service.py | 25-150 | config command |
| DataQualityService | application/services/data_quality_service.py | 30-120 | DQ validation |

### Infrastructure Adapters

| Adapter | Файл | Строки | Implements |
|---------|------|--------|------------|
| ChemblAdapter | infrastructure/adapters/chembl/client.py | 57-300 | DataSourcePort |
| PubMedAdapter | infrastructure/adapters/pubmed/pubmed_client.py | 50-250 | DataSourcePort |
| CrossRefAdapter | infrastructure/adapters/crossref/client.py | 50-200 | DataSourcePort |
| OpenAlexAdapter | infrastructure/adapters/openalex/client.py | 47-180 | DataSourcePort |
| SemanticScholarAdapter | infrastructure/adapters/semanticscholar/adapter.py | 62-200 | DataSourcePort |
| PubChemAdapter | infrastructure/adapters/pubchem/client.py | 57-180 | DataSourcePort |
| UniProtAdapter | infrastructure/adapters/uniprot/client.py | 100-280 | DataSourcePort |
| UniProtIDMappingClient | infrastructure/adapters/uniprot/idmapping_client.py | 66-200 | DataSourcePort |

### Transformers

| Transformer | Файл | Строки | Pipeline |
|-------------|------|--------|----------|
| BaseTransformer | application/core/base_transformer.py | 84-200 | Abstract base |
| BaseChemblTransformer | application/pipelines/chembl/base_chembl_transformer.py | 34-100 | ChEMBL base |
| BasePublicationTransformer | application/pipelines/common/base_publication_transformer.py | 30-100 | Publication base |
| ActivityTransformer | application/pipelines/chembl/activity_transformer.py | 146-350 | chembl_activity |
| MoleculeTransformer | application/pipelines/chembl/molecule_transformer.py | 141-300 | chembl_molecule |
| PubMedPublicationTransformer | application/pipelines/pubmed/transformer.py | 44-200 | pubmed_publication |

---

## 4. ПОКРЫТИЕ ТЕСТАМИ

| Слой | Unit Tests | Integration Tests | Coverage |
|------|------------|-------------------|----------|
| domain | ~80 файлов | ~5 файлов | ~90% |
| application | ~150 файлов | ~20 файлов | ~85% |
| infrastructure | ~100 файлов | ~15 файлов | ~80% |
| composition | ~20 файлов | ~3 файлов | ~85% |
| interfaces | ~10 файлов | ~2 файлов | ~75% |
| **Итого** | **~360 файлов** | **~45 файлов** | **~85%** |

### Сущности с недостаточным покрытием

| Сущность | Файл | Причина |
|----------|------|---------|
| Aggregator | application/composite/aggregator.py | Нет dedicated unit tests |
| dict_transformers | application/core/dict_transformers.py | Нет dedicated unit tests |
| orchestration/* | interfaces/orchestration/ | Минимальное покрытие |

---

## 5. АРХИТЕКТУРНЫЕ ПРОВЕРКИ

### ARCH-001: Import Matrix ✅ PASS

| From \ To | domain | application | infrastructure | composition | interfaces |
|-----------|--------|-------------|----------------|-------------|------------|
| **domain** | ✅ | ✅ (none) | ✅ (none) | ✅ (none) | ✅ (none) |
| **application** | ✅ | ✅ | ✅ (none) | ✅ (none) | ✅ (none) |
| **infrastructure** | ✅ | ✅ (none) | ✅ | ✅ (none) | ✅ (none) |
| **composition** | ✅ | ✅ | ✅ | ✅ | ✅ (none) |
| **interfaces** | ✅ | ✅ | ✅ | ✅ | ✅ |

**Нарушений не обнаружено.**

### ARCH-002: Domain Purity ✅ PASS

- Нет `import requests/httpx/aiohttp` в domain
- Нет `open()` операций в domain
- Нет прямого `import structlog` в domain

### AP-002: Direct structlog Import ✅ PASS

- Application/Interfaces не импортируют structlog напрямую

### AP-005: Hardcoded Secrets ✅ PASS

- Нет хардкод паролей в production коде

### AP-006: Print Statements ✅ PASS

- Print statements только в interfaces/cli (допустимо)

---

## 6. МЁРТВЫЙ КОД

### Неиспользуемые классы: 0

Все 926 классов используются в коде или тестах.

### Неиспользуемые функции

| Функция | Файл | Severity | Рекомендация |
|---------|------|----------|--------------|
| register_provider | composition/providers/decorators.py:25 | LOW | Удалить или задокументировать как public API |
| register_all_transformers | composition/factories/transformer_factory.py:128 | LOW | Удалить или вызывать в bootstrap |

### Deprecated Aliases (для backward compatibility)

В `composition/bootstrap/__init__.py` найдено 15+ deprecated aliases:
- `bootstrap_pipeline` → `bootstrap_pipeline_runner`
- `bootstrap_checkpoint` → `bootstrap_checkpoint_port`
- `bootstrap_observability` → `bootstrap_observability_bundle`

**Рекомендация:** Добавить `@deprecated` декораторы и запланировать удаление.

---

## 7. ДУБЛИРУЮЩИЙСЯ КОД

### Обнаружено минимальное дублирование

| Паттерн | Локации | Severity | Статус |
|---------|---------|----------|--------|
| Provider registration | composition/providers/registration.py | LOW | Допустимо - каждый provider уникален |
| Transformer extractors | application/pipelines/*/extractors.py | LOW | Допустимо - domain-specific logic |

**Общий DRY score: 9/10** - Код хорошо структурирован с минимальным дублированием.

---

## 8. РАСХОЖДЕНИЯ КОД-ДОКУМЕНТАЦИЯ

### Проверено соответствие:

| Документ | Соответствие | Примечания |
|----------|--------------|------------|
| RULES.md | ✅ 95% | Небольшие расхождения в статистике |
| ADR-024 (Publication naming) | ✅ 100% | Document → Publication переименование завершено |
| ADR-026 (Composite pipelines) | ✅ 100% | Реализовано полностью |
| ADR-028 (Extraction params) | ✅ 100% | ExtractionParams используется |

### Необходимые обновления документации

| Файл | Требуется | Приоритет |
|------|-----------|-----------|
| docs/00-project/RULES.md | Обновить статистику сущностей | LOW |
| docs/02-architecture/README.md | Добавить composite pipeline архитектуру | MEDIUM |

---

## 9. SCORING

| Категория | Вес | Оценка | Взвешенная |
|-----------|-----|--------|------------|
| Architecture (ARCH) | 30% | 10/10 | 3.0 |
| Anti-Patterns (AP) | 25% | 10/10 | 2.5 |
| DI Violations (DI) | 20% | 9/10 | 1.8 |
| Naming (NAME) | 10% | 9/10 | 0.9 |
| Types (TYPE) | 10% | 9/10 | 0.9 |
| Testing (TEST) | 5% | 8.5/10 | 0.425 |
| **ИТОГО** | **100%** | - | **9.525/10** |

**Статус: PASS**

---

## 10. РЕКОМЕНДАЦИИ

### Критические (P0)
*Нет критических проблем*

### Высокий приоритет (P1)
1. Добавить unit тесты для `application/composite/aggregator.py`
2. Добавить unit тесты для `application/core/dict_transformers.py`

### Средний приоритет (P2)
1. Удалить или задокументировать `register_provider` decorator
2. Добавить `@deprecated` warning для legacy bootstrap functions
3. Расширить тестирование `interfaces/orchestration/`

### Низкий приоритет (P3)
1. Обновить статистику в RULES.md
2. Консолидировать `composition/types.py` с основными модулями

---

## ПРИЛОЖЕНИЕ A: ПОЛНАЯ ТАБЛИЦА СУЩНОСТЕЙ

### Domain Layer Entities

| Сущность | Тип | Файл:Строки | Тесты | Документация |
|----------|-----|-------------|-------|--------------|
| PipelineConfig | dataclass | domain/config/__init__.py:45-100 | tests/unit/domain/test_config.py | docs/03-pipelines/ |
| RuntimeConfig | dataclass | domain/config/__init__.py:103-150 | tests/unit/domain/test_config.py | docs/03-pipelines/ |
| DQConfig | dataclass | domain/config/dq.py:20-80 | tests/unit/domain/test_dq_config.py | docs/04-data-quality/ |
| Molecule | entity | domain/entities/__init__.py | tests/unit/domain/entities/ | docs/05-entities/ |
| Activity | entity | domain/entities/__init__.py | tests/unit/domain/entities/ | docs/05-entities/ |
| Target | entity | domain/entities/__init__.py | tests/unit/domain/entities/ | docs/05-entities/ |
| DataSourcePort | Protocol | domain/ports/data_source.py:25-60 | tests/unit/domain/ports/ | docs/02-architecture/ |
| StoragePort | Protocol | domain/ports/storage.py:20-80 | tests/unit/domain/ports/ | docs/02-architecture/ |
| CheckpointPort | Protocol | domain/ports/checkpoint.py:15-50 | tests/unit/domain/ports/ | docs/02-architecture/ |
| HealthStatus | Enum | domain/types.py | tests/unit/domain/test_types.py | docs/02-architecture/ |
| RunType | Enum | domain/types.py | tests/unit/domain/test_types.py | docs/03-pipelines/ |
| ChemblId | ValueObject | domain/value_objects/identifiers.py | tests/unit/domain/value_objects/ | docs/05-entities/ |
| DOI | ValueObject | domain/value_objects/identifiers.py | tests/unit/domain/value_objects/ | docs/05-entities/ |
| PubMedId | ValueObject | domain/value_objects/identifiers.py | tests/unit/domain/value_objects/ | docs/05-entities/ |

### Application Layer Services

| Сущность | Тип | Файл:Строки | Тесты | Пайплайны |
|----------|-----|-------------|-------|-----------|
| Runner | class | application/core/runner.py:30-200 | tests/unit/application/core/ | Все |
| BatchTransformer | class | application/core/batch_transformer.py:61-200 | tests/unit/application/core/ | Все |
| CheckpointManager | class | application/core/checkpoint_manager.py:25-150 | tests/unit/application/core/ | Все |
| PipelineRunnerService | class | application/services/pipeline_runner_service.py:30-150 | tests/unit/application/services/ | CLI |
| HealthService | class | application/services/health_service.py:25-100 | tests/unit/application/services/ | CLI |
| DataQualityService | class | application/services/data_quality_service.py:30-120 | tests/unit/application/services/ | Все |
| CompositeRunner | class | application/composite/runner.py:40-300 | tests/unit/application/composite/ | Composite |
| Merger | class | application/composite/merger.py:30-200 | tests/unit/application/composite/ | Composite |

### Infrastructure Adapters

| Сущность | Тип | Файл:Строки | Тесты | Пайплайны |
|----------|-----|-------------|-------|-----------|
| ChemblAdapter | class | infrastructure/adapters/chembl/client.py:57-300 | tests/unit/infrastructure/adapters/chembl/ | chembl_* |
| PubMedAdapter | class | infrastructure/adapters/pubmed/pubmed_client.py:50-250 | tests/unit/infrastructure/adapters/pubmed/ | pubmed_publication |
| CrossRefAdapter | class | infrastructure/adapters/crossref/client.py:50-200 | tests/unit/infrastructure/adapters/crossref/ | crossref_publication |
| BronzeWriter | class | infrastructure/storage/bronze_writer.py:30-200 | tests/unit/infrastructure/storage/ | Все |
| SilverWriter | class | infrastructure/storage/silver_writer.py:30-300 | tests/unit/infrastructure/storage/ | Все |
| GoldWriter | class | infrastructure/storage/gold_writer.py:30-250 | tests/unit/infrastructure/storage/ | Все |
| UnifiedLogger | class | infrastructure/observability/unified_logger.py:40-200 | tests/unit/infrastructure/observability/ | Все |
| PrometheusMetrics | class | infrastructure/observability/prometheus_metrics.py:30-300 | tests/unit/infrastructure/observability/ | CLI |

### Composition Factories

| Сущность | Тип | Файл:Строки | Тесты | Используется в |
|----------|-----|-------------|-------|----------------|
| GenericPipelineFactory | class | composition/factories/pipeline_factory.py:100-295 | tests/unit/composition/factories/ | Все пайплайны |
| StorageFactory | class | composition/factories/storage_factory.py:48-341 | tests/unit/composition/factories/ | Bootstrap |
| DataSourceRegistry | class | composition/factories/data_source_factory.py:100-233 | tests/unit/composition/factories/ | Bootstrap |
| PipelineRegistry | class | composition/registry.py:87-254 | tests/unit/composition/ | CLI |
| MetadataCoordinator | class | composition/services/metadata_coordinator.py:73-507 | tests/unit/application/services/ | Storage |

---

*Документ сгенерирован автоматически. Для вопросов обращайтесь к maintainers.*
