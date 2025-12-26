# ADR-018: Строгая валидация Gold-схем

*   **Status**: Proposed
*   **Date**: 2025-12-26
*   **Context**: Gold-слой должен гарантировать качество данных для downstream consumers. Текущая реализация позволяет пайплайнам работать без определённой Gold-схемы, что может привести к несогласованности данных и проблемам интеграции.

## The Decision

Мы вводим **строгую валидацию Gold-схем** с feature flag для контролируемой миграции существующих пайплайнов.

### 1. Обязательная Gold-схема

При `strict_gold_validation=True` в конфигурации пайплайна:

```python
@dataclass(frozen=True)
class PipelineConfig:
    """Конфигурация пайплайна."""
    name: str
    provider: str
    entity: str
    strict_gold_validation: bool = False  # Feature flag
    gold_schema: GoldSchema | None = None
```

**Правила валидации:**

| Условие | `strict_gold_validation=True` | `strict_gold_validation=False` |
|---------|-------------------------------|--------------------------------|
| `gold_schema=None` | `SchemaValidationError` (FAIL) | Warning в лог |
| Несоответствие типов | `SchemaValidationError` (FAIL) | Warning + пропуск записи |
| Отсутствующие поля | `SchemaValidationError` (FAIL) | Warning + `None` значение |

### 2. Иерархия валидации

```
Pipeline Start
    │
    ▼
┌─────────────────────────────────────┐
│ Check: strict_gold_validation=True? │
└─────────────────────────────────────┘
    │ Yes                      │ No
    ▼                          ▼
┌─────────────────────┐   ┌─────────────────────┐
│ Check: gold_schema? │   │ Soft validation     │
└─────────────────────┘   │ (warnings only)     │
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
            SchemaValidationError: Если strict_gold_validation=True и схема отсутствует.
        """
        config = context.config

        if config.strict_gold_validation and config.gold_schema is None:
            raise SchemaValidationError(
                f"Pipeline '{config.name}' requires Gold schema when "
                f"strict_gold_validation=True. Define gold_schema in config."
            )

        if config.gold_schema is None:
            self.logger.warning(
                "gold_schema_missing",
                pipeline=config.name,
                message="Gold schema not defined. Validation skipped.",
            )
```

### 4. Feature Flag для миграции

Feature flag `strict_gold_validation` позволяет:

1. **Постепенную миграцию**: Существующие пайплайны продолжают работать
2. **Явный opt-in**: Новые пайплайны включают строгую валидацию
3. **Тестирование**: Можно включить в staging до production

**План миграции:**

| Фаза | Действие | Срок |
|------|----------|------|
| 1 | Добавить `strict_gold_validation` flag | Сейчас |
| 2 | Определить Gold-схемы для всех пайплайнов | - |
| 3 | Включить `strict_gold_validation=True` поэтапно | - |
| 4 | Сделать `strict_gold_validation=True` по умолчанию | - |

### 5. Конфигурация пайплайна

```yaml
# configs/pipelines/chembl/activity.yaml
pipeline:
  name: chembl_activity
  provider: chembl
  entity: activity
  strict_gold_validation: true

gold_schema:
  fields:
    - name: activity_id
      type: int64
      nullable: false
    - name: assay_chembl_id
      type: string
      nullable: false
    - name: molecule_chembl_id
      type: string
      nullable: false
    - name: standard_value
      type: float64
      nullable: true
    - name: standard_units
      type: string
      nullable: true
    - name: standard_type
      type: string
      nullable: true
```

### 6. Исключение ошибок

Новый тип исключения для валидации схем:

```python
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
```

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

### 4. Feature Flag минимизирует риск

Постепенное включение:
- Нет breaking changes для существующих пайплайнов
- Можно откатить на уровне конфигурации
- Не требует code changes для rollback

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
        self._pandera_schema = self._build_pandera_schema(schema)

    def validate(self, df: pl.DataFrame) -> ValidationResult:
        """Валидация DataFrame против Gold-схемы."""
        try:
            self._pandera_schema.validate(df.to_pandas())
            return ValidationResult(valid=True)
        except pa.errors.SchemaError as e:
            return ValidationResult(valid=False, errors=e.failure_cases)
```

### Тестирование

```python
# tests/unit/application/test_gold_validation.py

def test_strict_validation_fails_without_schema():
    """strict_gold_validation=True без схемы должен падать."""
    config = PipelineConfig(
        name="test_pipeline",
        provider="test",
        entity="test",
        strict_gold_validation=True,
        gold_schema=None,
    )
    context = create_test_context(config)
    pipeline = TestPipeline()

    with pytest.raises(SchemaValidationError) as exc_info:
        await pipeline.validate_gold_schema(context)

    assert "requires Gold schema" in str(exc_info.value)


def test_non_strict_validation_warns_without_schema(caplog):
    """strict_gold_validation=False без схемы должен логировать warning."""
    config = PipelineConfig(
        name="test_pipeline",
        provider="test",
        entity="test",
        strict_gold_validation=False,
        gold_schema=None,
    )
    context = create_test_context(config)
    pipeline = TestPipeline()

    await pipeline.validate_gold_schema(context)

    assert "gold_schema_missing" in caplog.text
```

## Alternatives Considered

### 1. Всегда требовать Gold-схему

Отклонено потому что:
- Breaking change для всех существующих пайплайнов
- Требует одновременного обновления всех конфигов
- Высокий риск при деплое

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
- **Безопасная миграция**: Feature flag позволяет постепенное внедрение
- **Тестируемость**: Можно unit-тестировать валидацию

### Negative

- **Дополнительная конфигурация**: Каждый пайплайн требует gold_schema
- **Начальные усилия**: Нужно определить схемы для существующих пайплайнов
- **Сложность**: Дополнительный слой валидации в pipeline

## Related ADRs

- [ADR-002](ADR-002-medallion-architecture.md): Medallion Architecture (Gold layer definition)
- [ADR-016](ADR-016-error-handling-strategy.md): Error Handling Strategy (error classification)
- [ADR-017](ADR-017-observability-architecture.md): Observability Architecture (logging integration)
