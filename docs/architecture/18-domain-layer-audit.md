# Domain Layer Audit - BioETL

> **Дата аудита**: 2025-12-10
> **Версия**: 2.0
> **Область анализа**: `src/bioetl/domain/`

---

## 1. Краткий обзор domain-слоя

### 1.1 Структура и организация

Domain-слой BioETL организован по принципам **Hexagonal Architecture (Ports & Adapters)** и содержит:

```
src/bioetl/domain/
├── __init__.py                 # Экспорт доменных ошибок
├── enums.py                    # ErrorAction enum
├── errors.py                   # Иерархия исключений (10 классов)
├── models.py                   # Core Value Objects (4 класса)
├── providers.py                # Provider abstractions
├── provider_registry.py        # Provider registry ABC + impl
├── record_source.py            # Record source abstractions
├── clients/                    # Client ports (8 ABC)
├── configs/                    # Configuration models (~30 классов)
├── pipelines/                  # Pipeline contracts (4 ABC)
├── ports/                      # Extraction ports (6 ABC)
├── schemas/                    # Schema definitions
│   ├── chembl/                 # ChEMBL-specific schemas (8 Pandera models)
│   └── registry.py             # Schema registry
├── transform/                  # Transform contracts + impl
│   └── normalizers/            # Field normalizers
├── validation/                 # Validation contracts
└── observability/              # Observability ports (4 ABC)
```

### 1.2 Основные агрегаты и контексты

| Bounded Context | Ключевые сущности | Файлы |
|-----------------|-------------------|-------|
| **Pipeline Execution** | `RunContext`, `RunResult`, `StageResult`, `StageDescriptor` | `models.py` |
| **Configuration** | `PipelineConfig` (aggregate), 25+ config VOs | `configs/pipeline.py`, `configs/defaults.py` |
| **Provider Management** | `ProviderId`, `ProviderDefinition`, `ProviderRegistryABC` | `providers.py`, `provider_registry.py` |
| **Data Extraction** | `RecordSourceABC`, `ExtractionServiceABC`, `RecordFetcherABC` | `record_source.py`, `ports/extraction.py` |
| **Data Transform** | `HasherABC`, `HashServiceABC`, `NormalizationServiceABC`, `TransformerABC` | `transform/` |
| **Data Validation** | `ValidatorABC`, `SchemaProviderABC`, `ValidationResult` | `validation/` |
| **ChEMBL Schemas** | `ActivityTableSchema`, `AssayTableSchema`, `MoleculeTableSchema`, etc. | `schemas/chembl/` |

### 1.3 Статистика

| Метрика | Значение |
|---------|----------|
| Всего классов/моделей | ~95 |
| Abstract Base Classes (ABC) | ~40 |
| Protocols | ~12 |
| Конкретных реализаций в domain | ~20 |
| Enums | 3 |
| Value Objects | ~45 |
| Exceptions | 10 |
| Файлов Python | 57 |

---

## 2. Выявленные проблемы

### 2.1 Дублирующие и семантически пересекающиеся модели

| ID | Проблема | Файлы | Суть нарушения | Приоритет |
|----|----------|-------|----------------|-----------|
| **DUP-01** | `HttpClientSettings` vs `HttpClientDefaults` vs `ClientConfig` | `configs/pipeline.py:38-85` | Три модели с перекрывающимися полями (`timeout`, `retries`, `backoff`, `rate_limit`). `ClientConfig` содержит метод `from_http_settings()` для синхронизации, что указывает на дублирование. | **Высокий** |
| **DUP-02** | `ClientDefaultsConfig` extends `ClientConfig` | `configs/defaults.py:32-35` | Класс-наследник без добавления полей - фактический дубликат. | Средний |
| **DUP-03** | `NormalizationConfig` в двух местах | `configs/normalization.py`, `transform/contracts.py` (re-export) | Модель определена в `normalization.py`, но re-export в `transform/contracts.py` создаёт путаницу в ownership. | Низкий |
| **DUP-04** | `RecordFetcherABC` vs `ExtractionServiceABC` | `ports/extraction.py:13-69` | Оба интерфейса содержат методы `iter_extract()` и `extract_all()` с идентичными сигнатурами. `ExtractionServiceABC` расширяет функциональность, но дублирует базовые методы. | **Высокий** |
| **DUP-05** | `VersionedRecordFetcherABC` | `ports/extraction.py:35-37` | Пустой класс-маркер, наследующий от двух ABC без добавления логики. | Низкий |

### 2.2 Неиспользуемые/слабо используемые модели

| ID | Элемент | Файл | Использование | Рекомендация | Приоритет |
|----|---------|------|---------------|--------------|-----------|
| **UNUSED-01** | `SideInputProviderABC` | `clients/base/contracts.py:136-147` | 0 реализаций, только в документации | Удалить или задокументировать как roadmap | Средний |
| **UNUSED-02** | `TracingPortABC` | `observability/contracts.py:39-52` | 1 stub-реализация, не интегрирован в pipeline | Пометить как experimental | Низкий |
| **UNUSED-03** | `SecretProviderABC` | `clients/base/contracts.py:126-133` | 1 реализация (`EnvSecretProvider`), редко используется | Оставить для Vault интеграции | Низкий |
| **UNUSED-04** | `CacheABC` | `clients/base/contracts.py:104-123` | 1 реализация, используется ограниченно | Расширить использование или удалить | Низкий |
| **UNUSED-05** | `VersionedRecordFetcherABC` | `ports/extraction.py:35-37` | Минимальное использование | Удалить, использовать композицию | Низкий |
| **UNUSED-06** | `RecordSource` alias | `record_source.py:29` | Backward compatibility alias | Удалить после миграции | Низкий |

### 2.3 God Objects и разросшиеся агрегаты

| ID | Элемент | Файл | Проблема | Метрика | Приоритет |
|----|---------|------|----------|---------|-----------|
| **GOD-01** | `PipelineConfig` | `configs/pipeline.py:456-785` | **330 строк**, 15+ вложенных секций, 20+ property-аксессоров для backward compatibility, сложная логика миграции legacy формата | Cyclomatic complexity: высокая | **Критический** |
| **GOD-02** | `ExtractionServiceABC` | `ports/extraction.py:40-69` | 6 абстрактных методов с разной семантикой (fetch, parse, serialize) - нарушение ISP | Cohesion: низкая | **Высокий** |
| **GOD-03** | `HashService` | `transform/hash_service.py` | Содержит stateful логику (`_index_counter`, `_extracted_at`) - не чистый сервис | Statefulness в domain service | Средний |

### 2.4 Нарушения принципов DDD

#### 2.4.1 Смешение слоёв (Layer Leakage)

| ID | Нарушение | Файл:строка | Описание | Приоритет |
|----|-----------|-------------|----------|-----------|
| **LAYER-01** | `pandas.DataFrame` в domain contracts | `transform/contracts.py:35-56`, `validation/contracts.py:26-31` | Domain-интерфейсы зависят от pandas - это infrastructure concern | **Высокий** |
| **LAYER-02** | `Path` в domain contracts | `pipelines/contracts.py:68-85` | `LoaderABC` принимает `Path` - это I/O деталь | Средний |
| **LAYER-03** | `ApiRecordSource` - конкретная реализация в domain | `record_source.py:49-82` | Класс содержит логику оркестрации, должен быть в application layer | **Высокий** |
| **LAYER-04** | `InMemoryProviderRegistry` в domain | `provider_registry.py:70-101` | Конкретная реализация в domain, хотя это infrastructure concern | Средний |
| **LAYER-05** | Global singleton `registry` | `schemas/registry.py:71` | Глобальное состояние в domain layer | Средний |

#### 2.4.2 Нарушение границ агрегатов

| ID | Нарушение | Описание | Приоритет |
|----|-----------|----------|-----------|
| **AGG-01** | `PipelineConfig` как mega-aggregate | Содержит ВСЕ аспекты конфигурации: runtime, observability, quality, features, transform, output, provider | **Критический** |
| **AGG-02** | `ProviderDefinition` содержит `HttpClientSettings` | Provider definition смешивается с HTTP-конфигурацией | Средний |

#### 2.4.3 Примитивы вместо Value Objects

| ID | Место | Текущий тип | Рекомендуемый VO | Приоритет |
|----|-------|-------------|------------------|-----------|
| **VO-01** | `RunContext.run_id` | `str` | `RunId` (с валидацией UUID) | Низкий |
| **VO-02** | `PipelineConfig.entity` | `str` | `EntityName` (с ограничениями) | Низкий |
| **VO-03** | `HashingConfig.algorithm` | `str` | `HashAlgorithm` (enum или VO) | Низкий |
| **VO-04** | `*Config.path` fields | `str` | `FilePath` или `DirectoryPath` VO | Низкий |
| **VO-05** | Business key fields | `list[str]` | `BusinessKeySpec` VO | Средний |

#### 2.4.4 Нарушение Ubiquitous Language

| ID | Термин в коде | Термин предметной области | Файл | Приоритет |
|----|---------------|---------------------------|------|-----------|
| **LANG-01** | `RawRecord` | `SourceRecord` / `ExtractedRecord` | `record_source.py` | Низкий |
| **LANG-02** | `hash_row` / `hash_business_key` | `row_fingerprint` / `entity_key_hash` | `transform/` | Низкий |
| **LANG-03** | `extracted_at` | `acquisition_timestamp` | `transform/hash_service.py` | Низкий |
| **LANG-04** | `QcConfig` | `QualityControlConfig` | `configs/pipeline.py` | Низкий |

---

## 3. Предлагаемые изменения

### 3.1 Критический приоритет

#### REF-01: Декомпозиция `PipelineConfig`

**Проблема**: `PipelineConfig` - god object с 330 строками, 15+ секциями, сложной миграцией legacy формата.

**Решение**:
```
PipelineConfig (aggregate root, ~50 строк)
├── PipelineIdentity (id, provider, entity, primary_key)
├── DataSourceConfig (input_mode, input_path, batch_size)
├── DataSinkConfig (output_path, dry_run)
└── provider_config: ProviderConfigUnion

Отдельные конфигурационные агрегаты:
- RuntimeConfig (уже существует, оставить)
- ObservabilityConfig (уже существует, оставить)
- QualityConfig (уже существует, оставить)
```

**Действия**:
1. Вынести legacy migration в отдельный `ConfigMigrator` сервис
2. Удалить 20+ property-аксессоров backward compatibility
3. Создать builder или factory для сборки полной конфигурации

#### REF-02: Унификация `RecordFetcherABC` и `ExtractionServiceABC`

**Проблема**: Дублирование методов `iter_extract()` и `extract_all()`.

**Решение**:
```python
# Базовый интерфейс
class RecordFetcherABC(ABC):
    def iter_extract(self, entity: str, **filters) -> Iterable[list[RawRecord]]: ...
    def extract_all(self, entity: str, **filters) -> list[RawRecord]: ...

# Расширенный интерфейс (без дублирования)
class ExtractionServiceABC(RecordFetcherABC):
    def get_release_version(self) -> str: ...
    def request_batch(self, entity: str, batch_ids: list[str], filter_key: str) -> dict: ...
    def parse_response(self, raw_response: object) -> list[RawRecord]: ...
    def serialize_records(self, entity: str, records: list[object]) -> list[object]: ...
```

**Действия**:
1. Сделать `ExtractionServiceABC` наследником `RecordFetcherABC`
2. Удалить дублирующие методы из `ExtractionServiceABC`
3. Удалить `VersionedRecordFetcherABC`

### 3.2 Высокий приоритет

#### REF-03: Устранение дублирования HTTP-конфигураций

**Проблема**: `HttpClientSettings`, `HttpClientDefaults`, `ClientConfig` имеют перекрывающиеся поля.

**Решение**:
```python
# Единственный источник истины для HTTP-настроек
class HttpClientConfig(BaseModel):
    timeout_sec: PositiveFloat = 30.0
    max_retries: NonNegativeInt = 3
    rate_limit_per_sec: PositiveFloat = 2.5
    backoff_factor: float = 2.0
    retry_enabled: bool = True

    # Circuit breaker - опционально
    circuit_breaker_threshold: int | None = None
    circuit_breaker_recovery_time: float | None = None

# Для провайдеров - расширение с base_url
class ProviderHttpConfig(HttpClientConfig):
    base_url: AnyHttpUrl
```

**Действия**:
1. Объединить `HttpClientSettings`, `HttpClientDefaults`, `ClientConfig` в `HttpClientConfig`
2. Удалить метод `ClientConfig.from_http_settings()`
3. Удалить `ClientDefaultsConfig`

#### REF-04: Вынос `ApiRecordSource` в application layer

**Проблема**: Конкретная реализация с логикой оркестрации находится в domain.

**Решение**:
```
domain/record_source.py:
  - RecordSourceABC (оставить)
  - RawRecord (оставить)
  - InMemoryRecordSource (оставить - простая реализация)

application/sources/api_record_source.py:
  - ApiRecordSource (перенести)
```

#### REF-05: Абстрагирование от pandas в domain contracts

**Проблема**: `HasherABC`, `NormalizationServiceABC`, `ValidatorABC` зависят от `pd.DataFrame`.

**Решение**:
1. Ввести generic type alias: `DataFrame = TypeVar('DataFrame')`
2. Или использовать Protocol для DataFrame-like объектов
3. Или оставить как есть с документированным обоснованием (pandas - де-факто стандарт для tabular data в Python)

**Рекомендация**: Оставить с обоснованием - pandas слишком фундаментален для data pipelines, абстрагирование создаст ненужную сложность.

### 3.3 Средний приоритет

#### REF-06: Удаление неиспользуемых ABC

**Действия**:
1. Удалить `SideInputProviderABC` (0 реализаций)
2. Удалить `VersionedRecordFetcherABC` (пустой маркер)
3. Пометить `TracingPortABC` как `@experimental`

#### REF-07: Устранение глобального состояния

**Проблема**: `schemas/registry.py:71` содержит глобальный singleton `registry`.

**Решение**:
1. Удалить глобальный `registry`
2. Создавать экземпляры через DI container
3. Оставить `default_schema_provider()` factory function

#### REF-08: Перенос `InMemoryProviderRegistry` в infrastructure

**Проблема**: Конкретная реализация в domain layer.

**Решение**:
```
domain/provider_registry.py:
  - ProviderRegistryABC
  - ProviderRegistryError (и наследники)
  - default_provider_registry() -> ProviderRegistryABC

infrastructure/provider_registry.py:
  - InMemoryProviderRegistry
```

### 3.4 Низкий приоритет

#### REF-09: Введение Value Objects для строковых полей

Создать VO для:
- `RunId` (UUID validation)
- `EntityName` (snake_case, limited charset)
- `HashAlgorithm` (enum: blake2b, sha256, etc.)

#### REF-10: Выравнивание терминологии

- `RawRecord` → `SourceRecord`
- `hash_row` → `row_fingerprint`
- `QcConfig` → `QualityControlConfig`

#### REF-11: Удаление backward compatibility aliases

- Удалить `RecordSource = RecordSourceABC` alias
- Удалить property-аксессоры в `PipelineConfig` после миграции

---

## 4. Сводная таблица приоритетов

| ID | Проблема | Приоритет | Сложность | Риск breaking changes |
|----|----------|-----------|-----------|----------------------|
| REF-01 | Декомпозиция PipelineConfig | Критический | Высокая | Высокий |
| REF-02 | Унификация Fetcher/Extraction ABC | Критический | Средняя | Средний |
| REF-03 | Устранение дублирования HTTP-конфигов | Высокий | Средняя | Высокий |
| REF-04 | Вынос ApiRecordSource | Высокий | Низкая | Низкий |
| REF-05 | Абстрагирование от pandas | Высокий | - | - |
| REF-06 | Удаление неиспользуемых ABC | Средний | Низкая | Низкий |
| REF-07 | Устранение глобального состояния | Средний | Низкая | Средний |
| REF-08 | Перенос InMemoryProviderRegistry | Средний | Низкая | Низкий |
| REF-09 | Введение Value Objects | Низкий | Средняя | Низкий |
| REF-10 | Выравнивание терминологии | Низкий | Низкая | Средний |
| REF-11 | Удаление BC aliases | Низкий | Низкая | Высокий |

---

## 5. Итоговое резюме

### 5.1 Общая оценка

**Состояние domain-слоя: удовлетворительное с локальными проблемами**

**Сильные стороны**:
- Чёткая структура по принципам Hexagonal Architecture
- Хорошее разделение на подмодули (clients, configs, transform, validation, etc.)
- Правильное использование ABC/Protocol для определения портов
- Детерминированная обработка данных (hash service, timestamps)
- Расширяемость через registry patterns

**Ключевые проблемы**:
1. **`PipelineConfig` - god object** (~330 строк, 15+ секций) - требует декомпозиции
2. **Дублирование HTTP-конфигураций** (3 класса с перекрывающимися полями)
3. **Дублирование extraction интерфейсов** (`RecordFetcherABC` vs `ExtractionServiceABC`)
4. **Смешение слоёв**: конкретные реализации (`ApiRecordSource`, `InMemoryProviderRegistry`) в domain
5. **Неиспользуемые абстракции** (`SideInputProviderABC`, `VersionedRecordFetcherABC`)

### 5.2 Рекомендуемый roadmap

| Этап | Срок | Задачи |
|------|------|--------|
| **Этап 1** (Quick wins) | 1-2 недели | REF-06 (удаление unused ABC), REF-07 (global state), REF-04 (перенос ApiRecordSource) |
| **Этап 2** (Унификация) | 2-4 недели | REF-02 (унификация extraction ABC), REF-03 (HTTP configs) |
| **Этап 3** (Рефакторинг) | 1-2 месяца | REF-01 (декомпозиция PipelineConfig), REF-08 (перенос registry) |
| **Этап 4** (Polish) | По мере необходимости | REF-09, REF-10, REF-11 |

### 5.3 Метрики для отслеживания

- Количество строк в `PipelineConfig` (цель: < 100)
- Количество дублирующих моделей (цель: 0)
- Количество конкретных реализаций в domain (цель: только immutable VOs)
- Покрытие тестами domain layer (цель: > 90%)
