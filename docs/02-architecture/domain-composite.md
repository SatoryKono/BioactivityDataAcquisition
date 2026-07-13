# Composite Domain Layer

## Обзор

Composite Domain Layer реализует паттерн Composite для оркестрации составных пайплайнов обогащения данных. Этот слой управляет конфигурацией, выполнением и слиянием данных из multiple enrichment pipelines в единую результирующую структуру.

**Связанный ADR:** ADR-026 (Composite Pipeline Pattern).

## Архитектура

### Основные компоненты

```
src/bioetl/domain/composite/
├── aggregation.py                    # Агрегация 1:M enrichers
├── config.py                         # Публичный API конфигурации
├── config_composite_serialization.py # Сериализация/десериализация
├── config_composite_validation.py    # Валидация конфигурации
├── config_cross_validation.py        # Immutable cross-enricher config и пороговые инварианты
├── config_dq.py                      # DQ конфигурация
├── config_merge.py                   # Конфигурация слияния
├── config_models.py                  # Базовые модели конфигурации
├── config_parsing.py                 # Парсинг конфигурации
├── config_runtime.py                 # Runtime конфигурация
├── config_schema.py                  # Schema конфигурации
├── config_validators.py              # Валидаторы конфигурации
├── cross_validation.py               # Cross-validation логика
├── field_groups.py                   # Field groups
├── field_groups_models.py            # Модели field groups
├── field_groups_registry.py          # Registry field groups
├── lineage.py                        # Lineage tracking
├── result.py                         # Результаты выполнения
├── result_composite.py               # Composite результаты
├── result_enrichment.py              # Enrichment результаты
├── result_merge.py                   # Merge результаты
├── result_seed_dependency.py         # Seed dependency результаты
├── state.py                          # State machine
└── strategy.py                       # Стратегии слияния
```

## Ключевые сущности

### 1. CompositeConfig

**Файл:** `config.py`

**Назначение:** Корневая конфигурация составного пайплайна.

**Поля:**
- `name: str` - имя пайплайна
- `version: str` - версия конфигурации
- `seed: SeedConfig` - конфигурация seed данных
- `enrichers: tuple[EnricherConfig, ...]` - конфигурации enrichers
- `merge: MergeConfig` - конфигурация слияния
- `dependencies: tuple[DependencyConfig, ...]` - зависимости
- `dq: CompositeDQConfig` - DQ конфигурация
- `execution: ExecutionConfig` - execution конфигурация
- `lineage: LineageConfig` - lineage конфигурация
- `cross_validation: CrossValidationConfig` - cross-validation конфигурация

**Методы:**
- `composite_from_dict()` - десериализация из dict
- `composite_to_dict()` - сериализация в dict
- `validate_composite_config()` - валидация конфигурации

### 2. EnricherConfig

**Файл:** `config_models.py`

**Назначение:** Конфигурация单个 enrichment pipeline.

**Поля:**
- `name: str` - имя enricher
- `pipeline_name: str` - имя пайплайна для обогащения
- `cardinality: EnricherCardinality` - кардинальность (1:1 или 1:M)
- `aggregation: AggregationConfig | None` - конфигурация агрегации для 1:M
- `field_mappings: tuple[FieldMapping, ...]` - маппинг полей
- `join_keys: tuple[str, ...]` - ключи для join с seed

### 3. AggregationConfig

**Файл:** `aggregation.py`

**Назначение:** Конфигурация агрегации для 1:M enrichers.

**Функции агрегации:**
- `COLLECT_LIST` - собрать все значения в список
- `COLLECT_SET` - собрать уникальные значения в список
- `COUNT` - количество значений
- `FIRST` - первое значение
- `CONCAT_STR` - конкатенация строк с разделителем

**Поля:**
- `function: AggregationFunction` - функция агрегации
- `field_specs: tuple[AggregationFieldSpec, ...]` - спецификации полей

### 4. MergeConfig

**Файл:** `config_merge.py`

**Назначение:** Конфигурация слияния enriched данных.

**Стратегии слияния:**
- `MERGE_LEFT_JOIN` - left join с seed
- `MERGE_INNER_JOIN` - inner join с seed
- `MERGE_FULL_OUTER_JOIN` - full outer join

**Поля:**
- `strategy: MergeStrategy` - стратегия слияния
- `column_groups: tuple[ColumnGroupConfig, ...]` - группировка колонок
- `conflict_resolution: ConflictResolution` - разрешение конфликтов

### 5. CrossValidationConfig

**Файл:** `cross_validation.py`

**Назначение:** Конфигурация cross-validation между enrichers.

**Поля:**
- `enabled: bool` - включена ли cross-validation
- `field_pairings: tuple[EnricherFieldPairing, ...]` - пары полей для сравнения
- `comparison_method: ComparisonMethod` - метод сравнения
- `tolerance: float | None` - допуск для численных сравнений

**Вердикты:**
- `MATCH` - поля совпадают
- `MISMATCH` - поля не совпадают
- `MISSING` - поле отсутствует в одном из enrichers

### 6. Field Groups

**Файл:** `field_groups.py`

**Назначение:** Определение групп полей для структурной организации.

**Классы:**
- `FieldGroupDefinition` - определение группы полей
- `FieldGroupId` - идентификатор группы полей
- `FieldGroupRegistry` - реестр групп полей
- `FieldMapping` - маппинг между полями разных enrichers

**Методы:**
- `build_field_group_registry()` - построение реестра групп полей

### 7. Lineage Tracking

**Файл:** `lineage.py`

**Назначение:** Отслеживание происхождения данных (provenance).

**Классы:**
- `CompositeLineageMetadata` - метаданные lineage для merged records
- `EnrichmentStatusRecord` - статус enrichment для каждой записи
- `FieldSource` - источник поля (seed или конкретный enricher)

**Поля:**
- `record_id: str` - идентификатор записи
- `enricher_name: str` - имя enricher
- `status: EnrichmentStatus` - статус enrichment
- `field_sources: dict[str, FieldSource]` - маппинг полей к источникам

### 8. CompositeResult

**Файл:** `result.py`

**Назначение:** Результат выполнения composite пайплайна.

**Классы:**
- `CompositeResult` - общий результат
- `SeedResult` - результат seed этапа
- `EnrichmentResult` - результат enrichment этапа
- `MergeResult` - результат merge этапа
- `DependencyResult` - результат dependency этапа

**Статусы:**
- `SUCCESS` - успешное выполнение
- `FAILURE` - ошибка выполнения
- `PARTIAL` - частичное выполнение
- `SKIPPED` - пропущено

### 9. State Machine

**Файл:** `state.py`

**Назначение:** FSM для lifecycle composite пайплайна.

**Состояния:**
- `INITIALIZED` - пайплайн инициализирован
- `SEED_LOADING` - загрузка seed данных
- `ENRICHING` - enrichment данных
- `MERGING` - слияние данных
- `CROSS_VALIDATING` - cross-validation
- `COMPLETED` - выполнение завершено
- `FAILED` - ошибка выполнения

**Методы:**
- `can_transition()` - проверка возможности перехода
- `validate_transition()` - валидация перехода
- `get_transition_rules()` - получение правил переходов

### 10. Merge Strategies

**Файл:** `strategy.py`

**Назначение:** Стратегии слияния и разрешения конфликтов.

**Стратегии слияния:**
- `MERGE_LEFT_JOIN` - left join
- `MERGE_INNER_JOIN` - inner join
- `MERGE_FULL_OUTER_JOIN` - full outer join

**Разрешение конфликтов:**
- `PREFER_SEED` - предпочитать seed значения
- `PREFER_ENRICHER` - предпочитать enricher значения
- `PREFER_LATEST` - предпочитать последние значения
- `RAISE_ERROR` - вызывать ошибку при конфликте

**Fallback стратегии:**
- `USE_NULL` - использовать NULL
- `USE_DEFAULT` - использовать значение по умолчанию
- `SKIP_RECORD` - пропустить запись

## Workflow выполнения

1. **Initialization**
   - Загрузка CompositeConfig
   - Валидация конфигурации
   - Инициализация state machine

2. **Seed Loading**
   - Загрузка seed данных
   - Валидация seed данных
   - Переход в состояние `SEED_LOADING`

3. **Enrichment**
   - Последовательное выполнение enrichers
   - Применение aggregation для 1:M enrichers
   - Field mapping
   - Переход в состояние `ENRICHING`

4. **Merge**
   - Слияние enriched данных с seed
   - Применение merge strategy
   - Разрешение конфликтов
   - Переход в состояние `MERGING`

5. **Cross-Validation**
   - Сравнение полей между enrichers
   - Генерация mismatch отчетов
   - Применение tolerance для численных сравнений
   - Переход в состояние `CROSS_VALIDATING`

6. **Completion**
   - Формирование CompositeResult
   - Генерация lineage metadata
   - Переход в состояние `COMPLETED`

## Связанные ADR

- **ADR-026:** принятое архитектурное решение для этого слоя.
- **ADR-008:** Graceful Shutdown Strategy — исторический superseded ADR;
  он не определяет архитектуру этого слоя.

## Зависимости

### Internal
- `bioetl.domain.ports` - порты для доступа к данным
- `bioetl.domain.value_objects` - value objects для domain модели
- `bioetl.domain.aggregates` - aggregates для domain модели

### External
- `dataclasses` - для dataclass моделей
- `enum` - для enum типов
- `typing` - для type hints

## Примеры использования

### Создание CompositeConfig

```python
from bioetl.domain.composite import CompositeConfig, SeedConfig, EnricherConfig, MergeConfig

seed_config = SeedConfig(
    pipeline_name="seed_pipeline",
    table_name="seed_table",
)

enricher_config = EnricherConfig(
    name="pubchem_enricher",
    pipeline_name="pubchem_pipeline",
    cardinality=EnricherCardinality.ONE_TO_MANY,
    join_keys=("compound_id",),
)

merge_config = MergeConfig(
    strategy=MergeStrategy.MERGE_LEFT_JOIN,
    conflict_resolution=ConflictResolution.PREFER_SEED,
)

composite_config = CompositeConfig(
    name="bioactivity_composite",
    version="1.0.0",
    seed=seed_config,
    enrichers=(enricher_config,),
    merge=merge_config,
)
```

### Cross-Validation

```python
from bioetl.domain.composite import CrossValidationConfig, EnricherFieldPairing, ComparisonMethod

field_pairing = EnricherFieldPairing(
    enricher_a="pubchem_enricher",
    enricher_b="chembl_enricher",
    field_a="activity_value",
    field_b="standard_value",
)

cv_config = CrossValidationConfig(
    enabled=True,
    field_pairings=(field_pairing,),
    comparison_method=ComparisonMethod.ABSOLUTE_DIFFERENCE,
    tolerance=0.1,
)
```

## Тестирование

Тесты для composite domain layer находятся в:
- `tests/unit/domain/composite/` - unit тесты
- `tests/integration/domain/composite/` - integration тесты

## Метрики качества

- Покрытие тестами: >90%
- Cyclomatic complexity: <10 для всех функций
- Type coverage: 100% (strict mode)
