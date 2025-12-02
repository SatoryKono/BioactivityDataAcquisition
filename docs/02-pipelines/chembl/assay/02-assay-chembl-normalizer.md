# 02 Assay ChEMBL Normalizer

## Описание

`AssayNormalizer` — нормализатор данных assay. Предназначен для приведения и очистки колонок ассая (в т.ч. обработки вложенных параметров), чтобы привести DataFrame к целевому виду.

## Модуль

`src/bioetl/pipelines/chembl/assay/normalizers.py`

## Основной метод

### `normalize(self, df: pd.DataFrame) -> pd.DataFrame`

Нормализует DataFrame с данными assay, приводя колонки к целевому виду.

**Параметры:**
- `df` — DataFrame с данными assay

**Процесс:**
1. Обработка вложенных параметров
2. Очистка и нормализация значений колонок
3. Приведение типов данных

**Возвращает:** нормализованный DataFrame.

## Использование

Нормализатор используется в `ChemblAssayPipeline` для обработки данных перед валидацией:

```python
from bioetl.pipelines.chembl.assay.normalizers import AssayNormalizer

normalizer = AssayNormalizer()
normalized_df = normalizer.normalize(df)
```

## Related Components

- **ChemblAssayPipeline**: использует нормализатор для обработки данных (см. `docs/02-pipelines/chembl/assay/00-assay-chembl-overview.md`)
- **AssaySchema**: схема валидации данных assay (см. `docs/02-pipelines/schemas/30-assay-schema.md`)

