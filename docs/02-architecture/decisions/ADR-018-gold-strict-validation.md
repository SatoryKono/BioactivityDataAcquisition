______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-018: Строгая валидация Gold-схем

**Date:** 2025-12-26
**Status:** Accepted
**Decision makers:** @BioETL-Team
**Related:** ADR-035 (JSON Field Typing Policy)

## Context

Gold-слой должен гарантировать качество данных для downstream consumers.
Исторически ADR вводила feature flag для контролируемой миграции существующих
пайплайнов. Этот миграционный этап завершён: текущий runtime contract требует
строгую Gold validation по умолчанию и fail-closed поведение для Gold write path.

## Decision

BioETL использует **обязательную строгую валидацию Gold-схем**. Текущий
источник истины для runtime enforcement:

- `src/bioetl/domain/config/runtime.py`: `RuntimeConfig.strict_gold_validation`
  по умолчанию `True`;
- `src/bioetl/composition/factories/pipeline/_factory_method_control_plane.py`:
  production runs принудительно включают strict Gold validation;
- `src/bioetl/infrastructure/storage/gold/validation_mixin.py`: Gold schema
  validation требует Pandera `strict=True`;
- `docs/04-reference/contracts/gold-schemas.md`: public contract documentation
  фиксирует Pandera-based `strict=True` для Gold.

Миграционный feature flag остаётся только историческим контекстом. Его нельзя
использовать как текущую Gold policy, отключающую fail-closed runtime behavior.

**Operationalization note (2026-05-14):** for semantic field unification,
Gold-facing schema and config validation surfaces bind to canonical names
listed in `configs/field_registry/canonical_registry.json`.

### 1. Обязательная Gold-схема

В текущем runtime strict Gold validation включена по умолчанию:

```python
@dataclass(frozen=True)
class RuntimeConfig:
    """Runtime policy shared by pipeline assembly."""

    strict_gold_validation: bool = True
```

**Правила валидации:**

| Условие              | Текущее Gold runtime поведение |
| -------------------- | ------------------------------ |
| `gold_schema=None`   | FAIL для strict Gold write path |
| Pandera `strict=False` | FAIL: Gold schemas must use `strict=True` |
| Несоответствие типов | FAIL до публикации Gold output |
| Отсутствующие поля   | FAIL до публикации Gold output |

### 2. Иерархия валидации

```
Pipeline Start
    │
    ▼
┌─────────────────────────────────────┐
│ Resolve strict_gold_validation       │
│ default=True; prod forces True       │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────┐   ┌─────────────────────┐
│ Check: gold schema │   │ Check: Pandera      │
└─────────────────────┘   │ strict=True         │
    │ None       │ Set    └─────────────────────┘
    ▼            ▼
┌──────────┐ ┌─────────────────┐
│ FAIL     │ │ Strict schema   │
│ Pipeline │ │ enforcement     │
└──────────┘ └─────────────────┘
```

### 3. Реализация в BasePipeline

```python
class BasePipeline:
    """Базовый класс пайплайна с поддержкой строгой валидации."""

    async def validate_gold_schema(self, context: PipelineContext) -> None:
        """Валидация Gold-схемы перед трансформацией.

        Raises:
            SchemaValidationError: Если Gold-схема отсутствует или не strict.
        """
        config = context.config

        if config.gold_schema is None:
            raise SchemaValidationError(
                f"Pipeline '{config.name}' requires strict Gold schema."
            )

        validate_schema_is_strict(config.gold_schema)
```

### 4. Исторический миграционный flag

Первоначальная версия ADR использовала feature flag `strict-gold-validation`
для безопасной миграции. В текущей архитектуре этот flag не является способом
отключить Gold strictness в production. Текущий статус миграции:

| Фаза | Действие                                           | Статус |
| ---- | -------------------------------------------------- | ------ |
| 1    | Добавить миграционный flag                         | Завершено |
| 2    | Определить Gold-схемы для опубликованных сущностей | Завершено для managed Gold contracts |
| 3    | Включить `strict_gold_validation=True` по умолчанию | Завершено |
| 4    | Принудительно включать strictness для production    | Завершено |

### 5. Конфигурация пайплайна

```yaml
# configs/entities/chembl/activity.yaml
pipeline:
  name: chembl_activity
  provider: chembl
  entity: activity
  strict-gold-validation: true

gold-schema:
  fields:
    - name: activity-id
      type: int64
      nullable: false
    - name: assay-chembl-id
      type: string
      nullable: false
    - name: molecule-chembl-id
      type: string
      nullable: false
    - name: standard-value
      type: float64
      nullable: true
    - name: standard-units
      type: string
      nullable: true
    - name: standard-type
      type: string
      nullable: true
```

### 6. Исключение ошибок

Новый тип исключения для валидации схем:

````python
class SchemaValidationError(BioETLError):
    """Ошибка валидации схемы Gold-слоя.

    Возникает при:
    - Отсутствии обязательной Gold-схемы (strict mode)
    - Несоответствии типов данных схеме
    - Отсутствии обязательных полей
    """

    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.field = field

### 7. Политика историчности Gold (SCD2)

Для Gold-слоя вводится явная классификация сущностей по требованиям к хранению истории.

| Класс сущности | Критерии | Рекомендуемый Gold mode |
|---|---|---|
| Reference dictionaries | Справочники/таксономии, где коды и названия корректируются со временем (без удаления исторических значений) | `scd2` |
| Slowly evolving records | Записи с редкими, но бизнес-значимыми изменениями атрибутов (например, аннотации/классификация) | `scd2` |
| Publication metadata | Метаданные публикаций из внешних API, где поля обогащения могут изменяться ретроспективно | `scd2` |
| Recomputed aggregates / derived outputs | Полностью пересчитываемые витрины и производные аналитические таблицы | `overwrite` |

Для всех SCD2-кандидатов Gold mode **MUST** задаваться явно в pipeline YAML (не полагаться на базовый дефолт).

**Шаблон `scd_config` (обязательные поля):**

```yaml
sink:
  gold:
    mode: scd2
    scd_config:
      valid_from_col: _valid_from
      valid_to_col: _valid_to
      current_flag_col: _is_current
      version_col: _version
````

Обязательные ключи `scd_config`: `valid_from_col`, `valid_to_col`, `current_flag_col`, `version_col`.

### 8. Migration table (Gold write mode)

| Entity                                                                                                                                | Current Mode                            | Recommended Mode       | Breaking                                 | Migration                                                                                 |
| ------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------- | ---------------------- | ---------------------------------------- | ----------------------------------------------------------------------------------------- |
| publication (chembl, pubmed, crossref, openalex, semanticscholar)                                                                     | `overwrite` (implicit via base/default) | `scd2`                 | Yes (new SCD2 columns/history semantics) | Full snapshot bootstrap -> enable `mode: scd2` + `scd_config` -> backfill valid intervals |
| reference dictionaries (chembl: assay, assay-parameters, cell-line, tissue, protein-class, subcellular-fraction)                      | `overwrite` (implicit)                  | `scd2`                 | Yes                                      | Rebuild Gold once, then switch to SCD2 with versioned updates                             |
| slowly evolving records (chembl: target, target-component, molecule, compound-record; uniprot: protein, idmapping; pubchem: compound) | `overwrite` (implicit)                  | `scd2`                 | Yes                                      | Initialize current snapshot as version=1, future changes produce new versions             |
| high-volume facts (chembl: activity)                                                                                                  | `overwrite` (implicit)                  | `merge`                | No                                       | Set explicit `mode: merge` with stable business keys for idempotent reruns                |
| recomputed derived outputs (chembl: publication-similarity, publication-term)                                                         | `overwrite` (implicit)                  | `overwrite` (explicit) | No                                       | Keep overwrite, but configure explicitly in pipeline YAML                                 |

### 9. Политика типов JSON-полей (дополнение)

С 2026-02-17 strict validation в Gold синхронизирована с единой политикой типизации JSON-like полей:

- **Канонический стандарт**: JSON-like поля в Silver и Gold представлены как canonical JSON string.
- **Нормативный источник**: [ADR-035](ADR-035-json-field-typing-policy.md).
- **Ограничение для strict mode**: при `strict-gold-validation=True` поля, определенные как JSON-like, валидируются как `Series[str]` (не `Series[object]`).

Это устраняет классы ошибок, где Silver передает `pa.list-(...)`, а Gold ожидает `Series[str]` (или наоборот), и делает контракты межслойной валидации детерминированными.

## Justification

### 1. Гарантия качества данных

Gold-слой потребляется downstream системами:

- ML pipelines
- Reporting dashboards
- API endpoints

Несогласованная схема ведёт к runtime ошибкам в downstream.

### 2. Раннее обнаружение проблем

Валидация на этапе трансформации:

- Быстрый feedback loop
- Проблемы обнаруживаются до записи в хранилище
- Меньше затрат на исправление

### 3. Документирование контракта

Gold-схема служит документацией:

- Явный контракт с consumers
- Версионирование схемы возможно
- Self-documenting pipeline configuration

### 4. Fail-closed strictness минимизирует downstream риск

Текущий default/production strictness:

- не допускает тихую публикацию непроверенных Gold outputs;
- делает contract drift видимым до записи;
- исключает расхождение dev/prod для published Gold contracts.

## Implementation Details

### Расположение файлов

```
src/bioetl/
├── domain/
│   ├── errors.py              # + SchemaValidationError
│   └── models/
│       └── gold_schema.py     # GoldSchema dataclass
├── application/
│   └── core/
│       └── base_pipeline.py   # + validate_gold_schema()
└── infrastructure/
    └── validation/
        └── gold_validator.py  # Pandera schema validation
```

### Интеграция с Pandera

```python
# infrastructure/validation/gold_validator.py
import pandera as pa

class GoldValidator:
    """Валидатор Gold-схем на основе Pandera."""

    def __init__(self, schema: GoldSchema):
        self.-pandera-schema = self.-build-pandera-schema(schema)

    def validate(self, df: pl.DataFrame) -> ValidationResult:
        """Валидация DataFrame против Gold-схемы."""
        try:
            self.-pandera-schema.validate(df.to-pandas())
            return ValidationResult(valid=True)
        except pa.errors.SchemaError as e:
            return ValidationResult(valid=False, errors=e.failure-cases)
```

### Тестирование

```python
# tests/unit/application/test_gold_validation.py

def test-strict-validation-fails-without-schema():
    """strict-gold-validation=True без схемы должен падать."""
    config = PipelineConfig(
        name="test-pipeline",
        provider="test",
        entity="test",
        strict-gold-validation=True,
        gold-schema=None,
    )
    context = create-test-context(config)
    pipeline = TestPipeline()

    with pytest.raises(SchemaValidationError) as exc-info:
        await pipeline.validate-gold-schema(context)

    assert "requires Gold schema" in str(exc-info.value)

def test-create-runner-forces-strict-gold-validation-in-prod():
    """Production assembly forces strict Gold validation."""
    runtime = RuntimeConfig(strict_gold_validation=False)
    settings = Settings(env="prod", test_mode=False)

    assert resolve_strict_gold_validation(runtime=runtime, settings=settings) is True
```

## Alternatives Considered

### 1. Всегда требовать Gold-схему

Исторически отклонялось на период миграции потому что:

- Breaking change для всех существующих пайплайнов
- Требует одновременного обновления всех конфигов
- Высокий риск при деплое

Текущий runtime contract после миграции принимает этот вариант для managed Gold
write path: Gold validation strictness включена по умолчанию, а production
assembly принудительно включает strictness даже если локальный runtime объект
создан со значением `False`.

### 2. Валидация только в production

Отклонено потому что:

- Проблемы обнаруживаются слишком поздно
- Dev/prod parity нарушается
- Сложнее отлаживать

### 3. Schema inference вместо явной схемы

Отклонено потому что:

- Не гарантирует стабильность
- Schema drift остаётся незамеченным
- Нет документации контракта

### 4. Валидация на уровне Delta Lake

Отклонено потому что:

- Delta Lake schema enforcement недостаточно гибкий
- Нет semantic validation (ranges, patterns)
- Ошибки обнаруживаются на этапе записи, не трансформации

## Consequences

### Positive

- **Гарантия качества**: Gold-схема явно определена и проверена
- **Раннее обнаружение**: Ошибки видны до записи в хранилище
- **Документация**: Схема служит контрактом с consumers
- **Fail-closed Gold publication**: production не публикует Gold output без
  strict schema enforcement
- **Тестируемость**: Можно unit-тестировать валидацию

### Negative

- **Дополнительная конфигурация**: Каждый пайплайн требует gold-schema
- **Начальные усилия**: Нужно определить схемы для существующих пайплайнов
- **Сложность**: Дополнительный слой валидации в pipeline

## Implementation Status (2025-12-28)

Все основные механизмы реализованы:

| Компонент                              | Статус        | Расположение                                             |
| -------------------------------------- | ------------- | -------------------------------------------------------- |
| `strict-gold-validation` флаг          | ✅ Реализован | `domain/config.py:259`                                   |
| `GoldValidatorPort` протокол           | ✅ Реализован | `domain/ports/validation.py:41-61`                       |
| `PanderaGoldValidator`                 | ✅ Реализован | `infrastructure/validation/pandera_validator.py:97-210`  |
| `GoldWriter._validate_schema_strict()` | ✅ Реализован | `infrastructure/storage/gold_writer.py:226-232`          |
| `NoOpValidator`                        | ✅ Реализован | `infrastructure/validation/pandera_validator.py:235-255` |

**Отличия от первоначального предложения:**

- Вместо `SchemaValidationError` используется `ValidationResult` с errors — более гибкий подход
- Валидация интегрирована в `GoldWriter` через `_validate_schema_strict()` проверку
- Миграционный flag находится в `RuntimeConfig` вместо `PipelineConfig`, но
  текущая production assembly принудительно включает strictness и не трактует
  `False` как разрешение на soft Gold validation

## References

- [ADR-001](ADR-001-delta-lake-vs-parquet.md): Delta Lake vs Parquet — Gold layer uses Delta Lake
- [ADR-002](ADR-002-medallion-architecture.md): Medallion Architecture — Gold layer definition
- [ADR-004](ADR-004-pydantic-vs-dataclasses.md): Pydantic vs Dataclasses — Pydantic/Pandera for validation
- [ADR-016](ADR-016-error-handling-strategy.md): Error Handling Strategy — error classification for validation errors
- [ADR-017](ADR-017-observability-architecture.md): Observability Architecture — logging integration

## Update 2026-02-17: JSON typing alignment

В рамках ADR-035 строгая валидация Gold теперь дополнительно фиксирует тип JSON-like полей как `Series[str]` (canonical JSON string), чтобы исключить дрейф `object`/`str` между пайплайнами.

- `Series[object]` для JSON-like полей в Gold-контрактах считается нарушением контракта.
- Миграция выполняется через dual-read совместимость 14 дней, затем обязательный backfill Delta-таблиц.

## Compliance

| Control      | Requirement                                                                | Status | Evidence                             |
| ------------ | -------------------------------------------------------------------------- | ------ | ------------------------------------ |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-018-gold-strict-validation.md`  |
| Status       | ADR status MUST be explicit and consistent                                 | `pass` | `Accepted`                           |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `n/a`  | `metadata block`                     |
| Verification | Implementation and validation expectations MUST be documented              | `pass` | `Verification / Acceptance Criteria` |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass` | `References`                         |

## Rollout

- Rollout steps MUST be sequenced before broad adoption.
- Documentation, configuration, and test surfaces SHOULD be updated in the same change set when the decision is implemented.
- Breaking or migration-sensitive adoption SHOULD include an explicit transition window.

## Rollback

- Rollback MUST identify the last known-good behavior or artifact set.
- If the decision changes contracts, configuration, or storage semantics, rollback SHOULD include data and compatibility checks.
- Rollback triggers SHOULD be observable through tests, runtime signals, or regression symptoms.

## Verification

- Verify architecture, configuration, and documentation changes against the current codebase.
- Run the relevant tests, validators, or parity checks before considering the ADR fully adopted.
- Confirm downstream docs and contracts reflect the same decision boundaries.

## Acceptance Criteria

- [ ] The decision is documented with current status, date, and owner metadata.
- [ ] The implementation path or adoption boundary is testable and linked from the ADR.
- [ ] Supersession or migration impact is documented when the decision changes an earlier posture.
- [ ] Related docs, contracts, and operational guidance are aligned with this ADR.
