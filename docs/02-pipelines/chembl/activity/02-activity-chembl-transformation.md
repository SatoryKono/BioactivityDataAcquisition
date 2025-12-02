# 02 Activity ChEMBL Transformation

## Description

`ActivityTransformer` — класс этапа трансформации для активности ChEMBL. Нормализует и обогащает извлечённые данные (например, добавляет номер релиза ChEMBL). Наследуется от `StageABC` и реализует интерфейс стадии трансформации.

## Module

`src/bioetl/pipelines/chembl/activity/stages.py`

## Inheritance

Класс наследуется от `StageABC` и реализует интерфейс стадии трансформации данных.

## Main Method

### `transform(self, df: pd.DataFrame) -> pd.DataFrame`

Трансформирует извлечённые данные активности.

**Transformation Process:**

1. Обогащение доменными полями: добавление полей через `_domain_enrich` (например, `chembl_release`)
2. Нормализация данных: применение `ActivityNormalizer` для нормализации значений и типов
3. Приведение к схеме: обеспечение соответствия структуры данных целевой схеме

**Returns:** трансформированный DataFrame с нормализованными данными.

## Data Normalization

### ActivityNormalizer

`ActivityNormalizer` — утилита нормализации данных активности ChEMBL. Оборачивает общий нормализатор ChEMBL (`BaseChemblNormalizer`) с настроенными спецификациями колонок для активности, применяя его к DataFrame результатов. Обеспечивает приведение типов, заполнение значений по умолчанию и генерацию бизнес-ключей согласно схеме.

**Module:** `bioetl/pipelines/chembl/activity/normalizers.py`

**Main Method:**

#### `normalize(self, df_raw: pd.DataFrame) -> pd.DataFrame`

Применяет нормализацию к сырому DataFrame результатов извлечения.

**Parameters:**
- `df_raw` — сырой DataFrame с данными активности

**Normalization Process:**

1. Применение спецификаций: использование предварительно созданного `_ACTIVITY_NORMALIZER` с настроенными спецификациями колонок
2. Преобразование типов: приведение колонок к требуемым типам данных
3. Заполнение значений: установка значений по умолчанию для отсутствующих данных
4. Генерация ключей: вычисление бизнес-ключей и хешей строк при необходимости

**Returns:** очищенный и выровненный со схемой DataFrame.

### Column Normalization Specification

`ColumnNormalizationSpec` — спецификация нормализации для одной колонки. Описывает атрибуты столбца: целевой тип данных (`dtype`), значение по умолчанию (`default`), а также опциональную трансформацию (функцию для преобразования значений). Эти объекты используются `BaseChemblNormalizer` для последовательной обработки каждой колонки.

**Module:** `bioetl/clients/chembl` (спецификации колонок)

**Structure:**

ColumnNormalizationSpec является dataclass и содержит следующие поля:

- `name: str` — имя колонки
- `dtype: type` — целевой тип данных для колонки
- `default: Any | None` — значение по умолчанию для отсутствующих данных
- `transformer: Callable | None` — опциональная функция трансформации значений

**Usage:**

Спецификации используются для:
- Описания правил нормализации каждой колонки
- Приведения типов данных к требуемому формату
- Заполнения отсутствующих значений
- Применения кастомных трансформаций

**Example:**

```python
spec = ColumnNormalizationSpec(
    name="activity_id",
    dtype=int,
    default=None,
    transformer=lambda x: int(x) if x is not None else None
)
```

## Internal Methods

### `_domain_enrich(self, df: pd.DataFrame) -> pd.DataFrame`

Добавляет доменные поля в DataFrame. Например, добавляет поле `chembl_release`, если оно не было извлечено из API, используя значение из конфигурации.

## Normalization Features

Трансформация использует `ActivityNormalizer` для:
- Нормализации типов данных (строки, числа, даты)
- Приведения значений к стандартным единицам измерения
- Обработки NULL-значений
- Валидации форматов идентификаторов

## Related Components

- **BaseChemblNormalizer**: базовый нормализатор для всех ChEMBL-пайплайнов (см. `../common/00-base-chembl-normalizer.md`)
- **TransformerABC**: transformation contract (см. `docs/reference/abc/26-transformer-abc.md`)
- **ColumnNormalizationSpec**: спецификация нормализации колонки (см. выше)
