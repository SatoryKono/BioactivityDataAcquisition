# 00 TestItem ChEMBL Overview

## Описание

`TestItemChemblPipeline` — класс пайплайна ChEMBL для тестовых элементов, реализующий сбор данных по **test item** (молекулы/образцы) из ChEMBL с последующим обогащением через PubChem.

## Модуль

`src/bioetl/pipelines/chembl/testitem/run.py`

## Наследование

Пайплайн наследуется от `ChemblBasePipeline` и использует общую инфраструктуру ChEMBL-пайплайнов. Реализует ETL конвейер с кастомной трансформацией (обогащение через PubChem).

## Основные методы

### `__init__(self, ...)`

Инициализирует пайплайн с конфигурацией и опциональными параметрами.

### `build_descriptor(self)`

Построить дескриптор извлечения данных для testitem из ChEMBL.

### `pre_transform(self, df: pd.DataFrame) -> pd.DataFrame`

Выполняет предварительную трансформацию данных перед основной стадией transform. Используется для подготовки данных к обогащению, включая нормализацию InChI ключей и молекулярных свойств.

### `transform(self, df: pd.DataFrame, options: StageExecutionOptions) -> pd.DataFrame`

Применяет трансформацию данных testitem с обогащением через PubChem. Переопределяет базовую трансформацию для добавления данных из PubChem, включая молекулярные свойства и структурные данные.

### `validate(self, df: pd.DataFrame, options: StageExecutionOptions) -> pd.DataFrame`

Выполняет валидацию данных testitem. Переопределяет базовую валидацию для добавления специфичных проверок, включая валидацию по `TestItemSchema`.

### `save_results(self, df: pd.DataFrame, artifacts: WriteArtifacts, options: StageExecutionOptions) -> WriteResult`

Сохраняет результаты пайплайна testitem с учётом специфики сущности и обогащения данными PubChem.

## Обогащение данными PubChem

Пайплайн обогащает данные testitem информацией из PubChem:

- Молекулярные свойства
- Структурные данные
- Идентификаторы соединений

## Related Components

- **ChemblBasePipeline**: базовый класс для ChEMBL-пайплайнов (см. `docs/02-pipelines/chembl/common/05-chembl-base-pipeline.md`)
- **ChemblWriteService**: сервис записи для ChEMBL-пайплайнов (см. `docs/02-pipelines/chembl/common/04-chembl-write-service.md`)
- **PubChemClient**: клиент для PubChem (см. `docs/02-pipelines/clients/02-pubchem-client.md`)
- **TestItemSchema**: схема валидации (см. `docs/02-pipelines/schemas/01-testitem-schema.md`)
- **TestitemPipelineOptions**: параметры CLI (см. `docs/02-pipelines/chembl/testitem/03-testitem-pipeline-options.md`)

