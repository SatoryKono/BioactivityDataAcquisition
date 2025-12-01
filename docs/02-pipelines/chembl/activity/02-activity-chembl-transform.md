# 02 Activity ChEMBL Transform

## Описание

`ActivityTransformer` — стадия Transform для пайплайна ChEMBL Activity. Выполняет трансформацию извлечённых данных: обогащение доменными полями, нормализация значений и типов данных, приведение к единому формату.

## Модуль

`bioetl/pipelines/chembl/activity/stages.py`

## Основной метод

### `transform(self, df: pd.DataFrame) -> pd.DataFrame`

Трансформирует извлечённые данные активности.

**Процесс трансформации:**

1. Обогащение доменными полями: добавление полей через `_domain_enrich` (например, `chembl_release`)
2. Нормализация данных: применение `ActivityNormalizer` для нормализации значений и типов
3. Приведение к схеме: обеспечение соответствия структуры данных целевой схеме

**Возвращает:** трансформированный DataFrame с нормализованными данными.

## Внутренние методы

### `_domain_enrich(self, df: pd.DataFrame) -> pd.DataFrame`

Добавляет доменные поля в DataFrame. Например, добавляет поле `chembl_release`, если оно не было извлечено из API, используя значение из конфигурации.

## Нормализация

Трансформация использует `ActivityNormalizer` для:
- Нормализации типов данных (строки, числа, даты)
- Приведения значений к стандартным единицам измерения
- Обработки NULL-значений
- Валидации форматов идентификаторов

## Related Components

- **ActivityNormalizer**: нормализатор данных активности (см. `docs/02-pipelines/chembl/activity/05-activity-chembl-normalizer.md`)
- **BaseChemblNormalizer**: базовый нормализатор для ChEMBL (см. `docs/02-pipelines/chembl/activity/08-base-chembl-normalizer.md`)

