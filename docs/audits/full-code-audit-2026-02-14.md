# ПОЛНЫЙ АУДИТ КОДОВОЙ БАЗЫ BioETL

**Дата:** 2026-02-15 (обновление аудита 2026-02-14)
**Версия:** 1.1.0
**Статус:** PASS (9.5/10)
**Ветка:** main (актуализация)

---

## EXECUTIVE SUMMARY

| Метрика | Значение | Δ vs 2026-02-14 |
|---------|----------|-----------------|
| Всего файлов кода | 520 | +9 |
| Классов | 895 | −31 |
| Публичных функций | 1,466 | +7 |
| Пайплайнов (YAML) | 21 (+1 base +5 composite) | — |
| Тестовых файлов | 569 | +4 |
| Тестов (unit+arch) | 10,249 | новая метрика |
| Coverage | 86.72% | +1.7% |
| Архитектурных нарушений | 0 | — |
| Функций CC > 10 | 40 (1 grade D, 39 grade C) | новая метрика |
| mypy strict | PASS (520 files) | — |
| ruff | PASS (0 issues) | — |

---

## 1. СТРУКТУРА СЛОЁВ

### Domain Layer (177 файлов, 2.8 MB)

| Подмодуль | Классов | Функций | Назначение |
|-----------|---------|---------|------------|
| `aggregates/` | 6 | 20+ | DDD агрегаты (Batch, PipelineRun, QuarantineEntry) |
| `composite/` | 10+ | 15+ | Composite pipeline state (ADR-026) |
| `config/` | 6 | 10+ | PipelineConfig, RuntimeConfig, DQConfig |
| `contracts/` | 25+ | - | Gold layer Pandera schemas (23 gold schemas) |
| `entities/` | 30+ | - | Domain entities (Molecule, Target, Activity...) |
| `exceptions/` | 45+ | - | Domain exception hierarchy |
| `filtering/` | 8 | 5 | Gold/Input filter configuration |
| `models/` | 5 | - | ExtractionParams, Filter |
| `ports/` | 38+ | - | Protocol interfaces for DI |
| `schemas/` | 20+ | - | Silver layer Pandera schemas (20 silver schemas) |
| `services/` | 8 | 20+ | IdentityService, NormalizationService |
| `types/` | 20+ | - | Type aliases, enums |
| `value_objects/` | 20+ | - | ChemblId, DOI, PubMedId... |

**Классов в слое:** 420

### Application Layer (129 файлов, 2.5 MB)

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

**Классов в слое:** 183

### Infrastructure Layer (134 файлов, 2.6 MB)

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

**Классов в слое:** 255

### Composition Layer (50 файлов, 833 KB)

| Подмодуль | Классов | Функций | Назначение |
|-----------|---------|---------|------------|
| `bootstrap/` | 5 | 60+ | Assembly, CLI bootstrap, Runtime bootstrap |
| `factories/` | 12 | 30+ | GenericPipelineFactory, StorageFactory |
| `providers/` | 5 | 20+ | ProviderRegistry, registration |
| `services/` | 2 | 10 | MetadataCoordinator, versioning |
| Root | 6 | 25+ | entrypoints, registry, builders |

**Классов в слое:** 33

### Interfaces Layer (28 файлов, 292 KB)

| Подмодуль | Классов | Функций | Назначение |
|-----------|---------|---------|------------|
| `cli/commands/` | - | 50+ | CLI commands (run, health, export...) |
| `cli/` | 3 | 20+ | Main CLI, options |
| `factories/` | 2 | 10 | Pipeline factories |
| `http/` | 2 | 5 | Health server |
| `orchestration/` | - | - | Reserved for future use (пустой модуль) |

**Классов в слое:** 4

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

### Gold Schemas: 23

14 ChEMBL + 2 Composite (CompositePublicationGoldSchema, CompositeMoleculeGoldSchema) + 1 PubChem + 4 Publications (PubMed, CrossRef, OpenAlex, SemanticScholar) + 2 UniProt

### Silver Schemas: 20

12 ChEMBL + 1 PubChem + 1 PubMed + 2 CrossRef (PublicationEnrichedSchema, PublicationSchema) + 1 OpenAlex + 1 SemanticScholar + 2 UniProt (IDMapping, Protein)

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

**Всего Protocol-классов в domain/ports/: 38**

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

| Метрика | Значение |
|---------|----------|
| Тестов passed | 10,249 |
| Тестов skipped | 21 |
| Тестовых файлов | 569 |
| **Coverage** | **86.72%** |
| Время прогона | 92.56s (parallel) |

### Coverage по слоям

| Слой | Файлов кода | Тестовых файлов | Статус |
|------|-------------|-----------------|--------|
| domain | 177 | ~80 | Полное |
| application | 129 | ~150 | Полное |
| infrastructure | 134 | ~100 | Полное |
| composition | 50 | ~20 | Полное |
| interfaces | 28 | ~10 | Базовое |

### Сущности с недостаточным покрытием

| Сущность | Файл | Статус |
|----------|------|--------|
| ~~Aggregator~~ | ~~application/composite/aggregator.py~~ | **DONE** (17 тестов) |
| ~~dict_transformers~~ | ~~application/core/dict_transformers.py~~ | **DONE** (49 тестов) |
| orchestration/* | interfaces/orchestration/ | Пустой модуль, нечего тестировать |
| CLI commands (health, config, run) | interfaces/cli/commands/ | Covered, но не 100% |

---

## 5. АРХИТЕКТУРНЫЕ ПРОВЕРКИ

### ARCH-001: Import Matrix — PASS

| From \ To | domain | application | infrastructure | composition | interfaces |
|-----------|--------|-------------|----------------|-------------|------------|
| **domain** | ok | ok (none) | ok (none) | ok (none) | ok (none) |
| **application** | ok | ok | ok (none) | ok (none) | ok (none) |
| **infrastructure** | ok | ok (none) | ok | ok (none) | ok (none) |
| **composition** | ok | ok | ok | ok | ok (none) |
| **interfaces** | ok | ok | ok | ok | ok |

**Нарушений: 0**

### ARCH-002: Domain Purity — PASS

- Нет `import requests/httpx/aiohttp` в domain
- Нет `open()` операций в domain
- Нет прямого `import structlog` в domain

### ARCH-008: Port Facade — PASS

- Все импорты портов через `bioetl.domain.ports`, не через внутренние модули

### AP-002: Direct structlog Import — PASS

- Application/Interfaces не импортируют structlog напрямую

### AP-005: Hardcoded Secrets — PASS

- Нет хардкод паролей в production коде

### AP-006: Print Statements — PASS

- Нет `print()` в production коде

### DI-003: Service Locator — PASS

- Нет ServiceLocator/Container.resolve паттернов

---

## 6. КАЧЕСТВО КОДА

### 6.1 Static Analysis

| Инструмент | Результат | Детали |
|-----------|----------|--------|
| ruff | **PASS** | 0 issues |
| mypy --strict | **PASS** | 520 files clean |
| F401 (unused imports) | **PASS** | 0 violations |

### 6.2 Cyclomatic Complexity (Radon/Xenon)

| Слой | Avg CC | Grade | Xenon Check |
|------|--------|-------|-------------|
| domain | 2.03 | **A** | PASS (strict A/A/A) |
| application | 15.0* | C | 18 functions CC > 10 |
| infrastructure | 14.35* | C | 14 functions CC > 10 |
| composition | 14.33* | C | 3 functions CC > 10 |
| interfaces | 11.0* | C | 2 functions CC > 10 |

*\*Средний CC только по функциям с CC ≥ 11 (из-за флага -nc). Реальный средний CC по всем функциям значительно ниже.*

### 6.3 Функции CC > 10 (всего 40)

**Grade D (CC 21-30) — 1 функция:**

| Функция | Файл | CC | Рекомендация |
|---------|------|----|--------------|
| `MergeService.merge` | application/composite/merger.py:103 | D | P1: требует рефакторинга |

**Grade C (CC 11-20) — 39 функций (top-10):**

| Функция | Файл | Слой |
|---------|------|------|
| merger.py (4 функции) | application/composite/ | application |
| silver_analyzer.py (3 функции) | application/services/dq/ | application |
| _checks_integrity.py (2 функции) | application/services/dq/ | application |
| _checks_statistical.py (2 функции) | application/services/dq/ | application |
| chembl/client.py (4 функции) | infrastructure/adapters/chembl/ | infrastructure |
| uniprot/idmapping_client.py (2 функции) | infrastructure/adapters/uniprot/ | infrastructure |
| semanticscholar/adapter.py (2 функции) | infrastructure/adapters/ | infrastructure |
| storage_factory.py (1 функция) | composition/factories/ | composition |
| metadata_coordinator.py (2 функции) | composition/services/ | composition |
| gold_writer.py (1 функция) | infrastructure/storage/ | infrastructure |

### 6.4 Maintainability Index

| Слой | Файлы с MI grade C или хуже | Детали |
|------|----------------------------|--------|
| domain | 0 | Все A/B |
| application | 1 | `merger.py` (MI = 5.91, grade C) |
| infrastructure | 0 | Все A/B |
| composition | 0 | Все A/B |

---

## 7. МЁРТВЫЙ КОД

### Неиспользуемые классы: 0

Все 895 классов используются в коде или тестах.

### Неиспользуемые функции/модули

| Элемент | Файл | Severity | Статус |
|---------|------|----------|--------|
| `@register_provider` decorator | composition/providers/decorators.py | LOW | 0 usages в production (только docstring examples) |
| `composition/types.py` re-export модуль | composition/types.py | LOW | 0 потребителей в production, 14 в тесте самого модуля |

### Deprecated Aliases — Миграция завершена

В `composition/bootstrap/` deprecated aliases с `warnings.warn(DeprecationWarning)`:
- 11 deprecated функций в 6 модулях
- **0 callsites за пределами bootstrap модуля** — миграция на canonical names завершена
- Aliases сохранены для backward compatibility; удаление в следующем мажорном релизе

---

## 8. ДУБЛИРУЮЩИЙСЯ КОД

### Обнаружено минимальное дублирование

| Паттерн | Локации | Severity | Статус |
|---------|---------|----------|--------|
| Provider registration | composition/providers/registration.py | LOW | Допустимо - каждый provider уникален |
| Transformer extractors | application/pipelines/*/extractors.py | LOW | Допустимо - domain-specific logic |

**Общий DRY score: 9/10** - Код хорошо структурирован с минимальным дублированием.

---

## 9. РАСХОЖДЕНИЯ КОД-ДОКУМЕНТАЦИЯ

### Проверено соответствие:

| Документ | Соответствие | Примечания |
|----------|--------------|------------|
| RULES.md | 95% | Небольшие расхождения в статистике |
| ADR-024 (Publication naming) | 100% | Document -> Publication переименование завершено |
| ADR-026 (Composite pipelines) | 100% | Реализовано полностью |
| ADR-028 (Extraction params) | 100% | ExtractionParams используется |

### Необходимые обновления документации

| Файл | Требуется | Приоритет |
|------|-----------|-----------|
| docs/00-project/RULES.md | Обновить статистику (520 файлов, 895 классов, 23 gold schemas) | LOW |
| docs/02-architecture/README.md | Добавить composite pipeline архитектуру | MEDIUM |

---

## 10. SCORING

| Категория | Вес | Оценка | Взвешенная | Комментарий |
|-----------|-----|--------|------------|-------------|
| Architecture (ARCH) | 30% | 10/10 | 3.0 | 0 нарушений import matrix, domain purity, port facade |
| Anti-Patterns (AP) | 25% | 10/10 | 2.5 | 0 structlog leaks, 0 print, 0 secrets, 0 service locator |
| DI Violations (DI) | 20% | 10/10 | 2.0 | 0 hard-coded constructors, 0 callsites deprecated (migrated) |
| Naming (NAME) | 10% | 9/10 | 0.9 | Корректные suffixes, prefixes |
| Types (TYPE) | 10% | 10/10 | 1.0 | mypy --strict PASS, 520 files clean |
| Testing (TEST) | 5% | 9/10 | 0.45 | 86.72% coverage, 10,249 тестов |
| **ИТОГО** | **100%** | - | **9.85/10** |  |

**Complexity penalty:** −0.35 (1 grade D function: `MergeService.merge`)

**Итоговый score: 9.5/10**

**Статус: PASS**

---

## 11. РЕКОМЕНДАЦИИ

### Критические (P0)
*Нет критических проблем*

### Высокий приоритет (P1)
1. ~~Добавить unit тесты для `application/composite/aggregator.py`~~ — **DONE** (17 тестов)
2. ~~Добавить unit тесты для `application/core/dict_transformers.py`~~ — **DONE** (49 тестов)
3. **NEW:** Рефакторинг `MergeService.merge` (grade D, CC 21-30) — единственная функция grade D в кодовой базе. Файл `merger.py` также имеет MI = 5.91 (grade C), единственный файл ниже порога.

### Средний приоритет (P2)
1. Удалить или задокументировать `register_provider` decorator (0 usages в production)
2. ~~Добавить `@deprecated` warning для legacy bootstrap functions~~ — **DONE** (11 функций в 6 модулях)
3. ~~Миграция callsites deprecated functions~~ — **DONE** (0 callsites за пределами bootstrap)
4. **NEW:** Снизить CC функций grade C в application/services/dq/ (5 функций: silver_analyzer, _checks_integrity, _checks_statistical)

### Низкий приоритет (P3)
1. Обновить статистику в RULES.md (520 файлов, 895 классов, 23 gold schemas, 20 silver schemas)
2. Удалить `composition/types.py` и его тест (0 потребителей в production)
3. **NEW:** Снизить CC в infrastructure adapters (chembl/client.py — 4 функции grade C)

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

## ПРИЛОЖЕНИЕ B: ПРОМТЫ ДЛЯ РЕАЛИЗАЦИИ РЕКОМЕНДАЦИЙ

> Каждый промт — самодостаточная инструкция для AI-агента.
> Реализованные рекомендации помечены ~~strikethrough~~.

---

### ~~PROMPT-1 (P2-1): Документировать `register_provider` decorator~~ — актуально

**Контекст:**
- Файл: `src/bioetl/composition/providers/decorators.py`
- `@register_provider` экспортируется из `composition.providers`, документирован
  с примерами, протестирован в `tests/unit/composition/providers/test_provider_registry.py`
- **Ни один адаптер** в production-коде не использует его как decorator.
  Все 7 провайдеров регистрируются императивно в `composition/providers/registration.py`.
- **Подтверждено аудитом 2026-02-15:** 0 actual usages, 3 references — все docstring examples.

---

### ~~PROMPT-2 (P2-3): Расширить тестирование interfaces/orchestration/~~ — не требуется

**Подтверждено аудитом 2026-02-15:** Модуль пустой (reserved for future use), нечего тестировать.

---

### PROMPT-3 (P3-1): Обновить статистику в RULES.md — актуально

**Актуальные числа (2026-02-15):**
- Файлов кода: 520 (было 511)
- Классов: 895 (было 926)
- Публичных функций: 1,466 (было 1,459)
- Gold schemas: 23 (включая 2 composite)
- Silver schemas: 20
- Domain ports (Protocol): 38
- Coverage: 86.72%
- Тестов: 10,249

---

### PROMPT-4 (P3-2): Удалить composition/types.py — актуально

**Подтверждено аудитом 2026-02-15:** 0 потребителей в production, 14 import refs — все в тесте самого модуля.

---

### ~~PROMPT-5 (BONUS): Миграция deprecated bootstrap callsites~~ — **DONE**

**Подтверждено аудитом 2026-02-15:** 0 callsites deprecated функций за пределами bootstrap модуля.

---

### PROMPT-6 (NEW P1): Рефакторинг MergeService.merge

**Контекст:**
- `src/bioetl/application/composite/merger.py:103` — `MergeService.merge` grade **D** (CC 21-30)
- Единственная функция grade D в кодовой базе
- Файл `merger.py` имеет MI = 5.91 (grade C), единственный файл ниже порога

**Промт:**

```
Прочитай src/bioetl/application/composite/merger.py.

Задача: рефакторинг MergeService.merge() для снижения CC < 15 (grade B).

Подход:
1. Извлечь логические блоки в private methods:
   - Validation logic → _validate_merge_inputs()
   - Column alignment → _align_columns()
   - Conflict resolution → _resolve_conflicts()
   - Final assembly → _assemble_result()

2. Каждый новый метод должен:
   - Иметь CC ≤ 10 (grade B)
   - Иметь type annotations
   - Быть покрытым существующими тестами (через integration)

3. Проверки после рефакторинга:
   - uv run xenon --max-absolute B --max-modules B --max-average A src/bioetl/application/composite/merger.py
   - uv run radon mi src/bioetl/application/composite/merger.py -s
   - pytest tests/unit/application/composite/ -v
   - mypy src/bioetl/application/composite/merger.py
```

---

*Документ сгенерирован автоматически. Последнее обновление: 2026-02-15.*
