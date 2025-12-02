# 01 TestItem ChEMBL Methods

## Описание

Документ описывает приватные методы `TestItemChemblPipeline`, используемые для обработки данных тестовых элементов и обогащения через PubChem.

## Внутренние методы

### `_canonicalize_inchikey(self, df: pd.DataFrame) -> pd.DataFrame`

Канонизирует InChI ключи в DataFrame для обеспечения единообразия идентификаторов молекул.

**Параметры:**
- `df` — DataFrame с данными testitem

**Процесс:**
1. Извлечение InChI ключей из исходных данных
2. Нормализация формата InChI ключей
3. Удаление дубликатов и невалидных значений

**Возвращает:** DataFrame с канонизированными InChI ключами.

### `_normalize_molecule_properties(self, df: pd.DataFrame) -> pd.DataFrame`

Нормализует молекулярные свойства в DataFrame, приводя их к стандартным единицам измерения и форматам.

**Параметры:**
- `df` — DataFrame с данными testitem

**Процесс:**
1. Нормализация молекулярной массы
2. Приведение значений к стандартным единицам
3. Валидация диапазонов значений

**Возвращает:** DataFrame с нормализованными молекулярными свойствами.

### `_enrich_with_pubchem(self, df: pd.DataFrame) -> pd.DataFrame`

Обогащает DataFrame данными из PubChem, добавляя молекулярные свойства, структурные данные и идентификаторы соединений.

**Параметры:**
- `df` — DataFrame с данными testitem

**Процесс:**
1. Извлечение идентификаторов для запроса PubChem
2. Выполнение запросов к PubChem API через `PubChemClient`
3. Объединение полученных данных с исходным DataFrame
4. Обработка отсутствующих данных (fallback)

**Возвращает:** DataFrame, обогащённый данными из PubChem.

## Related Components

- **TestItemChemblPipeline**: основной пайплайн для testitem (см. `docs/02-pipelines/chembl/testitem/00-testitem-chembl-overview.md`)
- **PubChemClient**: клиент для PubChem API (см. `docs/02-pipelines/clients/20-pubchem-client.md`)

