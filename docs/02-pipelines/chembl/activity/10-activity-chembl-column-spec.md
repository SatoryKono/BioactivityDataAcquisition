# 10 Activity ChEMBL Column Spec

## Описание

`ColumnNormalizationSpec` — спецификация нормализации для одной колонки. Описывает атрибуты столбца: целевой тип данных (`dtype`), значение по умолчанию (`default`), а также опциональную трансформацию (функцию для преобразования значений). Эти объекты используются `BaseChemblNormalizer` для последовательной обработки каждой колонки.

## Модуль

`bioetl/clients/chembl` (спецификации колонок)

## Структура

ColumnNormalizationSpec является dataclass и содержит следующие поля:

- `name: str` — имя колонки
- `dtype: type` — целевой тип данных для колонки
- `default: Any | None` — значение по умолчанию для отсутствующих данных
- `transformer: Callable | None` — опциональная функция трансформации значений

## Использование

Спецификации используются для:

- Описания правил нормализации каждой колонки
- Приведения типов данных к требуемому формату
- Заполнения отсутствующих значений
- Применения кастомных трансформаций

## Пример

```python
spec = ColumnNormalizationSpec(
    name="activity_id",
    dtype=int,
    default=None,
    transformer=lambda x: int(x) if x is not None else None
)
```

## Related Components

- **BaseChemblNormalizer**: использует спецификации для нормализации колонок (см. `docs/02-pipelines/chembl/activity/08-base-chembl-normalizer.md`)
- **ActivityNormalizer**: создаёт спецификации для колонок активности (см. `docs/02-pipelines/chembl/activity/05-activity-chembl-normalizer.md`)

