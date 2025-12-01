# 05 Activity ChEMBL Normalizer

## Описание

`ActivityNormalizer` — утилита нормализации данных активности ChEMBL. Оборачивает общий нормализатор ChEMBL (`BaseChemblNormalizer`) с настроенными спецификациями колонок для активности, применяя его к DataFrame результатов. Обеспечивает приведение типов, заполнение значений по умолчанию и генерацию бизнес-ключей согласно схеме.

## Модуль

`bioetl/pipelines/chembl/activity/normalizers.py`

## Основной метод

### `normalize(self, df_raw: pd.DataFrame) -> pd.DataFrame`

Применяет нормализацию к сырому DataFrame результатов извлечения.

**Параметры:**
- `df_raw` — сырой DataFrame с данными активности

**Процесс нормализации:**

1. Применение спецификаций: использование предварительно созданного `_ACTIVITY_NORMALIZER` с настроенными спецификациями колонок
2. Преобразование типов: приведение колонок к требуемым типам данных
3. Заполнение значений: установка значений по умолчанию для отсутствующих данных
4. Генерация ключей: вычисление бизнес-ключей и хешей строк при необходимости

**Возвращает:** очищенный и выровненный со схемой DataFrame.

## Спецификации колонок

Нормализатор использует `ColumnNormalizationSpec` для описания правил нормализации каждой колонки:

- Целевой тип данных (`dtype`)
- Значение по умолчанию (`default`)
- Опциональная функция трансформации

## Related Components

- **BaseChemblNormalizer**: базовый нормализатор для ChEMBL (см. `docs/02-pipelines/chembl/activity/08-base-chembl-normalizer.md`)
- **ColumnNormalizationSpec**: спецификация нормализации колонки (см. `docs/02-pipelines/chembl/activity/10-activity-chembl-column-spec.md`)
- **ActivityTransformer**: использует нормализатор для трансформации данных (см. `docs/02-pipelines/chembl/activity/02-activity-chembl-transform.md`)

