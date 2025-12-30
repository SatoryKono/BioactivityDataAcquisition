# Неиспользуемые Domain Services: Назначение и План Интеграции

**Дата:** 2025-12-30
**Статус:** Запланировано

---

## 1. Обзор Сервисов

В domain-слое проекта BioETL есть 4 сервиса, которые покрыты тестами, но не интегрированы в продакшн-пайплайны:

| Сервис | Строк | Назначение | Тесты |
|--------|-------|------------|-------|
| `NormalizationService` | 385 | Фасад для нормализации биоактивных данных | ✅ `tests/unit/domain/services/test_normalization_service.py` |
| `ActivityAggregator` | 359 | Агрегация множественных измерений | ✅ `tests/unit/domain/services/test_activity_aggregator.py` |
| `UnitConverter` | 221 | Конвертация единиц (nM, µM, mM) | ✅ `tests/unit/domain/services/test_unit_converter.py` |
| `ValueValidator` | 296 | Валидация диапазонов значений | ✅ `tests/unit/domain/services/test_value_validator.py` |

**Активно используется:**
- `IdentityService` — генерация entity_id и content_hash (используется всеми трансформерами)

---

## 2. Детальное Описание

### 2.1. UnitConverter

**Файл:** `src/bioetl/domain/services/unit_converter.py`

**Назначение:** Конвертация между единицами концентрации (nM, µM, mM, M) и вычисление pChEMBL значений.

**Ключевые методы:**
```python
class UnitConverter:
    def convert(value: float, from_unit: str, to_unit: str) -> float
    def to_concentration(value: float, unit: str) -> Concentration
    def to_pchembl(concentration: Concentration) -> PChemblValue | None
    def normalize_unit(unit: str) -> str  # "uM" -> "µM"
```

**Пример использования:**
```python
converter = UnitConverter()
result = converter.convert(100.0, "nM", "µM")  # 0.1
pchembl = converter.to_pchembl(converter.to_concentration(100.0, "nM"))  # 7.00
```

### 2.2. ValueValidator

**Файл:** `src/bioetl/domain/services/value_validator.py`

**Назначение:** Валидация биоактивных значений на соответствие ожидаемым диапазонам для разных типов измерений.

**Ключевые методы:**
```python
class ValueValidator:
    def validate_ic50(value: float, unit: str) -> ValidationResult
    def validate_ki(value: float, unit: str) -> ValidationResult
    def validate_pchembl(value: float) -> ValidationResult
    def is_outlier(value: float, activity_type: str) -> bool
```

**Пример использования:**
```python
validator = ValueValidator()
result = validator.validate_ic50(1000.0, "nM")
if not result.is_valid:
    print(result.message)  # "IC50 value outside expected range (1pM - 100µM)"
```

### 2.3. ActivityAggregator

**Файл:** `src/bioetl/domain/services/activity_aggregator.py`

**Назначение:** Агрегация множественных измерений одной активности (например, несколько IC50 для одной молекулы/мишени).

**Ключевые методы:**
```python
class ActivityAggregator:
    def aggregate(activities: Sequence[ActivityMeasurement]) -> AggregatedActivity
    def compute_median(values: Sequence[float]) -> float
    def compute_geometric_mean(values: Sequence[float]) -> float
    def detect_outliers(values: Sequence[float]) -> list[int]
```

**Пример использования:**
```python
aggregator = ActivityAggregator()
measurements = [
    ActivityMeasurement(value=100.0, unit="nM", activity_type="IC50"),
    ActivityMeasurement(value=120.0, unit="nM", activity_type="IC50"),
    ActivityMeasurement(value=95.0, unit="nM", activity_type="IC50"),
]
result = aggregator.aggregate(measurements)
print(result.median_value)  # ~100.0
print(result.count)  # 3
```

### 2.4. NormalizationService

**Файл:** `src/bioetl/domain/services/normalization_service.py`

**Назначение:** Фасад, объединяющий UnitConverter, ValueValidator и ActivityAggregator для полной нормализации биоактивных данных.

**Ключевые методы:**
```python
class NormalizationService:
    def normalize_activity(
        value: float,
        unit: str,
        activity_type: str
    ) -> NormalizationResult

    def normalize_and_aggregate(
        activities: Sequence[RawActivity]
    ) -> AggregatedNormalizationResult
```

**Пример использования:**
```python
config = NormalizationConfig(
    target_unit="nM",
    potency_threshold=6.0,  # pChEMBL >= 6 считается potent
)
service = NormalizationService(config)

result = service.normalize_activity(100.0, "nM", "IC50")
print(result.value)      # 100.0
print(result.unit)       # "nM"
print(result.pchembl)    # 7.0
print(result.is_potent)  # True (pChEMBL >= 6)
print(result.is_valid)   # True
```

---

## 3. План Интеграции

### 3.1. Точки Интеграции

| Пайплайн | Сервис | Место Интеграции | Описание |
|----------|--------|------------------|----------|
| `chembl_activity` | `NormalizationService` | `ActivityTransformer.transform_record()` | Нормализация IC50/Ki/Kd значений |
| `pubchem_bioassay` | `UnitConverter` | `PubChemTransformer.transform_record()` | Конвертация единиц |
| Все | `ValueValidator` | `BaseTransformer._validate_record()` | DQ-валидация значений |
| Gold Layer | `ActivityAggregator` | `GoldWriter.write_gold()` | Агрегация дублирующихся измерений |

### 3.2. Этапы Внедрения

#### Этап 1: Интеграция в ActivityTransformer (2-3 часа)

**Файл:** `src/bioetl/application/pipelines/chembl/activity_transformer.py`

```python
# Текущая реализация
class ActivityTransformer(BaseChemblTransformer):
    def transform_record(self, raw: dict) -> Bioactivity:
        # ... просто маппинг полей ...

# Целевая реализация
class ActivityTransformer(BaseChemblTransformer):
    def __init__(
        self,
        identity: IdentityService,
        normalizer: NormalizationService,  # Добавить
    ):
        super().__init__(identity)
        self._normalizer = normalizer

    def transform_record(self, raw: dict) -> Bioactivity:
        # Нормализация значений
        if raw.get("standard_value") and raw.get("standard_units"):
            norm_result = self._normalizer.normalize_activity(
                value=raw["standard_value"],
                unit=raw["standard_units"],
                activity_type=raw.get("standard_type", ""),
            )
            raw["normalized_value"] = norm_result.value
            raw["normalized_unit"] = norm_result.unit
            raw["is_potent"] = norm_result.is_potent

            if not norm_result.is_valid:
                # Пометить для DQ
                raw["_dq_warn"] = True
                raw["_dq_message"] = norm_result.validation_message

        # ... остальная логика ...
```

#### Этап 2: Добавление в DI-контейнер (1 час)

**Файл:** `src/bioetl/composition/factories/pipeline_factory.py`

```python
def _create_activity_transformer() -> ActivityTransformer:
    return ActivityTransformer(
        identity=IdentityService(),
        normalizer=NormalizationService(NormalizationConfig()),
    )
```

#### Этап 3: Интеграция ActivityAggregator в Gold Layer (3-4 часа)

**Файл:** `src/bioetl/infrastructure/storage/gold_writer.py`

Для агрегации дублирующихся активностей при записи в Gold:

```python
def _aggregate_duplicates(
    self,
    df: pl.DataFrame,
    aggregator: ActivityAggregator,
) -> pl.DataFrame:
    """Агрегировать дублирующиеся измерения (molecule + target + assay)."""
    # Группировать по ключам
    # Применить aggregator для numeric полей
    # Вернуть агрегированный DataFrame
```

#### Этап 4: Добавление портов для DI (2 часа)

Создать порты для инъекции сервисов:

```python
# src/bioetl/domain/ports/normalization.py (уже существуют!)
class UnitConverterPort(Protocol):
    def convert(self, value: float, from_unit: str, to_unit: str) -> float: ...

class ValueValidatorPort(Protocol):
    def validate(self, value: float, activity_type: str) -> ValidationResult: ...
```

---

## 4. Оценка Трудозатрат

| Этап | Описание | Время |
|------|----------|-------|
| 1 | Интеграция в ActivityTransformer | 2-3 часа |
| 2 | Обновление DI-контейнера | 1 час |
| 3 | Интеграция в Gold Layer | 3-4 часа |
| 4 | Тесты и документация | 2 часа |
| **Итого** | | **8-10 часов** |

---

## 5. Рекомендация

**Рекомендуется интеграция**, так как:

1. Сервисы уже полностью реализованы и покрыты тестами
2. Нормализация биоактивных данных — ключевая бизнес-логика ETL
3. Порты уже определены в `domain/ports/normalization.py`
4. Интеграция улучшит качество данных в Gold Layer

**Альтернатива (НЕ рекомендуется):**
Удаление сервисов — потеря ~1260 строк протестированного кода.

---

## 6. Приоритет Интеграции

1. **Высокий**: `NormalizationService` + `UnitConverter` — основная нормализация
2. **Средний**: `ValueValidator` — DQ-валидация
3. **Низкий**: `ActivityAggregator` — агрегация в Gold (опционально)
