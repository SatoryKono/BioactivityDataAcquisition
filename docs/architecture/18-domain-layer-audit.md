# 18 Domain Layer Audit

## 0. Область аудита

Анализ охватывает пакет `src/bioetl/domain`, конфигурации (`configs/pipelines/chembl/*.yaml`, `configs/defaults/*.yaml`), схемы `src/bioetl/domain/schemas/chembl/*.py` и документацию (`docs/domain`, `docs/architecture/14-class-diagrams-domain.md`). Цель — зафиксировать фактические модели, bounded context’ы, абстракции и нарушения границ DDD, а также сформировать целевой образ доменного слоя.

## 1. Инвентаризация моделей

### 1.1 Runtime, registry и config-сущности

| Сущность | Файл | Тип | Основные поля / ответственность | Контекст |
| --- | --- | --- | --- | --- |
| `StageResult` | `src/bioetl/domain/models.py` | dataclass | `stage_name`, `success`, счётчики записей/чанков, длительность, список ошибок | Телеметрия стадий |
| `RunContext` | `src/bioetl/domain/models.py` | dataclass | `run_id`, `entity_name`, `provider`, `started_at`, `config`, `dry_run`, `metadata` | Оркестрация запуска |
| `RunResult` | `src/bioetl/domain/models.py` | dataclass | Итог (`row_count`, `output_path`, длительность, ошибки, per-stage метрики) | Сводка пайплайна |
| `StageDescriptor` | `src/bioetl/domain/models.py` | value object | Имя стадии, callable, флаги `skip_on_dry_run`/`required` | Сборка пайплайна |
| `PipelineConfig` + секции | `src/bioetl/domain/configs/pipeline.py` | Pydantic aggregate | ID/`entity`/`provider`, `provider_config`, HTTP таймауты, storage пути, логирование, метрики, детерминизм, нормализация, хеширование | Конфигурация, смешивающая домен и инфраструктуру |
| `ProviderDefinition` | `src/bioetl/domain/providers.py` | dataclass | Сопоставляет `ProviderId`, тип конфигурации и фабрику компонентов | Реестр провайдеров |
| `InMemoryProviderRegistry` | `src/bioetl/domain/provider_registry.py` | сервис | Register/list/restore провайдеров, проверка дубликатов | Реестр провайдеров |
| `RawRecord` / `RecordSource` | `src/bioetl/domain/record_source.py` | TypedDict + Protocol | Типизированные raw записи и контракт источника батчей | Порт Extraction |
| `ApiRecordSource` | `src/bioetl/domain/record_source.py` | сервис | Цикл по `ExtractionServiceABC.iter_extract`, фильтры, chunking, optional `batch_adapter` | По сути application-оркестрация |
| `ValidationResult` | `src/bioetl/domain/validation/contracts.py` | dataclass | `is_valid`, `errors`, `warnings`, `validated_df: pd.DataFrame \| None` | Валидация |
| `WriteResult` | `src/bioetl/domain/clients/base/output/contracts.py` | dataclass | `path: Path`, `row_count`, `duration_sec`, `checksum` | IO-порт |
| `HashService` | `src/bioetl/domain/transform/hash_service.py` | сервис | Добавляет `hash_row`, `hash_business_key`, `index`, `database_version`, `extracted_at` | Пост-обогащение таблиц |
| `SchemaRegistry` | `src/bioetl/domain/schemas/registry.py` | сервис | Регистрация Pandera-схем, хранение `column_order`, `list/get` API | Управление схемами |

### 1.2 Сущности по bounded context

| Контекст | Pandera schema | Pipeline config | Основные поля | Примечания |
| --- | --- | --- | --- | --- |
| Activity | `src/bioetl/domain/schemas/chembl/activity.py` | `configs/pipelines/chembl/activity.yaml` | 45+ колонок (assay/document/molecule связи, измерения, hash) | CSV фикстура `data/input/activity.csv` |
| Assay | `src/bioetl/domain/schemas/chembl/assay.py` | `configs/pipelines/chembl/assay.yaml` | Organism, BAO id/label, классификации, target ссылки | Config повторяет schema |
| Document | `src/bioetl/domain/schemas/chembl/document.py` | `configs/pipelines/chembl/document.yaml` | DOI/PMID, журнал, тип, score | Поля строго типизированы |
| Molecule / «TestItem» | `src/bioetl/domain/schemas/chembl/molecule.py` | `configs/pipelines/chembl/molecule.yaml` | ChEMBL/PubChem ID, клиническая стадия, parent-child, синонимы | Docs используют имя `TestItem`, код — только `Molecule` |
| Target | `src/bioetl/domain/schemas/chembl/target.py` | `configs/pipelines/chembl/target.yaml` | Taxonomy, organism, UniProt, связи с assay/activity | Единственный таргетный контекст |
| Cell / Tissue | — | — | Входы `data/input/cell.csv`, `data/input/tissue.csv` без схем и конфигов | Данные есть, доменной модели нет |

### 1.3 Наблюдения

- Все активные сущности представлены Pandera-схемами; агрегатов/dataclass’ов для Activity/Assay/etc нет.
- Документация (`docs/domain/01-glossary.md`, `docs/domain/schemas/00-schemas-overview.md`, `docs/architecture/01-domain-objects.md`, диаграммы в `docs/architecture/diagrams/class/*.mmd`) продолжает описывать `TestItem`, которого нет в коде.
- CSV `cell/tissue` присутствуют во входных данных, но не валидируются и не документированы в домене.

## 2. Дубликаты и разночтения

| Кейс | Файлы | Проблема | Риск |
| --- | --- | --- | --- |
| Два `HashService` | `src/bioetl/domain/transform/hash_service.py`, `src/bioetl/infrastructure/transform/impl/hash_service_impl.py` | Дублирование фасада `HashServiceABC` | Расхождение поведения, лишние импорты |
| Логгер-шим | `src/bioetl/domain/clients/base/logging/contracts.py` vs `src/bioetl/domain/observability/contracts.py` | Deprecated модуль всё ещё импортируется и кидает `DeprecationWarning` | Нарушение политики UnifiedLogger |
| Переэкспорт конфигов | `src/bioetl/domain/configs/base.py` | Полный re-export `pipeline.py` | Скрывает единственный источник истины, мешает tooling |
| Extraction shim | `src/bioetl/domain/contracts.py` | Alias на `domain.ports.extraction` | Поддерживает легаси-импорты |
| Docs vs код | `docs/domain/*`, `docs/architecture/14-class-diagrams-domain.md` | Docs обещают `TestItem/TestitemSchema`, в коде есть только `MoleculeTableSchema` | Команды используют разные названия сущностей |
| Неописанные входы | `data/input/cell.csv`, `data/input/tissue.csv` | Данные есть, схем/конфигов нет | Обход Pandera/детерминизма |

### 2.1 Чеклисты

- [ ] **HashService**: объединить реализации, оставить доменный фасад + инжектируемый `Hasher`.  
- [ ] **Logging shim**: удалить `domain.clients.base.logging`, обновить импорты на `domain.observability`.  
- [ ] **Configs/base**: удалить re-export, зафиксировать breaking change.  
- [ ] **`domain.contracts`**: убрать shim, обновить диаграммы/доки.  
- [ ] **Docs TestItem**: синхронизировать glossary/диаграммы с фактической `Molecule` или добавить реальную сущность.  
- [ ] **Cell/Tissue**: либо описать схемами/конфигами, либо удалить входные CSV.

## 3. Аудит абстракций (ABC/Protocol)

| Абстракция | Файл | Реализации | Использование | Решение |
| --- | --- | --- | --- | --- |
| `RequestBuilderABC` | `domain/clients/base/contracts.py` | 1 (`ChemblRequestBuilderImpl`) | Только ChemBL | Инлайнить или оставить конкретный builder |
| `ResponseParserABC` | `domain/clients/base/contracts.py` | 1 | Только ChemBL | Инлайнить |
| `PaginatorABC` | `domain/clients/base/contracts.py` | 1 | Только ChemBL | Упростить до enum/стратегии |
| `RateLimiterABC` | `domain/clients/base/contracts.py` | 1 (`TokenBucket`) | Нет вариативности | Добавить `Noop` или заменить на config |
| `RetryPolicyABC` | `domain/clients/base/contracts.py` | 1 (`ExponentialBackoff`) | Нет альтернатив | Аналогично rate limiter |
| `SecretProviderABC` | `domain/clients/base/contracts.py` | 1 (`EnvSecretProvider`) | Используется фабрикой клиента | Перенести в инфраструктуру или добавить Vault |
| `SideInputProviderABC` | `domain/clients/base/contracts.py` | 0 | Никто не реализует | Удалить |
| `BatchAdapterABC` | `domain/ports/extraction.py` | 1 (`PandasBatchAdapter`) | Только `ApiRecordSource` | Заменить на `Callable[[Any], list[RawRecord]]` |
| `DataClientABC` / `ChemblDataClientABC` | `domain/clients/*.py` | 1 (`ChemblDataClientHTTPImpl`) | Нет других провайдеров | Пока держать конкретный клиент |
| `ExtractionServiceABC` | `domain/ports/extraction.py` | 1 (`ChemblExtractionServiceImpl`) | Один провайдер | Рассмотреть переименование в ChemBL сервис |
| `HashServiceABC` / `HasherABC` | `domain/transform/contracts.py` | 2 (domain и infra) | Пост-трансформер | Оставить единственную canonical реализацию |
| `NormalizationServiceABC` | `domain/transform/contracts.py` | 2 (generic, ChemBL) | Нужна вариативность | Сохранить, но усилить тестами |
| `SchemaProviderABC` / `ValidatorABC` | `domain/validation/contracts.py` | 1 (SchemaRegistry / Pandera) | Через фабрики | Зафиксировать roadmap альтернатив |
| `WriterABC` / `MetadataWriterABC` / `QualityReportABC` / `OutputWriterABC` | `domain/clients/base/output/contracts.py` | 1–2 | Зависят от `Path` и `pd.DataFrame` | Вынести в инфраструктуру, оставить DTO-порт |
| `LoggingPortABC` / `PipelineMetricsPortABC` | `domain/observability/contracts.py` | 1 (Structured logger, SimpleNamespace metrics) | Метрики реализованы лямбдами в `interfaces/wiring.py` | Создать полноценный адаптер и зарегистрировать в ABC registry |

Абстракции с ≥2 реальными реализациями (`CacheABC`, `NormalizationServiceABC`, CSV/Parquet writers) остаются, но потребуют документации причины вариативности.

## 4. Нарушения границ DDD

1. **Domain ↔ pandas** — `domain/transform/contracts.py`, `domain/validation/contracts.py`, `domain/clients/base/output/contracts.py` оперируют `pd.DataFrame`. → Нужны value objects + адаптеры DataFrame ↔ VO.
2. **Конфиг смешивает слои** — `PipelineConfig` содержит HTTP таймауты, пути ФС, настройки логирования и метрик. → Разделить на доменный контракт и инфраструктурный профиль.
3. **`ApiRecordSource` оркестрирует пайплайн** — `src/bioetl/domain/record_source.py` управляет пагинацией и batch adapter. → Перенести класс в application слой, в домене оставить только Protocol.
4. **IO-порты знают про `Path` и атомарность** — `WriterABC`/`OutputWriterABC` диктуют файловую семантику. → Доменный порт описывает DTO; детали записи — инфраструктура.
5. **Документация vs код** — docs продолжают ссылаться на `TestItem/TestitemSchema`, отсутствующие в коде. → Синхронизировать документацию и схемы.
6. **Metrics port без реализации** — `PipelineMetricsPortABC` реализован `types.SimpleNamespace` в `src/bioetl/interfaces/wiring.py`. → Добавить настоящий адаптер (Prometheus) и зарегистрировать его в ABC registry.

## 5. Целевой образ

- Единственная каноническая модель (schema/dataclass) на каждую бизнес-сущность.
- Доменные сервисы работают с типизированными сущностями/DTO; DataFrame остаётся транспортом на границах.
- В домене только осмысленные порты (каждый ABC имеет ≥2 реализации или roadmap).
- Конфиги разделены: домен знает об идентификаторах и правилах, инфраструктура — про HTTP/storage/logging/metrics.
- Документация и диаграммы синхронизированы с кодом; входы `cell/tissue` либо описаны, либо удалены.

## 6. Рекомендации и чеклисты

### 6.1 Roadmap

| Горизонт | Фокус | Ключевые действия |
| --- | --- | --- |
| Быстрые победы (≤1 спринт) | Очистка | Слить `HashService`, удалить logging/config/extraction shim’ы, обновить docs (TestItem → Molecule), задокументировать отсутствие cell/tissue |
| Средний срок (1–3 спринта) | Моделирование | Ввести dataclass/TypedDict для Activity/Assay/Document/Target/Molecule, добавить мапперы, перенести `ApiRecordSource` в application слой, разделить pipeline config |
| Долгий срок (3+ спринта) | Жёсткие границы | Создать реальные metrics/writer адаптеры, подготовить абстракции под новых провайдеров, покрыть новые сущности схемами |

### 6.2 Итоговый чеклист

- [ ] Выполнить действия из раздела 2.1 (дубликаты, документация).
- [ ] Сократить ABC до списка из раздела 3.
- [ ] Зафиксировать разделение конфигов и перенос инфраструктурных зависимостей (раздел 4).
- [ ] Обновить `docs/architecture/14-class-diagrams-domain.md` и связанные диаграммы после переименований/удалений.
- [ ] Обновить `CHANGELOG.md` для всех публичных API/CLI изменений.

Следование roadmap обеспечит детерминизм, чистые границы домена и прозрачную эволюцию модели данных.
# 18 Domain Layer Audit

## 0. Область аудита

Анализ охватывает пакет `src/bioetl/domain`, конфигурации (`configs/pipelines/chembl/*.yaml`, `configs/defaults/*.yaml`), схемы `src/bioetl/domain/schemas/chembl/*.py` и документацию (`docs/domain`, `docs/architecture/14-class-diagrams-domain.md`). Цель — зафиксировать фактические модели, bounded context’ы, абстракции и нарушения границ DDD, а также сформировать целевой образ доменного слоя.

## 1. Инвентаризация моделей

### 1.1 Runtime, registry и config-сущности

| Сущность | Файл | Тип | Основные поля / ответственность | Контекст |
| --- | --- | --- | --- | --- |
| `StageResult` | `src/bioetl/domain/models.py` | dataclass | `stage_name`, `success`, счётчики записей/чанков, длительность, список ошибок | Телеметрия стадий |
| `RunContext` | `src/bioetl/domain/models.py` | dataclass | `run_id`, `entity_name`, `provider`, `started_at`, `config`, `dry_run`, `metadata` | Оркестрация запуска |
| `RunResult` | `src/bioetl/domain/models.py` | dataclass | Итог (`row_count`, `output_path`, длительность, ошибки, per-stage метрики) | Сводка пайплайна |
| `StageDescriptor` | `src/bioetl/domain/models.py` | value object | Имя стадии, callable, флаги `skip_on_dry_run`/`required` | Сборка пайплайна |
| `PipelineConfig` + секции | `src/bioetl/domain/configs/pipeline.py` | Pydantic aggregate | ID/`entity`/`provider`, `provider_config`, HTTP таймауты, storage пути, логирование, метрики, детерминизм, нормализация, хеширование | Конфигурация, смешивающая домен и инфраструктуру |
| `ProviderDefinition` | `src/bioetl/domain/providers.py` | dataclass | Сопоставляет `ProviderId`, тип конфигурации и фабрику компонентов | Реестр провайдеров |
| `InMemoryProviderRegistry` | `src/bioetl/domain/provider_registry.py` | сервис | Register/list/restore провайдеров, проверка дубликатов | Реестр провайдеров |
| `RawRecord` / `RecordSource` | `src/bioetl/domain/record_source.py` | TypedDict + Protocol | Типизированные raw записи и контракт источника батчей | Порт Extraction |
| `ApiRecordSource` | `src/bioetl/domain/record_source.py` | сервис | Цикл по `ExtractionServiceABC.iter_extract`, фильтры, chunking, optional `batch_adapter` | По сути application-оркестрация |
| `ValidationResult` | `src/bioetl/domain/validation/contracts.py` | dataclass | `is_valid`, `errors`, `warnings`, `validated_df: pd.DataFrame | None` | Валидация |
| `WriteResult` | `src/bioetl/domain/clients/base/output/contracts.py` | dataclass | `path: Path`, `row_count`, `duration_sec`, `checksum` | IO-порт |
| `HashService` | `src/bioetl/domain/transform/hash_service.py` | сервис | Добавляет `hash_row`, `hash_business_key`, `index`, `database_version`, `extracted_at` | Пост-обогащение таблиц |
| `SchemaRegistry` | `src/bioetl/domain/schemas/registry.py` | сервис | Регистрация Pandera-схем, хранение `column_order`, `list/get` API | Управление схемами |

### 1.2 Сущности по bounded context

| Контекст | Pandera schema | Pipeline config | Основные поля | Примечания |
| --- | --- | --- | --- | --- |
| Activity | `src/bioetl/domain/schemas/chembl/activity.py` | `configs/pipelines/chembl/activity.yaml` | 45+ колонок (assay/document/molecule связи, измерения, hash) | CSV фикстура `data/input/activity.csv` |
| Assay | `src/bioetl/domain/schemas/chembl/assay.py` | `configs/pipelines/chembl/assay.yaml` | Organism, BAO id/label, классификации, target ссылки | Config повторяет schema |
| Document | `src/bioetl/domain/schemas/chembl/document.py` | `configs/pipelines/chembl/document.yaml` | DOI/PMID, журнал, тип, score | Поля строго типизированы |
| Molecule / «TestItem» | `src/bioetl/domain/schemas/chembl/molecule.py` | `configs/pipelines/chembl/molecule.yaml` | ChEMBL/PubChem ID, клиническая стадия, parent-child, синонимы | Docs используют имя `TestItem`, код — только `Molecule` |
| Target | `src/bioetl/domain/schemas/chembl/target.py` | `configs/pipelines/chembl/target.yaml` | Taxonomy, organism, UniProt, связи с assay/activity | Единственный таргетный контекст |
| Cell / Tissue | — | — | Входы `data/input/cell.csv`, `data/input/tissue.csv` без схем и конфигов | Данные есть, доменной модели нет |

### 1.3 Наблюдения

- Все активные сущности представлены Pandera-схемами; агрегатов/dataclass’ов для Activity/Assay/etc нет.
- Документация (`docs/domain/01-glossary.md`, `docs/domain/schemas/00-schemas-overview.md`, `docs/architecture/01-domain-objects.md`, диаграммы в `docs/architecture/diagrams/class/*.mmd`) продолжает описывать `TestItem`, которого нет в коде.
- CSV `cell/tissue` присутствуют во входных данных, но не валидируются и не документированы в домене.

## 2. Дубликаты и разночтения

| Кейс | Файлы | Проблема | Риск |
| --- | --- | --- | --- |
| Два `HashService` | `src/bioetl/domain/transform/hash_service.py`, `src/bioetl/infrastructure/transform/impl/hash_service_impl.py` | Дублирование фасада `HashServiceABC` | Расхождение поведения, лишние импорты |
| Логгер-шим | `src/bioetl/domain/clients/base/logging/contracts.py` vs `src/bioetl/domain/observability/contracts.py` | Deprecated модуль всё ещё импортируется и кидает `DeprecationWarning` | Нарушение политики UnifiedLogger |
| Переэкспорт конфигов | `src/bioetl/domain/configs/base.py` | Полный re-export `pipeline.py` | Скрывает единственный источник истины, мешает tooling |
| Extraction shim | `src/bioetl/domain/contracts.py` | Alias на `domain.ports.extraction` | Поддерживает легаси-импорты |
| Docs vs код | `docs/domain/*`, `docs/architecture/14-class-diagrams-domain.md` | Docs обещают `TestItem/TestitemSchema`, в коде есть только `MoleculeTableSchema` | Команды используют разные названия сущностей |
| Неописанные входы | `data/input/cell.csv`, `data/input/tissue.csv` | Данные есть, схем/конфигов нет | Обход Pandera/детерминизма |

### 2.1 Чеклисты

- [ ] **HashService**: объединить реализации, оставить доменный фасад + инжектируемый `Hasher`.  
- [ ] **Logging shim**: удалить `domain.clients.base.logging`, обновить импорты на `domain.observability`.  
- [ ] **Configs/base**: удалить re-export, зафиксировать breaking change.  
- [ ] **`domain.contracts`**: убрать shim, обновить диаграммы/доки.  
- [ ] **Docs TestItem**: синхронизировать glossary/диаграммы с фактической `Molecule` или добавить реальную сущность.  
- [ ] **Cell/Tissue**: либо описать схемами/конфигами, либо удалить входные CSV.

## 3. Аудит абстракций (ABC/Protocol)

| Абстракция | Файл | Реализации | Использование | Решение |
| --- | --- | --- | --- | --- |
| `RequestBuilderABC` | `domain/clients/base/contracts.py` | 1 (`ChemblRequestBuilderImpl`) | Только ChemBL | Инлайнить или оставить конкретный builder |
| `ResponseParserABC` | `domain/clients/base/contracts.py` | 1 | Только ChemBL | Инлайнить |
| `PaginatorABC` | `domain/clients/base/contracts.py` | 1 | Только ChemBL | Упростить до enum/стратегии |
| `RateLimiterABC` | `domain/clients/base/contracts.py` | 1 (`TokenBucket`) | Нет вариативности | Либо добавить `Noop`, либо заменить на config |
| `RetryPolicyABC` | `domain/clients/base/contracts.py` | 1 (`ExponentialBackoff`) | Нет альтернатив | Аналогично rate limiter |
| `SecretProviderABC` | `domain/clients/base/contracts.py` | 1 (`EnvSecretProvider`) | Используется фабрикой клиента | Перенести в инфраструктуру или добавить Vault |
| `SideInputProviderABC` | `domain/clients/base/contracts.py` | 0 | Никто не реализует | Удалить |
| `BatchAdapterABC` | `domain/ports/extraction.py` | 1 (`PandasBatchAdapter`) | Только `ApiRecordSource` | Заменить на `Callable[[Any], list[RawRecord]]` |
| `DataClientABC` / `ChemblDataClientABC` | `domain/clients/*.py` | 1 (`ChemblDataClientHTTPImpl`) | Нет других провайдеров | Пока держать конкретный клиент |
| `ExtractionServiceABC` | `domain/ports/extraction.py` | 1 (`ChemblExtractionServiceImpl`) | Один провайдер | Рассмотреть переименование в ChemBL сервис |
| `HashServiceABC` / `HasherABC` | `domain/transform/contracts.py` | 2 (domain и infra) | Пост-трансформер | Оставить единственную canonical реализацию |
| `NormalizationServiceABC` | `domain/transform/contracts.py` | 2 (generic, ChemBL) | Нужна вариативность | Сохранить, но усилить тестами |
| `SchemaProviderABC` / `ValidatorABC` | `domain/validation/contracts.py` | 1 (SchemaRegistry / Pandera) | Через фабрики | Зафиксировать roadmap альтернатив |
| `WriterABC` / `MetadataWriterABC` / `QualityReportABC` / `OutputWriterABC` | `domain/clients/base/output/contracts.py` | 1–2 | Жёсткая зависимость от `Path` и `pd.DataFrame` | Вынести в инфраструктуру, оставить DTO-порт |
| `LoggingPortABC` / `PipelineMetricsPortABC` | `domain/observability/contracts.py` | 1 (Structured logger, SimpleNamespace metrics) | Метрики реализованы лямбдами в `interfaces/wiring.py` | Написать полноценный адаптер и зарегистрировать в ABC registry |

Абстракции с ≥2 реальными реализациями (`CacheABC`, `NormalizationServiceABC`, CSV/Parquet writers) оставляем, но документируем зачем они нужны.

## 4. Нарушения границ DDD

1. **Domain ↔ pandas** — `domain/transform/contracts.py`, `domain/validation/contracts.py`, `domain/clients/base/output/contracts.py` оперируют `pd.DataFrame`. Бизнес-правила выражены через колонки, агрегатов нет. → Нужны value objects + адаптеры DataFrame ↔ VO.
2. **Конфиг смешивает слои** — `PipelineConfig` содержит HTTP таймауты, пути файловой системы, настройки логирования и метрик. → Разделить на доменный контракт и инфраструктурный профиль.
3. **`ApiRecordSource` оркестрирует пайплайн** — `src/bioetl/domain/record_source.py` управляет пагинацией и batch adapter. → Перенести класс в application слой, в домене оставить только Protocol.
4. **IO-порты знают про `Path` и атомарность** — `WriterABC`/`OutputWriterABC` требуют `Path` и описывают файловую семантику. → Доменный порт должен работать с DTO, детали записи — задача инфраструктуры.
5. **Документация расходится с кодом** — docs продолжают ссылаться на `TestItem/TestitemSchema`, отсутствующие в коде. → Синхронизировать документацию и схемы.
6. **Metrics port без реализации** — `PipelineMetricsPortABC` реализуется `types.SimpleNamespace` в `src/bioetl/interfaces/wiring.py`. → Написать настоящий адаптер (Prometheus) и зарегистрировать его через ABC registry.

## 5. Целевой образ

- Единственная каноническая модель (schema/dataclass) на каждую бизнес-сущность с идентичными именами в коде и документации.
- Доменные сервисы работают с типизированными сущностями/DTO; DataFrame остаётся транспортом на границах.
- В домене остаются только осмысленные порты (каждый ABC имеет ≥2 реализации или дорожную карту расширения).
- Конфиги разделены: домен знает только об идентификаторах и правилах, инфраструктура — про HTTP, storage, логирование, метрики.
- Документация и диаграммы синхронизированы с кодом, входы `cell/tissue` покрыты схемами или удалены.

## 6. Рекомендации и чеклисты

### 6.1 Roadmap

| Горизонт | Фокус | Ключевые действия |
| --- | --- | --- |
| Быстрые победы (≤1 спринт) | Очистка | Слить `HashService`, удалить logging/config/extraction shim’ы, обновить docs (TestItem → Molecule), задокументировать отсутствие cell/tissue |
| Средний срок (1–3 спринта) | Моделирование | Ввести dataclass/TypedDict для Activity/Assay/Document/Target/Molecule, добавить мапперы, перенести `ApiRecordSource` в application слой, разделить pipeline config |
| Долгий срок (3+ спринта) | Жёсткие границы | Создать реальные metrics/writer адаптеры, подготовить абстракции под новых провайдеров, покрыть новые сущности схемами |

### 6.2 Итоговый чеклист

- [ ] Выполнить действия из раздела 2.1 (дубликаты, документация).
- [ ] Сократить ABC до списка из раздела 3.
- [ ] Зафиксировать разделение конфигов и перенос инфраструктурных зависимостей (раздел 4).
- [ ] Обновить `docs/architecture/14-class-diagrams-domain.md` и связанные диаграммы после переименований/удалений.
- [ ] Обновить `CHANGELOG.md` для всех публичных API/CLI изменений.

Следование roadmap обеспечит детерминизм, чистые границы домена и прозрачную эволюцию модели данных.

# 18 Domain Layer Audit

## 0. Область аудита

Анализ охватывает весь пакет `src/bioetl/domain`, связанные конфиги (`configs/pipelines/chembl/*.yaml`, `configs/defaults/*.yaml`), схемы (`src/bioetl/domain/schemas/chembl/*.py`) и документацию (`docs/domain`, `docs/architecture/14-class-diagrams-domain.md`). Цель — зафиксировать фактические модели, bounded context’ы, абстракции и нарушения границ DDD, а также сформировать целевое состояние и дорожную карту.

## 1. Инвентаризация моделей

### 1.1 Runtime, registry и config-сущности

| Сущность | Файл | Тип | Основные поля / ответственность | Контекст |
| --- | --- | --- | --- | --- |
| `StageResult` | `src/bioetl/domain/models.py` | dataclass | `stage_name`, `success`, счётчики записей/чанков, длительность, список ошибок | Телеметрия стадий пайплайна |
| `RunContext` | `src/bioetl/domain/models.py` | dataclass | `run_id`, `entity_name`, `provider`, `started_at`, `config`, `dry_run`, произвольный `metadata` | Оркестрация запуска |
| `RunResult` | `src/bioetl/domain/models.py` | dataclass | Итог выполнения (`row_count`, `output_path`, длительность, ошибки, пер-стадийные метрики) | Сводка пайплайна |
| `StageDescriptor` | `src/bioetl/domain/models.py` | value object | Имя стадии, исполнимый callable, флаги `skip_on_dry_run`/`required` | Сборка пайплайна |
| `PipelineConfig` + секции | `src/bioetl/domain/configs/pipeline.py` | Pydantic aggregate | Идентификаторы пайплайна, `provider_config`, HTTP таймауты, storage пути, логирование, метрики, детерминизм, хеширование, нормализация | Конфигурация, смешивающая домен и инфраструктуру |
| `ProviderDefinition` | `src/bioetl/domain/providers.py` | dataclass | Сопоставляет `ProviderId`, тип конфигурации и фабрику компонентов | Реестр провайдеров |
| `InMemoryProviderRegistry` | `src/bioetl/domain/provider_registry.py` | сервис | Регистрация/list/restore провайдеров, проверка дубликатов, ошибки `Provider*` | Реестр провайдеров |
| `RawRecord` / `RecordSource` | `src/bioetl/domain/record_source.py` | TypedDict + Protocol | Типизация сырых записей и контракт источника батчей | Порт Extraction |
| `ApiRecordSource` | `src/bioetl/domain/record_source.py` | сервис | Цикл по `ExtractionServiceABC.iter_extract`, фильтры, chunking, `batch_adapter` | Оркестрация выгрузки (по факту application-логика) |
| `ValidationResult` | `src/bioetl/domain/validation/contracts.py` | dataclass | `is_valid`, `errors`, `warnings`, `validated_df: pd.DataFrame | None` | Валидация |
| `WriteResult` | `src/bioetl/domain/clients/base/output/contracts.py` | dataclass | `path: Path`, `row_count`, `duration_sec`, `checksum` | IO порт |
| `HashService` | `src/bioetl/domain/transform/hash_service.py` | сервис | Добавляет `hash_row`, `hash_business_key`, `index`, `database_version`, `extracted_at` | Пост-обогащение таблиц |
| `SchemaRegistry` | `src/bioetl/domain/schemas/registry.py` | сервис | Регистрация Pandera-схем, хранение `column_order`, list/get API | Управление схемами |

### 1.2 Сущности по bounded context

| Контекст | Pandera schema | Pipeline config | Основные поля | Примечания |
| --- | --- | --- | --- | --- |
| Activity | `src/bioetl/domain/schemas/chembl/activity.py` (`ActivityTableSchema`) | `configs/pipelines/chembl/activity.yaml` | 45+ колонок: связи `assay`/`document`/`molecule`, измерения, hash-метаданные | Отдельные CSV фикстуры `data/input/activity.csv` |
| Assay | `src/bioetl/domain/schemas/chembl/assay.py` | `configs/pipelines/chembl/assay.yaml` | Организм, BAO-id/label, классификации, target ссылки | Конфиг задаёт тот же набор полей, что и схема |
| Document | `src/bioetl/domain/schemas/chembl/document.py` | `configs/pipelines/chembl/document.yaml` | DOI/PMID, журнал, тип документа, quality score | Валидация на строчные идентификаторы |
| Molecule / «TestItem» | `src/bioetl/domain/schemas/chembl/molecule.py` | `configs/pipelines/chembl/molecule.yaml` | Идентификаторы ChEMBL/PubChem, клиническая стадия, синонимы, parent-child | Документация называет сущность `TestItem`, код — `Molecule` |
| Target | `src/bioetl/domain/schemas/chembl/target.py` | `configs/pipelines/chembl/target.yaml` | Taxonomy, organism, UniProt, связи с assay/activity | Единственный таргетный контекст в домене |
| Cell / Tissue | — | — | CSV входы (`data/input/cell.csv`, `data/input/tissue.csv`) без схем и конфигов | Сущности присутствуют во входных данных, но не описаны доменом |

### 1.3 Наблюдения по покрытию

- Все активные сущности живут в виде Pandera-схем, доменных агрегатов нет — границы контекстов определяются названием схемы/конфига.
- Документация (`docs/domain/01-glossary.md`, `docs/domain/schemas/00-schemas-overview.md`, `docs/architecture/01-domain-objects.md`, `docs/architecture/diagrams/class/*.mmd`) продолжает оперировать `TestItem`, хотя в коде существует только `Molecule`.
- Инпуты `cell/tissue` и вспомогательные CSV не имеют схем/конфигов, из-за чего данные не могут пройти через пайплайны без дополнительной разработки.

## 2. Дубликаты и разночтения

| Кейс | Файлы | Проблема | Риск |
| --- | --- | --- | --- |
| Два `HashService` | `src/bioetl/domain/transform/hash_service.py`, `src/bioetl/infrastructure/transform/impl/hash_service_impl.py` | Идентичная логика добавления hash/index/date реализована дважды | Расхождение поведения при будущих правках, сложность выбора канонического импорта |
| Логгер-шим | `src/bioetl/domain/clients/base/logging/contracts.py` против `src/bioetl/domain/observability/contracts.py` | Deprecated модуль всё ещё импортируется и бросает `DeprecationWarning`, дублируя современный порт | Новый код может случайно выбрать устаревший API, нарушая unified logging policy |
| Переэкспорт конфигов | `src/bioetl/domain/configs/base.py` просто re-export `pipeline.py` | Удерживает легаси-импорты и скрывает исходный модуль | Искажённые зависимости, дополнительный слой для mypy/ruff |
| Extraction shim | `src/bioetl/domain/contracts.py` | Пустой модуль с комментариями «Deprecated shim» | Увековечивает старые пути, удлиняет миграцию |
| Документы vs код | `docs/domain/*`, `docs/architecture/14-class-diagrams-domain.md` описывают `TestItem/TestitemSchema`, отсутствующие в `src/bioetl/domain/schemas/chembl` | Несостыковка glossary → схемы → пайплайны | Разные команды оперируют разными названиями сущностей |
| Неописанные входы | `data/input/cell.csv`, `data/input/tissue.csv` без соответствующих `schemas/*.py` и `configs/pipelines/*.yaml` | Данные в репозитории, но пайплайны не знают про них | Реальные данные могут обрабатываться вне системы контроля схем |

### 2.1 Чеклисты по расхождениям

- [ ] **HashService**  
  - Сущности: `HashService` (domain) vs `HashServiceImpl` (infra).  
  - Отличия: разный нейминг методов, но идентичная логика/состояние (`_index_counter`, `_extracted_at`).  
  - Целевая модель: оставить один фасад в домене, внедрять через фабрику; infra-слой ограничить поставкой `Hasher`.
- [ ] **Logging port shim**  
  - Сущности: `ProgressReporterABC` и `LoggingPortABC`.  
  - Отличия: первый модуль кидает `DeprecationWarning`, второй — рабочий UnifiedLogger порт.  
  - Целевая модель: удалить shim и починить импорты в приложении/тестах.
- [ ] **Configs/base**  
  - Сущности: `domain.configs.base` re-export `pipeline`.  
  - Отличия: отсутствует собственная логика, но попадает в ABC registry.  
  - Целевая модель: удалить файл, обновить импорты, зафиксировать breaking change в `CHANGELOG.md`.
- [ ] **`domain.contracts`**  
  - Сущности: alias на `domain.ports.extraction`.  
  - Отличия: пустой файл, но фигурирует в документации.  
  - Целевая модель: удалить shim, обновить диаграммы/доки.
- [ ] **Документация `TestItem`**  
  - Сущности: docs vs `MoleculeTableSchema`.  
  - Отличия: glossary и диаграммы обещают отдельную сущность, в коде нет.  
  - Целевая модель: либо переименовать `Molecule` → `TestItem`, либо добавить реальную модель + схему.
- [ ] **Cell/Tissue входы**  
  - Сущности: CSV файлы vs отсутствие схем/конфигов.  
  - Отличия: данные лежат в репозитории, но никак не валидируются.  
  - Целевая модель: создать Pandera-схемы и pipeline configs или удалить входы как legacy.

## 3. Аудит абстракций (ABC/Protocol)

| Абстракция | Файл | Реализации | Использование | Действие |
| --- | --- | --- | --- | --- |
| `RequestBuilderABC` | `domain/clients/base/contracts.py` | 1 (`ChemblRequestBuilderImpl`) | Зарегистрирован в `abc_impls.yaml`, используется только ChemBL | Удалить или сделать частью клиента пока нет 2‑го провайдера |
| `ResponseParserABC` | `domain/clients/base/contracts.py` | 1 (`ChemblResponseParserImpl`) | Только ChemBL extractor | Инлайнить в клиент/сервис |
| `PaginatorABC` | `domain/clients/base/contracts.py` | 1 (`ChemblPaginatorImpl`) | Только ChemBL | Упростить до стратегии/enum |
| `RateLimiterABC` | `domain/clients/base/contracts.py` | 1 (`TokenBucketRateLimiterImpl`) | Не подменяется, нет noop-версии | Либо добавить `NoopRateLimiter`, либо заменить на конфиг объект |
| `RetryPolicyABC` | `domain/clients/base/contracts.py` | 1 (`ExponentialBackoffRetryImpl`) | Только HTTP клиент | Аналогично rate limiter |
| `SecretProviderABC` | `domain/clients/base/contracts.py` | 1 (`EnvSecretProvider`) | Используется для загрузки токенов | Переместить в инфраструктуру или добавить Vault-реализацию |
| `SideInputProviderABC` | `domain/clients/base/contracts.py` | 0 (factory бросает `NotImplementedError`) | Никто не внедряет | Удалить порт до появления use-case |
| `BatchAdapterABC` | `domain/ports/extraction.py` | 1 (`PandasBatchAdapter`) | Только `ApiRecordSource` | Заменить на `Callable[[Any], list[RawRecord]]` |
| `DataClientABC` / `ChemblDataClientABC` | `domain/clients/contracts.py`, `domain/clients/chembl/contracts.py` | 1 (`ChemblDataClientHTTPImpl`) | Нет других источников | До появления второго клиента оставить конкретный класс |
| `ExtractionServiceABC` | `domain/ports/extraction.py` | 1 (`ChemblExtractionServiceImpl`) | Один провайдер | Если мульти-провайдеры не планируются — переименовать в ChemBL сервис |
| `HashServiceABC` | `domain/transform/contracts.py` | 2 (domain и infra) | Используется пост-трансформером | Объединить реализации |
| `HasherABC` | `domain/transform/contracts.py` | 2 ( `_DefaultHasherImpl`, `HasherImpl`) | Оба реализуют BLAKE2b | Оставить одну canonical реализацию, вторую удалить |
| `NormalizationServiceABC` | `domain/transform/contracts.py` | 2 (generic + ChemBL) | Разные профили нормализации | Оставить, добавить property-based тесты |
| `SchemaProviderABC` / `ValidatorABC` | `domain/validation/contracts.py` | 1 (SchemaRegistry / PanderaValidator) | Используются через фабрики | Дополнить планом альтернатив (e.g. Arrow) или зафиксировать single impl |
| `WriterABC` / `MetadataWriterABC` / `QualityReportABC` / `OutputWriterABC` | `domain/clients/base/output/contracts.py` | 1–2 (CSV/Parquet, Metadata, QualityReport, UnifiedOutputWriter) | Зависят от `Path`/`pd.DataFrame` | Переместить в инфраструктуру и оставить только «порт экспортирования DTO» |
| `LoggingPortABC` / `PipelineMetricsPortABC` | `domain/observability/contracts.py` | 1 (Structured logger, SimpleNamespace метрики) | Метрики фактически реализованы лямбдами в `interfaces/wiring.py` | Создать полноценный адаптер и убрать временный namespace |

Абстракции с двумя и более реальными реализациями (`CacheABC`, `NormalizationServiceABC`, `WriterABC` c CSV/Parquet) оставляем, но документируем причину вариативности.

## 4. Нарушения границ DDD

1. **Domain ↔ pandas** — все сервисы (`src/bioetl/domain/transform/contracts.py`, `src/bioetl/domain/validation/contracts.py`, `src/bioetl/domain/clients/base/output/contracts.py`) оперируют `pd.DataFrame` и `pd.Series`. Бизнес-правила выражены через колонки, агрегатов (Activity, Assay, …) нет. → Нужны value objects + адаптеры DataFrame ↔ VO в application слое.
2. **Конфиги включают инфраструктуру** — `PipelineConfig` содержит таймауты HTTP, пути файловой системы, настройки логирования/метрик, фич-флаги. → Разделить на `PipelineContract` (id, entity, provider) и `RuntimeProfile` (client/storage/logging/determinism) в инфраструктуре.
3. **`ApiRecordSource` делает оркестрацию** — цикл пагинации, batch-adapter, фильтры (`src/bioetl/domain/record_source.py`). → Переместить класс в application слой, оставить в домене только `RecordSource` Protocol.
4. **IO-порты знают про `Path` и атомарную запись** — `WriterABC`/`OutputWriterABC` диктуют работу с файловой системой, контроль атомарности, QC-репорты. → Доменный порт должен описывать «запиши таблицу/метаданные» в терминах DTO, а реализация решает как.
5. **Документация расходится с кодом** — `docs/domain/01-glossary.md`, `docs/architecture/14-class-diagrams-domain.md` и диаграммы в `docs/architecture/diagrams/class/*` содержат `TestItem`, `SchemaRegistry -> TestItemSchema`, но в коде есть только `MoleculeTableSchema`. → Срочно синхронизировать, иначе DDD границы фиктивны.
6. **Metrics port — лямбды** — `PipelineMetricsPortABC` реализуется через `types.SimpleNamespace` в `src/bioetl/interfaces/wiring.py`, без типовой реализации. → Добавить инфраструктурный адаптер (Prometheus/Grafana) и зарегистрировать его в ABC registry.

## 5. Целевой образ

- Одна каноническая модель (schema или dataclass) на бизнес-сущность, единые названия в коде и документации.
- Доменные сервисы работают с типизированными сущностями/DTO, DataFrame остаётся транспортом на границах.
- В домене остаются только осмысленные порты — каждый ABC либо имеет ≥2 реализации, либо чётко описанный roadmap по расширению.
- Конфигурация разделена: домен знает только об идентификаторах и правилах, инфраструктура — про HTTP, файловую систему, логирование, метрики.
- Документы и диаграммы синхронизированы с кодом (нет упоминания `TestItem`, если нет соответствующего кода; добавлены новые сущности — обновили docs).

## 6. Рекомендации и чеклисты

### 6.1 Roadmap

| Горизонт | Фокус | Ключевые действия |
| --- | --- | --- |
| Быстрые победы (≤1 спринт) | Удаление мусора | Слить `HashService`, удалить logging/config/extraction shim’ы, обновить docs (TestItem → Molecule), задокументировать отсутствие cell/tissue. |
| Средний срок (1–3 спринта) | Моделирование домена | Ввести dataclass/TypedDict для Activity/Assay/Document/Target/Molecule, добавить мапперы, переместить `ApiRecordSource` в application слой, разделить pipeline config. |
| Долгий срок (3+ спринта) | Жёсткие границы | Внедрить новые порты (DTO-экспорт, реальные metrics adapters), подготовить почву для множественных провайдеров (request builder/response parser), покрыть новые сущности (cell/tissue) схемами. |

### 6.2 Итоговый чеклист

- [ ] Выполнить действия из раздела 2.1 (слияние дубликатов, обновление документации).
- [ ] Сократить ABC до осмысленных (таблица в разделе 3).
- [ ] Зафиксировать разделение конфигов и перенос инфраструктурных зависимостей (раздел 4).
- [ ] Обновить `docs/architecture/14-class-diagrams-domain.md` и связанные диаграммы после переименований/удалений.
- [ ] Обновить `CHANGELOG.md` для всех публичных API/CLI изменений.

Следование дорожной карте обеспечит детерминизм, чистые границы домена и понятную эволюцию модели данных.

# 18 Domain Layer Audit

## Executive Summary

- The current domain layer mixes execution plumbing, provider wiring, and infrastructure ports with very few actual domain entities; most data is still handled as Pandas dataframes instead of aggregates.
- Several duplicate or deprecated constructs (e.g. two hash services, legacy logging shims, config re-exports) add noise and make it unclear which model is canonical.
- Most ABC/Protocol definitions have a single (or zero) implementation, signalling speculative generality without proven variability.
- Documentation (glossary and schema overview) references concepts such as `TestItem` that are not backed by code, leading to mismatched bounded contexts.

## 1. Model inventory

### 1.1 Core runtime/config models

| Model | File | Type | Key data / responsibility | Domain area |
| --- | --- | --- | --- | --- |
| `StageResult` | `src/bioetl/domain/models.py` | dataclass | Stage name, success flag, record/chunk counters, duration, error list | Pipeline runtime telemetry |
| `RunContext` | `src/bioetl/domain/models.py` | dataclass | `run_id`, `entity_name`, `provider`, `started_at`, opaque `config`/`metadata` dicts | Pipeline orchestration |
| `RunResult` | `src/bioetl/domain/models.py` | dataclass | Aggregated run outcome (`row_count`, `output_path`, per-stage metrics) | Pipeline orchestration |
| `StageDescriptor` | `src/bioetl/domain/models.py` | descriptor | Binds stage `name` to callable, `skip_on_dry_run`, `required` flags | Pipeline wiring |
| `PipelineConfig` (+ nested sections) | `src/bioetl/domain/configs/pipeline.py` | Pydantic aggregate | Canonical pipeline config plus HTTP client, storage paths, logging, metrics, determinism, hashing, normalization | Configuration (cross-layer) |
| `ProviderDefinition` | `src/bioetl/domain/providers.py` | dataclass | Links `ProviderId`, provider config type, and component factory protocol | Provider registry |
| `InMemoryProviderRegistry` | `src/bioetl/domain/provider_registry.py` | mutable registry | Register/list/restore provider definitions, throws specific errors | Provider registry |
| `RawRecord` / `RecordSource` / `ApiRecordSource` | `src/bioetl/domain/record_source.py` | TypedDict + Protocol + concrete class | Describe batches of raw provider records and wrap `ExtractionServiceABC.iter_extract` with optional adapters | Extraction ports |
| `ValidationResult` | `src/bioetl/domain/validation/contracts.py` | dataclass | `is_valid`, `errors`, `warnings`, optional `validated_df` | Validation |
| `WriteResult` | `src/bioetl/domain/clients/base/output/contracts.py` | dataclass | Output `Path`, `row_count`, duration, checksum | Output/IO port |

Other notable configuration/value objects include `HashingConfig`, `NormalizationConfig`, `DefaultsConfig`, and the schema registry singleton in `src/bioetl/domain/schemas/registry.py`.

### 1.2 Entity schemas per bounded context

| Bounded context | Schema class | File | Highlights |
| --- | --- | --- | --- |
| Activity | `ActivityTableSchema` | `src/bioetl/domain/schemas/chembl/activity.py` | ~45 business columns (activity IDs, assay/document links, measurement values) plus deterministic metadata columns via `build_output_column_order`. |
| Assay | `AssayTableSchema` | `src/bioetl/domain/schemas/chembl/assay.py` | Captures assay metadata (category, organism, BAO IDs/labels, classifications, strain/tissue, target IDs). |
| Document | `DocumentTableSchema` | `src/bioetl/domain/schemas/chembl/document.py` | Publication-level data (DOI/PubMed, journal info, doc type, score). |
| Molecule (acts as “TestItem”) | `MoleculeTableSchema` | `src/bioetl/domain/schemas/chembl/molecule.py` | Molecule hierarchies, properties, clinical phase, availability flags, synonyms. |
| Target | `TargetTableSchema` | `src/bioetl/domain/schemas/chembl/target.py` | Target identifiers, taxonomy, organism, type, UniProt linkage, cross references. |

### 1.3 Bounded context coverage

- ChEMBL entities (`activity`, `assay`, `document`, `molecule`, `target`) have Pandera schemas registered via `bioetl.domain.schemas.register_schemas`.
- Documentation still references `TestItem` as a separate concept, but code only exposes `MoleculeTableSchema`; there are no domain objects or schemas for `cell`, `tissue`, `test_item`, despite CSV fixtures existing under `data/input`.
- All entities are handled as Pandas dataframes; there are no aggregate/domain classes per entity, so the bounded contexts are defined solely by schema names.

## 2. Duplicate / divergent definitions

1. **Hash service duplication** – `src/bioetl/domain/transform/hash_service.py` implements `HashService` while `src/bioetl/infrastructure/transform/impl/hash_service_impl.py` re-implements the same API (hash columns, index, metadata) against the same `HashServiceABC`. Keeping both causes drift risk and confuses consumers about the canonical entry point.
2. **Logging/observability shims** – `src/bioetl/domain/observability/contracts.py` defines the current logging/tracing ports, yet `src/bioetl/domain/clients/base/logging/contracts.py` (deprecated) still exposes `ProgressReporterABC` and emits runtime `DeprecationWarning`. Both modules are exported from the domain layer, which means new code can still import the legacy shim accidentally.
3. **Config re-export layer** – `src/bioetl/domain/configs/base.py` is a purely duplicative module that re-imports everything from `pipeline.py` for “legacy compatibility”. It keeps stale import paths alive and hides the real source of truth.
4. **Extraction contract shim** – `src/bioetl/domain/contracts.py` re-exports `ExtractionServiceABC` and `BatchAdapterABC` from `domain.ports.extraction` with a `Deprecated shim` banner, adding another dangling alias.
5. **Domain glossary vs code** – `docs/domain/01-glossary.md` and `docs/domain/schemas/00-schemas-overview.md` describe `TestItem`/`TestitemSchema`, but the codebase only has `MoleculeTableSchema`. Two names for the same business concept lead to fragmented documentation.

#### Duplicate cleanup checklist

- [ ] Merge `HashService` and `HashServiceImpl` into one canonical implementation (keep tests + DI wiring in a single place).
- [ ] Remove/replace `bioetl.domain.clients.base.logging.contracts` exports; migrate remaining imports to `bioetl.domain.observability`.
- [ ] Drop `bioetl.domain.configs.base` and update callers to import directly from `pipeline.py`.
- [ ] Remove `bioetl.domain.contracts` shim and fix imports to use `bioetl.domain.ports.extraction`.
- [ ] Update glossary/schema docs to rename `TestItem` → `Molecule` (or introduce an actual `TestItem` model) so code and documentation agree.

## 3. ABC / Protocol audit

| Port / ABC | Location | Implementations today | Observation | Suggested action |
| --- | --- | --- | --- | --- |
| `RequestBuilderABC` | `domain/clients/base/contracts.py` | Only `ChemblRequestBuilderImpl` via `default_request_builder` (requires `base_url`) | No evidence of alternative providers; factory raises without URL | Collapse into provider-specific builder or keep interface only if another provider is imminent. |
| `ResponseParserABC` | same | Only `ChemblResponseParserImpl` | Currently redundant abstraction | Inline into ChemBL client or stub explicit reason for polymorphism. |
| `PaginatorABC` | same | Only `ChemblPaginatorImpl` | No non-ChemBL paginator | Replace with simple strategy enum or postpone until we add a second provider. |
| `RateLimiterABC` | same | Only `TokenBucketRateLimiterImpl` | Abstraction around a single implementation | Keep only if we expect to inject e.g. noop limiter in tests; otherwise expose concrete helper. |
| `RetryPolicyABC` | same | Only `ExponentialBackoffRetryImpl` | Same as above | Consider collapsing into plain dataclass/config-driven helper. |
| `CacheABC` | same | `MemoryCacheImpl`, `FileCacheImpl` | Two variants exist; abstraction justified | Keep. |
| `SecretProviderABC` | same | `EnvSecretProvider` | Only env-backed provider, but extension is plausible (vault) | Keep but move out of “domain” namespace into infrastructure-facing package. |
| `SideInputProviderABC` | same | No implementation (`default_side_input_provider` raises) | Classic speculative generality | Remove until a real provider exists. |
| `BatchAdapterABC` | `domain/ports/extraction.py` | Only `PandasBatchAdapter` | Could be replaced with `Callable[[Any], list[RawRecord]]` | Downgrade to simple callable type alias. |
| `HashServiceABC` | `domain/transform/contracts.py` | `HashService` (domain) + `HashServiceImpl` (infra) | Two parallel trees implement same thing | Keep the ABC but delete one concrete implementation. |

#### Abstraction cleanup checklist

- [ ] Remove `SideInputProviderABC` (or implement a real provider + tests).
- [ ] Replace `RequestBuilderABC` / `ResponseParserABC` / `PaginatorABC` / `BatchAdapterABC` with simpler callables until a second provider appears.
- [ ] Document an explicit extension plan for `RateLimiterABC` + `RetryPolicyABC`; if none exists, inline them to reduce noise.
- [ ] Keep `CacheABC`, `SecretProviderABC`, `HashServiceABC`, `NormalizationServiceABC`, `SchemaProviderABC` as the vetted ports.

## 4. DDD boundary issues

1. **DataFrame-centric “domain”** – Core contracts such as `NormalizationServiceABC`, `HashServiceABC`, and `ValidationResult` operate directly on `pandas.DataFrame`/`Series` (`src/bioetl/domain/transform/contracts.py`, `src/bioetl/domain/validation/contracts.py`). There are no aggregates for `Activity`, `Assay`, etc., so business logic is expressed as column-level mutations. This makes the domain layer dependent on Pandas internals and hard to unit-test without DataFrames.
2. **Infrastructure-heavy pipeline config** – `PipelineConfig` embeds HTTP timeouts, rate limits, cache paths, logging levels, and feature flags in the same object that carries domain identifiers (`entity`, `provider`). The domain layer therefore knows about networking, observability, and storage (see `src/bioetl/domain/configs/pipeline.py` sections `ClientConfig`, `StorageConfig`, `LoggingConfig`, `MetricsConfig`). Split the structure into a pure domain contract plus infrastructure profiles.
3. **Record source orchestrates extraction** – `ApiRecordSource` (`src/bioetl/domain/record_source.py`) loops over `ExtractionServiceABC.iter_extract`, applies chunking, and batch adaptation. This is orchestration logic that fits better in the application layer; today it lives in the domain package and depends on the extraction service protocol.
4. **Domain-defined IO ports know filesystem semantics** – `WriterABC` / `OutputWriterABC` in `src/bioetl/domain/clients/base/output/contracts.py` require `pathlib.Path`, atomic-write knowledge, and Pandas DataFrames. Those concerns belong to infrastructure; the domain should define an abstract “export table” use case with DTOs instead of file paths.
5. **Documentation vs code boundaries** – Architecture docs still present `TestItem` as a first-class aggregate (`docs/architecture/01-domain-objects.md`), but no such model or schema exists. This misalignment confuses bounded contexts and hides that the “test item” context is currently served by `MoleculeTableSchema`.

Each of these issues dilutes the “pure domain” boundary and makes it harder to enforce deterministic, infrastructure-agnostic business logic.

## 5. Target state for a clean domain layer

- Exactly one canonical model (class or schema) per business concept (`Activity`, `Assay`, `Target`, `Molecule/TestItem`, `Document`, etc.).
- Domain services operate on typed aggregates/value objects rather than raw `pd.DataFrame` instances; adapters handle conversion at the application boundary.
- Only meaningful ports remain; every ABC has at least two real implementations or a clear extension strategy. Legacy shims and speculative abstractions are removed.
- Domain packages no longer expose infrastructure details (paths, HTTP settings, logging flags). Those live in configuration profiles or infrastructure services.
- Docs and diagrams mirror the codebase (matching names, column sets, and dependencies) to keep bounded contexts explicit.

## 6. Refactoring roadmap

| Phase | Focus | Key actions |
| --- | --- | --- |
| Phase 0 – Cleanup (now) | Remove dead weight | Apply the duplicate and abstraction checklists: delete shims, collapse hash service, drop unused ABCs, update documentation terminology. |
| Phase 1 – Domain modeling | Introduce aggregates | Define lightweight dataclasses (or Pydantic models) for `Activity`, `Assay`, `Document`, `Target`, `Molecule` that mirror Pandera schemas; add mappers to/from DataFrames inside the application layer. |
| Phase 2 – Boundary hardening | Separate concerns | Split `PipelineConfig` into domain contract + infrastructure profile, move `ApiRecordSource` and writer abstractions into application/infrastructure namespaces, and keep only pure domain ports (e.g., `ExtractionServiceABC`). |
| Phase 3 – Provider extensibility | Justify abstractions | Once the domain has aggregates, re-introduce only the ports that are needed for multiple providers (e.g., additional request builders, parsers, or normalization services). Document expected variants and ensure tests cover each port. |

Tracking these phases alongside the provided checklists will progressively declutter the domain layer and prepare it for stricter DDD and hexagonal boundaries.

