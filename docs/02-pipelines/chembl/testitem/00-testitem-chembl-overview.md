# 00 TestItem ChEMBL Overview

## Описание

`TestItemChemblPipeline` — скелет пайплайна "testitem" для тестовых веществ, включает обогащение данными PubChem. Реализует ETL конвейер с кастомной трансформацией (обогащение через PubChem).

## Модуль

`src/bioetl/pipelines/chembl/testitem/run.py`

## Наследование

Пайплайн наследуется от `PipelineBase` и использует общую инфраструктуру ChEMBL-пайплайнов.

## Основные методы

### `pre_transform(self, df: pd.DataFrame) -> pd.DataFrame`

Выполняет предварительную трансформацию данных перед основной стадией transform. Используется для подготовки данных к обогащению.

### `transform(self, df: pd.DataFrame, options: StageExecutionOptions) -> pd.DataFrame`

Применяет трансформацию данных testitem с обогащением через PubChem. Переопределяет базовую трансформацию для добавления данных из PubChem.

### `validate(self, df: pd.DataFrame, options: StageExecutionOptions) -> pd.DataFrame`

Выполняет валидацию данных testitem. Переопределяет базовую валидацию для добавления специфичных проверок.

### `save_results(self, df: pd.DataFrame, artifacts: WriteArtifacts, options: StageExecutionOptions) -> WriteResult`

Сохраняет результаты пайплайна testitem с учётом специфики сущности и обогащения данными PubChem.

## Обогащение данными PubChem

Пайплайн обогащает данные testitem информацией из PubChem:
- Молекулярные свойства
- Структурные данные
- Идентификаторы соединений

## Related Components

- **PipelineBase**: базовый класс пайплайнов (см. `docs/02-pipelines/00-pipeline-base.md`)
- **ChemblWriteService**: сервис записи для ChEMBL-пайплайнов (см. `docs/02-pipelines/chembl/17-chembl-write-service.md`)
- **PubChemClient**: клиент для PubChem (см. `docs/02-pipelines/clients/20-pubchem-client.md`)

