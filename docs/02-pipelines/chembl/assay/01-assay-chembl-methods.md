# 01 Assay ChEMBL Methods

## Описание

Документ описывает приватные методы `ChemblAssayPipeline`, используемые для обработки данных assay и обеспечения целостности данных.

## Внутренние методы

### `_normalize_nested_parameters(self, df: pd.DataFrame) -> pd.DataFrame`

Нормализует вложенные параметры assay в DataFrame, приводя их к структурированному виду.

**Параметры:**
- `df` — DataFrame с данными assay

**Процесс:**
1. Извлечение вложенных параметров из JSON-полей
2. Развёртывание вложенных структур в плоские колонки
3. Нормализация значений параметров

**Возвращает:** DataFrame с нормализованными параметрами.

### `_ensure_assay_class_mapping(self, df: pd.DataFrame) -> pd.DataFrame`

Обеспечивает соответствие assay class в DataFrame, добавляя недостающие маппинги.

**Параметры:**
- `df` — DataFrame с данными assay

**Процесс:**
1. Проверка наличия поля `assay_class`
2. Применение маппинга стандартных значений assay class
3. Заполнение отсутствующих значений значениями по умолчанию

**Возвращает:** DataFrame с корректными маппингами assay class.

### `_ensure_target_integrity(self, df: pd.DataFrame) -> pd.DataFrame`

Проверяет и обеспечивает целостность данных target в DataFrame.

**Параметры:**
- `df` — DataFrame с данными assay

**Процесс:**
1. Проверка наличия обязательных полей target
2. Валидация идентификаторов target
3. Обработка отсутствующих или некорректных значений

**Возвращает:** DataFrame с проверенной целостностью target.

## Related Components

- **ChemblAssayPipeline**: основной пайплайн для assay (см. `docs/02-pipelines/chembl/assay/00-assay-chembl-overview.md`)
- **AssaySchema**: схема валидации данных assay (см. `docs/02-pipelines/schemas/04-assay-schema.md`)

